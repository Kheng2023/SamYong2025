from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel

# Import the GeoJSONProcessor from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from map_baker.geojson_processor import GeoJSONProcessor

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

# Define models
class GeoJSONFile(BaseModel):
    name: str
    path: str
    size: int
    directory: str

class GeoJSONFileList(BaseModel):
    files: List[GeoJSONFile]

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
    filter_property: Optional[str] = None
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

        # Convert to GeoJSON
        temp_path = "temp_heatmap.geojson"
        processor.save_heatmap_geojson(heatmap_df, temp_path)

        # Read the GeoJSON file
        with open(temp_path, "r") as f:
            geojson_data = json.load(f)

        # Clean up
        os.remove(temp_path)

        return geojson_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files for frontend
app.mount("/", StaticFiles(directory="static", html=True), name="frontend")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
