
import pandas as pd
import numpy as np
from geoheat.engine import GeoCatalog, GeoJSONProcessor, GridSpec, LayerSpec, resample_points_to_grid

def build_engine(tmp_path=None):
    cat = GeoCatalog()
    cat.add("power", "data/points.geojson")
    cat.add("roads", "data/lines.geojson")
    cat.add("zones", "data/polygons.geojson")
    bounds = cat.combined_bounds_wgs()
    # small grid for tests
    grid = GridSpec(bounds=bounds, nx=25, ny=25)
    eng = GeoJSONProcessor()
    eng.attach_catalog(cat)
    return eng, grid

def test_points_sumk_layer():
    eng, grid = build_engine()
    spec = LayerSpec(
        source_id="power",
        geometry_type="point",
        mode="sum_k",
        filter_property={"featuretype":"Power Station"},
        weight_property="generationmw",
        dataset_weight=1.0,
        decay="exp",
        decay_params={"scale": 5000},
        k=2
    )
    df = eng.generate_layer_on_grid(grid, spec)
    assert set(df.columns) == {"lat", "lon", "value"}
    assert len(df) == grid.nx * grid.ny
    # values should be non-negative and finite
    assert np.isfinite(df["value"]).all()
    assert (df["value"] >= 0).all()

def test_lines_nearest_layer():
    eng, grid = build_engine()
    spec = LayerSpec(
        source_id="roads",
        geometry_type="line",
        mode="nearest",
        dataset_weight=1.0,
        decay="inverse",
        decay_params={"eps": 20.0, "power": 1.0}
    )
    df = eng.generate_layer_on_grid(grid, spec)
    assert len(df) == grid.nx * grid.ny
    assert np.isfinite(df["value"]).all()
    assert (df["value"] >= 0).all()

def test_polygons_mask_layer():
    eng, grid = build_engine()
    spec = LayerSpec(
        source_id="zones",
        geometry_type="polygon",
        mode="mask",
        filter_property={"zone":"ExistingBuilding"},
        dataset_weight=-1.0,
        mask_value=1.0
    )
    df = eng.generate_layer_on_grid(grid, spec)
    assert len(df) == grid.nx * grid.ny
    # some negatives where mask applies
    assert (df["value"] <= 0).any()

def test_linear_combination_multi():
    eng, grid = build_engine()
    layers = [
        LayerSpec(source_id="power", geometry_type="point", mode="sum_k",
                  filter_property={"featuretype":"Power Station"},
                  weight_property="generationmw", dataset_weight=0.7,
                  decay="exp", decay_params={"scale": 8000}, k=3),
        LayerSpec(source_id="roads", geometry_type="line", mode="nearest",
                  dataset_weight=0.3, decay="inverse", decay_params={"eps": 50, "power": 1.0}),
        LayerSpec(source_id="zones", geometry_type="polygon", mode="mask",
                  filter_property={"zone":"ExistingBuilding"}, dataset_weight=-1.0, mask_value=1.0),
    ]
    df = eng.generate_linear_combination_multi(grid, layers)
    assert len(df) == grid.nx * grid.ny
    assert np.isfinite(df["value"]).all()

def test_resampler_nearest_neighbor():
    # make a tiny 2x2 source grid
    src = pd.DataFrame({
        "lat":[-34.92, -34.90, -34.92, -34.90],
        "lon":[138.60, 138.60, 138.62, 138.62],
        "value":[1.0, 2.0, 3.0, 4.0]
    })
    # target grid covers same area but bigger
    grid = GridSpec(bounds=(138.60, -34.92, 138.62, -34.90), nx=10, ny=10)
    out = resample_points_to_grid(src, grid)
    assert len(out) == grid.nx * grid.ny
    # all values should be from the set {1,2,3,4}
    assert set(np.unique(out["value"])) <= {1.0,2.0,3.0,4.0}
