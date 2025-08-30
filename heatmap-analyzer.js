// Advanced Heatmap Generator for Data Center Location Analysis
// Implements comprehensive suitability analysis with multiple data sources

class DataCenterHeatmapAnalyzer {
    constructor() {
        this.analysisGrid = [];
        this.gridResolution = 0.1; // degrees (approximately 11km)
        this.australiaBounds = {
            north: -10,
            south: -44,
            east: 154,
            west: 113
        };
        
        this.criteriaWeights = {
            userDemographics: 0.20,      // 20% - Target audience concentration
            networkInfrastructure: 0.25, // 25% - Fiber networks & IXPs
            energyGrid: 0.20,            // 20% - Power reliability & capacity
            renewableEnergy: 0.10,       // 10% - Green energy availability
            climateWater: 0.15,          // 15% - Cooling efficiency & water
            disasterRisk: 0.10           // 10% - Natural disaster mitigation
        };
        
        this.heatmapLayer = null;
        this.analysisData = {};
    }

    // Generate comprehensive heatmap analysis
    async generateHeatmap(uploadedData) {
        console.log('🔥 Starting heatmap generation...');
        
        // Clear previous analysis
        this.clearHeatmap();
        
        // Create analysis grid
        this.createAnalysisGrid();
        
        // Analyze each grid cell
        const analysisPromises = this.analysisGrid.map(cell => 
            this.analyzeGridCell(cell, uploadedData)
        );
        
        const results = await Promise.all(analysisPromises);
        
        // Generate heatmap visualization
        this.visualizeHeatmap(results);
        
        // Show analysis summary
        this.showAnalysisSummary(results);
        
        return results;
    }

    // Create analysis grid covering Australia
    createAnalysisGrid() {
        this.analysisGrid = [];
        
        for (let lat = this.australiaBounds.south; lat <= this.australiaBounds.north; lat += this.gridResolution) {
            for (let lng = this.australiaBounds.west; lng <= this.australiaBounds.east; lng += this.gridResolution) {
                this.analysisGrid.push({
                    lat: lat,
                    lng: lng,
                    cellId: `${lat.toFixed(2)}_${lng.toFixed(2)}`
                });
            }
        }
        
        console.log(`📊 Created analysis grid: ${this.analysisGrid.length} cells`);
    }

    // Analyze individual grid cell for all criteria
    async analyzeGridCell(cell, uploadedData) {
        const scores = {
            userDemographics: this.analyzeUserDemographics(cell, uploadedData),
            networkInfrastructure: this.analyzeNetworkInfrastructure(cell, uploadedData),
            energyGrid: this.analyzeEnergyGrid(cell, uploadedData),
            renewableEnergy: this.analyzeRenewableEnergy(cell, uploadedData),
            climateWater: this.analyzeClimateWater(cell, uploadedData),
            disasterRisk: this.analyzeDisasterRisk(cell, uploadedData)
        };

        // Calculate weighted total score
        const totalScore = Object.keys(scores).reduce((total, criterion) => {
            return total + (scores[criterion] * this.criteriaWeights[criterion]);
        }, 0);

        return {
            ...cell,
            scores,
            totalScore,
            suitabilityLevel: this.getSuitabilityLevel(totalScore)
        };
    }

    // Analyze user demographics (target audience concentration)
    analyzeUserDemographics(cell, data) {
        // Use the specialized user demographics data
        const populationData = data.userDemographics;
        if (!populationData || !populationData.features) return 0.3;

        let score = 0;
        let nearbyFeatures = 0;

        populationData.features.forEach(feature => {
            if (!feature.geometry || !feature.geometry.coordinates) return;
            
            const distance = this.calculateDistance(
                cell.lat, cell.lng,
                feature.geometry.coordinates[1], feature.geometry.coordinates[0]
            );

            if (distance < 50) { // Within 50km
                const proximity = Math.max(0, (50 - distance) / 50);
                
                // Use actual population density if available
                const popDensity = feature.properties.populationDensity || feature.properties.targetScore || 50;
                const densityScore = Math.min(1, popDensity / 200); // Normalize
                
                score += proximity * densityScore;
                nearbyFeatures++;
            }
        });

        // Major cities get higher scores
        const majorCities = [
            { name: 'Sydney', lat: -33.8688, lng: 151.2093, weight: 1.0 },
            { name: 'Melbourne', lat: -37.8136, lng: 144.9631, weight: 0.9 },
            { name: 'Brisbane', lat: -27.4698, lng: 153.0251, weight: 0.8 },
            { name: 'Perth', lat: -31.9505, lng: 115.8605, weight: 0.7 },
            { name: 'Adelaide', lat: -34.9285, lng: 138.6007, weight: 0.6 }
        ];

        majorCities.forEach(city => {
            const distance = this.calculateDistance(cell.lat, cell.lng, city.lat, city.lng);
            if (distance < 100) {
                const proximity = Math.max(0, (100 - distance) / 100);
                score += proximity * city.weight;
            }
        });

        return Math.min(1.0, score / 3); // Normalize to 0-1
    }

    // Analyze network infrastructure (fiber networks & IXPs)
    analyzeNetworkInfrastructure(cell, data) {
        const networkData = data.networkInfrastructure;
        if (!networkData || !networkData.features) return 0.2;

        let score = 0;
        let fiberDensity = 0;

        networkData.features.forEach(feature => {
            if (!feature.geometry || !feature.geometry.coordinates) return;
            
            const distance = this.calculateDistance(
                cell.lat, cell.lng,
                feature.geometry.coordinates[1], feature.geometry.coordinates[0]
            );

            if (distance < 25) { // Within 25km
                const proximity = Math.max(0, (25 - distance) / 25);
                
                // Use actual network score if available
                const networkScore = feature.properties.networkScore || feature.properties.providers || 50;
                const normalizedScore = Math.min(1, networkScore / 100);
                
                score += proximity * normalizedScore;
                fiberDensity++;
            }
        });

        return Math.min(1.0, (score + fiberDensity * 0.1) / 3);
    }

    // Analyze energy grid reliability and capacity
    analyzeEnergyGrid(cell, data) {
        const electricityData = data.energyGrid;
        if (!electricityData || !electricityData.features) return 0.3;

        let score = 0;
        let powerStations = 0;
        let totalCapacity = 0;

        electricityData.features.forEach(feature => {
            if (!feature.geometry || !feature.geometry.coordinates) return;
            
            const distance = this.calculateDistance(
                cell.lat, cell.lng,
                feature.geometry.coordinates[1], feature.geometry.coordinates[0]
            );

            if (distance < 100) { // Within 100km
                const proximity = Math.max(0, (100 - distance) / 100);
                const capacity = feature.properties.capacity || feature.properties.gridScore || 100;
                
                score += proximity * (capacity / 1000); // Normalize by 1000MW
                totalCapacity += capacity;
                powerStations++;
            }
        });

        // Grid redundancy bonus (multiple power sources)
        const redundancyBonus = Math.min(0.3, powerStations * 0.05);
        
        return Math.min(1.0, (score / 5) + redundancyBonus);
    }

    // Analyze renewable energy availability
    analyzeRenewableEnergy(cell, data) {
        const renewableData = data.renewableEnergy;
        
        let score = 0;
        
        if (renewableData && renewableData.features) {
            renewableData.features.forEach(feature => {
                if (!feature.geometry || !feature.geometry.coordinates) return;
                
                const distance = this.calculateDistance(
                    cell.lat, cell.lng,
                    feature.geometry.coordinates[1], feature.geometry.coordinates[0]
                );

                if (distance < 50) { // Within 50km
                    const proximity = Math.max(0, (50 - distance) / 50);
                    const capacityScore = feature.properties.capacityScore || 50;
                    const normalizedScore = capacityScore / 100;
                    
                    score += proximity * normalizedScore;
                }
            });
        }
        
        // Solar potential (based on latitude - closer to equator = better)
        const solarScore = Math.max(0, (30 - Math.abs(cell.lat)) / 30);
        
        // Wind potential (coastal areas and hills)
        const windScore = this.calculateWindPotential(cell);
        
        // Hydro potential (near water sources)
        const hydroScore = this.calculateHydroPotential(cell, data);
        
        // Combine actual data with calculated potential
        const actualDataScore = Math.min(1.0, score / 2);
        const potentialScore = (solarScore * 0.5 + windScore * 0.3 + hydroScore * 0.2);
        
        return (actualDataScore * 0.6 + potentialScore * 0.4);
    }

    // Analyze climate and water availability
    analyzeClimateWater(cell, data) {
        const climateWaterData = data.climateWater;
        
        let score = 0;
        
        if (climateWaterData && climateWaterData.features) {
            climateWaterData.features.forEach(feature => {
                if (!feature.geometry || !feature.geometry.coordinates) return;
                
                const distance = this.calculateDistance(
                    cell.lat, cell.lng,
                    feature.geometry.coordinates[1], feature.geometry.coordinates[0]
                );

                if (distance < 50) { // Within 50km
                    const proximity = Math.max(0, (50 - distance) / 50);
                    
                    if (feature.properties.type === 'Climate Station') {
                        const climateScore = feature.properties.climateScore || 50;
                        score += proximity * (climateScore / 100);
                    } else if (feature.properties.type === 'Water Source') {
                        const waterScore = feature.properties.waterScore || feature.properties.reliability || 50;
                        score += proximity * (waterScore / 100);
                    }
                }
            });
        }

        // Temperature analysis (cooler = better for free cooling)
        const tempScore = this.calculateTemperatureScore(cell);
        
        // Humidity (lower = better for cooling)
        const humidityScore = this.calculateHumidityScore(cell);
        
        // Combine actual data with calculated scores
        const actualDataScore = Math.min(1.0, score / 2);
        const calculatedScore = (tempScore * 0.6 + humidityScore * 0.4);
        
        return (actualDataScore * 0.5 + calculatedScore * 0.5);
    }

    // Analyze natural disaster risk
    analyzeDisasterRisk(cell, data) {
        const disasterData = data.disasterRisk;
        
        let riskScore = 0.8; // Start with low risk baseline
        
        if (disasterData && disasterData.features) {
            disasterData.features.forEach(feature => {
                if (!feature.geometry || !feature.geometry.coordinates) return;
                
                const distance = this.calculateDistance(
                    cell.lat, cell.lng,
                    feature.geometry.coordinates[1], feature.geometry.coordinates[0]
                );

                if (distance < 100) { // Within 100km
                    const proximity = (100 - distance) / 100;
                    const safetyScore = feature.properties.safetyScore || 70;
                    const riskImpact = (100 - safetyScore) / 100; // Convert safety to risk
                    
                    riskScore -= proximity * riskImpact * 0.3; // Reduce score based on risk
                }
            });
        }
        
        // Additional calculated risk factors
        const seismicScore = this.calculateSeismicRisk(cell);
        const floodScore = this.calculateFloodRisk(cell, data);
        const bushfireScore = this.calculateBushfireRisk(cell);
        const cycloneScore = this.calculateCycloneRisk(cell);
        
        // Average risk scores (inverted - lower risk = higher score)
        const calculatedRisk = 1 - ((1 - seismicScore) + (1 - floodScore) + (1 - bushfireScore) + (1 - cycloneScore)) / 4;
        
        return Math.max(0, Math.min(1.0, (riskScore + calculatedRisk) / 2));
    }

    // Helper method: Calculate distance between two points
    calculateDistance(lat1, lng1, lat2, lng2) {
        const R = 6371; // Earth's radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                 Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                 Math.sin(dLng/2) * Math.sin(dLng/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    // Environmental analysis helper methods
    calculateWindPotential(cell) {
        // Coastal areas and elevated regions have better wind
        const coastalBonus = this.isCoastal(cell) ? 0.6 : 0.2;
        const elevationBonus = Math.max(0, (Math.abs(cell.lat) - 25) / 20); // Higher latitudes
        return Math.min(1.0, coastalBonus + elevationBonus);
    }

    calculateHydroPotential(cell, data) {
        const waterData = data.water;
        if (!waterData || !waterData.features) return 0.2;

        let potential = 0;
        waterData.features.forEach(feature => {
            const distance = this.calculateDistance(
                cell.lat, cell.lng,
                feature.geometry.coordinates[1], feature.geometry.coordinates[0]
            );
            if (distance < 100) {
                potential += Math.max(0, (100 - distance) / 100);
            }
        });

        return Math.min(1.0, potential / 2);
    }

    calculateTemperatureScore(cell) {
        // Southern latitudes are cooler (better for data centers)
        const latitudeScore = Math.max(0, (Math.abs(cell.lat) - 25) / 20);
        
        // Coastal areas are more moderate
        const coastalModeration = this.isCoastal(cell) ? 0.2 : 0;
        
        return Math.min(1.0, latitudeScore + coastalModeration);
    }

    calculateHumidityScore(cell) {
        // Inland and southern areas typically have lower humidity
        const inlandBonus = this.isCoastal(cell) ? 0.3 : 0.7;
        const latitudeBonus = Math.max(0, (Math.abs(cell.lat) - 20) / 30);
        
        return Math.min(1.0, inlandBonus + latitudeBonus);
    }

    calculateSeismicRisk(cell) {
        // Australia's seismic zones (lower risk in most areas)
        const highRiskZones = [
            { lat: -31.9505, lng: 115.8605, radius: 100 }, // Perth area
            { lat: -37.8136, lng: 144.9631, radius: 80 },  // Melbourne area
            { lat: -19.2590, lng: 146.8169, radius: 150 }  // North Queensland
        ];

        let riskLevel = 0.1; // Base low risk for Australia
        
        highRiskZones.forEach(zone => {
            const distance = this.calculateDistance(cell.lat, cell.lng, zone.lat, zone.lng);
            if (distance < zone.radius) {
                const proximity = (zone.radius - distance) / zone.radius;
                riskLevel += proximity * 0.4;
            }
        });

        return Math.max(0, 1 - riskLevel);
    }

    calculateFloodRisk(cell, data) {
        // Areas near rivers and low-lying coastal areas
        let risk = 0.1; // Base risk
        
        if (this.isCoastal(cell)) {
            risk += 0.3; // Coastal flood risk
        }

        // Near major rivers (approximate major river locations)
        const majorRivers = [
            { lat: -33.8688, lng: 151.2093 }, // Parramatta River
            { lat: -37.8136, lng: 144.9631 }, // Yarra River
            { lat: -27.4698, lng: 153.0251 }  // Brisbane River
        ];

        majorRivers.forEach(river => {
            const distance = this.calculateDistance(cell.lat, cell.lng, river.lat, river.lng);
            if (distance < 50) {
                const proximity = (50 - distance) / 50;
                risk += proximity * 0.2;
            }
        });

        return Math.max(0, 1 - risk);
    }

    calculateBushfireRisk(cell) {
        // Higher risk in forested and dry inland areas
        let risk = 0.2; // Base risk
        
        // Higher risk in certain states and inland areas
        if (cell.lat > -30 && cell.lat < -20 && cell.lng > 140) {
            risk += 0.4; // Inland Queensland/NSW
        }
        
        if (cell.lat < -35 && cell.lng > 140 && cell.lng < 150) {
            risk += 0.3; // Victoria bush areas
        }

        return Math.max(0, 1 - risk);
    }

    calculateCycloneRisk(cell) {
        // Northern areas have cyclone risk
        let risk = 0.1; // Base risk
        
        if (cell.lat > -26) { // North of Tropic of Capricorn
            risk += 0.6;
            
            if (this.isCoastal(cell)) {
                risk += 0.2; // Higher coastal risk
            }
        }

        return Math.max(0, 1 - risk);
    }

    isCoastal(cell) {
        // Simplified coastal detection (within ~100km of major coastlines)
        const coastalThreshold = 1.0; // degrees (~111km)
        
        return (
            cell.lng < this.australiaBounds.west + coastalThreshold ||
            cell.lng > this.australiaBounds.east - coastalThreshold ||
            cell.lat > this.australiaBounds.north - coastalThreshold ||
            cell.lat < this.australiaBounds.south + coastalThreshold
        );
    }

    getSuitabilityLevel(score) {
        if (score >= 0.8) return 'Excellent';
        if (score >= 0.6) return 'Very Good';
        if (score >= 0.4) return 'Good';
        if (score >= 0.2) return 'Fair';
        return 'Poor';
    }

    // Visualize heatmap on the map
    visualizeHeatmap(results) {
        if (this.heatmapLayer) {
            map.removeLayer(this.heatmapLayer);
        }

        // Create heatmap points
        const heatmapData = results
            .filter(cell => cell.totalScore > 0.1) // Filter out very low scores
            .map(cell => [
                cell.lat,
                cell.lng,
                cell.totalScore
            ]);

        // Create heatmap layer
        this.heatmapLayer = L.heatLayer(heatmapData, {
            radius: 50,
            blur: 30,
            maxZoom: 15,
            max: 1.0,
            gradient: {
                0.0: '#313695',
                0.2: '#4575b4',
                0.4: '#74add1',
                0.6: '#abd9e9',
                0.7: '#fee090',
                0.8: '#fdae61',
                0.9: '#f46d43',
                1.0: '#d73027'
            }
        }).addTo(map);

        // Add top locations as markers
        this.addTopLocationMarkers(results);
    }

    addTopLocationMarkers(results) {
        // Find top 10 locations
        const topLocations = results
            .sort((a, b) => b.totalScore - a.totalScore)
            .slice(0, 10);

        topLocations.forEach((location, index) => {
            const marker = L.marker([location.lat, location.lng], {
                icon: L.divIcon({
                    html: `<div style="background: #d73027; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${index + 1}</div>`,
                    className: 'top-location-marker',
                    iconSize: [30, 30],
                    iconAnchor: [15, 15]
                })
            });

            const popupContent = this.createDetailedLocationPopup(location, index + 1);
            marker.bindPopup(popupContent);
            marker.addTo(layers.analysis);
        });
    }

    createDetailedLocationPopup(location, rank) {
        return `
            <div style="font-family: Arial, sans-serif; width: 300px;">
                <h3 style="color: #d73027; margin: 0 0 10px 0;">🏆 Rank #${rank} Location</h3>
                <p><strong>Overall Score:</strong> ${(location.totalScore * 100).toFixed(1)}%</p>
                <p><strong>Suitability:</strong> ${location.suitabilityLevel}</p>
                <p><strong>Coordinates:</strong> ${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}</p>
                
                <h4 style="margin: 15px 0 5px 0;">Detailed Scores:</h4>
                <div style="font-size: 12px;">
                    <div>👥 User Demographics: ${(location.scores.userDemographics * 100).toFixed(1)}%</div>
                    <div>🌐 Network Infrastructure: ${(location.scores.networkInfrastructure * 100).toFixed(1)}%</div>
                    <div>⚡ Energy Grid: ${(location.scores.energyGrid * 100).toFixed(1)}%</div>
                    <div>🔋 Renewable Energy: ${(location.scores.renewableEnergy * 100).toFixed(1)}%</div>
                    <div>🌡️ Climate & Water: ${(location.scores.climateWater * 100).toFixed(1)}%</div>
                    <div>🛡️ Disaster Risk: ${(location.scores.disasterRisk * 100).toFixed(1)}%</div>
                </div>
            </div>
        `;
    }

    showAnalysisSummary(results) {
        const topLocation = results.reduce((best, current) => 
            current.totalScore > best.totalScore ? current : best
        );

        const averageScore = results.reduce((sum, cell) => sum + cell.totalScore, 0) / results.length;

        const summary = `
            🔥 HEATMAP ANALYSIS COMPLETE
            
            📊 Analysis Coverage: ${results.length} grid cells
            🏆 Best Score: ${(topLocation.totalScore * 100).toFixed(1)}%
            📈 Average Score: ${(averageScore * 100).toFixed(1)}%
            📍 Top Location: ${topLocation.lat.toFixed(4)}, ${topLocation.lng.toFixed(4)}
            
            💡 Check the red numbered markers for top 10 locations!
            🎯 Use the heatmap colors to identify suitable regions.
        `;

        console.log(summary);
        alert(summary);
    }

    clearHeatmap() {
        if (this.heatmapLayer) {
            map.removeLayer(this.heatmapLayer);
            this.heatmapLayer = null;
        }
        
        // Clear analysis markers
        layers.analysis.clearLayers();
    }

    updateCriteriaWeights(newWeights) {
        this.criteriaWeights = { ...this.criteriaWeights, ...newWeights };
    }
}

// Export for use in main application
if (typeof window !== 'undefined') {
    window.DataCenterHeatmapAnalyzer = DataCenterHeatmapAnalyzer;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataCenterHeatmapAnalyzer;
}
