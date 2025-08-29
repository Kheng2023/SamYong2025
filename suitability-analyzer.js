// Advanced Suitability Analysis Algorithm
// This module provides sophisticated algorithms for data center location analysis

class DataCenterSuitabilityAnalyzer {
    constructor() {
        this.weights = {
            power: 0.25,           // Electricity availability and reliability
            connectivity: 0.20,    // Telecommunications infrastructure
            cooling: 0.15,         // Climate and cooling requirements
            water: 0.12,           // Water supply for cooling
            transport: 0.10,       // Transportation accessibility
            geology: 0.08,         // Geological stability
            security: 0.05,        // Physical security considerations
            regulations: 0.05      // Regulatory environment
        };
        
        this.criteria = {
            power: {
                minCapacity: 50,        // Minimum MW capacity required
                reliabilityThreshold: 0.8,  // Minimum reliability factor
                redundancyRequired: true,    // Backup power required
                renewablePreference: 0.3     // Preference for renewable energy
            },
            connectivity: {
                minBandwidth: 1000,     // Minimum Gbps
                latencyThreshold: 10,   // Maximum latency in ms
                redundancyRequired: true,
                internationalRequired: false
            },
            cooling: {
                maxTemperature: 25,     // Maximum average temperature
                maxHumidity: 70,        // Maximum humidity percentage
                coolingDaysLimit: 200   // Maximum cooling days per year
            },
            water: {
                minCapacity: 1000,      // Minimum daily ML capacity
                qualityThreshold: 85,   // Minimum water quality percentage
                sustainabilityFactor: 0.7
            },
            transport: {
                minAccessibility: 70,   // Minimum accessibility score
                freightAccess: true,    // Freight transportation required
                airportProximity: 50    // Maximum km to major airport
            },
            geology: {
                minStability: 75,       // Minimum soil stability percentage
                maxSeismicRisk: 3.0,    // Maximum seismic magnitude
                floodRiskTolerance: 0.1 // Maximum flood risk
            }
        };
    }

    // Main analysis method
    analyzeLocation(lat, lng, dataLayers) {
        const scores = {
            power: this.analyzePowerInfrastructure(lat, lng, dataLayers.electricity),
            connectivity: this.analyzeConnectivity(lat, lng, dataLayers.telecommunications),
            cooling: this.analyzeCoolingRequirements(lat, lng, dataLayers.climate),
            water: this.analyzeWaterSupply(lat, lng, dataLayers.water),
            transport: this.analyzeTransportation(lat, lng, dataLayers.transport),
            geology: this.analyzeGeology(lat, lng, dataLayers.geology),
            security: this.analyzeSecurityFactors(lat, lng, dataLayers),
            regulations: this.analyzeRegulatoryEnvironment(lat, lng, dataLayers)
        };

        const weightedScore = this.calculateWeightedScore(scores);
        const riskFactors = this.identifyRiskFactors(scores);
        const recommendations = this.generateRecommendations(scores, lat, lng);

        return {
            overallScore: weightedScore,
            detailedScores: scores,
            riskFactors: riskFactors,
            recommendations: recommendations,
            suitabilityLevel: this.getSuitabilityLevel(weightedScore),
            coordinates: { lat, lng }
        };
    }

    // Analyze power infrastructure
    analyzePowerInfrastructure(lat, lng, electricityData) {
        if (!electricityData || !electricityData.features) {
            return { score: 0.3, factors: ['No electricity data available'] };
        }

        let score = 0;
        let factors = [];
        let nearestStation = null;
        let minDistance = Infinity;
        let totalCapacity = 0;
        let reliabilityScore = 0;
        let renewableRatio = 0;

        // Find nearby power stations
        electricityData.features.forEach(station => {
            const distance = this.calculateDistance(
                lat, lng,
                station.geometry.coordinates[1],
                station.geometry.coordinates[0]
            );

            if (distance < 100) { // Within 100km
                totalCapacity += station.properties.capacity_mw || 0;
                reliabilityScore += station.properties.reliability_factor || 0;
                
                if (station.properties.type === 'Wind' || 
                    station.properties.type === 'Solar' || 
                    station.properties.type === 'Hydro') {
                    renewableRatio += 1;
                }

                if (distance < minDistance) {
                    minDistance = distance;
                    nearestStation = station;
                }
            }
        });

        const stationCount = electricityData.features.filter(station => {
            const distance = this.calculateDistance(
                lat, lng,
                station.geometry.coordinates[1],
                station.geometry.coordinates[0]
            );
            return distance < 100;
        }).length;

        renewableRatio = stationCount > 0 ? renewableRatio / stationCount : 0;
        reliabilityScore = stationCount > 0 ? reliabilityScore / stationCount : 0;

        // Scoring logic
        if (totalCapacity >= this.criteria.power.minCapacity) {
            score += 0.4;
            factors.push(`Adequate capacity: ${totalCapacity}MW`);
        } else {
            factors.push(`Insufficient capacity: ${totalCapacity}MW (need ${this.criteria.power.minCapacity}MW)`);
        }

        if (reliabilityScore >= this.criteria.power.reliabilityThreshold) {
            score += 0.3;
            factors.push(`Good reliability: ${(reliabilityScore * 100).toFixed(1)}%`);
        } else {
            factors.push(`Low reliability: ${(reliabilityScore * 100).toFixed(1)}%`);
        }

        if (minDistance < 20) {
            score += 0.2;
            factors.push(`Close to power source: ${minDistance.toFixed(1)}km`);
        } else if (minDistance < 50) {
            score += 0.1;
            factors.push(`Moderate distance to power: ${minDistance.toFixed(1)}km`);
        } else {
            factors.push(`Far from power source: ${minDistance.toFixed(1)}km`);
        }

        if (renewableRatio >= this.criteria.power.renewablePreference) {
            score += 0.1;
            factors.push(`Good renewable energy mix: ${(renewableRatio * 100).toFixed(1)}%`);
        }

        return {
            score: Math.min(score, 1.0),
            factors: factors,
            details: {
                nearestDistance: minDistance,
                totalCapacity: totalCapacity,
                reliability: reliabilityScore,
                renewableRatio: renewableRatio,
                stationCount: stationCount
            }
        };
    }

    // Analyze telecommunications connectivity
    analyzeConnectivity(lat, lng, telecomData) {
        if (!telecomData || !telecomData.features) {
            return { score: 0.2, factors: ['No telecommunications data available'] };
        }

        let score = 0;
        let factors = [];
        let nearestNode = null;
        let minDistance = Infinity;
        let maxCapacity = 0;
        let hasRedundancy = false;
        let hasInternational = false;
        let avgLatency = 0;

        // Analyze nearby telecom nodes
        telecomData.features.forEach(node => {
            const distance = this.calculateDistance(
                lat, lng,
                node.geometry.coordinates[1],
                node.geometry.coordinates[0]
            );

            if (distance < 50) { // Within 50km
                const capacity = this.parseCapacity(node.properties.capacity);
                maxCapacity = Math.max(maxCapacity, capacity);
                avgLatency += node.properties.latency_ms || 5;

                if (node.properties.redundancy === 'Triple' || node.properties.redundancy === 'Double') {
                    hasRedundancy = true;
                }

                if (node.properties.international_connection) {
                    hasInternational = true;
                }

                if (distance < minDistance) {
                    minDistance = distance;
                    nearestNode = node;
                }
            }
        });

        const nodeCount = telecomData.features.filter(node => {
            const distance = this.calculateDistance(
                lat, lng,
                node.geometry.coordinates[1],
                node.geometry.coordinates[0]
            );
            return distance < 50;
        }).length;

        avgLatency = nodeCount > 0 ? avgLatency / nodeCount : 10;

        // Scoring logic
        if (maxCapacity >= this.criteria.connectivity.minBandwidth) {
            score += 0.4;
            factors.push(`High bandwidth available: ${maxCapacity}Gbps`);
        } else {
            factors.push(`Limited bandwidth: ${maxCapacity}Gbps`);
        }

        if (avgLatency <= this.criteria.connectivity.latencyThreshold) {
            score += 0.3;
            factors.push(`Low latency: ${avgLatency.toFixed(1)}ms`);
        } else {
            factors.push(`High latency: ${avgLatency.toFixed(1)}ms`);
        }

        if (hasRedundancy) {
            score += 0.2;
            factors.push('Redundant connections available');
        } else {
            factors.push('Limited redundancy');
        }

        if (hasInternational) {
            score += 0.1;
            factors.push('International connectivity available');
        }

        return {
            score: Math.min(score, 1.0),
            factors: factors,
            details: {
                nearestDistance: minDistance,
                maxCapacity: maxCapacity,
                avgLatency: avgLatency,
                hasRedundancy: hasRedundancy,
                hasInternational: hasInternational,
                nodeCount: nodeCount
            }
        };
    }

    // Analyze cooling requirements based on climate
    analyzeCoolingRequirements(lat, lng, climateData) {
        if (!climateData || !climateData.features) {
            return { score: 0.5, factors: ['No climate data available'] };
        }

        let score = 0;
        let factors = [];
        let nearestClimate = null;
        let minDistance = Infinity;

        // Find nearest climate zone
        climateData.features.forEach(zone => {
            const distance = this.calculateDistance(
                lat, lng,
                zone.geometry.coordinates[1],
                zone.geometry.coordinates[0]
            );

            if (distance < minDistance) {
                minDistance = distance;
                nearestClimate = zone;
            }
        });

        if (nearestClimate) {
            const props = nearestClimate.properties;
            const temp = props.avg_temperature_c;
            const humidity = props.avg_humidity_percent;
            const coolingDays = props.cooling_days_per_year;
            const stabilityScore = props.stability_score;

            // Temperature scoring
            if (temp <= this.criteria.cooling.maxTemperature) {
                score += 0.4;
                factors.push(`Good temperature: ${temp}°C`);
            } else {
                const penalty = (temp - this.criteria.cooling.maxTemperature) * 0.02;
                score += Math.max(0.1, 0.4 - penalty);
                factors.push(`High temperature: ${temp}°C (requires more cooling)`);
            }

            // Humidity scoring
            if (humidity <= this.criteria.cooling.maxHumidity) {
                score += 0.3;
                factors.push(`Acceptable humidity: ${humidity}%`);
            } else {
                const penalty = (humidity - this.criteria.cooling.maxHumidity) * 0.01;
                score += Math.max(0.05, 0.3 - penalty);
                factors.push(`High humidity: ${humidity}% (increases cooling costs)`);
            }

            // Cooling days scoring
            if (coolingDays <= this.criteria.cooling.coolingDaysLimit) {
                score += 0.2;
                factors.push(`Low cooling requirement: ${coolingDays} days/year`);
            } else {
                factors.push(`High cooling requirement: ${coolingDays} days/year`);
            }

            // Climate stability
            if (stabilityScore >= 80) {
                score += 0.1;
                factors.push(`Stable climate conditions`);
            } else {
                factors.push(`Variable climate conditions`);
            }
        }

        return {
            score: Math.min(score, 1.0),
            factors: factors,
            details: nearestClimate ? {
                temperature: nearestClimate.properties.avg_temperature_c,
                humidity: nearestClimate.properties.avg_humidity_percent,
                coolingDays: nearestClimate.properties.cooling_days_per_year,
                stability: nearestClimate.properties.stability_score,
                disasterRisks: nearestClimate.properties.natural_disaster_risks
            } : null
        };
    }

    // Analyze water supply
    analyzeWaterSupply(lat, lng, waterData) {
        if (!waterData || !waterData.features) {
            return { score: 0.4, factors: ['No water data available'] };
        }

        let score = 0;
        let factors = [];
        let nearestSource = null;
        let minDistance = Infinity;
        let totalCapacity = 0;
        let avgQuality = 0;
        let sourceCount = 0;

        // Analyze nearby water sources
        waterData.features.forEach(source => {
            const distance = this.calculateDistance(
                lat, lng,
                source.geometry.coordinates[1],
                source.geometry.coordinates[0]
            );

            if (distance < 100) { // Within 100km
                totalCapacity += source.properties.daily_capacity_megalitres || 0;
                avgQuality += source.properties.water_quality || 80;
                sourceCount++;

                if (distance < minDistance) {
                    minDistance = distance;
                    nearestSource = source;
                }
            }
        });

        avgQuality = sourceCount > 0 ? avgQuality / sourceCount : 0;

        // Scoring logic
        if (totalCapacity >= this.criteria.water.minCapacity) {
            score += 0.4;
            factors.push(`Adequate water capacity: ${totalCapacity}ML/day`);
        } else {
            factors.push(`Limited water capacity: ${totalCapacity}ML/day`);
        }

        if (avgQuality >= this.criteria.water.qualityThreshold) {
            score += 0.3;
            factors.push(`Good water quality: ${avgQuality.toFixed(1)}%`);
        } else {
            factors.push(`Water quality concerns: ${avgQuality.toFixed(1)}%`);
        }

        if (minDistance < 20) {
            score += 0.2;
            factors.push(`Close to water source: ${minDistance.toFixed(1)}km`);
        } else if (minDistance < 50) {
            score += 0.1;
            factors.push(`Moderate distance to water: ${minDistance.toFixed(1)}km`);
        }

        if (sourceCount > 1) {
            score += 0.1;
            factors.push(`Multiple water sources available: ${sourceCount}`);
        }

        return {
            score: Math.min(score, 1.0),
            factors: factors,
            details: {
                nearestDistance: minDistance,
                totalCapacity: totalCapacity,
                avgQuality: avgQuality,
                sourceCount: sourceCount
            }
        };
    }

    // Analyze transportation infrastructure
    analyzeTransportation(lat, lng, transportData) {
        if (!transportData || !transportData.features) {
            return { score: 0.5, factors: ['No transport data available'] };
        }

        let score = 0;
        let factors = [];
        let hasHighwayAccess = false;
        let hasAirportAccess = false;
        let hasPortAccess = false;
        let minAirportDistance = Infinity;
        let avgAccessibility = 0;
        let facilityCount = 0;

        // Analyze nearby transport facilities
        transportData.features.forEach(facility => {
            const distance = this.calculateDistance(
                lat, lng,
                facility.geometry.coordinates[1],
                facility.geometry.coordinates[0]
            );

            facilityCount++;
            avgAccessibility += facility.properties.accessibility_score || 60;

            if (facility.properties.transport_type === 'Highway' && distance < 10) {
                hasHighwayAccess = true;
            }

            if (facility.properties.transport_type === 'Airport') {
                minAirportDistance = Math.min(minAirportDistance, distance);
                if (distance < this.criteria.transport.airportProximity) {
                    hasAirportAccess = true;
                }
            }

            if (facility.properties.transport_type === 'Port' && distance < 50) {
                hasPortAccess = true;
            }
        });

        avgAccessibility = facilityCount > 0 ? avgAccessibility / facilityCount : 0;

        // Scoring logic
        if (hasHighwayAccess) {
            score += 0.3;
            factors.push('Highway access available');
        } else {
            factors.push('Limited highway access');
        }

        if (hasAirportAccess) {
            score += 0.3;
            factors.push(`Airport within ${this.criteria.transport.airportProximity}km`);
        } else if (minAirportDistance < 100) {
            score += 0.15;
            factors.push(`Airport ${minAirportDistance.toFixed(1)}km away`);
        } else {
            factors.push('No nearby airport access');
        }

        if (hasPortAccess) {
            score += 0.2;
            factors.push('Port access for freight');
        }

        if (avgAccessibility >= this.criteria.transport.minAccessibility) {
            score += 0.2;
            factors.push(`Good overall accessibility: ${avgAccessibility.toFixed(1)}`);
        }

        return {
            score: Math.min(score, 1.0),
            factors: factors,
            details: {
                hasHighwayAccess: hasHighwayAccess,
                hasAirportAccess: hasAirportAccess,
                hasPortAccess: hasPortAccess,
                minAirportDistance: minAirportDistance,
                avgAccessibility: avgAccessibility
            }
        };
    }

    // Analyze geological factors
    analyzeGeology(lat, lng, geologyData) {
        if (!geologyData || !geologyData.features) {
            return { score: 0.6, factors: ['No geological data available'] };
        }

        let score = 0;
        let factors = [];
        let nearestSite = null;
        let minDistance = Infinity;

        // Find nearest geological data
        geologyData.features.forEach(site => {
            const distance = this.calculateDistance(
                lat, lng,
                site.geometry.coordinates[1],
                site.geometry.coordinates[0]
            );

            if (distance < minDistance) {
                minDistance = distance;
                nearestSite = site;
            }
        });

        if (nearestSite) {
            const props = nearestSite.properties;
            const stability = props.soil_stability_percent;
            const seismicRisk = props.seismic_risk_magnitude;
            const foundationSuitability = props.foundation_suitability;

            // Soil stability scoring
            if (stability >= this.criteria.geology.minStability) {
                score += 0.4;
                factors.push(`Good soil stability: ${stability}%`);
            } else {
                factors.push(`Poor soil stability: ${stability}%`);
            }

            // Seismic risk scoring
            if (seismicRisk <= this.criteria.geology.maxSeismicRisk) {
                score += 0.3;
                factors.push(`Low seismic risk: ${seismicRisk} magnitude`);
            } else {
                factors.push(`High seismic risk: ${seismicRisk} magnitude`);
            }

            // Foundation suitability
            if (foundationSuitability === 'Excellent') {
                score += 0.3;
                factors.push('Excellent foundation conditions');
            } else if (foundationSuitability === 'Good') {
                score += 0.2;
                factors.push('Good foundation conditions');
            } else {
                score += 0.1;
                factors.push('Fair foundation conditions');
            }
        }

        return {
            score: Math.min(score, 1.0),
            factors: factors,
            details: nearestSite ? {
                stability: nearestSite.properties.soil_stability_percent,
                seismicRisk: nearestSite.properties.seismic_risk_magnitude,
                foundationSuitability: nearestSite.properties.foundation_suitability,
                groundwaterDepth: nearestSite.properties.groundwater_depth_m
            } : null
        };
    }

    // Analyze security factors
    analyzeSecurityFactors(lat, lng, dataLayers) {
        let score = 0.7; // Default security score
        let factors = ['Security analysis based on location characteristics'];

        // Distance from major urban areas (balance between access and security)
        const majorCities = [
            { lat: -33.8688, lng: 151.2093 }, // Sydney
            { lat: -37.8136, lng: 144.9631 }, // Melbourne
            { lat: -27.4698, lng: 153.0251 }, // Brisbane
        ];

        let minCityDistance = Infinity;
        majorCities.forEach(city => {
            const distance = this.calculateDistance(lat, lng, city.lat, city.lng);
            minCityDistance = Math.min(minCityDistance, distance);
        });

        // Optimal distance: 20-100km from major cities
        if (minCityDistance >= 20 && minCityDistance <= 100) {
            score += 0.2;
            factors.push(`Optimal distance from city: ${minCityDistance.toFixed(1)}km`);
        } else if (minCityDistance < 20) {
            score += 0.1;
            factors.push(`Close to urban area: ${minCityDistance.toFixed(1)}km (higher security needs)`);
        } else {
            factors.push(`Remote location: ${minCityDistance.toFixed(1)}km (limited emergency services)`);
        }

        // Check for natural disaster risks from climate data
        if (dataLayers.climate && dataLayers.climate.features) {
            const nearestClimate = this.findNearestFeature(lat, lng, dataLayers.climate);
            if (nearestClimate && nearestClimate.properties.natural_disaster_risks) {
                const risks = nearestClimate.properties.natural_disaster_risks;
                if (risks.includes('Cyclone') || risks.includes('Flood')) {
                    score -= 0.1;
                    factors.push('High natural disaster risk area');
                } else if (risks.includes('Bushfire')) {
                    score -= 0.05;
                    factors.push('Moderate natural disaster risk');
                }
            }
        }

        return {
            score: Math.min(Math.max(score, 0.2), 1.0),
            factors: factors,
            details: {
                distanceFromCity: minCityDistance,
                securityLevel: score > 0.8 ? 'High' : score > 0.6 ? 'Medium' : 'Low'
            }
        };
    }

    // Analyze regulatory environment
    analyzeRegulatoryEnvironment(lat, lng, dataLayers) {
        let score = 0.8; // Default good regulatory score for Australia
        let factors = ['Australia has favorable data center regulations'];

        // State-based considerations
        const states = {
            'NSW': { lat: -33.8688, lng: 151.2093, score: 0.85, name: 'New South Wales' },
            'VIC': { lat: -37.8136, lng: 144.9631, score: 0.90, name: 'Victoria' },
            'QLD': { lat: -27.4698, lng: 153.0251, score: 0.80, name: 'Queensland' },
            'WA': { lat: -31.9505, lng: 115.8605, score: 0.75, name: 'Western Australia' },
            'SA': { lat: -34.9285, lng: 138.6007, score: 0.80, name: 'South Australia' },
            'NT': { lat: -12.4634, lng: 130.8456, score: 0.70, name: 'Northern Territory' }
        };

        let nearestState = null;
        let minDistance = Infinity;

        Object.values(states).forEach(state => {
            const distance = this.calculateDistance(lat, lng, state.lat, state.lng);
            if (distance < minDistance) {
                minDistance = distance;
                nearestState = state;
            }
        });

        if (nearestState) {
            score = nearestState.score;
            factors.push(`Located in ${nearestState.name}`);
            
            if (nearestState.score >= 0.85) {
                factors.push('Excellent regulatory environment');
            } else if (nearestState.score >= 0.75) {
                factors.push('Good regulatory environment');
            } else {
                factors.push('Adequate regulatory environment');
            }
        }

        // Additional regulatory factors
        factors.push('Strong data protection laws');
        factors.push('Stable political environment');
        factors.push('Good international trade relations');

        return {
            score: score,
            factors: factors,
            details: {
                state: nearestState ? nearestState.name : 'Unknown',
                regulatoryScore: score
            }
        };
    }

    // Helper methods
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

    findNearestFeature(lat, lng, dataset) {
        if (!dataset || !dataset.features) return null;
        
        let nearest = null;
        let minDistance = Infinity;

        dataset.features.forEach(feature => {
            const distance = this.calculateDistance(
                lat, lng,
                feature.geometry.coordinates[1],
                feature.geometry.coordinates[0]
            );

            if (distance < minDistance) {
                minDistance = distance;
                nearest = feature;
            }
        });

        return nearest;
    }

    parseCapacity(capacityString) {
        if (!capacityString) return 0;
        const match = capacityString.match(/(\d+\.?\d*)/);
        if (!match) return 0;
        
        const value = parseFloat(match[1]);
        if (capacityString.includes('Tbps')) {
            return value * 1000; // Convert to Gbps
        }
        return value;
    }

    calculateWeightedScore(scores) {
        let totalScore = 0;
        for (const [factor, weight] of Object.entries(this.weights)) {
            totalScore += (scores[factor]?.score || 0) * weight;
        }
        return totalScore;
    }

    identifyRiskFactors(scores) {
        const risks = [];
        
        for (const [factor, data] of Object.entries(scores)) {
            if (data.score < 0.5) {
                risks.push({
                    factor: factor,
                    severity: data.score < 0.3 ? 'High' : 'Medium',
                    description: data.factors[0] || `Low ${factor} score`
                });
            }
        }

        return risks;
    }

    generateRecommendations(scores, lat, lng) {
        const recommendations = [];

        // Power recommendations
        if (scores.power.score < 0.6) {
            recommendations.push({
                category: 'Power Infrastructure',
                priority: 'High',
                recommendation: 'Consider installing backup generators or battery storage systems',
                estimatedCost: '$500K - $2M'
            });
        }

        // Connectivity recommendations
        if (scores.connectivity.score < 0.6) {
            recommendations.push({
                category: 'Telecommunications',
                priority: 'High',
                recommendation: 'Establish redundant fiber connections to multiple providers',
                estimatedCost: '$200K - $800K'
            });
        }

        // Cooling recommendations
        if (scores.cooling.score < 0.6) {
            recommendations.push({
                category: 'Cooling System',
                priority: 'Medium',
                recommendation: 'Implement advanced cooling systems (liquid cooling, free air cooling)',
                estimatedCost: '$300K - $1M'
            });
        }

        // Water recommendations
        if (scores.water.score < 0.5) {
            recommendations.push({
                category: 'Water Supply',
                priority: 'Medium',
                recommendation: 'Secure water rights or implement water recycling systems',
                estimatedCost: '$100K - $500K'
            });
        }

        // General recommendations
        recommendations.push({
            category: 'Site Preparation',
            priority: 'Low',
            recommendation: 'Conduct detailed geological and environmental impact assessments',
            estimatedCost: '$50K - $150K'
        });

        return recommendations;
    }

    getSuitabilityLevel(score) {
        if (score >= 0.8) return { level: 'Excellent', description: 'Highly suitable for data center development' };
        if (score >= 0.7) return { level: 'Very Good', description: 'Very suitable with minor considerations' };
        if (score >= 0.6) return { level: 'Good', description: 'Suitable with some infrastructure improvements needed' };
        if (score >= 0.5) return { level: 'Fair', description: 'Marginally suitable, significant improvements required' };
        if (score >= 0.4) return { level: 'Poor', description: 'Not recommended without major infrastructure investments' };
        return { level: 'Very Poor', description: 'Not suitable for data center development' };
    }

    // Method to update analysis weights
    updateWeights(newWeights) {
        this.weights = { ...this.weights, ...newWeights };
    }

    // Method to update criteria
    updateCriteria(newCriteria) {
        this.criteria = { ...this.criteria, ...newCriteria };
    }
}

// Export for use in main application
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataCenterSuitabilityAnalyzer;
} else {
    window.DataCenterSuitabilityAnalyzer = DataCenterSuitabilityAnalyzer;
}
