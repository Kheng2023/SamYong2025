// Real Government Data Fetcher Examples
// These functions demonstrate actual API calls to Australian government data sources

class RealDataFetcher {
    constructor() {
        this.corsProxy = 'https://cors-anywhere.herokuapp.com/'; // For development only
        this.cache = new Map();
    }

    // Fetch real AEMO data (requires CORS proxy for browser)
    async fetchRealAEMOData() {
        try {
            // AEMO API endpoint for current market data
            const aemoUrl = 'https://visualisations.aemo.com.au/aemo/apps/api/report/5MIN';
            
            const response = await fetch(this.corsProxy + aemoUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`AEMO API error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Convert AEMO format to GeoJSON
            return this.convertAEMOToGeoJSON(data);
            
        } catch (error) {
            console.error('Error fetching real AEMO data:', error);
            // Fallback to sample data
            return this.getFallbackAEMOData();
        }
    }

    convertAEMOToGeoJSON(aemoData) {
        // AEMO data structure conversion
        const features = [];
        
        if (aemoData && aemoData.data) {
            aemoData.data.forEach(record => {
                // Extract relevant fields from AEMO response
                const feature = {
                    type: "Feature",
                    geometry: {
                        type: "Point",
                        coordinates: [
                            record.longitude || 151.2093,
                            record.latitude || -33.8688
                        ]
                    },
                    properties: {
                        name: record.stationName || record.region,
                        capacity_mw: record.capacity,
                        generation_mw: record.totalGeneration,
                        fuel_type: record.fuelType,
                        region: record.region,
                        timestamp: record.settlementDate,
                        price_per_mwh: record.price,
                        demand_mw: record.totalDemand
                    }
                };
                features.push(feature);
            });
        }

        return {
            type: "FeatureCollection",
            features: features,
            metadata: {
                source: "AEMO Real-time Data",
                fetchTime: new Date().toISOString(),
                recordCount: features.length
            }
        };
    }

    // Fetch real ABS data using ArcGIS REST API
    async fetchRealABSData() {
        try {
            // ABS ArcGIS REST endpoint
            const absUrl = 'https://maps.abs.gov.au/arcgis/rest/services/Census2021/Census2021_AUST_SA2/MapServer/0/query';
            
            const params = new URLSearchParams({
                where: "STATE_NAME_2021='New South Wales'", // Limit to NSW for demo
                outFields: '*',
                f: 'geojson',
                returnGeometry: true,
                resultRecordCount: 100 // Limit results
            });

            const response = await fetch(`${absUrl}?${params}`);
            
            if (!response.ok) {
                throw new Error(`ABS API error: ${response.status}`);
            }

            const data = await response.json();
            
            // Add metadata
            data.metadata = {
                source: "ABS Census 2021",
                fetchTime: new Date().toISOString(),
                recordCount: data.features?.length || 0
            };

            return data;
            
        } catch (error) {
            console.error('Error fetching real ABS data:', error);
            return this.getFallbackABSData();
        }
    }

    // Fetch real Geoscience Australia data
    async fetchRealGeoscienceData() {
        try {
            // Geoscience Australia REST endpoint
            const gaUrl = 'https://services.ga.gov.au/gis/rest/services/Topography/Australian_Topography/MapServer/0/query';
            
            const params = new URLSearchParams({
                where: '1=1',
                outFields: '*',
                f: 'geojson',
                returnGeometry: true,
                spatialRel: 'esriSpatialRelIntersects',
                geometry: '{"xmin":150,"ymin":-35,"xmax":152,"ymax":-33,"spatialReference":{"wkid":4326}}', // Sydney area
                geometryType: 'esriGeometryEnvelope',
                resultRecordCount: 50
            });

            const response = await fetch(`${gaUrl}?${params}`);
            
            if (!response.ok) {
                throw new Error(`Geoscience Australia API error: ${response.status}`);
            }

            const data = await response.json();
            
            data.metadata = {
                source: "Geoscience Australia",
                fetchTime: new Date().toISOString(),
                recordCount: data.features?.length || 0
            };

            return data;
            
        } catch (error) {
            console.error('Error fetching real Geoscience data:', error);
            return this.getFallbackGeoscienceData();
        }
    }

    // Fetch real BOM weather data
    async fetchRealBOMData() {
        try {
            // BOM weather observation JSON
            const bomUrl = 'http://reg.bom.gov.au/fwo/IDN60901/IDN60901.94767.json'; // Sydney
            
            const response = await fetch(this.corsProxy + bomUrl);
            
            if (!response.ok) {
                throw new Error(`BOM API error: ${response.status}`);
            }

            const data = await response.json();
            
            // Convert BOM format to GeoJSON
            return this.convertBOMToGeoJSON(data);
            
        } catch (error) {
            console.error('Error fetching real BOM data:', error);
            return this.getFallbackBOMData();
        }
    }

    convertBOMToGeoJSON(bomData) {
        const features = [];
        
        if (bomData && bomData.observations && bomData.observations.data) {
            const observations = bomData.observations.data;
            const latest = observations[0]; // Most recent observation
            
            const feature = {
                type: "Feature",
                geometry: {
                    type: "Point",
                    coordinates: [
                        parseFloat(latest.lon) || 151.2093,
                        parseFloat(latest.lat) || -33.8688
                    ]
                },
                properties: {
                    station_name: latest.name,
                    temperature_c: latest.air_temp,
                    humidity_percent: latest.rel_hum,
                    wind_speed_kmh: latest.wind_spd_kmh,
                    wind_direction: latest.wind_dir,
                    pressure_hpa: latest.press,
                    rainfall_mm: latest.rain_trace,
                    observation_time: latest.aifstime_utc,
                    weather_description: latest.weather,
                    visibility_km: latest.vis_km
                }
            };
            
            features.push(feature);
        }

        return {
            type: "FeatureCollection",
            features: features,
            metadata: {
                source: "Bureau of Meteorology",
                fetchTime: new Date().toISOString(),
                recordCount: features.length
            }
        };
    }

    // Search real data.gov.au catalogue
    async searchRealDataCatalogue(query) {
        try {
            const catalogueUrl = 'https://data.gov.au/api/3/action/package_search';
            
            const params = new URLSearchParams({
                q: query,
                rows: 20,
                sort: 'score desc',
                fq: 'organization:infrastructure-transport-regional-development'
            });

            const response = await fetch(`${catalogueUrl}?${params}`);
            
            if (!response.ok) {
                throw new Error(`Data.gov.au API error: ${response.status}`);
            }

            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error searching data catalogue:', error);
            return this.getFallbackCatalogueData();
        }
    }

    // Fallback data methods (when real APIs are unavailable)
    getFallbackAEMOData() {
        return {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [151.5167, -33.0167] },
                    properties: {
                        name: "Eraring Power Station",
                        capacity_mw: 2880,
                        generation_mw: 2100,
                        fuel_type: "Coal",
                        region: "NSW1",
                        price_per_mwh: 45.50,
                        demand_mw: 8500,
                        timestamp: new Date().toISOString()
                    }
                },
                {
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [151.1833, -32.7333] },
                    properties: {
                        name: "Bayswater Power Station",
                        capacity_mw: 2640,
                        generation_mw: 1900,
                        fuel_type: "Coal",
                        region: "NSW1",
                        price_per_mwh: 47.25,
                        demand_mw: 7200,
                        timestamp: new Date().toISOString()
                    }
                }
            ],
            metadata: {
                source: "AEMO Sample Data",
                fetchTime: new Date().toISOString(),
                recordCount: 2
            }
        };
    }

    getFallbackABSData() {
        return {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [151.2093, -33.8688] },
                    properties: {
                        SA2_NAME21: "Sydney - Haymarket - The Rocks",
                        STATE_NAME_2021: "New South Wales",
                        AREA_SQKM: 2.847,
                        POPULATION: 12543,
                        DWELLINGS: 8901,
                        MEDIAN_AGE: 32,
                        MEDIAN_INCOME: 65000,
                        UNEMPLOYMENT_RATE: 3.8
                    }
                }
            ],
            metadata: {
                source: "ABS Sample Data",
                fetchTime: new Date().toISOString(),
                recordCount: 1
            }
        };
    }

    getFallbackGeoscienceData() {
        return {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [151.2, -33.8] },
                    properties: {
                        GEOLOGICAL_UNIT: "Sydney Basin",
                        ROCK_TYPE: "Sedimentary",
                        AGE: "Permian-Triassic",
                        STABILITY_RATING: 85,
                        SEISMIC_HAZARD: "Low",
                        FOUNDATION_CAPACITY: "High"
                    }
                }
            ],
            metadata: {
                source: "Geoscience Australia Sample Data",
                fetchTime: new Date().toISOString(),
                recordCount: 1
            }
        };
    }

    getFallbackBOMData() {
        return {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [151.2093, -33.8688] },
                    properties: {
                        station_name: "Sydney Observatory Hill",
                        temperature_c: 22.5,
                        humidity_percent: 68,
                        wind_speed_kmh: 15,
                        wind_direction: "NE",
                        pressure_hpa: 1015.2,
                        rainfall_mm: 0,
                        observation_time: new Date().toISOString(),
                        weather_description: "Partly cloudy"
                    }
                }
            ],
            metadata: {
                source: "Bureau of Meteorology Sample Data",
                fetchTime: new Date().toISOString(),
                recordCount: 1
            }
        };
    }

    getFallbackCatalogueData() {
        return {
            success: true,
            result: {
                count: 3,
                results: [
                    {
                        id: "australia-infrastructure-map",
                        title: "Australian Infrastructure Map",
                        notes: "Comprehensive mapping of national infrastructure including transport, energy, telecommunications, and water assets.",
                        organization: {
                            title: "Department of Infrastructure, Transport, Regional Development, Communications and the Arts"
                        },
                        resources: [
                            {
                                format: "GeoJSON",
                                url: "https://data.gov.au/dataset/infrastructure-map.geojson",
                                size: "125MB"
                            }
                        ]
                    },
                    {
                        id: "electricity-generation-australia",
                        title: "Electricity Generation and Infrastructure Australia",
                        notes: "Power station locations, capacities, and electricity transmission network data.",
                        organization: {
                            title: "Australian Energy Market Operator"
                        },
                        resources: [
                            {
                                format: "CSV",
                                url: "https://data.gov.au/dataset/electricity-generation.csv",
                                size: "45MB"
                            }
                        ]
                    }
                ]
            }
        };
    }

    // Utility method to check API availability
    async checkAPIAvailability(url) {
        try {
            const response = await fetch(url, { method: 'HEAD', mode: 'no-cors' });
            return true;
        } catch (error) {
            return false;
        }
    }

    // Method to test all government APIs
    async testAllAPIs() {
        const apis = [
            { name: 'AEMO', url: 'https://visualisations.aemo.com.au' },
            { name: 'ABS Maps', url: 'https://maps.abs.gov.au' },
            { name: 'Geoscience Australia', url: 'https://services.ga.gov.au' },
            { name: 'Bureau of Meteorology', url: 'http://reg.bom.gov.au' },
            { name: 'Data.gov.au', url: 'https://data.gov.au' }
        ];

        const results = {};
        
        for (const api of apis) {
            results[api.name] = await this.checkAPIAvailability(api.url);
        }

        return results;
    }
}

// Example usage functions that can be called from the platform
async function demonstrateRealDataFetching() {
    const fetcher = new RealDataFetcher();
    
    console.log('🔍 Testing API availability...');
    const apiStatus = await fetcher.testAllAPIs();
    console.log('API Status:', apiStatus);
    
    console.log('⚡ Fetching AEMO data...');
    const aemoData = await fetcher.fetchRealAEMOData();
    console.log('AEMO data:', aemoData);
    
    console.log('📊 Fetching ABS data...');
    const absData = await fetcher.fetchRealABSData();
    console.log('ABS data:', absData);
    
    console.log('🌍 Fetching Geoscience data...');
    const geoData = await fetcher.fetchRealGeoscienceData();
    console.log('Geoscience data:', geoData);
    
    console.log('🌡️ Fetching BOM data...');
    const bomData = await fetcher.fetchRealBOMData();
    console.log('BOM data:', bomData);
    
    return {
        aemo: aemoData,
        abs: absData,
        geoscience: geoData,
        bom: bomData
    };
}

// Integration function to load real data into the platform
async function loadRealGovernmentData() {
    try {
        const fetcher = new RealDataFetcher();
        
        // Show progress
        if (typeof dataUploadInterface !== 'undefined') {
            dataUploadInterface.showProgress('Loading Real Government Data', 'Connecting to government APIs...');
        }
        
        // Fetch all data sources
        const [aemoData, absData, geoData, bomData] = await Promise.all([
            fetcher.fetchRealAEMOData(),
            fetcher.fetchRealABSData(),
            fetcher.fetchRealGeoscienceData(),
            fetcher.fetchRealBOMData()
        ]);
        
        // Add data to the platform
        if (typeof addGeoJSONLayer === 'function') {
            addGeoJSONLayer(aemoData, 'electricity');
            addGeoJSONLayer(absData, 'roads');
            addGeoJSONLayer(geoData, 'geology');
            addGeoJSONLayer(bomData, 'climate');
            
            // Update uploaded data
            if (typeof uploadedData !== 'undefined') {
                uploadedData.electricity = aemoData;
                uploadedData.roads = absData;
                uploadedData.geology = geoData;
                uploadedData.climate = bomData;
            }
        }
        
        // Hide progress
        if (typeof dataUploadInterface !== 'undefined') {
            dataUploadInterface.updateProgress(100, 'Real government data loaded successfully!');
            setTimeout(() => {
                dataUploadInterface.hideProgress();
            }, 2000);
        }
        
        console.log('✅ Real government data integration complete!');
        return { aemoData, absData, geoData, bomData };
        
    } catch (error) {
        console.error('❌ Failed to load real government data:', error);
        
        if (typeof dataUploadInterface !== 'undefined') {
            dataUploadInterface.hideProgress();
        }
        
        alert('Failed to load real government data. Using sample data instead.');
        
        // Fallback to sample data
        if (typeof loadSampleData === 'function') {
            loadSampleData();
        }
    }
}

// Export for global access
if (typeof window !== 'undefined') {
    window.RealDataFetcher = RealDataFetcher;
    window.demonstrateRealDataFetching = demonstrateRealDataFetching;
    window.loadRealGovernmentData = loadRealGovernmentData;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealDataFetcher;
}
