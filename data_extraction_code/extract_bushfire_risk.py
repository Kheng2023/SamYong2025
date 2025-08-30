#!/usr/bin/env python3
"""
Bushfire Risk Extractor for Data Centre Site Analysis

This script extracts bushfire boundary information from large GDB files
and creates a smaller dataset for data centre site risk assessment.

Focus: Extract bushfire risk zones and severity levels for site selection.
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional
import argparse

try:
    import geopandas as gpd
    import pandas as pd
    import fiona
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    print("Error: geopandas is required for processing GDB files.")
    print("Please install with: pip install geopandas")
    sys.exit(1)

def inspect_bushfire_gdb(gdb_path: str):
    """Inspect the layers and structure of the bushfire GDB file."""
    try:
        layers = fiona.listlayers(gdb_path)
        print(f"\n📂 Inspecting {os.path.basename(gdb_path)}:")
        print(f"   Found {len(layers)} layer(s): {layers}")
        
        for layer in layers:
            try:
                with fiona.open(gdb_path, layer=layer) as src:
                    print(f"\n🔍 Layer '{layer}':")
                    print(f"   Total features: {len(src):,}")
                    
                    # Sample first feature to see properties
                    first_feature = next(iter(src), None)
                    if first_feature:
                        props = list(first_feature['properties'].keys())
                        print(f"   Properties: {props}")
                        
                        # Show sample values for key properties
                        sample_props = {}
                        for prop_name, prop_value in first_feature['properties'].items():
                            if prop_value is not None:
                                sample_props[prop_name] = prop_value
                        
                        print(f"   Sample values:")
                        for prop, value in list(sample_props.items())[:10]:
                            print(f"     {prop}: {value}")
                    
            except Exception as e:
                print(f"     Error reading layer {layer}: {e}")
                
        return layers
    except Exception as e:
        print(f"Error inspecting {gdb_path}: {e}")
        return []

def extract_bushfire_risk_areas(gdb_path: str, layer_name: str, chunk_size: int = 5000) -> List[Dict[str, Any]]:
    """
    Extract bushfire risk areas using chunked processing.
    """
    risk_areas = []
    
    try:
        print(f"🔥 Processing {os.path.basename(gdb_path)} layer '{layer_name}' in chunks...")
        
        # First, get total count
        with fiona.open(gdb_path, layer=layer_name) as src:
            total_features = len(src)
            print(f"   Total features: {total_features:,}")
        
        # Process in chunks to manage memory
        processed_count = 0
        chunk_num = 0
        
        while processed_count < total_features:
            chunk_num += 1
            start_idx = processed_count
            end_idx = min(start_idx + chunk_size, total_features)
            
            print(f"   📦 Processing chunk {chunk_num}: features {start_idx:,} to {end_idx:,}")
            
            try:
                # Read chunk
                gdf_chunk = gpd.read_file(
                    gdb_path, 
                    layer=layer_name,
                    rows=slice(start_idx, end_idx)
                )
                
                # Ensure WGS84 for consistency
                if gdf_chunk.crs and gdf_chunk.crs != 'EPSG:4326':
                    gdf_chunk = gdf_chunk.to_crs('EPSG:4326')
                
                # Extract bushfire risk features
                chunk_risk_areas = extract_risk_features(gdf_chunk)
                risk_areas.extend(chunk_risk_areas)
                
                print(f"      ✅ Found {len(chunk_risk_areas)} risk areas in this chunk")
                
                # Clear chunk from memory
                del gdf_chunk
                
            except Exception as e:
                print(f"      ❌ Error processing chunk {chunk_num}: {e}")
            
            processed_count = end_idx
        
        print(f"🎯 Total bushfire risk areas extracted: {len(risk_areas)}")
        
    except Exception as e:
        print(f"Error in chunked processing: {e}")
    
    return risk_areas

def extract_risk_features(gdf: gpd.GeoDataFrame) -> List[Dict[str, Any]]:
    """
    Extract bushfire risk features from a GeoDataFrame.
    """
    risk_features = []
    
    for idx, row in gdf.iterrows():
        try:
            # Extract risk level and other important properties
            risk_level = get_risk_level(row)
            fire_name = get_fire_name(row)
            status = get_fire_status(row)
            area_hectares = get_area_info(row)
            
            # Convert geometry based on type
            geometry = None
            if hasattr(row.geometry, '__geo_interface__'):
                geom = row.geometry.__geo_interface__
                
                # For risk assessment, convert to centroid for distance calculations
                if geom.get('type') in ['Polygon', 'MultiPolygon']:
                    centroid = row.geometry.centroid
                    geometry = centroid.__geo_interface__
                elif geom.get('type') in ['Point', 'MultiPoint']:
                    geometry = geom
                else:
                    # For lines, use centroid
                    centroid = row.geometry.centroid
                    geometry = centroid.__geo_interface__
            
            if geometry:
                feature = {
                    "type": "Feature",
                    "properties": {
                        "risk_level": risk_level,
                        "fire_name": fire_name,
                        "status": status,
                        "area_hectares": area_hectares,
                        "original_geometry_type": geom.get('type', 'unknown'),
                        "data_source": "Operational_Bushfire_Boundaries"
                    },
                    "geometry": geometry
                }
                risk_features.append(feature)
                
        except Exception as e:
            continue  # Skip problematic features
    
    return risk_features

def get_risk_level(row: pd.Series) -> str:
    """Extract bushfire risk level from various possible field names."""
    
    # Get fire title and area to assess risk
    title = str(row.get('Title', '')).lower()
    hectares = row.get('Hectares', 0)
    
    # Safe conversion of hectares to float - handles strings and various data types
    area = 0
    try:
        if hectares is not None and hectares != '' and str(hectares).lower() not in ['nan', 'null', 'none']:
            # Handle string numeric values and clean them
            hectares_str = str(hectares).strip().replace(',', '')
            if hectares_str and hectares_str != '0':
                area = float(hectares_str)
    except (ValueError, TypeError, AttributeError):
        area = 0
    
    # Risk assessment based on size and keywords
    risk_keywords = {
        'extreme': ['extreme', 'emergency', 'evacuation', 'catastrophic'],
        'high': ['high', 'severe', 'major', 'large', 'complex'],
        'moderate': ['moderate', 'medium', 'controlled'],
        'low': ['low', 'small', 'contained', 'patrolled']
    }
    
    # Check for risk keywords in title
    for risk_level, keywords in risk_keywords.items():
        if any(keyword in title for keyword in keywords):
            return risk_level.title()
    
    # Risk assessment based on area (hectares)
    if area >= 10000:  # Very large fires (100+ sq km)
        return "Extreme"
    elif area >= 1000:  # Large fires (10+ sq km)
        return "High"
    elif area >= 100:   # Medium fires (1+ sq km)
        return "Moderate"
    elif area >= 10:    # Small fires
        return "Low"
    elif area > 0:      # Very small fires
        return "Minimal"
    else:
        return "Unknown"

def get_fire_name(row: pd.Series) -> str:
    """Extract fire incident name."""
    # This dataset uses 'Title' for fire names
    if 'Title' in row and pd.notna(row['Title']):
        title = str(row['Title']).strip()
        if title and title != '' and title.lower() != 'null':
            return title
    
    # Fallback to other name fields
    name_fields = [
        'FIRE_NAME', 'NAME', 'INCIDENT_NAME', 'EVENT_NAME',
        'LOCATION', 'AREA_NAME', 'LOCALITY'
    ]
    
    for field in name_fields:
        if field in row and pd.notna(row[field]):
            name = str(row[field]).strip()
            if name and name != '' and name.lower() != 'null':
                return name
    
    return "Unnamed Fire Area"

def get_fire_status(row: pd.Series) -> str:
    """Extract fire status."""
    # Check if we have explicit status fields
    status_fields = [
        'STATUS', 'FIRE_STATUS', 'STATE', 'CONDITION',
        'STAGE', 'PHASE', 'CURRENT_STATUS'
    ]
    
    for field in status_fields:
        if field in row and pd.notna(row[field]):
            return str(row[field])
    
    # Infer status from other information
    agency = str(row.get('Agency', '')).lower()
    title = str(row.get('Title', '')).lower()
    
    # Status inference from agency and title keywords
    if 'controlled' in title or 'contained' in title:
        return "Controlled"
    elif 'patrolled' in title or 'patrol' in title:
        return "Being Patrolled"
    elif any(word in title for word in ['emergency', 'evacuation', 'immediate']):
        return "Emergency"
    elif 'rural fire service' in agency:
        return "Active"
    else:
        return "Operational"

def get_area_info(row: pd.Series) -> Optional[float]:
    """Extract area information if available with safe string handling."""
    area_fields = [
        'AREA_HA', 'AREA_HECTARES', 'SIZE_HA', 'Hectares',
        'SHAPE_Area', 'AREA', 'SIZE', 'Shape_Area'
    ]
    
    for field in area_fields:
        if field in row and pd.notna(row[field]):
            try:
                value = row[field]
                
                # Handle different data types safely
                if isinstance(value, (int, float)):
                    area = float(value)
                elif isinstance(value, str):
                    # Clean string and convert
                    value_clean = value.strip().replace(',', '').replace(' ', '')
                    if value_clean and value_clean.lower() not in ['null', 'nan', 'none', '']:
                        area = float(value_clean)
                    else:
                        continue
                else:
                    continue
                
                # Convert square meters to hectares if needed
                if area > 100000:  # Likely in square meters
                    area = area / 10000
                    
                return area if area > 0 else None
                
            except (ValueError, TypeError, AttributeError):
                continue
    
    return None

def save_bushfire_data(risk_areas: List[Dict[str, Any]], output_file: str):
    """Save bushfire risk data to GeoJSON file."""
    
    # Analyze risk levels
    risk_counts = {}
    for area in risk_areas:
        risk = area['properties'].get('risk_level', 'Unknown')
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    
    output_data = {
        "type": "FeatureCollection",
        "features": risk_areas,
        "metadata": {
            "description": "Bushfire risk areas for data centre site analysis",
            "extraction_date": "2025-08-30",
            "purpose": "Risk assessment for data centre location planning",
            "total_features": len(risk_areas),
            "risk_level_summary": risk_counts
        }
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, separators=(',', ':'))
        
        file_size = os.path.getsize(output_file) / 1024 / 1024
        print(f"\n✅ Successfully created {output_file}")
        print(f"📊 Contains {len(risk_areas):,} bushfire risk areas")
        print(f"📁 File size: {file_size:.2f} MB")
        
        # Show risk level summary
        print(f"\n🔥 Risk Level Summary:")
        for risk_level, count in sorted(risk_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {risk_level}: {count:,} areas")
        
    except Exception as e:
        print(f"❌ Error writing output file: {e}")

def main():
    parser = argparse.ArgumentParser(description='Extract bushfire risk data for data centre analysis')
    parser.add_argument('--input', '-i', 
                       default='Operational_Bushfire_Boundaries.gdb',
                       help='Input bushfire GDB file')
    parser.add_argument('--output', '-o', 
                       default='bushfire_risk_for_datacenter.geojson',
                       help='Output GeoJSON file')
    parser.add_argument('--chunk-size', type=int, default=5000,
                       help='Chunk size for processing (default: 5000)')
    parser.add_argument('--inspect', action='store_true',
                       help='Just inspect the GDB file structure without processing')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        return
    
    print(f"🔥 Bushfire Risk Extractor for Data Centre Analysis")
    print(f"📂 Input: {args.input}")
    print(f"📄 Output: {args.output}")
    
    # Inspect the GDB file
    layers = inspect_bushfire_gdb(args.input)
    
    if args.inspect:
        print("\n🔍 Inspection complete. Use without --inspect to extract data.")
        return
    
    if not layers:
        print("❌ No layers found in GDB file")
        return
    
    # Look for the comprehensive layer first
    layer_name = None
    for layer in layers:
        if 'All_Operational_Bushfire_Boundaries' in layer:
            layer_name = layer
            break
    
    # If comprehensive layer not found, use any operational boundaries layer
    if layer_name is None:
        for layer in layers:
            if 'operational' in layer.lower() and 'boundary' in layer.lower():
                layer_name = layer
                break
    
    # Fallback to first layer
    if layer_name is None:
        layer_name = layers[0]
    
    if len(layers) > 1:
        print(f"\n⚠️  Found {len(layers)} layers. Using: {layer_name}")
        print(f"💡 To use a different layer, modify the script or create separate runs")
    
    print(f"\n🎯 Processing layer: {layer_name}")
    
    # Extract bushfire risk areas
    risk_areas = extract_bushfire_risk_areas(args.input, layer_name, args.chunk_size)
    
    if risk_areas:
        # Save results
        save_bushfire_data(risk_areas, args.output)
        
        # Show sample results
        print(f"\n📋 Sample bushfire risk areas:")
        for i, area in enumerate(risk_areas[:5], 1):
            name = area['properties'].get('fire_name', 'Unnamed')[:40]
            risk = area['properties'].get('risk_level', 'Unknown')
            status = area['properties'].get('status', 'Unknown')
            print(f"   {i}. {name} | Risk: {risk} | Status: {status}")
        
        if len(risk_areas) > 5:
            print(f"   ... and {len(risk_areas) - 5:,} more")
        
        print(f"\n🎯 Next step: Use this data to assess bushfire risk for your data centre locations!")
        print(f"💡 Tip: Avoid areas with 'High', 'Extreme', or 'Critical' risk levels")
        
    else:
        print("\n❌ No bushfire risk areas found.")
        print("💡 This might mean:")
        print("   - The layer doesn't contain bushfire boundary data")
        print("   - Different property naming is used")
        print("   - Try the --inspect flag to understand the data structure")

if __name__ == "__main__":
    main()
