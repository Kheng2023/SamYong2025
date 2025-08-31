# Govhack2025-Datacentres — GeoJSON Viewer and Heatmap Generator

This repository includes a FastAPI server with a simple web interface for displaying GeoJSON files as layers on a map, as well as PlantUML diagrams describing the architecture for an interactive heatmap system.

## GeoJSON Viewer

A FastAPI server with a Leaflet-based web interface for displaying GeoJSON files as layers on a map.

### Features

- List and view GeoJSON files from multiple directories
- Display GeoJSON files as layers on a map
- Toggle layer visibility
- Change layer colors
- View feature properties in popups
- Process GeoJSON files to generate heatmaps

### Running the Server

Run the FastAPI server:

```bash
python api.py
```

This will start the server at http://localhost:8000.

### Using the Web Interface

1. Open your browser and navigate to http://localhost:8000
2. The sidebar shows available GeoJSON files grouped by directory
3. Click on a file to load it as a layer on the map
4. Use the layer controls to:
   - Toggle layer visibility with the checkbox
   - Change layer color with the color picker
   - Remove a layer with the × button
5. Click on features to view their properties in a popup

### API Endpoints

The server provides the following API endpoints:

- `GET /api/files`: List all available GeoJSON files
- `GET /api/files/{directory}/{filename}`: Get a specific GeoJSON file
- `GET /api/process`: Process a GeoJSON file to generate a heatmap

## Architecture Diagrams

This repository also includes PlantUML diagrams describing the architecture to "make the maps" for an interactive heatmap built from N parallel geospatial pipelines.

- Diagram file: `diagrams\maps.puml`
- Contents: High-level components, ingestion pipelines, grid normalization, aggregation/weighting, and tile serving path.

### Quick View
Paste the contents of `diagrams\maps.puml` into any PlantUML renderer (IntelliJ plugin, VSCode extension, or https://www.plantuml.com/plantuml/).

### Export Locally (examples)
- Using PlantUML CLI: `plantuml -tpng diagrams\maps.puml`
- Export SVG: `plantuml -tsvg diagrams\maps.puml`

## Implementation Notes

The GeoJSON Viewer implements the "Next Steps" outlined in the architecture diagrams:
- Frontend: Uses Leaflet for interactive maps
- Data Processing: Implements weighted combination of GeoJSON layers
- API: Provides endpoints for accessing and processing GeoJSON files
