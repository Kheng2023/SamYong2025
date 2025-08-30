import streamlit as st
import numpy as np
import pandas as pd
import pydeck as pdk
from pydeck.bindings.base_map_provider import BaseMapProvider
import json
import matplotlib.pyplot as plt
# Add these imports for tile server integration
import requests

st.set_page_config(page_title="AI Data Centre Heatmap MVP", layout="wide")

st.title("🇦🇺 Data Centres: Heatmap MVP")

mode = st.sidebar.selectbox("View", ["Dummy heatmap", "Power Stations", "GeoJSON Heatmaps"])

# if mode == "ABS GPKG map":
#     # Lazy-import geopandas to avoid heavy deps when not needed
#     import geopandas as gpd
#
#     GPKG_PATH = r"abs_population_data/32180_ERP_2024_SA2_GDA2020.gpkg"
#
#     st.sidebar.write("GeoPackage settings")
#     engine = st.sidebar.selectbox("Read engine", options=["pyogrio", "fiona"], index=0)
#
#     # Discover available layers in the GeoPackage and let user select
#     @st.cache_data(show_spinner=False)
#     def list_layers(path, prefer_engine="pyogrio", refresh_key=0):
#         """
#         Try multiple strategies to list layers:
#         1) pyogrio.list_layers
#         2) fiona.listlayers
#         Returns tuple of layer names; empty tuple if all fail.
#         refresh_key is included to allow user-triggered refresh bypassing cache.
#         """
#         errors = []
#         layers = []
#         if prefer_engine == "pyogrio":
#             # Try pyogrio first
#             try:
#                 import pyogrio
#                 info = pyogrio.list_layers(path)
#                 layers = [i.name for i in info]
#             except Exception as e:
#                 errors.append(f"pyogrio: {e}")
#             # If still empty, try fiona
#             if not layers:
#                 try:
#                     import fiona
#                     with fiona.Env():
#                         layers = list(fiona.listlayers(path))
#                 except Exception as e:
#                     errors.append(f"fiona: {e}")
#         else:
#             # Try fiona first
#             try:
#                 import fiona
#                 with fiona.Env():
#                     layers = list(fiona.listlayers(path))
#             except Exception as e:
#                 errors.append(f"fiona: {e}")
#             if not layers:
#                 try:
#                     import pyogrio
#                     info = pyogrio.list_layers(path)
#                     layers = [i.name for i in info]
#                 except Exception as e:
#                     errors.append(f"pyogrio: {e}")
#         return tuple(layers), " | ".join(errors)
#
#     # Allow user to refresh layer listing to avoid stale cache of empty results
#     refresh = st.sidebar.button("Refresh layers")
#     layers, list_err = list_layers(GPKG_PATH, prefer_engine=engine, refresh_key=1 if refresh else 0)
#     if layers:
#         layer_name = st.sidebar.selectbox("Select layer", options=("<first layer>",) + layers, index=0)
#         if layer_name == "<first layer>":
#             layer_name = ""
#     else:
#         warn_msg = "Could not list layers. Enter layer name manually."
#         if list_err:
#             warn_msg += f" Details: {list_err}"
#         st.sidebar.warning(warn_msg)
#         layer_name = st.sidebar.text_input("Layer name (blank = first layer)", value="")
#
#     @st.cache_data(show_spinner=True)
#     def load_gpkg(path, layer, engine):
#         read_kwargs = {}
#         # geopandas 1.0: engine can be 'pyogrio' or 'fiona'. Only pass when not None to avoid version quirks.
#         if engine and engine.strip():
#             read_kwargs["engine"] = engine
#         if layer.strip() != "":
#             read_kwargs["layer"] = layer
#         gdf = gpd.read_file(path, **read_kwargs)
#         try:
#             gdf = gdf.to_crs(4326)
#         except Exception:
#             pass
#         return gdf
#
#     with st.spinner("Reading GeoPackage…"):
#         try:
#             gdf = load_gpkg(GPKG_PATH, layer_name, engine)
#         except Exception as e:
#             # Fallback: try alternate engine
#             alt = "fiona" if engine == "pyogrio" else "pyogrio"
#             st.warning(f"Primary read engine '{engine}' failed: {e}. Trying '{alt}'…")
#             gdf = load_gpkg(GPKG_PATH, layer_name, alt)
#
#     st.success(f"Loaded {len(gdf)} features. CRS: {gdf.crs}")
#     # Diagnostics: warn if no geometries or all are empty
#     try:
#         non_empty = gdf.geometry.notna() & ~gdf.geometry.is_empty
#         if non_empty.sum() == 0:
#             st.warning("All geometries are empty or missing in the selected layer. Nothing to display.")
#     except Exception:
#         pass
#
#     # Choose attribute for coloring
#     numeric_cols = [c for c in gdf.columns if c != gdf.geometry.name and str(gdf[c].dtype).startswith(("int", "float"))]
#     attr = st.sidebar.selectbox("Color by attribute", options=(numeric_cols or ["None"]))
#     outlines_only = st.sidebar.checkbox("Show outlines only", value=False)
#
#     geojson_obj = json.loads(gdf.to_json())
#
#     def make_color(value, vmin, vmax):
#         if attr == "None" or vmin is None or vmax is None or vmin == vmax or value is None:
#             return [33, 158, 188, 120]
#         t = (float(value) - vmin) / (vmax - vmin)
#         t = max(0.0, min(1.0, t))
#         r = int(253 * t + 33 * (1 - t))
#         g = int(174 * t + 158 * (1 - t))
#         b = int(97 * t + 188 * (1 - t))
#         return [r, g, b, 140]
#
#     vmin = vmax = None
#     if attr != "None" and attr in gdf.columns:
#         vmin = float(gdf[attr].min())
#         vmax = float(gdf[attr].max())
#
#     for feat in geojson_obj["features"]:
#         val = feat["properties"].get(attr) if attr != "None" else None
#         feat["properties"]["_fill_color"] = make_color(val, vmin, vmax)
#
#     minx, miny, maxx, maxy = gdf.total_bounds
#     center_lat = (miny + maxy) / 2
#     center_lon = (minx + maxx) / 2
#
#     layer = pdk.Layer(
#         "GeoJsonLayer",
#         geojson_obj,
#         stroked=True,
#         filled=not outlines_only,
#         get_fill_color="[33,158,188,200]" if outlines_only else "properties._fill_color",
#         get_line_color=[20, 20, 20, 255],
#         line_width_min_pixels=1.5,
#         pickable=True,
#         extruded=False,
#     )
#
#     # If bounds are degenerate (e.g., single point), fall back to a national view
#     if not np.isfinite([center_lat, center_lon]).all() or (minx == maxx and miny == maxy):
#         view_state = pdk.ViewState(latitude=-25.5, longitude=134.5, zoom=3)
#     else:
#         view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=4)
#
#     r = pdk.Deck(
#         layers=[layer],
#         initial_view_state=view_state,
#         map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
#         tooltip={"text": "{sa2_name_2021}\\n{sa4_name_2021}\\n{erp_2024}"},
#         height=650,
#         parameters={"cull": False},
#     )
#
#     st.pydeck_chart(r, use_container_width=True)
#
#     with st.expander("Data preview"):
#         st.dataframe(gdf.drop(columns=[gdf.geometry.name], errors="ignore").head(1000))
# elif mode == "Tile Server Map":
#         st.subheader("Map Data from Tile Server")
#
#         tile_server_public = st.sidebar.text_input(
#             "Tile server URL (browser-accessible)",
#             value="http://localhost:8080",
#         )
#
#         style_url = f"{tile_server_public}/styles/basic/style.json"  # STYLE JSON
#
#         # Center on Zurich (your current demo tiles only cover Zurich)
#         view_state = pdk.ViewState(latitude=47.3769, longitude=8.5417, zoom=11)
#
#         # Add a tiny marker so we know WebGL is rendering even if basemap fails
#         sanity_layer = pdk.Layer(
#             "ScatterplotLayer",
#             data=[{"lon": 8.5417, "lat": 47.3769}],
#             get_position=["lon", "lat"],
#             get_radius=200,
#             pickable=True,
#         )
#
#         r = pdk.Deck(
#             layers=[sanity_layer],
#             map_style=style_url,
#             initial_view_state=view_state,
#             height=650,
#             map_provider=None,  # don’t force Mapbox with a custom style
#         )
#
#         st.pydeck_chart(r, use_container_width=True)
#

if mode == "Dummy heatmap":
    # --- Dummy heatmap mode (existing MVP) ---
    GRID_SIZE = 50

    # Fake dataset A (population density-like pattern)
    x, y = np.meshgrid(np.linspace(-10, 10, GRID_SIZE), np.linspace(-10, 10, GRID_SIZE))
    grid1 = np.exp(-(x**2 + y**2) / 20) * 100

    # Fake dataset B (renewable zones-like pattern)
    grid2 = (np.sin(x) + np.cos(y)) * 50 + 50

    # --- Step 2: Add sliders for weights ---
    st.sidebar.header("Adjust Weights")
    w1 = st.sidebar.slider("Weight Dataset A (Population)", 0.0, 1.0, 0.5, 0.01)
    w2 = st.sidebar.slider("Weight Dataset B (Energy)", 0.0, 1.0, 0.5, 0.01)

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

elif mode == "GeoJSON Heatmaps":
    st.subheader("Heatmaps from GeoJSON Files")

    # Add a selector for the heatmap type
    heatmap_type = st.sidebar.selectbox("Heatmap Type", ["Simple Heatmap", "Weighted Heatmap"])

    # Determine the file path based on the selection
    if heatmap_type == "Simple Heatmap":
        geojson_path = "output/simple_heatmap.geojson"
        st.write("Displaying Simple Heatmap")
    else:
        geojson_path = "output/weighted_heatmap.geojson"
        st.write("Displaying Weighted Heatmap")

    # Add controls for heatmap visualization
    st.sidebar.header("Heatmap Settings")
    radius_pixels = st.sidebar.slider("Radius (pixels)", 10, 100, 40)
    intensity = st.sidebar.slider("Intensity", 0.1, 5.0, 1.0, 0.1)
    threshold = st.sidebar.slider("Threshold", 0.01, 0.5, 0.01, 0.01)

    # Color scheme selection
    color_scheme = st.sidebar.selectbox(
        "Color Scheme", 
        ["Default", "Viridis", "Plasma", "Inferno", "Magma", "Cividis"]
    )

    # Normalization option
    normalize = st.sidebar.checkbox("Normalize Values", value=False)

    # Load the selected GeoJSON file
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        # Extract features
        features = geojson_data.get("features", [])
        st.write(f"Loaded {len(features)} data points from {geojson_path}")

        # Convert GeoJSON features to DataFrame for pydeck
        data_points = []
        for feature in features:
            props = feature.get("properties", {})
            value = props.get("value")
            # Handle null values
            if value is None:
                value = 0.0

            # Get coordinates from geometry
            coords = feature.get("geometry", {}).get("coordinates", [0, 0])
            if len(coords) >= 2:
                data_points.append({
                    "lon": coords[0],
                    "lat": coords[1],
                    "value": float(value)
                })

        # Create DataFrame
        df = pd.DataFrame(data_points)

        # Normalize values if requested
        if normalize and len(df) > 0:
            min_val = df['value'].min()
            max_val = df['value'].max()
            if max_val > min_val:  # Avoid division by zero
                df['normalized_value'] = (df['value'] - min_val) / (max_val - min_val)
                weight_column = 'normalized_value'
                st.info(f"Values normalized from range [{min_val:.2f}, {max_val:.2f}] to [0, 1]")
            else:
                weight_column = 'value'
        else:
            weight_column = 'value'

        # Define color map based on selection
        color_maps = {
            "Default": [[255, 255, 178], [254, 217, 118], [254, 178, 76], [253, 141, 60], [240, 59, 32], [189, 0, 38]],
            "Viridis": [[68, 1, 84], [72, 40, 120], [62, 83, 160], [49, 104, 142], [38, 130, 142], [31, 158, 137], [53, 183, 121], [109, 205, 89], [180, 222, 44], [253, 231, 37]],
            "Plasma": [[13, 8, 135], [75, 3, 161], [125, 3, 168], [168, 34, 150], [203, 70, 121], [229, 107, 93], [248, 148, 65], [253, 195, 40], [240, 249, 33]],
            "Inferno": [[0, 0, 4], [40, 12, 70], [101, 21, 110], [159, 42, 99], [212, 72, 66], [245, 125, 21], [250, 193, 39], [252, 255, 164]],
            "Magma": [[0, 0, 4], [34, 12, 64], [88, 24, 124], [142, 41, 121], [192, 67, 87], [230, 107, 45], [249, 165, 22], [253, 227, 124], [251, 252, 191]],
            "Cividis": [[0, 32, 76], [0, 42, 102], [0, 52, 110], [8, 64, 116], [20, 76, 120], [33, 88, 120], [46, 100, 120], [62, 112, 120], [82, 124, 118], [102, 136, 116], [124, 148, 112], [146, 162, 108], [171, 176, 104], [198, 192, 99], [226, 210, 97]]
        }

        # Get the selected color map or default if not found
        color_map = color_maps.get(color_scheme, color_maps["Default"])

        # Create heatmap layer with user-selected parameters
        layer = pdk.Layer(
            "HeatmapLayer",
            data=df,
            get_position=["lon", "lat"],
            get_weight=weight_column,
            radiusPixels=radius_pixels,
            intensity=intensity,
            threshold=threshold,
            colorRange=color_map,
        )

        # Set view state to Australia
        view_state = pdk.ViewState(
            latitude=-30, longitude=135, zoom=4, pitch=0
        )

        # Create and display the deck
        r = pdk.Deck(
            layers=[layer], 
            initial_view_state=view_state,
            tooltip={"text": "Value: {value}"}
        )

        st.pydeck_chart(r, use_container_width=True)

        # Show data statistics
        with st.expander("Data Statistics"):
            if len(df) > 0:
                # Calculate statistics
                min_val = df['value'].min()
                max_val = df['value'].max()
                mean_val = df['value'].mean()
                median_val = df['value'].median()
                non_zero = (df['value'] > 0).sum()

                # Create two columns for statistics display
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Total points:** {len(df)}")
                    st.write(f"**Non-zero points:** {non_zero} ({non_zero/len(df)*100:.1f}%)")
                    st.write(f"**Min value:** {min_val:.2f}")
                    st.write(f"**Max value:** {max_val:.2f}")

                with col2:
                    st.write(f"**Mean value:** {mean_val:.2f}")
                    st.write(f"**Median value:** {median_val:.2f}")
                    st.write(f"**Sum of values:** {df['value'].sum():.2f}")

                # Show histogram of values
                if non_zero > 0:
                    st.write("**Value Distribution (non-zero values only)**")
                    # Filter out zeros for better visualization
                    hist_data = df[df['value'] > 0]['value']
                    fig = plt.figure(figsize=(10, 4))
                    plt.hist(hist_data, bins=20)
                    plt.xlabel('Value')
                    plt.ylabel('Frequency')
                    st.pyplot(fig)
            else:
                st.write("No data points available for statistics.")

    except Exception as e:
        st.error(f"Error loading or processing GeoJSON file: {e}")
        st.write("Please check that the file exists and is properly formatted.")

elif mode == "Power Stations":
    st.subheader("Major Power Stations in Australia")

    # --- Load file
    import math
    with open("map_data/Major_Power_Stations.geo.json", "r", encoding="utf-8") as f:
        fc = json.load(f)

    feats = fc.get("features", [])
    st.write(f"Loaded features: {len(feats)}")

    # --- Extract points + quick QA
    pts = []
    out_of_range = 0
    for ft in feats:
        if not ft or ft.get("geometry", {}).get("type") != "Point":
            continue
        coords = ft["geometry"].get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        pts.append((lon, lat, ft))

        # Count obviously out-of-Australia points
        if not (110 <= (lon or 0) <= 155 and -45 <= (lat or 0) <= -10):
            out_of_range += 1

    st.write(f"Point features: {len(pts)} | Out-of-range (pre-fix): {out_of_range}")

    # --- Detect lat/lon swap and fix if needed (heuristic)
    # If most points are out-of-range but the swapped version falls in range, assume swap.
    if len(pts) > 0:
        in_range = sum(1 for lon, lat, _ in pts if 110 <= lon <= 155 and -45 <= lat <= -10)
        swapped_in_range = sum(1 for lon, lat, _ in pts if 110 <= lat <= 155 and -45 <= lon <= -10)
        swapped = swapped_in_range > in_range * 3 and swapped_in_range >= max(5, 0.5 * len(pts))
    else:
        swapped = False

    if swapped:
        st.warning("Detected probable lat/lon swap in data — auto-correcting.")
        for i, (lon, lat, ft) in enumerate(pts):
            pts[i] = (lat, lon, ft)  # swap
            ft["geometry"]["coordinates"] = [lat, lon]

    # --- Precompute radius safely + classify renewable vs non-renewable
    # Define renewable fuel types
    RENEWABLE_FUELS = {"solar", "wind", "hydro", "geothermal", "biomass", "biogas", "tidal", "wave"}

    total_valid = 0
    rows = []
    for lon, lat, ft in pts:
        props = ft.setdefault("properties", {})
        try:
            cap = float(props.get("generationmw", 0) or 0)
        except Exception:
            cap = 0.0
        # meters; clamp 2–25 km so tiny plants still visible
        props["__radius__"] = max(2000, min(cap * 50, 25000))

        # Classify as renewable or non-renewable
        fuel_type = str(props.get("primaryfueltype", "")).lower()
        props["class"] = "Renewable" if fuel_type in RENEWABLE_FUELS else "Non-Renewable"

        # Create a row for the normalized GeoJSON
        row = {"lon": lon, "lat": lat}
        row.update(props)
        rows.append(row)

        total_valid += 1
    st.write(f"Valid point features after fixes: {total_valid}")

    # Create normalized GeoJSON structure
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {k: v for k, v in r.items() if k not in ("lon", "lat")}
        }
        for r in rows
    ]
    fc_norm = {"type": "FeatureCollection", "features": features}

    # --- Center the view on your data (fallback to AU if empty)
    if total_valid > 0:
        lons = [lon for lon, _, _ in pts if isinstance(lon, (int, float)) and math.isfinite(lon)]
        lats = [lat for _, lat, _ in pts if isinstance(lat, (int, float)) and math.isfinite(lat)]
        if lons and lats:
            ctr_lon = sum(lons)/len(lons)
            ctr_lat = sum(lats)/len(lats)
        else:
            ctr_lon, ctr_lat = 135, -30
    else:
        ctr_lon, ctr_lat = 135, -30

    view_state = pdk.ViewState(latitude=ctr_lat, longitude=ctr_lon, zoom=4)

    # --- Build a layer with color based on renewable/non-renewable class
    layer_power = pdk.Layer(
        "GeoJsonLayer",
        data=fc_norm,
        pickable=True,
        auto_highlight=True,
        pointType="circle",
        filled=True,
        stroked=False,
        get_point_radius="properties.__radius__",
        get_fill_color="""
        properties.class === 'Renewable'
        ? [0, 180, 0, 180]
        : [255, 0, 0, 180]
    """,
        point_radius_min_pixels=2,                    # ensure dot visible when zoomed out
    )

    # A small sanity marker so you always see *something* render
    sanity_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lon": 151.21, "lat": -33.87}],  # Sydney
        get_position=["lon", "lat"],
        get_radius=5000,
        opacity=0.7,
    )

    # Create the deck with the updated layer
    deck = pdk.Deck(
        layers=[layer_power],
        initial_view_state=view_state,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        map_provider=None,
        tooltip={
            "html": (
                "<b>Name:</b> {properties.name}<br>"
                "<b>Type:</b> {properties.generationtype}<br>"
                "<b>Capacity:</b> {properties.generationmw} MW<br>"
                "<b>Fuel:</b> {properties.primaryfueltype}<br>"
                "<b>Class:</b> {properties.class}<br>"
                "<b>Status:</b> {properties.operationalstatus}<br>"
                "<b>Owner:</b> {properties.owner}<br>"
                "<b>Location:</b> {properties.locality}, {properties.state}"
            )
        },
        height=650,
        parameters={"cull": False},
    )

    st.pydeck_chart(deck, use_container_width=True)

    # --- Quick “table” peek to confirm properties exist
    with st.expander("Sample feature properties"):
        sample = [ft["properties"] for _, _, ft in pts[:5]]
        st.write(sample if sample else "No point features found.")
