"""
Step 3: Clean, verify and finalize location data
==================================================
Run: python src/03_clean_and_verify.py

Input:  data/raw/meama_locations_geocoded.csv
Output: data/processed/meama_locations_final.csv
        output/01_verification_map.html

This script:
1. Removes locations with bad/missing coordinates
2. Validates that coordinates are within Georgia
3. Generates a verification map so you can visually check
4. Outputs the clean dataset for analysis
"""

import pandas as pd
import folium
from folium.plugins import MarkerCluster
import os

# Bounding box for Georgia (country)
GEORGIA_BOUNDS = {
    'lat_min': 41.05, 'lat_max': 43.60,
    'lon_min': 40.00, 'lon_max': 46.80
}

# Tighter bounds for Tbilisi
TBILISI_BOUNDS = {
    'lat_min': 41.60, 'lat_max': 41.82,
    'lon_min': 44.65, 'lon_max': 45.00
}

TYPE_COLORS = {
    'Space': '#e84545',
    'Collect': '#f59e0b', 
    'Dropper': '#3b82f6',
    'Unknown': '#888888'
}

TYPE_ICONS = {
    'Space': 'star',
    'Collect': 'shopping-cart',
    'Dropper': 'tint',
    'Unknown': 'question-sign'
}

def run_cleaning():
    input_path = 'data/raw/meama_locations_geocoded.csv'
    output_csv = 'data/processed/meama_locations_final.csv'
    output_map = 'output/01_verification_map.html'
    
    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        print(f"   Run Step 2 first: python src/02_geocode.py")
        return
    
    os.makedirs('data/processed', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    
    df = pd.read_csv(input_path)
    print(f"📋 Loaded {len(df)} locations")
    
    # =========================================================
    # 1. REMOVE ROWS WITH NO COORDINATES
    # =========================================================
    before = len(df)
    df = df.dropna(subset=['latitude', 'longitude'])
    dropped_na = before - len(df)
    print(f"   Dropped {dropped_na} rows with missing coordinates")
    
    # =========================================================
    # 2. REMOVE ROWS OUTSIDE GEORGIA
    # =========================================================
    before = len(df)
    mask = (
        (df['latitude'] >= GEORGIA_BOUNDS['lat_min']) & 
        (df['latitude'] <= GEORGIA_BOUNDS['lat_max']) &
        (df['longitude'] >= GEORGIA_BOUNDS['lon_min']) & 
        (df['longitude'] <= GEORGIA_BOUNDS['lon_max'])
    )
    df = df[mask]
    dropped_bounds = before - len(df)
    print(f"   Dropped {dropped_bounds} rows outside Georgia bounds")
    
    # =========================================================
    # 3. FLAG CITY-ONLY GEOCODES (approximate, not street-level)
    # =========================================================
    approx = df[df['geocode_status'] == 'city_only']
    print(f"   ⚠️  {len(approx)} locations have city-level (approximate) coordinates")
    
    # =========================================================
    # 4. ADD DISTRICT INFO FOR TBILISI LOCATIONS
    # =========================================================
    # Simple district assignment based on lat/lon quadrants
    # (you can improve this later with actual district boundaries)
    def assign_district(row):
        if row['city'] != 'Tbilisi':
            return row['city']
        lat, lon = row['latitude'], row['longitude']
        
        # Rough district boundaries (approximate!)
        if lat > 41.73 and lon < 44.76:
            return 'Vake'
        elif lat > 41.73 and lon < 44.80:
            return 'Saburtalo'
        elif lat > 41.76:
            return 'Gldani/Nadzaladevi'
        elif lat > 41.72 and lon > 44.82:
            return 'Isani/Samgori'
        elif lat < 41.70:
            return 'Mtatsminda/Krtsanisi'
        elif lon < 44.78:
            return 'Didube'
        else:
            return 'Chughureti/Central'
    
    df['district'] = df.apply(assign_district, axis=1)
    
    # =========================================================
    # 5. SUMMARY STATISTICS
    # =========================================================
    print(f"\n{'='*60}")
    print(f"📊 CLEAN DATASET SUMMARY:")
    print(f"   Total locations: {len(df)}")
    
    print(f"\n   By type:")
    for t, c in df['type'].value_counts().items():
        print(f"     {t:10s} → {c}")
    
    print(f"\n   By city:")
    for t, c in df['city'].value_counts().items():
        print(f"     {t:12s} → {c}")
    
    tbilisi = df[df['city'] == 'Tbilisi']
    print(f"\n   Tbilisi districts:")
    for t, c in tbilisi['district'].value_counts().items():
        print(f"     {t:25s} → {c}")
    
    # =========================================================
    # 6. SAVE CLEAN CSV
    # =========================================================
    output_cols = ['name', 'type', 'city', 'district', 'address_clean', 
                   'latitude', 'longitude', 'hours', 'geocode_status']
    df[output_cols].to_csv(output_csv, index=False, encoding='utf-8')
    print(f"\n💾 Clean data saved to {output_csv}")
    
    # =========================================================
    # 7. GENERATE VERIFICATION MAP
    # =========================================================
    print(f"\n🗺️  Generating verification map...")
    
    m = folium.Map(
        location=[41.7151, 44.8271],
        zoom_start=12,
        tiles='CartoDB dark_matter'
    )
    
    # Add title
    title_html = '''
    <div style="position:fixed;top:10px;left:60px;z-index:9999;
         background:rgba(10,10,15,0.9);padding:12px 20px;border-radius:8px;
         border:1px solid #1e1e2e;font-family:Inter,sans-serif;">
        <span style="color:#e84545;font-weight:700;font-size:16px;">MEAMA</span>
        <span style="color:#e8e8ed;font-size:14px;"> Location Network</span>
        <span style="color:#8888a0;font-size:12px;display:block;">
            {} locations · Verification Map
        </span>
    </div>
    '''.format(len(df))
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add legend
    legend_html = '''
    <div style="position:fixed;bottom:30px;left:10px;z-index:9999;
         background:rgba(10,10,15,0.9);padding:12px 16px;border-radius:8px;
         border:1px solid #1e1e2e;font-family:Inter,sans-serif;">
        <div style="color:#e8e8ed;font-size:12px;font-weight:600;margin-bottom:8px;">Location Types</div>
        <div style="color:#e84545;font-size:11px;">● Space ({})</div>
        <div style="color:#f59e0b;font-size:11px;">● Collect ({})</div>
        <div style="color:#3b82f6;font-size:11px;">● Dropper ({})</div>
    </div>
    '''.format(
        len(df[df['type']=='Space']),
        len(df[df['type']=='Collect']),
        len(df[df['type']=='Dropper'])
    )
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add markers
    for _, row in df.iterrows():
        color = TYPE_COLORS.get(row['type'], '#888')
        
        popup_html = f"""
        <div style="font-family:sans-serif;min-width:200px;">
            <b>{row['name']}</b><br>
            <span style="color:#666;">Type: {row['type']}</span><br>
            <span style="color:#666;">Address: {row.get('address_clean','')}</span><br>
            <span style="color:#666;">District: {row['district']}</span><br>
            <span style="color:#666;">Hours: {row.get('hours','')}</span><br>
            <span style="color:{'green' if row['geocode_status']=='success' else 'orange'};">
                Geocode: {row['geocode_status']}
            </span><br>
            <span style="color:#999;font-size:10px;">{row['latitude']:.5f}, {row['longitude']:.5f}</span>
        </div>
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=8 if row['type'] == 'Space' else 6 if row['type'] == 'Collect' else 4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['name']
        ).add_to(m)
    
    m.save(output_map)
    print(f"💾 Verification map saved to {output_map}")
    print(f"\n   👀 OPEN {output_map} IN YOUR BROWSER")
    print(f"   Check that markers are in the right places!")
    print(f"   If any are wrong, manually fix lat/lon in {output_csv}")
    
    print(f"\n🔜 Next step: Run python src/04_analysis.py")

if __name__ == '__main__':
    run_cleaning()
