import requests
import json

url = "https://hosting.wsapi.cloud.bom.gov.au/arcgis/rest/services/flood/National_Flood_Gauge_Network/FeatureServer/0/query"
params = {
    'where': '1=1',
    'outFields': '*',
    'f': 'geojson'
}

response = requests.get(url, params=params)
with open('flood_gauges.geojson', 'w') as f:
    json.dump(response.json(), f)