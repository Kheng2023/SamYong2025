#!/usr/bin/env python3
"""
Optimize Bushfire Boundaries for Data Center Site Selection

This script reduces the bushfire boundaries file size by:
1. Simplifying geometries (reducing coordinate precision)
2. Filtering for only significant fires that affect infrastructure planning
3. Removing redundant properties
4. Focusing on risk zones rather than individual fire details

Target: Create a lightweight risk assessment dataset for site selection.
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional
import argparse

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import shape
    from shapely.ops import unary_union
    import shapely.wkt
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    print("Error: geopandas is required for processing.")
    print("Please install with: pip install geopandas")
    sys.exit(1)

def simplify_geometry(geom_dict, tolerance=0.001):
    """Simplify geometry to reduce file size while maintaining shape."""
    try:
        geom = shape(geom_dict)
        simplified = geom.simplify(tolerance, preserve_topology=True)
        
        # Convert back to dict format for JSON serialization
        if hasattr(simplified, '__geo_interface__'):
            return simplified.__geo_interface__
        else:
            return geom_dict
    except:
        return geom_dict

def optimize_bushfire_data(input_file: str, output_file: str, 
                          min_area_ha: float = 100.0,
                          max_features: int = 5000,
                          simplify_tolerance: float = 0.001) -> bool:
    """
    Optimize bushfire boundaries for data center site selection.
    
    Args:
        input_file: Input GeoJSON file path
        output_file: Output optimized GeoJSON file path
        min_area_ha: Minimum fire area to include (hectares)
        max_features: Maximum features to keep
        simplify_tolerance: Geometry simplification tolerance
    """
    
    try:
        print(f"🔥 Optimizing bushfire data for data center site selection...")
        print(f"   Input: {input_file}")
        print(f"   Output: {output_file}")
        print(f"   Min area: {min_area_ha} hectares")
        print(f"   Max features: {max_features}")
        print(f"   Simplification: {simplify_tolerance}")
        
        # Load data
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        print(f"   Original features: {len(features):,}")
        
        # Filter for significant fires that affect infrastructure planning
        filtered_features = []
        
        for feature in features:
            props = feature['properties']
            area_ha = props.get('area_ha', 0)
            risk_level = props.get('risk_level', '')
            
            # Keep if:
            # 1. Large enough to be significant for infrastructure planning
            # 2. High or Very High risk regardless of size
            # 3. Recent fires (more relevant for current planning)
            
            keep_feature = False
            
            # Large fires are always significant
            if area_ha >= min_area_ha:
                keep_feature = True
            
            # High risk fires regardless of size
            if risk_level in ['High', 'Very High']:
                keep_feature = True
            
            # Medium risk fires if they're reasonably sized
            if risk_level == 'Medium' and area_ha >= 50:
                keep_feature = True
            
            if keep_feature:
                # Simplify geometry to reduce file size
                simplified_geom = simplify_geometry(feature['geometry'], simplify_tolerance)
                
                # Keep only essential properties for site selection
                optimized_feature = {
                    "type": "Feature",
                    "geometry": simplified_geom,
                    "properties": {
                        "id": props.get('id', ''),
                        "area_ha": area_ha,
                        "risk_level": risk_level,
                        "fire_type": props.get('fire_type', ''),
                        "year": None  # Extract year for temporal relevance
                    }
                }
                
                # Extract year from capture_date for temporal filtering
                capture_date = props.get('capture_date', '')
                if isinstance(capture_date, str) and len(capture_date) >= 4:
                    try:
                        year = int(capture_date[:4])
                        optimized_feature['properties']['year'] = year
                    except:
                        pass
                
                filtered_features.append(optimized_feature)
        
        print(f"   Filtered features: {len(filtered_features):,}")
        
        # Sort by risk level and area (most important first)
        risk_priority = {'Very High': 4, 'High': 3, 'Medium': 2, 'Low': 1, '': 0}
        
        filtered_features.sort(
            key=lambda x: (
                risk_priority.get(x['properties']['risk_level'], 0),
                x['properties']['area_ha']
            ), 
            reverse=True
        )
        
        # Keep only the most significant features
        if len(filtered_features) > max_features:
            filtered_features = filtered_features[:max_features]
            print(f"   Reduced to top {max_features} most significant fires")
        
        # Create risk zones by combining overlapping fires of same risk level
        print(f"   Creating risk zones...")
        risk_zones = create_risk_zones(filtered_features)
        
        # Create optimized GeoJSON
        optimized_data = {
            "type": "FeatureCollection",
            "features": risk_zones,
            "metadata": {
                "source": "Optimized from bushfire_boundaries.geojson",
                "purpose": "Data center site risk assessment",
                "optimization_date": pd.Timestamp.now().isoformat(),
                "total_original_features": len(features),
                "total_optimized_features": len(risk_zones),
                "min_area_filter": min_area_ha,
                "simplification_tolerance": simplify_tolerance,
                "notes": "Simplified geometries and properties for infrastructure planning"
            }
        }
        
        # Write optimized output
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(optimized_data, f, separators=(',', ':'))  # Compact JSON
        
        # Compare file sizes
        original_size = os.path.getsize(input_file) / (1024 * 1024)
        optimized_size = os.path.getsize(output_file) / (1024 * 1024)
        reduction = (1 - optimized_size / original_size) * 100
        
        print(f"\n✅ Optimization complete:")
        print(f"   Original: {original_size:.1f} MB ({len(features):,} features)")
        print(f"   Optimized: {optimized_size:.1f} MB ({len(risk_zones):,} features)")
        print(f"   Size reduction: {reduction:.1f}%")
        
        # Show risk level distribution
        risk_counts = {}
        for feature in risk_zones:
            risk = feature['properties']['risk_level']
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        print(f"   Risk zone distribution:")
        for risk, count in sorted(risk_counts.items(), key=lambda x: risk_priority.get(x[0], 0), reverse=True):
            print(f"     {risk}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error optimizing bushfire data: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_risk_zones(features):
    """Create consolidated risk zones from individual fire features."""
    risk_zones = []
    
    # Group features by risk level
    risk_groups = {}
    for feature in features:
        risk_level = feature['properties']['risk_level']
        if risk_level not in risk_groups:
            risk_groups[risk_level] = []
        risk_groups[risk_level].append(feature)
    
    # For each risk level, create representative zones
    for risk_level, group_features in risk_groups.items():
        if not group_features:
            continue
        
        # For Very High and High risk, keep individual large fires
        if risk_level in ['Very High', 'High']:
            for feature in group_features:
                area_ha = feature['properties']['area_ha']
                if area_ha >= 1000:  # Keep large individual fires
                    risk_zones.append(feature)
        
        # For Medium and Low risk, we could merge nearby fires
        # But for simplicity, we'll keep the largest ones
        elif risk_level in ['Medium', 'Low']:
            # Sort by area and keep top fires
            sorted_features = sorted(group_features, key=lambda x: x['properties']['area_ha'], reverse=True)
            
            # Keep top fires for each risk level
            max_keep = 200 if risk_level == 'Medium' else 100
            risk_zones.extend(sorted_features[:max_keep])
    
    return risk_zones

def create_site_suitability_zones(input_file: str, output_file: str, 
                                 buffer_distances: Dict[str, float] = None) -> bool:
    """
    Create simplified suitability zones for data center site selection.
    
    Args:
        input_file: Optimized bushfire data
        output_file: Site suitability zones output
        buffer_distances: Buffer distances (km) for each risk level
    """
    
    if buffer_distances is None:
        buffer_distances = {
            'Very High': 5.0,  # 5km buffer
            'High': 3.0,       # 3km buffer  
            'Medium': 1.0,     # 1km buffer
            'Low': 0.5         # 0.5km buffer
        }
    
    try:
        print(f"\n🎯 Creating site suitability zones...")
        
        # Load optimized data
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        
        # Create buffer zones for each risk level
        suitability_zones = []
        
        for risk_level, buffer_km in buffer_distances.items():
            risk_features = [f for f in features if f['properties']['risk_level'] == risk_level]
            
            if not risk_features:
                continue
            
            print(f"   Processing {len(risk_features)} {risk_level} risk areas (buffer: {buffer_km}km)")
            
            # Create buffer zones
            for feature in risk_features:
                try:
                    geom = shape(feature['geometry'])
                    # Buffer distance in degrees (approximate)
                    buffer_degrees = buffer_km / 111.0  # Rough conversion
                    buffered = geom.buffer(buffer_degrees)
                    
                    zone_feature = {
                        "type": "Feature",
                        "geometry": buffered.__geo_interface__,
                        "properties": {
                            "zone_type": f"{risk_level}_risk_buffer",
                            "risk_level": risk_level,
                            "buffer_km": buffer_km,
                            "suitability": get_suitability_rating(risk_level),
                            "original_fire_area_ha": feature['properties']['area_ha']
                        }
                    }
                    
                    suitability_zones.append(zone_feature)
                    
                except Exception as e:
                    print(f"     Warning: Could not create buffer for feature: {e}")
                    continue
        
        # Create suitability GeoJSON
        suitability_data = {
            "type": "FeatureCollection",
            "features": suitability_zones,
            "metadata": {
                "source": "Derived from optimized bushfire boundaries",
                "purpose": "Data center site suitability assessment",
                "creation_date": pd.Timestamp.now().isoformat(),
                "buffer_distances_km": buffer_distances,
                "suitability_ratings": {
                    "Suitable": "Low risk areas with adequate buffers",
                    "Caution": "Medium risk areas requiring assessment", 
                    "High Risk": "High risk areas, avoid if possible",
                    "Unsuitable": "Very high risk areas, not recommended"
                }
            }
        }
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(suitability_data, f, separators=(',', ':'))
        
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"   Created suitability zones: {output_file} ({file_size:.1f} MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating suitability zones: {e}")
        return False

def get_suitability_rating(risk_level: str) -> str:
    """Get suitability rating for data center sites."""
    ratings = {
        'Very High': 'Unsuitable',
        'High': 'High Risk', 
        'Medium': 'Caution',
        'Low': 'Suitable'
    }
    return ratings.get(risk_level, 'Unknown')

def main():
    parser = argparse.ArgumentParser(description='Optimize bushfire boundaries for data center site selection')
    parser.add_argument('--input', default='map_data/bushfire_boundaries.geojson',
                       help='Input bushfire boundaries file')
    parser.add_argument('--output', default='map_data/bushfire_risk_zones_optimized.geojson',
                       help='Output optimized file')
    parser.add_argument('--min-area', type=float, default=100.0,
                       help='Minimum fire area in hectares')
    parser.add_argument('--max-features', type=int, default=3000,
                       help='Maximum features to keep')
    parser.add_argument('--simplify', type=float, default=0.002,
                       help='Geometry simplification tolerance')
    parser.add_argument('--create-zones', action='store_true',
                       help='Also create site suitability zones')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)
    
    # Optimize bushfire data
    success = optimize_bushfire_data(
        input_file=args.input,
        output_file=args.output,
        min_area_ha=args.min_area,
        max_features=args.max_features,
        simplify_tolerance=args.simplify
    )
    
    if not success:
        print(f"\n❌ Failed to optimize bushfire data")
        sys.exit(1)
    
    # Create suitability zones if requested
    if args.create_zones:
        zones_output = args.output.replace('.geojson', '_suitability_zones.geojson')
        create_site_suitability_zones(args.output, zones_output)
    
    print(f"\n🎉 Optimization complete!")
    print(f"   Optimized file: {args.output}")
    
    # Check if file is small enough for GitHub
    file_size_mb = os.path.getsize(args.output) / (1024 * 1024)
    if file_size_mb < 25:
        print(f"   ✅ File size ({file_size_mb:.1f} MB) is suitable for GitHub")
    else:
        print(f"   ⚠️  File size ({file_size_mb:.1f} MB) may still be too large for GitHub")
        print(f"       Consider reducing --max-features or increasing --min-area")

if __name__ == "__main__":
    main()
