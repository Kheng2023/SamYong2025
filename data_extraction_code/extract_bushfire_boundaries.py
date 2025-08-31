#!/usr/bin/env python3
"""
Extract Bushfire Boundary Polygons from Bushfire_Boundaries_Historical_2024_V3.gdb

This script extracts bushfire boundary polygons instead of points,
providing actual fire perimeter boundaries for risk analysis.
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional
import argparse
from datetime import datetime, timedelta

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

def inspect_bushfire_layer(gdb_path: str, layer_name: str):
    """Inspect the bushfire layer to understand fire data structure."""
    try:
        print(f"\n🔍 Inspecting {layer_name} in {os.path.basename(gdb_path)}:")
        
        with fiona.open(gdb_path, layer=layer_name) as src:
            total_features = len(src)
            print(f"   Total features: {total_features:,}")
            
            # Sample features to understand data structure
            fire_types = {}
            ignition_causes = {}
            years = {}
            sample_count = 0
            min_area = float('inf')
            max_area = 0
            
            for feature in src:
                if sample_count >= 1000:  # Sample first 1000 features
                    break
                    
                props = feature['properties']
                
                # Count fire types and causes
                fire_type = props.get('fire_type', 'Unknown')
                ignition_cause = props.get('ignition_cause', 'Unknown')
                
                fire_types[fire_type] = fire_types.get(fire_type, 0) + 1
                ignition_causes[ignition_cause] = ignition_causes.get(ignition_cause, 0) + 1
                
                # Parse years from capture_date since ignition_date might be None
                capture_date = props.get('capture_date')
                if capture_date:
                    try:
                        if isinstance(capture_date, str) and len(capture_date) >= 4:
                            year = int(capture_date[:4])
                            years[year] = years.get(year, 0) + 1
                    except:
                        pass
                
                # Track area ranges
                area_ha = props.get('area_ha')
                if area_ha and isinstance(area_ha, (int, float)):
                    min_area = min(min_area, area_ha)
                    max_area = max(max_area, area_ha)
                
                # Show sample for first feature
                if sample_count == 0:
                    print(f"   Sample feature properties:")
                    for prop, value in props.items():
                        print(f"     {prop}: {value}")
                
                sample_count += 1
            
            print(f"\n   Fire types found (sample of {sample_count}):")
            for fire_type, count in sorted(fire_types.items()):
                print(f"     {fire_type}: {count}")
            
            print(f"\n   Ignition causes:")
            for cause, count in sorted(ignition_causes.items()):
                print(f"     {cause}: {count}")
            
            print(f"\n   Years represented:")
            for year, count in sorted(years.items()):
                print(f"     {year}: {count}")
            
            if min_area != float('inf'):
                print(f"\n   Area range: {min_area:.2f} to {max_area:.2f} hectares")
                
    except Exception as e:
        print(f"Error inspecting layer: {e}")

def extract_bushfire_boundaries(gdb_path: str, layer_name: str, 
                               output_file: str = "map_data/bushfire_boundaries.geojson",
                               chunk_size: int = 5000,
                               filters: Optional[Dict[str, Any]] = None,
                               max_features: int = 30000) -> bool:
    """
    Extract bushfire boundary polygons with filtering for relevant fires.
    
    Args:
        gdb_path: Path to GDB file
        layer_name: Layer to process
        output_file: Output GeoJSON file path
        chunk_size: Features per chunk for memory management
        filters: Dictionary of filters to apply
        max_features: Maximum features to extract
    """
    
    # Default filters for recent and significant fires
    if filters is None:
        current_year = datetime.now().year
        filters = {
            'min_year': current_year - 10,  # Last 10 years
            'min_area_ha': 1.0,  # At least 1 hectare
            'fire_types': ['Bushfire', 'Wildfire', 'Forest Fire', 'Grass Fire'],
            'exclude_causes': ['Prescribed Burn', 'Hazard Reduction']
        }
    
    try:
        print(f"🔥 Extracting bushfire boundaries from {os.path.basename(gdb_path)}...")
        print(f"   Output: {output_file}")
        print(f"   Filters: {filters}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        extracted_features = []
        total_processed = 0
        total_matched = 0
        
        # Process in chunks to manage memory
        with fiona.open(gdb_path, layer=layer_name) as src:
            total_features = len(src)
            print(f"   Total features in layer: {total_features:,}")
            
            for i in range(0, min(total_features, max_features * 3), chunk_size):  # Process more to account for filtering
                end_idx = min(i + chunk_size, total_features)
                chunk_num = (i // chunk_size) + 1
                
                print(f"   📦 Processing chunk {chunk_num}: features {i:,} to {end_idx:,}")
                
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
                    
                    # Apply filters
                    match = True
                    
                    # Year filter - use capture_date since ignition_date is often None
                    if 'min_year' in filters:
                        capture_date = props.get('capture_date')
                        if capture_date:
                            try:
                                if isinstance(capture_date, str) and len(capture_date) >= 4:
                                    year = int(capture_date[:4])
                                    if year < filters['min_year']:
                                        match = False
                                else:
                                    # If not a string or too short, skip this filter
                                    pass
                            except:
                                # Skip if date parsing fails
                                pass
                    
                    # Area filter
                    if match and 'min_area_ha' in filters:
                        area_ha = props.get('area_ha')
                        if not area_ha or area_ha < filters['min_area_ha']:
                            match = False
                    
                    # Fire type filter
                    if match and 'fire_types' in filters:
                        fire_type = props.get('fire_type', '')
                        if fire_type and not any(ft.lower() in str(fire_type).lower() for ft in filters['fire_types']):
                            match = False
                    
                    # Exclude certain causes
                    if match and 'exclude_causes' in filters:
                        ignition_cause = props.get('ignition_cause', '')
                        if ignition_cause and any(ec.lower() in str(ignition_cause).lower() for ec in filters['exclude_causes']):
                            match = False
                    
                    if match:
                        # Parse dates for better formatting
                        ignition_date_str = ""
                        extinguish_date_str = ""
                        
                        try:
                            ignition_date = props.get('ignition_date')
                            if ignition_date:
                                if isinstance(ignition_date, str):
                                    ignition_date_str = pd.to_datetime(ignition_date).strftime('%Y-%m-%d')
                                else:
                                    ignition_date_str = ignition_date.strftime('%Y-%m-%d')
                        except:
                            pass
                        
                        try:
                            extinguish_date = props.get('extinguish_date')
                            if extinguish_date:
                                if isinstance(extinguish_date, str):
                                    extinguish_date_str = pd.to_datetime(extinguish_date).strftime('%Y-%m-%d')
                                else:
                                    extinguish_date_str = extinguish_date.strftime('%Y-%m-%d')
                        except:
                            pass
                        
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
                                "id": f"fire_{props.get('fire_id', feature_idx)}",
                                "fire_id": str(props.get('fire_id', '') or ''),
                                "fire_name": str(props.get('fire_name', '') or ''),
                                "ignition_date": ignition_date_str,
                                "extinguish_date": extinguish_date_str,
                                "fire_type": str(props.get('fire_type', '') or ''),
                                "ignition_cause": str(props.get('ignition_cause', '') or ''),
                                "capture_method": str(props.get('capt_method', '') or ''),
                                "area_ha": props.get('area_ha', 0),
                                "perimeter_km": props.get('perim_km', 0),
                                "capture_date": str(props.get('capture_date', '') or '')
                            }
                        }
                        
                        # Add risk level based on area
                        area_ha = props.get('area_ha', 0)
                        if area_ha >= 10000:
                            risk_level = "Very High"
                        elif area_ha >= 1000:
                            risk_level = "High"
                        elif area_ha >= 100:
                            risk_level = "Medium"
                        else:
                            risk_level = "Low"
                        
                        geojson_feature['properties']['risk_level'] = risk_level
                        
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
        
        # Sort by area (largest fires first) for better visualization priority
        extracted_features.sort(key=lambda x: x['properties'].get('area_ha', 0), reverse=True)
        
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
                "filters_applied": filters
            }
        }
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        
        # Show file size and summary
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"   Output file: {output_file} ({file_size_mb:.1f} MB)")
        
        # Risk level summary
        risk_counts = {}
        for feature in extracted_features:
            risk = feature['properties']['risk_level']
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        print(f"   Risk level distribution:")
        for risk, count in sorted(risk_counts.items()):
            print(f"     {risk}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting bushfire boundaries: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Extract bushfire boundary polygons from GDB file')
    parser.add_argument('--gdb', default='Bushfire_Boundaries_Historical_2024_V3.gdb',
                       help='Path to bushfire GDB file')
    parser.add_argument('--layer', default='Bushfire_Boundaries_Historical_V3',
                       help='Layer name to extract')
    parser.add_argument('--output', default='map_data/bushfire_boundaries.geojson',
                       help='Output GeoJSON file')
    parser.add_argument('--inspect', action='store_true',
                       help='Inspect the GDB structure without extracting')
    parser.add_argument('--max-features', type=int, default=30000,
                       help='Maximum features to extract')
    parser.add_argument('--chunk-size', type=int, default=5000,
                       help='Chunk size for processing')
    parser.add_argument('--min-year', type=int, default=2014,
                       help='Minimum year for fires to include')
    parser.add_argument('--min-area', type=float, default=1.0,
                       help='Minimum fire area in hectares')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.gdb):
        print(f"❌ GDB file not found: {args.gdb}")
        sys.exit(1)
    
    if args.inspect:
        inspect_bushfire_layer(args.gdb, args.layer)
    else:
        filters = {
            'min_year': args.min_year,
            'min_area_ha': args.min_area,
            'fire_types': ['Bushfire', 'Wildfire', 'Forest Fire', 'Grass Fire'],
            'exclude_causes': ['Prescribed Burn', 'Hazard Reduction']
        }
        
        success = extract_bushfire_boundaries(
            gdb_path=args.gdb,
            layer_name=args.layer,
            output_file=args.output,
            chunk_size=args.chunk_size,
            filters=filters,
            max_features=args.max_features
        )
        
        if success:
            print(f"\n🎉 Success! Bushfire boundaries extracted to {args.output}")
        else:
            print(f"\n❌ Failed to extract bushfire boundaries")
            sys.exit(1)

if __name__ == "__main__":
    main()
