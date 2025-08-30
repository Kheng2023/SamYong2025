from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel

# Import the GeoJSONProcessor
from geojson_processor import GeoJSONProcessor

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
    "data": "data",
    "output": "output",
    "map_data": "map_data"
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

# Serve HTML interface
@app.get("/", response_class=HTMLResponse)
async def get_html_interface():
    """Serve the HTML interface for viewing GeoJSON files."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GeoJSON Viewer</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body, html {
                margin: 0;
                padding: 0;
                height: 100%;
                font-family: Arial, sans-serif;
            }
            .container {
                display: flex;
                height: 100%;
            }
            .sidebar {
                width: 300px;
                padding: 20px;
                background-color: #f5f5f5;
                overflow-y: auto;
            }
            .map-container {
                flex-grow: 1;
            }
            #map {
                height: 100%;
            }
            h1 {
                font-size: 24px;
                margin-top: 0;
            }
            h2 {
                font-size: 18px;
                margin-top: 20px;
            }
            ul {
                list-style-type: none;
                padding: 0;
            }
            li {
                margin-bottom: 10px;
            }
            .file-item {
                cursor: pointer;
                padding: 8px;
                border-radius: 4px;
            }
            .file-item:hover {
                background-color: #e0e0e0;
            }
            .active {
                background-color: #d0d0d0;
            }
            .layer-control {
                margin-top: 5px;
                display: flex;
                align-items: center;
            }
            .color-picker {
                margin-left: 10px;
                width: 20px;
                height: 20px;
                border: none;
                padding: 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="sidebar">
                <h1>GeoJSON Viewer</h1>
                <h2>Available Files</h2>
                <div id="file-list">Loading...</div>
                <h2>Active Layers</h2>
                <ul id="layer-list"></ul>
            </div>
            <div class="map-container">
                <div id="map"></div>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // Initialize map
            const map = L.map('map').setView([-30, 135], 4);
            
            // Add base tile layer
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            
            // Store active layers
            const activeLayers = {};
            
            // Fetch available GeoJSON files
            async function fetchFiles() {
                try {
                    const response = await fetch('/api/files');
                    const data = await response.json();
                    displayFiles(data.files);
                } catch (error) {
                    console.error('Error fetching files:', error);
                    document.getElementById('file-list').innerHTML = 'Error loading files.';
                }
            }
            
            // Display files in sidebar
            function displayFiles(files) {
                const fileList = document.getElementById('file-list');
                if (files.length === 0) {
                    fileList.innerHTML = 'No GeoJSON files found.';
                    return;
                }
                
                // Group files by directory
                const filesByDir = {};
                files.forEach(file => {
                    if (!filesByDir[file.directory]) {
                        filesByDir[file.directory] = [];
                    }
                    filesByDir[file.directory].push(file);
                });
                
                // Create HTML
                let html = '';
                for (const [dir, dirFiles] of Object.entries(filesByDir)) {
                    html += `<h3>${dir}</h3><ul>`;
                    dirFiles.forEach(file => {
                        html += `
                            <li>
                                <div class="file-item" data-path="${file.path}" data-name="${file.name}" data-dir="${file.directory}">
                                    ${file.name} (${formatFileSize(file.size)})
                                </div>
                            </li>
                        `;
                    });
                    html += '</ul>';
                }
                
                fileList.innerHTML = html;
                
                // Add click event listeners
                document.querySelectorAll('.file-item').forEach(item => {
                    item.addEventListener('click', handleFileClick);
                });
            }
            
            // Format file size
            function formatFileSize(bytes) {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / 1048576).toFixed(1) + ' MB';
            }
            
            // Handle file click
            async function handleFileClick(event) {
                const fileItem = event.currentTarget;
                const fileName = fileItem.dataset.name;
                const dirName = fileItem.dataset.dir;
                const filePath = fileItem.dataset.path;
                
                try {
                    // Fetch GeoJSON data
                    const response = await fetch(`/api/files/${dirName}/${fileName}`);
                    const geojsonData = await response.json();
                    
                    // Add to map
                    addLayerToMap(fileName, geojsonData);
                    
                } catch (error) {
                    console.error('Error loading GeoJSON:', error);
                    alert(`Error loading ${fileName}`);
                }
            }
            
            // Add layer to map
            function addLayerToMap(name, geojsonData) {
                // Remove existing layer with same name if it exists
                if (activeLayers[name]) {
                    map.removeLayer(activeLayers[name].layer);
                }
                
                // Generate random color
                const color = getRandomColor();
                
                // Create layer
                const layer = L.geoJSON(geojsonData, {
                    style: function(feature) {
                        return {
                            color: color,
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.5
                        };
                    },
                    pointToLayer: function(feature, latlng) {
                        return L.circleMarker(latlng, {
                            radius: 8,
                            fillColor: color,
                            color: '#000',
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8
                        });
                    },
                    onEachFeature: function(feature, layer) {
                        if (feature.properties) {
                            let popupContent = '<div class="popup-content">';
                            for (const [key, value] of Object.entries(feature.properties)) {
                                popupContent += `<strong>${key}:</strong> ${value}<br>`;
                            }
                            popupContent += '</div>';
                            layer.bindPopup(popupContent);
                        }
                    }
                }).addTo(map);
                
                // Store layer
                activeLayers[name] = {
                    layer: layer,
                    color: color
                };
                
                // Update layer list
                updateLayerList();
                
                // Fit map to layer bounds
                map.fitBounds(layer.getBounds());
            }
            
            // Update layer list in sidebar
            function updateLayerList() {
                const layerList = document.getElementById('layer-list');
                let html = '';
                
                for (const [name, layerInfo] of Object.entries(activeLayers)) {
                    html += `
                        <li>
                            <div class="layer-control">
                                <input type="checkbox" id="layer-${name}" checked>
                                <label for="layer-${name}">${name}</label>
                                <input type="color" class="color-picker" data-layer="${name}" value="${layerInfo.color}">
                                <button class="remove-layer" data-layer="${name}">×</button>
                            </div>
                        </li>
                    `;
                }
                
                layerList.innerHTML = html;
                
                // Add event listeners
                document.querySelectorAll('input[type="checkbox"][id^="layer-"]').forEach(checkbox => {
                    checkbox.addEventListener('change', toggleLayerVisibility);
                });
                
                document.querySelectorAll('.color-picker').forEach(picker => {
                    picker.addEventListener('change', changeLayerColor);
                });
                
                document.querySelectorAll('.remove-layer').forEach(button => {
                    button.addEventListener('click', removeLayer);
                });
            }
            
            // Toggle layer visibility
            function toggleLayerVisibility(event) {
                const layerName = event.target.id.replace('layer-', '');
                const layer = activeLayers[layerName]?.layer;
                
                if (layer) {
                    if (event.target.checked) {
                        map.addLayer(layer);
                    } else {
                        map.removeLayer(layer);
                    }
                }
            }
            
            // Change layer color
            function changeLayerColor(event) {
                const layerName = event.target.dataset.layer;
                const newColor = event.target.value;
                const layerInfo = activeLayers[layerName];
                
                if (layerInfo) {
                    layerInfo.color = newColor;
                    
                    // Remove and re-add layer with new color
                    map.removeLayer(layerInfo.layer);
                    
                    // Fetch GeoJSON data again
                    fetch(`/api/files/${layerName.split('/')[0]}/${layerName.split('/')[1]}`)
                        .then(response => response.json())
                        .then(geojsonData => {
                            addLayerToMap(layerName, geojsonData);
                        })
                        .catch(error => {
                            console.error('Error reloading GeoJSON:', error);
                        });
                }
            }
            
            // Remove layer
            function removeLayer(event) {
                const layerName = event.target.dataset.layer;
                const layer = activeLayers[layerName]?.layer;
                
                if (layer) {
                    map.removeLayer(layer);
                    delete activeLayers[layerName];
                    updateLayerList();
                }
            }
            
            // Generate random color
            function getRandomColor() {
                const letters = '0123456789ABCDEF';
                let color = '#';
                for (let i = 0; i < 6; i++) {
                    color += letters[Math.floor(Math.random() * 16)];
                }
                return color;
            }
            
            // Initialize
            fetchFiles();
        </script>
    </body>
    </html>
    """
    return html_content

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)