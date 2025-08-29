import streamlit as st
import numpy as np
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="AI Data Centre Heatmap MVP", layout="wide")

st.title("🇦🇺 Data Centres: Heatmap MVP")

# --- Step 1: Generate dummy datasets ---
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
