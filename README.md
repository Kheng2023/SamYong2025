# Govhack2025-Datacentres — Maps Diagrams

This repository includes PlantUML diagrams describing the architecture to "make the maps" for an interactive heatmap built from N parallel geospatial pipelines.

- Diagram file: `diagrams\maps.puml`
- Contents: High-level components, ingestion pipelines, grid normalization, aggregation/weighting, and tile serving path.

## Quick View
Paste the contents of `diagrams\maps.puml` into any PlantUML renderer (IntelliJ plugin, VSCode extension, or https://www.plantuml.com/plantuml/).

## Export Locally (examples)
- Using PlantUML CLI: `plantuml -tpng diagrams\maps.puml`
- Export SVG: `plantuml -tsvg diagrams\maps.puml`

## Next Steps
If you want executable prototype maps:
- Frontend: MapLibre GL (heatmap layer) or Leaflet + canvas heatmap.
- Tile service: Serve raster tiles from `Heatmap Store` via `{z}/{x}/{y}` endpoint.
- Aggregation: Implement weighted combination `H(x,y,t) = Σ w_i(t) * f_i(grid_i(x,y,t))` with grid alignment to EPSG:3857.
