#!/usr/bin/env python3
"""
Optimized Water Body Point Extractor for Data Centre Site Analysis

This script efficiently extracts water body locations from SurfaceHydrology GDB files
using memory-optimized processing to handle large datasets without running out of RAM.

Focus: Extract water body POINTS for distance calculations to data centre sites.
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

def inspect_gdb_layers(gdb_path: str):
    """Inspect the layers in a GDB file to understand its structure."""
    try:
        layers = fiona.listlayers(gdb_path)
        print(f"\n📂 Inspecting {os.path.basename(gdb_path)}:")
        print(f"   Found {len(layers)} layer(s): {layers}")
        
        for layer in layers:
            try:
                # Just peek at the first few features to understand structure
                with fiona.open(gdb_path, layer=layer) as src:
                    print(f"   Layer '{layer}': {len(src)} features")
                    
                    # Sample first feature to see properties
                    first_feature = next(iter(src), None)
                    if first_feature:
                        props = list(first_feature['properties'].keys())[:10]  # First 10 properties
                        print(f"     Sample properties: {props}")
                        
                        # Look for water-related properties
                        water_props = []
                        for prop_name, prop_value in first_feature['properties'].items():
                            if prop_value and isinstance(prop_value, str):
                                prop_lower = str(prop_value).lower()
                                if any(keyword in prop_lower for keyword in ['water', 'lake', 'river', 'stream', 'pond']):
                                    water_props.append(f"{prop_name}={prop_value}")
                        
                        if water_props:
                            print(f"     🌊 Found water indicators: {water_props[:3]}")
                    
            except Exception as e:
                print(f"     Error reading layer {layer}: {e}")
                
        return layers
    except Exception as e:
        print(f"Error inspecting {gdb_path}: {e}")
        return []

def extract_water_points_chunked(gdb_path: str, layer_name: str, chunk_size: int = 5000) -> List[Dict[str, Any]]:
    """
    Extract water points using chunked processing to manage memory usage.
    """
    water_features = []
    
    # Water-related keywords to look for
    water_keywords = [
        'water', 'lake', 'river', 'stream', 'pond', 'reservoir', 'dam', 
        'waterway', 'canal', 'creek', 'bay', 'ocean', 'sea', 'lagoon',
        'wetland', 'swamp', 'marsh', 'spring', 'aquifer'
    ]
    
    try:
        print(f"🔄 Processing {os.path.basename(gdb_path)} layer '{layer_name}' in chunks...")
        
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
                # Read chunk using row selection
                gdf_chunk = gpd.read_file(
                    gdb_path, 
                    layer=layer_name,
                    rows=slice(start_idx, end_idx)
                )
                
                # Ensure WGS84 for distance calculations
                if gdf_chunk.crs and gdf_chunk.crs != 'EPSG:4326':
                    gdf_chunk = gdf_chunk.to_crs('EPSG:4326')
                
                # Filter for water features
                chunk_water_features = filter_water_features(gdf_chunk, water_keywords)
                water_features.extend(chunk_water_features)
                
                print(f"      ✅ Found {len(chunk_water_features)} water features in this chunk")
                
                # Clear chunk from memory
                del gdf_chunk
                
            except Exception as e:
                print(f"      ❌ Error processing chunk {chunk_num}: {e}")
            
            processed_count = end_idx
        
        print(f"🎯 Total water features extracted: {len(water_features)}")
        
    except Exception as e:
        print(f"Error in chunked processing: {e}")
    
    return water_features

def filter_water_features(gdf: gpd.GeoDataFrame, water_keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Filter a GeoDataFrame for water-related features and convert to simple format.
    """
    water_features = []
    
    for idx, row in gdf.iterrows():
        # Check if this feature is water-related
        is_water, water_type = is_water_feature(row, water_keywords)
        
        if is_water:
            # Extract basic information
            feature_name = get_feature_name(row)
            feature_id = get_feature_id(row, idx)
            
            # Convert geometry to GeoJSON
            try:
                if hasattr(row.geometry, '__geo_interface__'):
                    geometry = row.geometry.__geo_interface__
                    
                    # For distance calculations, convert polygons to centroids (point)
                    if geometry.get('type') in ['Polygon', 'MultiPolygon']:
                        # Get centroid for distance calculations
                        centroid = row.geometry.centroid
                        centroid_geom = centroid.__geo_interface__
                        
                        feature = {
                            "type": "Feature",
                            "properties": {
                                "water_type": water_type,
                                "name": feature_name,
                                "id": feature_id,
                                "original_geometry_type": geometry.get('type'),
                                "area_sq_meters": getattr(row, 'SHAPE_Area', None),
                                "perimeter_meters": getattr(row, 'SHAPE_Length', None)
                            },
                            "geometry": centroid_geom  # Use centroid for distance calc
                        }
                        water_features.append(feature)
                        
                    # For lines (rivers, streams), use centroid for distance calculation
                    elif geometry.get('type') in ['LineString', 'MultiLineString']:
                        # Get centroid for distance calculations
                        centroid = row.geometry.centroid
                        centroid_geom = centroid.__geo_interface__
                        
                        feature = {
                            "type": "Feature",
                            "properties": {
                                "water_type": water_type,
                                "name": feature_name,
                                "id": feature_id,
                                "original_geometry_type": geometry.get('type'),
                                "length_meters": getattr(row, 'SHAPE_Length', None),
                                "hierarchy": getattr(row, 'HIERARCHY', None),
                                "perenniality": getattr(row, 'PERENNIALITY', None)
                            },
                            "geometry": centroid_geom  # Use centroid for distance calc
                        }
                        water_features.append(feature)
                        
                    elif geometry.get('type') in ['Point', 'MultiPoint']:
                        feature = {
                            "type": "Feature",
                            "properties": {
                                "water_type": water_type,
                                "name": feature_name,
                                "id": feature_id,
                                "geometry_type": geometry.get('type')
                            },
                            "geometry": geometry
                        }
                        water_features.append(feature)
                        
                else:
                    continue  # Skip invalid geometries
                    
            except Exception as e:
                continue  # Skip problematic features
    
    return water_features

def is_water_feature(row: pd.Series, water_keywords: List[str]) -> tuple[bool, str]:
    """
    Determine if a feature represents a water body based on its properties.
    """
    # First check FEATURETYPE column specifically (for polygons/lines data)
    if 'FEATURETYPE' in row:
        featuretype = str(row['FEATURETYPE']).strip()
        if featuretype in ['Lake', 'Swamp', 'Reservoir Area', 'Dam', 'Waterhole', 'Wetland', 'Watercourse']:
            return True, featuretype
    
    # Then check all property values for water-related keywords
    for prop_name, prop_value in row.items():
        if prop_name == 'geometry':
            continue
            
        if pd.isna(prop_value):
            continue
            
        prop_str = str(prop_value).lower()
        
        # Check if any water keyword is in the property value
        for keyword in water_keywords:
            if keyword in prop_str:
                return True, str(prop_value)
    
    return False, "unknown"

def get_feature_name(row: pd.Series) -> str:
    """Extract name from feature properties."""
    name_fields = ['name', 'Name', 'NAME', 'feature_name', 'FEATURE_NAME', 'FEATNAME', 'TEXT_']
    for field in name_fields:
        if field in row and pd.notna(row[field]):
            return str(row[field])
    return "Unnamed Water Body"

def get_feature_id(row: pd.Series, fallback_idx: int) -> Any:
    """Extract ID from feature properties."""
    id_fields = ['id', 'ID', 'objectid', 'OBJECTID', 'fid', 'FID', 'HYDRO_ID']
    for field in id_fields:
        if field in row and pd.notna(row[field]):
            return row[field]
    return fallback_idx

def save_water_points(water_features: List[Dict[str, Any]], output_file: str):
    """Save extracted water points to GeoJSON file."""
    output_data = {
        "type": "FeatureCollection",
        "features": water_features,
        "metadata": {
            "description": "Water body points extracted for data centre site analysis",
            "extraction_date": "2025-08-30",
            "purpose": "Distance calculation for data centre cooling water access",
            "total_features": len(water_features)
        }
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, separators=(',', ':'))  # Compact format
        
        file_size = os.path.getsize(output_file) / 1024 / 1024
        print(f"\n✅ Successfully created {output_file}")
        print(f"📊 Contains {len(water_features):,} water body points")
        print(f"📁 File size: {file_size:.2f} MB")
        
    except Exception as e:
        print(f"❌ Error writing output file: {e}")

def main():
    parser = argparse.ArgumentParser(description='Extract water body points from SurfaceHydrology GDB files')
    parser.add_argument('--input', '-i', 
                       default='map_data/SurfaceHydrologyPointsNational.gdb',
                       help='Input GDB file (default: Points file)')
    parser.add_argument('--output', '-o', 
                       default='water_points_for_datacenter.geojson',
                       help='Output GeoJSON file')
    parser.add_argument('--chunk-size', type=int, default=5000,
                       help='Chunk size for processing (default: 5000)')
    parser.add_argument('--inspect', action='store_true',
                       help='Just inspect the GDB file structure without processing')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        print("\nAvailable SurfaceHydrology files:")
        for gdb in ['SurfaceHydrologyPointsNational.gdb', 'SurfaceHydrologyLinesNational.gdb', 'SurfaceHydrologyPolygonsNational.gdb']:
            path = f'map_data/{gdb}'
            if os.path.exists(path):
                size = os.path.getsize(path) / 1024 / 1024
                print(f"  {path} ({size:.1f} MB)")
        return
    
    print(f"🌊 Water Body Point Extractor for Data Centre Analysis")
    print(f"📂 Input: {args.input}")
    print(f"📄 Output: {args.output}")
    
    # Inspect the GDB file
    layers = inspect_gdb_layers(args.input)
    
    if args.inspect:
        print("\n🔍 Inspection complete. Use --inspect flag to see structure only.")
        return
    
    if not layers:
        print("❌ No layers found in GDB file")
        return
    
    # Use the first (and usually only) layer
    layer_name = layers[0]
    print(f"\n🎯 Processing layer: {layer_name}")
    
    # Extract water points
    water_features = extract_water_points_chunked(args.input, layer_name, args.chunk_size)
    
    if water_features:
        # Save results
        save_water_points(water_features, args.output)
        
        # Show sample results
        print(f"\n📋 Sample water bodies found:")
        for i, feature in enumerate(water_features[:5]):
            name = feature['properties'].get('name', 'Unnamed')
            water_type = feature['properties'].get('water_type', 'unknown')
            geom_type = feature['properties'].get('geometry_type', 'unknown')
            print(f"  {i+1}. {name} ({water_type}) [{geom_type}]")
        
        if len(water_features) > 5:
            print(f"  ... and {len(water_features) - 5:,} more")
        
        print(f"\n🎯 Next step: Use this file to calculate distances to your data centre location!")
        print(f"💡 Tip: For larger coverage, you can also process the Polygons file (lakes, etc.)")
        
    else:
        print("\n❌ No water features found.")
        print("💡 This might mean:")
        print("   - The layer doesn't contain water body data")
        print("   - Water features use different property naming")
        print("   - Try inspecting the data structure with --inspect flag")

if __name__ == "__main__":
    main()
