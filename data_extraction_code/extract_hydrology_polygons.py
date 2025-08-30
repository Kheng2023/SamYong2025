#!/usr/bin/env python3
"""
Extract Hydrology Polygons from SurfaceHydrologyPolygonsNational.gdb

This script extracts water body polygons (lakes, rivers, etc.) instead of points
for better representation of water boundaries and areas.
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
    from shapely.geometry import shape
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    print("Error: geopandas is required for processing GDB files.")
    print("Please install with: pip install geopandas")
    sys.exit(1)

def inspect_hydrology_layer(gdb_path: str, layer_name: str):
    """Inspect the hydrology layer to understand water body types."""
    try:
        print(f"\n🔍 Inspecting {layer_name} in {os.path.basename(gdb_path)}:")
        
        with fiona.open(gdb_path, layer=layer_name) as src:
            total_features = len(src)
            print(f"   Total features: {total_features:,}")
            
            # Sample features to understand data structure
            feature_types = {}
            perenniality_types = {}
            sample_count = 0
            
            for feature in src:
                if sample_count >= 1000:  # Sample first 1000 features
                    break
                    
                props = feature['properties']
                
                # Count feature types
                feat_type = props.get('FEATURETYPE', 'Unknown')
                type_val = props.get('TYPE', 'Unknown')
                perennial = props.get('PERENNIALITY', 'Unknown')
                
                feature_types[feat_type] = feature_types.get(feat_type, 0) + 1
                perenniality_types[perennial] = perenniality_types.get(perennial, 0) + 1
                
                # Show sample for first feature
                if sample_count == 0:
                    print(f"   Sample feature properties:")
                    for prop, value in props.items():
                        print(f"     {prop}: {value}")
                
                sample_count += 1
            
            print(f"\n   Feature types found (sample of {sample_count}):")
            for feat_type, count in sorted(feature_types.items()):
                print(f"     {feat_type}: {count}")
            
            print(f"\n   Perenniality types:")
            for peren_type, count in sorted(perenniality_types.items()):
                print(f"     {peren_type}: {count}")
                
    except Exception as e:
        print(f"Error inspecting layer: {e}")

def extract_hydrology_polygons(gdb_path: str, layer_name: str, 
                              output_file: str = "map_data/hydrology_polygons.geojson",
                              chunk_size: int = 5000,
                              feature_filter: Optional[Dict[str, List[str]]] = None,
                              max_features: int = 50000) -> bool:
    """
    Extract hydrology polygons with filtering for relevant water bodies.
    
    Args:
        gdb_path: Path to GDB file
        layer_name: Layer to process
        output_file: Output GeoJSON file path
        chunk_size: Features per chunk for memory management
        feature_filter: Dictionary of property filters
        max_features: Maximum features to extract
    """
    
    # Filter for significant water bodies - simpler approach based on actual data
    if feature_filter is None:
        feature_filter = {
            # Accept all feature types since the data structure is different than expected
            'min_area_threshold': 0.001  # Minimum area threshold instead of type filtering
        }
    
    try:
        print(f"🌊 Extracting hydrology polygons from {os.path.basename(gdb_path)}...")
        print(f"   Output: {output_file}")
        print(f"   Filters: {feature_filter}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        extracted_features = []
        total_processed = 0
        total_matched = 0
        
        # Process in chunks to manage memory
        with fiona.open(gdb_path, layer=layer_name) as src:
            total_features = len(src)
            print(f"   Total features in layer: {total_features:,}")
            
            for i in range(0, min(total_features, max_features), chunk_size):
                end_idx = min(i + chunk_size, total_features, max_features)
                chunk_num = (i // chunk_size) + 1
                total_chunks = min(total_features, max_features) // chunk_size + 1
                
                print(f"   📦 Processing chunk {chunk_num}/{total_chunks}: features {i:,} to {end_idx:,}")
                
                # Read chunk
                chunk_features = []
                feature_idx = 0
                
                for feature in src:
                    if feature_idx < i:
                        feature_idx += 1
                        continue
                    if feature_idx >= end_idx:
                        break
                        
                    props = feature['properties']
                    
                    # Simple filtering based on area and basic criteria
                    match = True
                    
                    # Filter by area if geometry is available
                    try:
                        geom = shape(feature['geometry'])
                        area = geom.area
                        if area < feature_filter.get('min_area_threshold', 0.001):
                            match = False
                    except:
                        # If we can't calculate area, include the feature
                        pass
                    
                    if match:
                        # Calculate area if possible
                        try:
                            geom = shape(feature['geometry'])
                            # Convert to hectares (approximate)
                            area_ha = geom.area / 10000  # Rough conversion from degrees to hectares
                            area_estimate = round(area_ha, 3)
                        except:
                            area_estimate = None
                        
                        # Create GeoJSON feature
                        # Ensure geometry is in dict format for JSON serialization
                        if hasattr(feature['geometry'], '__geo_interface__'):
                            geometry_dict = feature['geometry'].__geo_interface__
                        else:
                            geometry_dict = feature['geometry']
                        
                        geojson_feature = {
                            "type": "Feature",
                            "geometry": geometry_dict,
                            "properties": {
                                "id": f"hydro_{feature_idx}",
                                "feature_type": str(props.get('FEATURETYPE', 'Unknown')),
                                "type": str(props.get('TYPE', '')),
                                "name": str(props.get('NAME', '') or ''),
                                "perenniality": str(props.get('PERENNIALITY', '') or ''),
                                "hierarchy": str(props.get('HIERARCHY', '') or ''),
                                "dimension": str(props.get('DIMENSION', '') or ''),
                                "reliability": str(props.get('FEATURERELIABILITY', '') or ''),
                                "source": str(props.get('FEATURESOURCE', '') or ''),
                                "area_estimate_ha": area_estimate
                            }
                        }
                        
                        chunk_features.append(geojson_feature)
                        total_matched += 1
                    
                    feature_idx += 1
                    total_processed += 1
                
                extracted_features.extend(chunk_features)
                print(f"     Found {len(chunk_features)} matching features in this chunk")
                
                # Stop if we've reached max features
                if len(extracted_features) >= max_features:
                    print(f"   ⚠️  Reached maximum feature limit ({max_features})")
                    extracted_features = extracted_features[:max_features]
                    break
        
        print(f"\n✅ Extraction complete:")
        print(f"   Processed: {total_processed:,} features")
        print(f"   Matched filters: {total_matched:,} features")
        print(f"   Final output: {len(extracted_features):,} features")
        
        # Create GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "features": extracted_features,
            "metadata": {
                "source": os.path.basename(gdb_path),
                "layer": layer_name,
                "total_processed": total_processed,
                "total_matched": total_matched,
                "extraction_date": pd.Timestamp.now().isoformat(),
                "filters_applied": feature_filter
            }
        }
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        
        # Show file size
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"   Output file: {output_file} ({file_size_mb:.1f} MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting hydrology polygons: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Extract hydrology polygons from GDB file')
    parser.add_argument('--gdb', default='SurfaceHydrologyPolygonsNational.gdb',
                       help='Path to hydrology GDB file')
    parser.add_argument('--layer', default='HydroPolys',
                       help='Layer name to extract')
    parser.add_argument('--output', default='map_data/hydrology_polygons.geojson',
                       help='Output GeoJSON file')
    parser.add_argument('--inspect', action='store_true',
                       help='Inspect the GDB structure without extracting')
    parser.add_argument('--max-features', type=int, default=50000,
                       help='Maximum features to extract')
    parser.add_argument('--chunk-size', type=int, default=5000,
                       help='Chunk size for processing')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.gdb):
        print(f"❌ GDB file not found: {args.gdb}")
        sys.exit(1)
    
    if args.inspect:
        inspect_hydrology_layer(args.gdb, args.layer)
    else:
        success = extract_hydrology_polygons(
            gdb_path=args.gdb,
            layer_name=args.layer,
            output_file=args.output,
            chunk_size=args.chunk_size,
            max_features=args.max_features
        )
        
        if success:
            print(f"\n🎉 Success! Hydrology polygons extracted to {args.output}")
        else:
            print(f"\n❌ Failed to extract hydrology polygons")
            sys.exit(1)

if __name__ == "__main__":
    main()
