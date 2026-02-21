"""
Step 2: Geocode MEAMA locations (address → lat/lon)
=====================================================
Run: python src/02_geocode.py

Input:  data/raw/meama_locations_raw.csv
Output: data/raw/meama_locations_geocoded.csv

Uses OpenStreetMap Nominatim (free, no API key needed).
Rate limit: 1 request per second.
"""

import pandas as pd
import time
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

def geocode_address(geolocator, address, attempt=1, max_attempts=3):
    """Geocode a single address with retry logic."""
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude, location.address
        return None, None, None
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        if attempt <= max_attempts:
            time.sleep(2)
            return geocode_address(geolocator, address, attempt + 1)
        return None, None, None

def run_geocoding():
    input_path = 'data/raw/meama_locations_raw.csv'
    output_path = 'data/raw/meama_locations_geocoded.csv'
    
    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        print(f"   Run Step 1 first: python src/01_scrape_locations.py")
        return
    
    df = pd.read_csv(input_path)
    print(f"📍 Geocoding {len(df)} locations...")
    print(f"   ⏱️  This will take ~{len(df) * 1.5 / 60:.0f} minutes (rate limited to 1 req/sec)\n")
    
    geolocator = Nominatim(
        user_agent="meama-dropper-analysis-student-project-2025",
        timeout=10
    )
    
    latitudes = []
    longitudes = []
    matched_addresses = []
    geocode_status = []
    
    success_count = 0
    fail_count = 0
    
    for idx, row in df.iterrows():
        address = row['address_for_geocoding']
        name = row['name']
        
        # Skip if address is empty or placeholder
        if pd.isna(address) or '123 Main St' in str(address):
            latitudes.append(None)
            longitudes.append(None)
            matched_addresses.append(None)
            geocode_status.append('skipped')
            fail_count += 1
            print(f"  [{idx+1}/{len(df)}] ⏭️  SKIP  {name[:40]}")
            continue
        
        # Try geocoding with full address
        lat, lon, matched = geocode_address(geolocator, address)
        
        # If failed, try with just the street + Tbilisi
        if lat is None and row['city'] == 'Tbilisi':
            simplified = row['address_clean'] + ', Tbilisi, Georgia'
            lat, lon, matched = geocode_address(geolocator, simplified)
        
        # If still failed, try with just the name + city
        if lat is None:
            fallback = f"{row['city']}, Georgia"
            lat, lon, matched = geocode_address(geolocator, fallback)
            if lat:
                geocode_status.append('city_only')  # Mark as approximate
            else:
                geocode_status.append('failed')
        else:
            geocode_status.append('success')
        
        latitudes.append(lat)
        longitudes.append(lon)
        matched_addresses.append(matched)
        
        if lat:
            success_count += 1
            status_icon = '✅'
        else:
            fail_count += 1
            status_icon = '❌'
        
        print(f"  [{idx+1}/{len(df)}] {status_icon} {name[:40]:40s} → {lat}, {lon}")
        
        time.sleep(1.1)  # Respect Nominatim rate limit
    
    df['latitude'] = latitudes
    df['longitude'] = longitudes
    df['geocoded_address'] = matched_addresses
    df['geocode_status'] = geocode_status
    
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"\n{'='*60}")
    print(f"📊 GEOCODING RESULTS:")
    print(f"   ✅ Success:    {success_count}")
    print(f"   ❌ Failed:     {fail_count}")
    print(f"   📈 Rate:       {success_count/len(df)*100:.0f}%")
    print(f"\n💾 Saved to {output_path}")
    
    # Show failed ones so user can fix manually
    failed = df[df['geocode_status'].isin(['failed', 'skipped'])]
    if len(failed) > 0:
        print(f"\n⚠️  {len(failed)} locations need manual geocoding:")
        print(f"   Open {output_path} and add lat/lon for these rows:")
        for _, row in failed.iterrows():
            print(f"   - {row['name']}: {row['address_raw']}")
        print(f"\n   💡 Tip: Search each address on Google Maps,")
        print(f"      right-click → 'Coordinates' to get lat/lon")
    
    print(f"\n🔜 Next step: Run python src/03_clean_and_verify.py")

if __name__ == '__main__':
    run_geocoding()
