from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel

# Import the GeoJSONProcessor from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from map_baker.geojson_processor import GeoJSONProcessor
from map_baker.engine import LayerSpec, GridSpec

# Create FastAPI app
app = FastAPI(title="GeoJSON Viewer API", 
              description="API for viewing and processing GeoJSON files",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Define data directories
DATA_DIRS = {
    "geojsons": "geojsons"
}

# Define output directory for processed files
GEOJSONS_DIR = "/app/geojsons" if os.path.exists("/app/geojsons") else "geojsons"

# Define models
class GeoJSONFile(BaseModel):
    name: str
    path: str
    size: int
    directory: str

class GeoJSONFileList(BaseModel):
    files: List[GeoJSONFile]

class LayerConfig(BaseModel):
    file_path: str
    dataset_weight: float = 1.0
    weight_property: Optional[str] = None
    filter_property: Optional[Dict[str, Any]] = None

class AggregateRequest(BaseModel):
    layers: List[LayerConfig]
    grid_size: int = 50

class LayerSpecModel(BaseModel):
    source_id: str
    geometry_type: Literal["point", "line", "polygon"]
    mode: str
    filter_property: Optional[Dict[str, Any]] = None
    weight_property: Optional[str] = None
    dataset_weight: float = 1.0
    decay: str = "exp"
    decay_params: Optional[Dict[str, Any]] = None
    k: int = 8
    mask_value: float = 1.0
    output_filename: str

class BuildLayerRequest(BaseModel):
    layer: LayerSpecModel
    grid_size: int = 50
    bounds: Optional[List[float]] = None  # [minx, miny, maxx, maxy]

class BuildMultiLayerRequest(BaseModel):
    layers: List[LayerSpecModel]
    grid_size: int = 50
    output_filename: str

# Helper functions
def get_geojson_files() -> List[GeoJSONFile]:
    """Get all GeoJSON files from the data directories."""
    files = []
    for dir_name, dir_path in DATA_DIRS.items():
        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                if file.endswith(('.geojson', '.geo.json')):
                    file_path = os.path.join(dir_path, file)
                    files.append(GeoJSONFile(
                        name=file,
                        path=file_path,
                        size=os.path.getsize(file_path),
                        directory=dir_name
                    ))
    return files

# API endpoints
@app.get("/api/files", response_model=GeoJSONFileList)
async def list_geojson_files():
    """List all available GeoJSON files."""
    files = get_geojson_files()
    return {"files": files}

@app.get("/api/files/{directory}/{filename}")
async def get_geojson_file(directory: str, filename: str):
    """Get a specific GeoJSON file."""
    if directory not in DATA_DIRS:
        raise HTTPException(status_code=404, detail=f"Directory '{directory}' not found")

    file_path = os.path.join(DATA_DIRS[directory], filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in '{directory}'")

    return FileResponse(file_path)

@app.get("/api/process", response_model=Dict)
async def process_geojson(
    file_path: str,
    grid_size: int = 50,
    weight_property: Optional[str] = None,
    filter_property: Optional[str] = None,
    output_filename: Optional[str] = None
):
    """Process a GeoJSON file to generate a heatmap."""
    try:
        # Parse filter_property if provided
        filter_dict = json.loads(filter_property) if filter_property else None

        # Initialize processor
        processor = GeoJSONProcessor(file_path)

        # Generate heatmap
        heatmap_df = processor.generate_heatmap(
            grid_size=grid_size,
            weight_property=weight_property,
            filter_property=filter_dict
        )

        # Generate output filename if not provided
        if not output_filename:
            base_name = os.path.basename(file_path)
            name_parts = os.path.splitext(base_name)
            output_filename = f"{name_parts[0]}_processed{name_parts[1]}"

        # Save to GeoJSON in the mapped volume
        output_path = os.path.join(GEOJSONS_DIR, output_filename)
        processor.save_heatmap_geojson(heatmap_df, output_path)

        # Read the GeoJSON file
        with open(output_path, "r") as f:
            geojson_data = json.load(f)

        return geojson_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/aggregate", response_model=Dict)
async def aggregate_layers(request: AggregateRequest):
    """Aggregate multiple GeoJSON layers into a single heatmap."""
    try:
        if len(request.layers) < 1:
            raise HTTPException(status_code=400, detail="At least one layer is required")

        # Initialize processor with any file (we'll use the first layer's file)
        processor = GeoJSONProcessor(request.layers[0].file_path)

        # Prepare datasets for generate_multi_file_heatmap
        datasets = []
        for layer in request.layers:
            dataset = {
                'file_path': layer.file_path,
                'dataset_weight': layer.dataset_weight
            }

            if layer.weight_property:
                dataset['weight_property'] = layer.weight_property

            if layer.filter_property:
                dataset['filter_property'] = layer.filter_property

            datasets.append(dataset)

        # Generate multi-file heatmap
        heatmap_df = processor.generate_multi_file_heatmap(
            grid_size=request.grid_size,
            datasets=datasets
        )

        # Save to GeoJSON in the mapped volume
        output_filename = "aggregated_heatmap.geojson"
        output_path = os.path.join(GEOJSONS_DIR, output_filename)
        processor.save_heatmap_geojson(heatmap_df, output_path)

        # Read the GeoJSON file
        with open(output_path, "r") as f:
            geojson_data = json.load(f)

        return geojson_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/build_layer", response_model=Dict)
async def build_layer(request: BuildLayerRequest):
    """Build a single layer using engine.py functionality."""
    try:
        # Initialize processor with any file from the catalog
        processor = GeoJSONProcessor()

        # Create a catalog and add the source
        processor.catalog.add(request.layer.source_id, request.layer.source_id)

        # Create a GridSpec
        bounds = request.bounds if request.bounds else processor.catalog.combined_bounds_wgs()
        if isinstance(bounds, list):
            bounds = tuple(bounds)

        gridspec = GridSpec(
            bounds=bounds,
            nx=request.grid_size,
            ny=request.grid_size
        )

        # Create a LayerSpec from the request model
        layer_spec = LayerSpec(
            source_id=request.layer.source_id,
            geometry_type=request.layer.geometry_type,
            mode=request.layer.mode,
            filter_property=request.layer.filter_property,
            weight_property=request.layer.weight_property,
            dataset_weight=request.layer.dataset_weight,
            decay=request.layer.decay,
            decay_params=request.layer.decay_params,
            k=request.layer.k,
            mask_value=request.layer.mask_value
        )

        # Generate the layer
        layer_df = processor.engine_processor.generate_layer_on_grid(gridspec, layer_spec)

        # Save to GeoJSON in the mapped volume
        output_path = os.path.join(GEOJSONS_DIR, request.layer.output_filename)
        processor.save_heatmap_geojson(layer_df, output_path)

        return {"status": "success", "message": f"Layer saved to {output_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/build_multi_layer", response_model=Dict)
async def build_multi_layer(request: BuildMultiLayerRequest):
    """Build multiple layers and combine them using engine.py functionality."""
    try:
        if len(request.layers) < 1:
            raise HTTPException(status_code=400, detail="At least one layer is required")

        # Initialize processor
        processor = GeoJSONProcessor()

        # Add all sources to the catalog
        for layer in request.layers:
            processor.catalog.add(layer.source_id, layer.source_id)

        # Create a GridSpec
        bounds = processor.catalog.combined_bounds_wgs()
        gridspec = GridSpec(
            bounds=bounds,
            nx=request.grid_size,
            ny=request.grid_size
        )

        # Create LayerSpecs from the request models
        layer_specs = []
        for layer in request.layers:
            layer_specs.append(LayerSpec(
                source_id=layer.source_id,
                geometry_type=layer.geometry_type,
                mode=layer.mode,
                filter_property=layer.filter_property,
                weight_property=layer.weight_property,
                dataset_weight=layer.dataset_weight,
                decay=layer.decay,
                decay_params=layer.decay_params,
                k=layer.k,
                mask_value=layer.mask_value
            ))

        # Generate the combined layer
        combined_df = processor.engine_processor.generate_linear_combination_multi(gridspec, layer_specs)

        # Save to GeoJSON in the mapped volume
        output_path = os.path.join(GEOJSONS_DIR, request.output_filename)
        processor.save_heatmap_geojson(combined_df, output_path)

        return {"status": "success", "message": f"Combined layer saved to {output_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files for frontend
app.mount("/", StaticFiles(directory="static", html=True), name="frontend")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
