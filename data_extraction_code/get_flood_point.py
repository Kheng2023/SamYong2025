import requests
import json
import time
from pathlib import Path

def download_arcgis_geojson(base_url, output_filename, layer_id=0, chunk_size=1000):
    """
    Download data from ArcGIS FeatureServer as GeoJSON
    
    Args:
        base_url: ArcGIS FeatureServer base URL
        output_filename: Name for output GeoJSON file
        layer_id: Layer ID to download (usually 0)
        chunk_size: Number of features to request at once
    """
    
    # Construct the query URL for the specific layer
    query_url = f"{base_url}/{layer_id}/query"
    
    print(f"Downloading from: {query_url}")
    
    # First, get the total count of features
    count_params = {
        'where': '1=1',
        'returnCountOnly': 'true',
        'f': 'json'
    }
    
    try:
        response = requests.get(query_url, params=count_params)
        response.raise_for_status()
        count_data = response.json()
        total_features = count_data.get('count', 0)
        print(f"Total features to download: {total_features}")
        
        if total_features == 0:
            print("No features found!")
            return False
            
    except Exception as e:
        print(f"Error getting feature count: {e}")
        # Continue anyway, try to download without knowing count
        total_features = None
    
    # Download features in chunks
    all_features = []
    offset = 0
    
    while True:
        # Parameters for each request
        params = {
            'where': '1=1',              # Get all features
            'outFields': '*',            # Get all attributes
            'f': 'geojson',             # Output format
            'resultOffset': offset,      # Starting position
            'resultRecordCount': chunk_size  # Number of records
        }
        
        try:
            print(f"Downloading features {offset} to {offset + chunk_size}...")
            response = requests.get(query_url, params=params)
            response.raise_for_status()
            
            # Parse the GeoJSON response
            geojson_data = response.json()
            
            # Check if we got features
            features = geojson_data.get('features', [])
            
            if not features:
                print("No more features to download.")
                break
                
            # Add features to our collection
            all_features.extend(features)
            
            print(f"Downloaded {len(features)} features (total: {len(all_features)})")
            
            # If we got fewer features than requested, we've reached the end
            if len(features) < chunk_size:
                break
                
            # Move to next chunk
            offset += chunk_size
            
            # Small delay to be respectful to the server
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error downloading chunk at offset {offset}: {e}")
            break
    
    # Create final GeoJSON structure
    final_geojson = {
        "type": "FeatureCollection",
        "features": all_features
    }
    
    # Save to file
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(final_geojson, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully saved {len(all_features)} features to '{output_filename}'")
        return True
        
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def get_layer_info(base_url):
    """
    Get information about available layers in the FeatureServer
    """
    try:
        response = requests.get(f"{base_url}?f=json")
        response.raise_for_status()
        service_info = response.json()
        
        print("📋 Available Layers:")
        print("-" * 50)
        
        layers = service_info.get('layers', [])
        if not layers:
            print("No layers found, trying tables...")
            layers = service_info.get('tables', [])
        
        for layer in layers:
            layer_id = layer.get('id', 'Unknown')
            layer_name = layer.get('name', 'Unnamed')
            geometry_type = layer.get('geometryType', 'Unknown')
            
            print(f"Layer {layer_id}: {layer_name}")
            print(f"  Geometry Type: {geometry_type}")
            
            # Get feature count for this layer
            try:
                count_url = f"{base_url}/{layer_id}/query"
                count_params = {'where': '1=1', 'returnCountOnly': 'true', 'f': 'json'}
                count_response = requests.get(count_url, params=count_params)
                count_data = count_response.json()
                feature_count = count_data.get('count', 'Unknown')
                print(f"  Features: {feature_count}")
            except:
                print(f"  Features: Unable to determine")
            
            print()
        
        return layers
        
    except Exception as e:
        print(f"Error getting layer info: {e}")
        return []

def main():
    """
    Main function to download the flood study data
    """
    # Your ArcGIS FeatureServer URL
    base_url = "https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/flood_study_summary_3ce61/FeatureServer"
    
    print("🌊 Australian Flood Study Data Downloader")
    print("=" * 50)
    
    # First, get information about available layers
    layers = get_layer_info(base_url)
    
    if not layers:
        print("⚠️ No layers found. Trying to download from layer 0 anyway...")
        layer_id = 0
    else:
        # If multiple layers, you can specify which one to download
        layer_id = 0  # Usually the main layer is 0
        
        if len(layers) > 1:
            print(f"Multiple layers found. Downloading layer {layer_id} by default.")
            print("You can modify the script to download other layers if needed.")
    
    # Download the data
    output_filename = "flood_study_summary.geojson"
    
    success = download_arcgis_geojson(
        base_url=base_url,
        output_filename=output_filename,
        layer_id=layer_id,
        chunk_size=1000  # Adjust if you get timeout errors
    )
    
    if success:
        print(f"\n🎉 Download complete!")
        print(f"📁 File saved as: {output_filename}")
        print(f"💡 You can now use this GeoJSON file in your data center site selection analysis")
    else:
        print(f"\n❌ Download failed!")

# Alternative: Simple single request (if dataset is small)
def simple_download(base_url, layer_id=0, output_filename="output.geojson"):
    """
    Simple download for smaller datasets (single request)
    """
    query_url = f"{base_url}/{layer_id}/query"
    
    params = {
        'where': '1=1',
        'outFields': '*',
        'f': 'geojson'
    }
    
    try:
        print("Attempting simple download...")
        response = requests.get(query_url, params=params)
        response.raise_for_status()
        
        geojson_data = response.json()
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        
        feature_count = len(geojson_data.get('features', []))
        print(f"✅ Downloaded {feature_count} features to '{output_filename}'")
        return True
        
    except Exception as e:
        print(f"Simple download failed: {e}")
        print("Try using the chunked download instead.")
        return False

if __name__ == "__main__":
    # Try simple download first
    base_url = "https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/flood_study_summary_3ce61/FeatureServer"
    
    print("Trying simple download first...")
    success = simple_download(base_url, layer_id=0, output_filename="flood_study_simple.geojson")
    
    if not success:
        print("\nSimple download failed, trying chunked download...")
        main()
    else:
        print("\n🎉 Simple download succeeded!")