import json
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, List, Tuple, Union, Optional

# Import engine.py components
from map_baker.engine import GeoJSONProcessor as EngineProcessor, GeoCatalog, GridSpec, LayerSpec


class GeoJSONProcessor:
    """
    A class to process GeoJSON files and generate heatmaps based on feature density.
    Uses the engine.py components for advanced processing capabilities.
    """

    def __init__(self, geojson_path: str = None):
        """
        Initialize the GeoJSONProcessor.

        Args:
            geojson_path (str, optional): Path to the GeoJSON file to process.
        """
        self.geojson_path = geojson_path
        self.gdf = None
        self.features = None
        self.bounds = None

        # Initialize engine components
        self.engine_processor = EngineProcessor()
        self.catalog = GeoCatalog()
        self.engine_processor.attach_catalog(self.catalog)

        # Source ID for the main file
        self.main_source_id = "main"

        if geojson_path:
            self.load_geojson(geojson_path)

    def _convert_datetime_columns(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Convert datetime columns to ISO format strings to make them JSON serializable.

        Args:
            gdf (gpd.GeoDataFrame): The GeoDataFrame to process.

        Returns:
            gpd.GeoDataFrame: The GeoDataFrame with datetime columns converted to strings.
        """
        gdf_copy = gdf.copy()

        for column in gdf_copy.columns:
            if column != 'geometry':  # Skip the geometry column
                if pd.api.types.is_datetime64_any_dtype(gdf_copy[column]):
                    # Convert datetime to ISO format string
                    gdf_copy[column] = gdf_copy[column].dt.strftime('%Y-%m-%dT%H:%M:%S')
                elif gdf_copy[column].dtype == 'object':
                    # Check if object column contains Timestamp objects
                    if not gdf_copy[column].empty and isinstance(gdf_copy[column].iloc[0], pd.Timestamp):
                        gdf_copy[column] = gdf_copy[column].dt.strftime('%Y-%m-%dT%H:%M:%S')

        return gdf_copy

    def load_geojson(self, geojson_path: str) -> gpd.GeoDataFrame:
        """
        Load a GeoJSON file into a GeoDataFrame.

        Args:
            geojson_path (str): Path to the GeoJSON file.

        Returns:
            gpd.GeoDataFrame: The loaded GeoDataFrame.
        """
        self.geojson_path = geojson_path
        self.gdf = gpd.read_file(geojson_path)

        # Ensure CRS is set to WGS84 (standard for lat/lon)
        if self.gdf.crs is None or self.gdf.crs.to_string() != 'EPSG:4326':
            self.gdf = self.gdf.set_crs('EPSG:4326', allow_override=True)

        # Convert datetime columns to strings before JSON serialization
        gdf_for_json = self._convert_datetime_columns(self.gdf)

        # Extract features
        self.features = json.loads(gdf_for_json.to_json())['features']

        # Get bounds
        self.bounds = self.gdf.total_bounds  # [minx, miny, maxx, maxy]

        # Add to catalog
        self.catalog.add(self.main_source_id, geojson_path)

        return self.gdf

    def generate_heatmap(self, grid_size: int,
                         weight_property: Optional[str] = None,
                         filter_property: Optional[Dict] = None,
                         bounds: Optional[Tuple[float, float, float, float]] = None) -> pd.DataFrame:
        """
        Generate a heatmap based on feature density using engine.py.

        Args:
            grid_size (int): Size of the grid (number of cells in each dimension).
            weight_property (str, optional): Property name to use for weighting points.
            filter_property (Dict, optional): Filter features by property, e.g. {'class': 'Renewable'}.
            bounds (Tuple[float, float, float, float], optional): Bounds to use for the grid (minx, miny, maxx, maxy).

        Returns:
            pd.DataFrame: DataFrame with lat, lon, and value columns for the heatmap.
        """
        if self.gdf is None:
            raise ValueError("No GeoJSON loaded. Call load_geojson() first.")

        # Determine the geometry type to use
        geometry_type = "point"  # Default to point
        if not self.gdf.empty:
            # Check the most common geometry type
            geom_types = self.gdf.geometry.geom_type.value_counts()
            if not geom_types.empty:
                most_common = geom_types.index[0].lower()
                if "polygon" in most_common:
                    geometry_type = "polygon"
                elif "line" in most_common:
                    geometry_type = "line"

        # Get bounds
        if bounds is not None:
            grid_bounds = bounds
        else:
            # Use the bounds from the catalog for the main source
            grid_bounds = self.catalog.sources[self.main_source_id].bounds_wgs

        # Create a GridSpec
        gridspec = GridSpec(
            bounds=grid_bounds,
            nx=grid_size,
            ny=grid_size
        )

        # Create a LayerSpec
        layer_spec = LayerSpec(
            source_id=self.main_source_id,
            geometry_type=geometry_type,
            mode="nearest" if geometry_type == "point" else "mask" if geometry_type == "polygon" else "nearest",
            filter_property=filter_property,
            weight_property=weight_property,
            dataset_weight=1.0,
            decay="exp",  # Default decay function
            decay_params={"scale": 1000.0}  # Default decay parameters
        )

        # Generate the heatmap using the engine
        return self.engine_processor.generate_layer_on_grid(gridspec, layer_spec)

    def generate_weighted_heatmap(self, grid_size: int,
                                  datasets: List[Dict[str, Union[str, float]]]) -> pd.DataFrame:
        """
        Generate a weighted heatmap from multiple datasets from the same GeoJSON file.

        Args:
            grid_size (int): Size of the grid (number of cells in each dimension).
            datasets (List[Dict]): List of dataset configurations, each with:
                - filter_property (Dict): Filter to apply, e.g. {'class': 'Renewable'}
                - weight_property (str, optional): Property to use for weighting
                - dataset_weight (float): Weight for this dataset in the final heatmap

        Returns:
            pd.DataFrame: DataFrame with lat, lon, and value columns for the heatmap.
        """
        if self.gdf is None:
            raise ValueError("No GeoJSON loaded. Call load_geojson() first.")

        # Get overall bounds
        minx, miny, maxx, maxy = self.bounds

        # Create grid
        x_grid = np.linspace(minx, maxx, grid_size)
        y_grid = np.linspace(miny, maxy, grid_size)

        # Initialize combined heatmap
        combined_heatmap = np.zeros((grid_size, grid_size))

        # Process each dataset
        for dataset in datasets:
            filter_prop = dataset.get('filter_property', None)
            weight_prop = dataset.get('weight_property', None)
            dataset_weight = dataset.get('dataset_weight', 1.0)

            # Generate individual heatmap
            heatmap_df = self.generate_heatmap(grid_size, weight_prop, filter_prop, bounds=self.bounds)

            # Reshape and add to combined heatmap
            heatmap_values = heatmap_df['value'].values.reshape(grid_size, grid_size)
            combined_heatmap += dataset_weight * heatmap_values

        # Create DataFrame for visualization
        lon_grid, lat_grid = np.meshgrid(x_grid, y_grid)
        df = pd.DataFrame({
            'lat': lat_grid.flatten(),
            'lon': lon_grid.flatten(),
            'value': combined_heatmap.flatten()
        })

        return df

    def save_heatmap_csv(self, heatmap_df: pd.DataFrame, output_path: str) -> str:
        """
        Save a heatmap DataFrame to a CSV file.

        Args:
            heatmap_df (pd.DataFrame): DataFrame with lat, lon, and value columns.
            output_path (str): Path where the CSV file will be saved.

        Returns:
            str: Path to the saved file.
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Save to CSV
        heatmap_df.to_csv(output_path, index=False)

        return output_path

    def save_heatmap_geojson(self, heatmap_df: pd.DataFrame, output_path: str) -> str:
        """
        Save a heatmap DataFrame to a GeoJSON file.

        Args:
            heatmap_df (pd.DataFrame): DataFrame with lat, lon, and value columns.
            output_path (str): Path where the GeoJSON file will be saved.

        Returns:
            str: Path to the saved file.
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Convert DataFrame to GeoDataFrame
        geometry = [Point(lon, lat) for lon, lat in zip(heatmap_df['lon'], heatmap_df['lat'])]
        gdf = gpd.GeoDataFrame(heatmap_df, geometry=geometry, crs="EPSG:4326")

        # Save to GeoJSON
        gdf.to_file(output_path, driver='GeoJSON')

        return output_path

    def load_heatmap_geojson(self, file_path: str) -> pd.DataFrame:
        """
        Load a heatmap from a GeoJSON file.

        Args:
            file_path (str): Path to the GeoJSON file.

        Returns:
            pd.DataFrame: DataFrame with lat, lon, and value columns.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Heatmap file not found: {file_path}")

        # Load from GeoJSON
        gdf = gpd.read_file(file_path)

        # Extract lat, lon from geometry
        if 'lat' not in gdf.columns or 'lon' not in gdf.columns:
            gdf['lon'] = gdf.geometry.x
            gdf['lat'] = gdf.geometry.y

        # Validate the DataFrame
        if 'value' not in gdf.columns:
            raise ValueError("GeoJSON file must contain a 'value' column")

        # Convert to regular DataFrame with required columns
        df = pd.DataFrame({
            'lat': gdf['lat'],
            'lon': gdf['lon'],
            'value': gdf['value']
        })

        return df

    def generate_and_save_heatmap(self, grid_size: int, output_path: str, 
                                 format: str = 'csv',
                                 weight_property: Optional[str] = None,
                                 filter_property: Optional[Dict] = None) -> str:
        """
        Generate a heatmap and save it to disk in one step.

        Args:
            grid_size (int): Size of the grid (number of cells in each dimension).
            output_path (str): Path where the heatmap file will be saved.
            format (str): Format to save the heatmap in ('csv' or 'geojson').
            weight_property (str, optional): Property name to use for weighting points.
            filter_property (Dict, optional): Filter features by property, e.g. {'class': 'Renewable'}.

        Returns:
            str: Path to the saved file.
        """
        # Generate the heatmap
        heatmap_df = self.generate_heatmap(grid_size, weight_property, filter_property)

        # Save the heatmap
        if format.lower() == 'csv':
            return self.save_heatmap_csv(heatmap_df, output_path)
        elif format.lower() == 'geojson':
            return self.save_heatmap_geojson(heatmap_df, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'geojson'.")

    def generate_multi_file_heatmap(self, grid_size: int,
                                    datasets: List[Dict[str, Union[str, float]]]) -> pd.DataFrame:
        """
        Generate a weighted heatmap from multiple GeoJSON files using engine.py.

        Args:
            grid_size (int): Size of the grid (number of cells in each dimension).
            datasets (List[Dict]): List of dataset configurations, each with:
                - file_path (str): Path to the GeoJSON file
                - filter_property (Dict, optional): Filter to apply, e.g. {'class': 'Renewable'}
                - weight_property (str, optional): Property to use for weighting
                - dataset_weight (float, optional): Weight for this dataset in the final heatmap

        Returns:
            pd.DataFrame: DataFrame with lat, lon, and value columns for the heatmap.
        """
        if not datasets:
            raise ValueError("No datasets provided")

        # Create a new catalog and processor for this operation
        catalog = GeoCatalog()
        processor = EngineProcessor()
        processor.attach_catalog(catalog)

        # Add each dataset to the catalog with a unique source_id
        layer_specs = []
        for i, dataset in enumerate(datasets):
            file_path = dataset.get('file_path')
            if not file_path:
                continue

            source_id = f"source_{i}"
            catalog.add(source_id, file_path)

            # Determine geometry type
            gdf = gpd.read_file(file_path)
            geometry_type = "point"  # Default to point
            if not gdf.empty:
                # Check the most common geometry type
                geom_types = gdf.geometry.geom_type.value_counts()
                if not geom_types.empty:
                    most_common = geom_types.index[0].lower()
                    if "polygon" in most_common:
                        geometry_type = "polygon"
                    elif "line" in most_common:
                        geometry_type = "line"

            # Create a LayerSpec for this dataset
            layer_specs.append(LayerSpec(
                source_id=source_id,
                geometry_type=geometry_type,
                mode="nearest" if geometry_type == "point" else "mask" if geometry_type == "polygon" else "nearest",
                filter_property=dataset.get('filter_property'),
                weight_property=dataset.get('weight_property'),
                dataset_weight=dataset.get('dataset_weight', 1.0),
                decay="exp",  # Default decay function
                decay_params={"scale": 1000.0}  # Default decay parameters
            ))

        # Get combined bounds from the catalog
        bounds = catalog.combined_bounds_wgs()

        # Create a GridSpec
        gridspec = GridSpec(
            bounds=bounds,
            nx=grid_size,
            ny=grid_size
        )

        # Generate the combined heatmap using the engine
        return processor.generate_linear_combination_multi(gridspec, layer_specs)

    def generate_and_save_weighted_heatmap(self, grid_size: int, output_path: str,
                                           datasets: List[Dict[str, Union[str, float]]],
                                           format: str = 'csv') -> str:
        """
        Generate a weighted heatmap from multiple datasets and save it to disk in one step.

        Args:
            grid_size (int): Size of the grid (number of cells in each dimension).
            output_path (str): Path where the heatmap file will be saved.
            datasets (List[Dict]): List of dataset configurations, each with:
                - filter_property (Dict): Filter to apply, e.g. {'class': 'Renewable'}
                - weight_property (str, optional): Property to use for weighting
                - dataset_weight (float): Weight for this dataset in the final heatmap
            format (str): Format to save the heatmap in ('csv' or 'geojson').

        Returns:
            str: Path to the saved file.
        """
        # Generate the weighted heatmap
        heatmap_df = self.generate_weighted_heatmap(grid_size, datasets)

        # Save the heatmap
        if format.lower() == 'csv':
            return self.save_heatmap_csv(heatmap_df, output_path)
        elif format.lower() == 'geojson':
            return self.save_heatmap_geojson(heatmap_df, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'geojson'.")


# Example usage:
if __name__ == "__main__":
    # Initialize processor
    processor = GeoJSONProcessor("map_data/Major_Power_Stations.geo.json")

    # Create output directory
    os.makedirs("output", exist_ok=True)

    # Method 1: Generate and save separately
    print("\n--- Method 1: Generate and save separately ---")

    # Generate simple heatmap
    heatmap_df = processor.generate_heatmap(grid_size=500)

    # Generate weighted heatmap with multiple datasets
    weighted_heatmap_df = processor.generate_weighted_heatmap(
        grid_size=500,
        datasets=[
            {
                'filter_property': {'class': 'Renewable'},
                'weight_property': 'generationmw',
                'dataset_weight': 0.7
            },
            {
                'filter_property': {'class': 'Non Renewable'},
                'weight_property': 'generationmw',
                'dataset_weight': 0.3
            }
        ]
    )

    print(f"Generated heatmap with {len(heatmap_df)} points")
    print(f"Generated weighted heatmap with {len(weighted_heatmap_df)} points")

    # Save as GeoJSON (geospatial format)
    geojson_path = processor.save_heatmap_geojson(heatmap_df, "output/simple_heatmap.geojson")
    weighted_geojson_path = processor.save_heatmap_geojson(weighted_heatmap_df, "output/weighted_heatmap.geojson")

    print(f"Saved heatmaps to GeoJSON: {geojson_path} and {weighted_geojson_path}")

    # Method 2: Use convenience methods to generate and save in one step
    print("\n--- Method 2: Generate and save in one step ---")

    # Generate and save weighted heatmap
    geojson_path2 = processor.generate_and_save_weighted_heatmap(
        grid_size=50,
        output_path="output/weighted_heatmap2.geojson",
        format="geojson",
        datasets=[
            {
                'filter_property': {'class': 'Renewable'},
                'weight_property': 'generationmw',
                'dataset_weight': 0.7
            },
            {
                'filter_property': {'class': 'Non Renewable'},
                'weight_property': 'generationmw',
                'dataset_weight': 0.3
            }
        ]
    )

    print(f"Generated and saved weighted heatmap in one step: {geojson_path2}")

    # Load heatmaps back from disk
    print("\n--- Loading saved heatmaps ---")

    loaded_geojson_df = processor.load_heatmap_geojson(geojson_path)

    print(f"Loaded heatmap from GeoJSON: {len(loaded_geojson_df)} points")

    # These loaded DataFrames can now be used directly with Streamlit's pydeck HeatmapLayer
    print("\nThese loaded DataFrames can now be used directly with Streamlit's pydeck HeatmapLayer:"
          "\n\nlayer = pdk.Layer("
          "\n    \"HeatmapLayer\","
          "\n    data=loaded_csv_df,"
          "\n    get_position=[\"lon\", \"lat\"],"
          "\n    get_weight=\"value\","
          "\n    radiusPixels=40,"
          "\n    intensity=1,"
          "\n    threshold=0.01,"
          "\n)"
          "\n\nst.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))")
