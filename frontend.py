import streamlit as st
import numpy as np
import pandas as pd
import pydeck as pdk
import json

st.set_page_config(page_title="AI Data Centre Heatmap MVP", layout="wide")

st.title("🇦🇺 Data Centres: Heatmap MVP")

mode = st.sidebar.selectbox("View", ["Dummy heatmap", "ABS GPKG map"]) 

if mode == "ABS GPKG map":
    # Lazy-import geopandas to avoid heavy deps when not needed
    import geopandas as gpd

    GPKG_PATH = r"C:\\Users\\User\\PythonProjects\\Govhack2025-Datacetnres\\abs_population_data\\32180_ERP_2024_SA2_GDA2020.gpkg"

    st.sidebar.write("GeoPackage settings")
    engine = st.sidebar.selectbox("Read engine", options=["pyogrio", "fiona"], index=0)

    # Discover available layers in the GeoPackage and let user select
    @st.cache_data(show_spinner=False)
    def list_layers(path, prefer_engine="pyogrio", refresh_key=0):
        """
        Try multiple strategies to list layers:
        1) pyogrio.list_layers
        2) fiona.listlayers
        Returns tuple of layer names; empty tuple if all fail.
        refresh_key is included to allow user-triggered refresh bypassing cache.
        """
        errors = []
        layers = []
        if prefer_engine == "pyogrio":
            # Try pyogrio first
            try:
                import pyogrio
                info = pyogrio.list_layers(path)
                layers = [i.name for i in info]
            except Exception as e:
                errors.append(f"pyogrio: {e}")
            # If still empty, try fiona
            if not layers:
                try:
                    import fiona
                    with fiona.Env():
                        layers = list(fiona.listlayers(path))
                except Exception as e:
                    errors.append(f"fiona: {e}")
        else:
            # Try fiona first
            try:
                import fiona
                with fiona.Env():
                    layers = list(fiona.listlayers(path))
            except Exception as e:
                errors.append(f"fiona: {e}")
            if not layers:
                try:
                    import pyogrio
                    info = pyogrio.list_layers(path)
                    layers = [i.name for i in info]
                except Exception as e:
                    errors.append(f"pyogrio: {e}")
        return tuple(layers), " | ".join(errors)

    # Allow user to refresh layer listing to avoid stale cache of empty results
    refresh = st.sidebar.button("Refresh layers")
    layers, list_err = list_layers(GPKG_PATH, prefer_engine=engine, refresh_key=1 if refresh else 0)
    if layers:
        layer_name = st.sidebar.selectbox("Select layer", options=("<first layer>",) + layers, index=0)
        if layer_name == "<first layer>":
            layer_name = ""
    else:
        warn_msg = "Could not list layers. Enter layer name manually."
        if list_err:
            warn_msg += f" Details: {list_err}"
        st.sidebar.warning(warn_msg)
        layer_name = st.sidebar.text_input("Layer name (blank = first layer)", value="")

    @st.cache_data(show_spinner=True)
    def load_gpkg(path, layer, engine):
        read_kwargs = {}
        # geopandas 1.0: engine can be 'pyogrio' or 'fiona'. Only pass when not None to avoid version quirks.
        if engine and engine.strip():
            read_kwargs["engine"] = engine
        if layer.strip() != "":
            read_kwargs["layer"] = layer
        gdf = gpd.read_file(path, **read_kwargs)
        try:
            gdf = gdf.to_crs(4326)
        except Exception:
            pass
        return gdf

    with st.spinner("Reading GeoPackage…"):
        try:
            gdf = load_gpkg(GPKG_PATH, layer_name, engine)
        except Exception as e:
            # Fallback: try alternate engine
            alt = "fiona" if engine == "pyogrio" else "pyogrio"
            st.warning(f"Primary read engine '{engine}' failed: {e}. Trying '{alt}'…")
            gdf = load_gpkg(GPKG_PATH, layer_name, alt)

    st.success(f"Loaded {len(gdf)} features. CRS: {gdf.crs}")
    # Diagnostics: warn if no geometries or all are empty
    try:
        non_empty = gdf.geometry.notna() & ~gdf.geometry.is_empty
        if non_empty.sum() == 0:
            st.warning("All geometries are empty or missing in the selected layer. Nothing to display.")
    except Exception:
        pass

    # Choose attribute for coloring
    numeric_cols = [c for c in gdf.columns if c != gdf.geometry.name and str(gdf[c].dtype).startswith(("int", "float"))]
    attr = st.sidebar.selectbox("Color by attribute", options=(numeric_cols or ["None"]))
    outlines_only = st.sidebar.checkbox("Show outlines only", value=False)

    geojson_obj = json.loads(gdf.to_json())

    def make_color(value, vmin, vmax):
        if attr == "None" or vmin is None or vmax is None or vmin == vmax or value is None:
            return [33, 158, 188, 120]
        t = (float(value) - vmin) / (vmax - vmin)
        t = max(0.0, min(1.0, t))
        r = int(253 * t + 33 * (1 - t))
        g = int(174 * t + 158 * (1 - t))
        b = int(97 * t + 188 * (1 - t))
        return [r, g, b, 140]

    vmin = vmax = None
    if attr != "None" and attr in gdf.columns:
        vmin = float(gdf[attr].min())
        vmax = float(gdf[attr].max())

    for feat in geojson_obj["features"]:
        val = feat["properties"].get(attr) if attr != "None" else None
        feat["properties"]["_fill_color"] = make_color(val, vmin, vmax)

    minx, miny, maxx, maxy = gdf.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    layer = pdk.Layer(
        "GeoJsonLayer",
        geojson_obj,
        stroked=True,
        filled=not outlines_only,
        get_fill_color="[33,158,188,200]" if outlines_only else "properties._fill_color",
        get_line_color=[20, 20, 20, 255],
        line_width_min_pixels=1.5,
        pickable=True,
        extruded=False,
    )

    # If bounds are degenerate (e.g., single point), fall back to a national view
    if not np.isfinite([center_lat, center_lon]).all() or (minx == maxx and miny == maxy):
        view_state = pdk.ViewState(latitude=-25.5, longitude=134.5, zoom=3)
    else:
        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=4)

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={"text": "{sa2_name_2021}\\n{sa4_name_2021}\\n{erp_2024}"},
        height=650,
        parameters={"cull": False},
    )

    st.pydeck_chart(r, use_container_width=True)

    with st.expander("Data preview"):
        st.dataframe(gdf.drop(columns=[gdf.geometry.name], errors="ignore").head(1000))
else:
    # --- Dummy heatmap mode (existing MVP) ---
    GRID_SIZE = 50

    # Fake dataset A (population density-like pattern)
    x, y = np.meshgrid(np.linspace(-10, 10, GRID_SIZE), np.linspace(-10, 10, GRID_SIZE))
    grid1 = np.exp(-(x**2 + y**2) / 20) * 100

    # Fake dataset B (renewable zones-like pattern)
    grid2 = (np.sin(x) + np.cos(y)) * 50 + 50

    # --- Step 2: Add sliders for weights ---
    st.sidebar.header("Adjust Weights")
    w1 = st.sidebar.slider("Weight Dataset A (Population)", 0.0, 1.0, 0.5, 0.1)
    w2 = st.sidebar.slider("Weight Dataset B (Energy)", 0.0, 1.0, 0.5, 0.1)

    # --- Step 3: Aggregate ---
    heatmap = w1 * grid1 + w2 * grid2

    # Flatten grid into a DataFrame for pydeck
    lats = np.linspace(-35, -25, GRID_SIZE)  # Example: lat band across Australia
    lons = np.linspace(130, 140, GRID_SIZE)  # Example: lon band across NT/SA
    lat_grid, lon_grid = np.meshgrid(lats, lons)
    df = pd.DataFrame({
        "lat": lat_grid.flatten(),
        "lon": lon_grid.flatten(),
        "value": heatmap.flatten()
    })

    # --- Step 4: Display heatmap ---
    layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["lon", "lat"],
        get_weight="value",
        radiusPixels=40,
        intensity=1,
        threshold=0.01,
    )

    view_state = pdk.ViewState(
        latitude=-30, longitude=135, zoom=4, pitch=0
    )

    r = pdk.Deck(layers=[layer], initial_view_state=view_state,
                 tooltip={"text": "Value: {value}"})

    st.pydeck_chart(r)
