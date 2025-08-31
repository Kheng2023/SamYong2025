import requests
import json
import time
import subprocess
import sys
import os
from pathlib import Path

def test_api_server():
    """Test the FastAPI server by making requests to its endpoints."""
    print("Starting API server...")
    
    # Start the server in a separate process
    server_process = subprocess.Popen([sys.executable, "api.py"], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
    
    # Wait for the server to start
    time.sleep(3)
    
    try:
        # Test the /api/files endpoint
        print("\nTesting /api/files endpoint...")
        response = requests.get("http://localhost:8000/api/files")
        if response.status_code == 200:
            files = response.json()["files"]
            print(f"Success! Found {len(files)} GeoJSON files.")
            
            # Print the first few files
            for file in files[:3]:
                print(f"- {file['directory']}/{file['name']} ({file['size']} bytes)")
        else:
            print(f"Error: {response.status_code} - {response.text}")
        
        # Test the /api/files/{directory}/{filename} endpoint with a sample file
        if files:
            sample_file = files[0]
            print(f"\nTesting /api/files/{sample_file['directory']}/{sample_file['name']} endpoint...")
            response = requests.get(f"http://localhost:8000/api/files/{sample_file['directory']}/{sample_file['name']}")
            
            if response.status_code == 200:
                geojson = response.json()
                feature_count = len(geojson.get("features", []))
                print(f"Success! Retrieved GeoJSON with {feature_count} features.")
            else:
                print(f"Error: {response.status_code} - {response.text}")
        
        # Test the HTML interface
        print("\nTesting HTML interface...")
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            html_size = len(response.text)
            print(f"Success! Retrieved HTML interface ({html_size} bytes).")
        else:
            print(f"Error: {response.status_code} - {response.text}")
        
        print("\nAll tests completed!")
        print("The FastAPI server is running at http://localhost:8000")
        print("Press Ctrl+C to stop the server and exit.")
        
        # Keep the server running until user interrupts
        server_process.wait()
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure it's running on port 8000.")
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        # Terminate the server process
        server_process.terminate()
        server_process.wait()
        print("Server stopped.")

if __name__ == "__main__":
    test_api_server()