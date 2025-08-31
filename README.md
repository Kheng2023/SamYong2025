# Govhack2025 Datacentres — FlexiMap

This repository is the work of Sam and Yong for GovHack 2025 competition entry. It includes a FastAPI server with a simple web interface for displaying GeoJSON files as layers on a map, as well as PlantUML diagrams describing the architecture for an interactive heatmap system.

## Fleximap

A FastAPI server with a Leaflet-based web interface for displaying GeoJSON files as layers on a map.

### Features

- List and view GeoJSON files from multiple directories
- Display GeoJSON files as layers on a map
- Toggle layer visibility
- View feature properties in popups
- Process GeoJSON files to generate heatmaps

### Running the Map-Baker

Run the FastAPI server:

```bash
python api.py
```

This will start the server at http://localhost:8000.

## Docker
Use the provider docker-compose.yml file to build and run the server. Will be available at http://localhost:8000.

### Using the Web Interface

1. Open your browser and navigate to http://localhost:8000
2. The sidebar shows available GeoJSON files grouped by directory
3. Click on a file to load it as a layer on the map
4. Use the layer controls to:
   - Toggle layer visibility with the checkbox
   - Remove a layer with the × button
5. Click on features to view their properties in a popup

### API Endpoints

The server provides the following API endpoints:

- `GET /api/files`: List all available GeoJSON files
- `GET /api/heatmaps`: List all generated heatmap files (also is a layer)
- `GET /api/heatmaps/{filename}`: Get a specific heatmap file
- `GET /api/files/{directory}/{filename}`: Get a specific GeoJSON file
- `GET /api/properties`: Get the properties of a GeoJSON file (used for frontend selection)
- `GET /api/property-values`: List all available property values for a GeoJSON file (used for frontend selection)
- `GET /api/process`: Process a GeoJSON file to generate a heatmap
- `POST /api/build_layer`: Build a heatmap layer from a GeoJSON file, uses filters and weights
- `POST /api/build_multi_layer`: Not implemented yet, will allow selection of multiple GeoJSON files to build a combined heatmap layer

### Algorithms
GeoJSONs contain point, line, and polygon features. The following algorithms are used to generate heatmaps:
- **Point Heatmap**: Each point is assigned a weight based on its distance from the centre of the heatmap.
  - uses decay functions (exponential, linear_cutoff, power_decay) to generate values for desired grid size (default 
    50 x 50)
- **Line Heatmap**: Not yet implemented correctly. Should be able to generate a heatmap from a line feature, based 
  upon distance from line. Useful for access to existing roads or power lines
- **Polygon Heatmap**: Not yet implemented correctly. Should be able to use as a mask, to set values to zero for areas 
  outside or inside the polygon. Useful to exclude areas from the heatmap, such as water, heritage sites, etc. 
  Centroid algorithm could be used to determine the centre of the polygon, and then use the point heatmap algorithm to 
  generate a heatmap for the polygon.
#### Weighting
- Properties of the features from the GeoJSON points can be used to weight the generation of heatmap values. Curren 
  algorith allows for giving each property value found a weight, and dividing the contribution by that weight. Eg 
  the most important property should have a weight of 1, and the least important should have a weight of 100. (will 
  contribute 100x less to the heatmap than a feature with a weight of 1)
#### Filters
- Filters can be used to exclude features from the heatmap. Eg only includes features with a certain property value. 
  Currently only supports a single filter. Eg can select all power stations in SA, 

### Multilayer Heatmap
- Multilayer heatmap is not yet implemented correctly. Should be able to combine multiple heatmap GeoJSON files into a 
  single heatmap layer in additive, multiplicative, subtractive, or weighted mode.
- Front end interface for this feature is not yet implemented.

## Implementation Notes

The GeoJSON Viewer implements the "Next Steps" outlined in the architecture diagrams:
- Frontend: Uses Leaflet for interactive maps
- Data Processing: Implements weighted combination of GeoJSON layers
- API: Provides endpoints for accessing and processing GeoJSON files
