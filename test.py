import requests

def get_sa2_population():
    url = "https://data.api.abs.gov.au/rest/data/ABS,ERP_POP,1.0/SA2.?detail=dataonly"
    headers = {"Accept": "application/vnd.sdmx.data+json;version=1.0.0-wd"}
    resp = requests.get(url, headers=headers)
    print(resp.status_code)
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code} error: {resp.text}")
        return None
    try:
        data = resp.json()
    except Exception as e:
        print(f"Could not decode JSON; raw response:\n{resp.text}")
        raise
    # Example: Check the first keys of the data
    print("Top-level keys:", list(data.keys()))
    # ... (continue your parsing)
    return data

def list_dataflows():
    url = "https://data.api.abs.gov.au/rest/dataflow"
    resp = requests.get(url)
    print(resp.status_code)
    print(resp.text)  # show first 1000 chars for preview
    
def get_dataflow_structure(dataflow_code):
    url = f"https://data.api.abs.gov.au/rest/dataflow/{dataflow_code}"
    resp = requests.get(url)
    print(resp.status_code)
    print(resp.text)





if __name__ == "__main__":
    list_dataflows()
    get_dataflow_structure("ABS,ERP_POP,1.0")
    get_sa2_population()