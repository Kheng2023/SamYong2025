
import json
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List, Callable, Literal

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import STRtree
from shapely.geometry import Point
from shapely.ops import unary_union
from pyproj import Transformer


# --------- decay functions ---------
def decay_inverse(d: np.ndarray, eps: float = 1.0, power: float = 1.0) -> np.ndarray:
    return 1.0 / np.power(d + eps, power)


def decay_exponential(d: np.ndarray, scale: float = 1000.0) -> np.ndarray:
    return np.exp(-d / max(scale, 1e-9))


def decay_linear_cutoff(d: np.ndarray, radius: float = 1000.0) -> np.ndarray:
    r = max(radius, 1e-9)
    out = 1.0 - (d / r)
    out[out < 0.0] = 0.0
    return out


DECAYS: Dict[str, Callable[..., np.ndarray]] = {
    "inverse": decay_inverse,
    "exp": decay_exponential,
    "linear": decay_linear_cutoff,
}


# --------- grid & sources ---------
@dataclass
class GridSpec:
    bounds: Tuple[float, float, float, float]  # lon/lat
    nx: int
    ny: int
    crs_wgs84: str = "EPSG:4326"
    crs_metric: str = "EPSG:3857"

    def axes(self):
        minx, miny, maxx, maxy = self.bounds
        xs = np.linspace(minx, maxx, self.nx)
        ys = np.linspace(miny, maxy, self.ny)
        return xs, ys

    def mesh(self):
        xs, ys = self.axes()
        lon_grid, lat_grid = np.meshgrid(xs, ys)
        return lon_grid, lat_grid


class GeoSource:
    def __init__(self, path: str, metric_crs: str = "EPSG:3857"):
        self.path = path
        self.gdf_wgs: gpd.GeoDataFrame = gpd.read_file(path)
        if self.gdf_wgs.crs is None or self.gdf_wgs.crs.to_string() != "EPSG:4326":
            self.gdf_wgs = self.gdf_wgs.set_crs("EPSG:4326", allow_override=True)

        self.bounds_wgs = tuple(self.gdf_wgs.total_bounds)
        self.metric_crs = metric_crs
        self.gdf_metric = self.gdf_wgs.to_crs(metric_crs)

        gm = self.gdf_metric
        self.points = gm[gm.geometry.geom_type.isin(["Point", "MultiPoint"])].explode(index_parts=False)
        self.lines = gm[gm.geometry.geom_type.isin(["LineString", "MultiLineString"])].explode(index_parts=False)
        self.polys = gm[gm.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].explode(index_parts=False)

        self.points_tree = STRtree(self.points.geometry.values) if not self.points.empty else None
        self.lines_tree = STRtree(self.lines.geometry.values) if not self.lines.empty else None
        self.polys_series = self.polys.geometry if not self.polys.empty else gpd.GeoSeries([], crs=metric_crs)


class GeoCatalog:
    def __init__(self, metric_crs: str = "EPSG:3857"):
        self.metric_crs = metric_crs
        self.sources: Dict[str, GeoSource] = {}

    def add(self, source_id: str, path: str):
        self.sources[source_id] = GeoSource(path, metric_crs=self.metric_crs)

    def combined_bounds_wgs(self) -> Tuple[float, float, float, float]:
        mins = []; maxs = []
        for s in self.sources.values():
            minx, miny, maxx, maxy = s.bounds_wgs
            mins.append((minx, miny)); maxs.append((maxx, maxy))
        if not mins:
            raise ValueError("No sources loaded.")
        minx = min(v[0] for v in mins)
        miny = min(v[1] for v in mins)
        maxx = max(v[0] for v in maxs)
        maxy = max(v[1] for v in maxs)
        return (minx, miny, maxx, maxy)


# --------- layer spec ---------
@dataclass
class LayerSpec:
    source_id: str
    geometry_type: Literal["point", "line", "polygon"]
    mode: str
    filter_property: Optional[Dict] = None
    weight_property: Optional[str] = None
    dataset_weight: float = 1.0
    decay: str = "exp"
    decay_params: Optional[Dict] = None
    k: int = 8
    mask_value: float = 1.0


# --------- engine ---------
class GeoJSONProcessor:
    def __init__(self, metric_crs: str = "EPSG:3857"):
        self.metric_crs = metric_crs
        self.catalog: Optional[GeoCatalog] = None
        self._to_metric = Transformer.from_crs("EPSG:4326", metric_crs, always_xy=True)
        self._to_wgs84 = Transformer.from_crs(metric_crs, "EPSG:4326", always_xy=True)

    def attach_catalog(self, catalog: GeoCatalog):
        self.catalog = catalog

    # helpers
    def _grid_pts_metric(self, gridspec: GridSpec):
        lon_grid, lat_grid = gridspec.mesh()
        x, y = self._to_metric.transform(lon_grid, lat_grid)
        pts = [Point(px, py) for px, py in zip(x.ravel(), y.ravel())]
        return lon_grid, lat_grid, pts

    def _filter_df(self, gdf: gpd.GeoDataFrame, flt: Optional[Dict]) -> gpd.GeoDataFrame:
        if not flt:
            return gdf
        out = gdf
        for k, v in flt.items():
            if k in out.columns:
                out = out[out[k] == v]
        return out

    # distance helpers
    def _nearest_distance(self, pts_grid, tree: STRtree) -> np.ndarray:
        idxs = tree.nearest(pts_grid)
        targets = [tree.geometries[i] for i in idxs]
        d = np.fromiter((p.distance(t) for p, t in zip(pts_grid, targets)), float, count=len(pts_grid))
        return d, np.asarray(idxs)

    # per-geom evaluators
    def _eval_points_layer(self, src: GeoSource, gridspec: GridSpec, spec: LayerSpec) -> np.ndarray:
        if src.points_tree is None:
            return np.zeros(gridspec.nx * gridspec.ny)
        pts_df = self._filter_df(src.points, spec.filter_property)
        if pts_df.empty:
            return np.zeros(gridspec.nx * gridspec.ny)

        tree = STRtree(pts_df.geometry.values)
        feat_w = None
        if spec.weight_property and spec.weight_property in pts_df.columns:
            feat_w = pd.to_numeric(pts_df[spec.weight_property], errors="coerce").fillna(0.0).values

        _, _, pts_grid = self._grid_pts_metric(gridspec)
        decay_fn = DECAYS.get(spec.decay, decay_exponential)

        if spec.mode == "nearest":
            d, idxs = self._nearest_distance(pts_grid, tree)
            vals = decay_fn(d, **(spec.decay_params or {}))
            if feat_w is not None:
                vals *= feat_w[idxs]
            return vals

        elif spec.mode == "sum_k":
            try:
                from scipy.spatial import cKDTree
                coords = np.array([(g.x, g.y) for g in tree.geometries])
                qcoords = np.array([(p.x, p.y) for p in pts_grid])
                kk = min(spec.k, len(coords)) if len(coords) else 0
                if kk == 0:
                    return np.zeros(len(pts_grid))
                dists, idxs = cKDTree(coords).query(qcoords, k=kk)
                if dists.ndim == 1:
                    dists = dists[:, None]; idxs = idxs[:, None]
                w = decay_fn(dists, **(spec.decay_params or {}))
                if feat_w is not None:
                    fw = feat_w[idxs]
                    return np.sum(w * fw, axis=1)
                return np.sum(w, axis=1)
            except Exception:
                d, idxs = self._nearest_distance(pts_grid, tree)
                vals = decay_fn(d, **(spec.decay_params or {}))
                if feat_w is not None:
                    vals *= feat_w[idxs]
                return vals
        else:
            raise ValueError(f"Unsupported points mode: {spec.mode}")

    def _eval_lines_layer(self, src: GeoSource, gridspec: GridSpec, spec: LayerSpec) -> np.ndarray:
        if src.lines_tree is None:
            return np.zeros(gridspec.nx * gridspec.ny)
        lines_df = self._filter_df(src.lines, spec.filter_property)
        if lines_df.empty:
            return np.zeros(gridspec.nx * gridspec.ny)

        tree = STRtree(lines_df.geometry.values)
        _, _, pts_grid = self._grid_pts_metric(gridspec)
        d, idxs = self._nearest_distance(pts_grid, tree)
        decay_fn = DECAYS.get(spec.decay, decay_exponential)
        vals = decay_fn(d, **(spec.decay_params or {}))
        if spec.weight_property and spec.weight_property in lines_df.columns:
            feat_w = pd.to_numeric(lines_df[spec.weight_property], errors="coerce").fillna(0.0).values
            vals *= feat_w[idxs]
        return vals

    def _eval_polygons_layer(self, src: GeoSource, gridspec: GridSpec, spec: LayerSpec) -> np.ndarray:
        polys_df = self._filter_df(src.polys, spec.filter_property)
        if polys_df.empty:
            return np.zeros(gridspec.nx * gridspec.ny)

        mode = spec.mode
        _, _, pts_grid = self._grid_pts_metric(gridspec)

        if mode == "mask":
            union = unary_union(polys_df.geometry.values)
            inside = np.fromiter((union.contains(p) for p in pts_grid), bool, count=len(pts_grid))
            vals = np.zeros(len(pts_grid)); vals[inside] = spec.mask_value
            return vals

        elif mode == "centroid":
            cents = polys_df.geometry.centroid
            tree = STRtree(cents.values)
            d, idxs = self._nearest_distance(pts_grid, tree)
            decay_fn = DECAYS.get(spec.decay, decay_exponential)
            vals = decay_fn(d, **(spec.decay_params or {}))
            if spec.weight_property and spec.weight_property in polys_df.columns:
                feat_w = pd.to_numeric(polys_df[spec.weight_property], errors="coerce").fillna(0.0).values
                vals *= feat_w[idxs]
            return vals

        elif mode == "boundary":
            bounds = polys_df.geometry.boundary
            tree = STRtree(bounds.values)
            d, idxs = self._nearest_distance(pts_grid, tree)
            decay_fn = DECAYS.get(spec.decay, decay_exponential)
            vals = decay_fn(d, **(spec.decay_params or {}))
            if spec.weight_property and spec.weight_property in polys_df.columns:
                feat_w = pd.to_numeric(polys_df[spec.weight_property], errors="coerce").fillna(0.0).values
                vals *= feat_w[idxs]
            return vals

        else:
            raise ValueError("Polygon mode must be one of: centroid | boundary | mask")

    def generate_layer_on_grid(self, gridspec: GridSpec, spec: LayerSpec) -> pd.DataFrame:
        if self.catalog is None:
            raise ValueError("No catalog attached. Call attach_catalog().")
        if spec.source_id not in self.catalog.sources:
            raise ValueError(f"Unknown source_id: {spec.source_id}")
        src = self.catalog.sources[spec.source_id]

        if spec.geometry_type == "point":
            vals = self._eval_points_layer(src, gridspec, spec)
        elif spec.geometry_type == "line":
            vals = self._eval_lines_layer(src, gridspec, spec)
        elif spec.geometry_type == "polygon":
            vals = self._eval_polygons_layer(src, gridspec, spec)
        else:
            raise ValueError(f"Unknown geometry_type: {spec.geometry_type}")

        lon_grid, lat_grid = gridspec.mesh()
        return pd.DataFrame({
            "lat": lat_grid.ravel(),
            "lon": lon_grid.ravel(),
            "value": spec.dataset_weight * vals.ravel(),
        })

    def generate_linear_combination_multi(self, gridspec: GridSpec, layers: List[LayerSpec]) -> pd.DataFrame:
        lon_grid, lat_grid = gridspec.mesh()
        acc = np.zeros(lon_grid.size, dtype=float)
        for spec in layers:
            df = self.generate_layer_on_grid(gridspec, spec)
            acc += df["value"].values
        return pd.DataFrame({"lat": lat_grid.ravel(), "lon": lon_grid.ravel(), "value": acc})


# --------- resampler for external gridded data ---------
def resample_points_to_grid(points_df: pd.DataFrame, gridspec: GridSpec) -> pd.DataFrame:
    from scipy.spatial import cKDTree
    lon_grid, lat_grid = gridspec.mesh()
    q = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])
    p = np.column_stack([points_df["lon"].values, points_df["lat"].values])
    kd = cKDTree(p)
    _, idx = kd.query(q, k=1)
    values = points_df["value"].values[idx]
    return pd.DataFrame({"lat": lat_grid.ravel(), "lon": lon_grid.ravel(), "value": values})
