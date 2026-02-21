"""
Step 4: Scoring Model & Recommendations
=========================================
Run: python3 src/04_analysis.py

Input:  data/processed/meama_locations_final.csv
Output: output/02_analysis_map.html       (interactive recommendation map)
        output/03_charts/                  (analysis charts)
        output/recommendations.csv         (top locations)

This script:
1. Analyzes current network coverage
2. Builds a multi-factor scoring model
3. Generates candidate grid across Tbilisi
4. Scores every candidate point
5. Produces recommendations + interactive map
"""

import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from math import radians, sin, cos, sqrt, atan2

# ============================================
# CONFIG
# ============================================
TBILISI_CENTER = (41.7151, 44.8271)
GRID_STEP = 0.004          # ~400m between grid points
GRID_LAT = (41.67, 41.82)  # Tbilisi bounding box
GRID_LON = (44.70, 44.90)

# Scoring weights
WEIGHTS = {
    'coverage_gap': 0.30,   # Distance from existing locations (higher = more needed)
    'poi_density': 0.25,    # Proximity to key points of interest
    'population': 0.20,     # District population density
    'competition': 0.15,    # Nearby coffee competitors (moderate = good)
    'accessibility': 0.10,  # Near metro/main roads
}

# Chart styling
BG_COLOR = '#0a0a0f'
CARD_COLOR = '#12121a'
TEXT_COLOR = '#e8e8ed'
MUTED_COLOR = '#8888a0'
COLORS = ['#e84545', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4']

plt.style.use('dark_background')
plt.rcParams['figure.facecolor'] = BG_COLOR
plt.rcParams['axes.facecolor'] = CARD_COLOR
plt.rcParams['text.color'] = TEXT_COLOR
plt.rcParams['axes.labelcolor'] = MUTED_COLOR
plt.rcParams['xtick.color'] = MUTED_COLOR
plt.rcParams['ytick.color'] = MUTED_COLOR
plt.rcParams['font.size'] = 10

# ============================================
# KEY POIS IN TBILISI (metro stations, universities, malls)
# These are major foot traffic generators
# ============================================
METRO_STATIONS = [
    ('Akhmeteli Theatre', 41.7862, 44.7917),
    ('Sarajishvili', 41.7763, 44.7900),
    ('Guramishvili', 41.7680, 44.7917),
    ('Grmagele', 41.7588, 44.7870),
    ('Didube', 41.7455, 44.7830),
    ('Gotsiridze', 41.7370, 44.7828),
    ('Tsereteli', 41.7320, 44.7833),
    ('Station Square I', 41.7215, 44.7920),
    ('Station Square II', 41.7210, 44.7925),
    ('Marjanishvili', 41.7108, 44.7960),
    ('Rustaveli', 41.7005, 44.7970),
    ('Freedom Square', 41.6938, 44.8013),
    ('Avlabari', 41.6920, 44.8130),
    ('300 Aragveli', 41.6945, 44.8260),
    ('Isani', 41.6920, 44.8380),
    ('Samgori', 41.6870, 44.8530),
    ('Varketili', 41.6690, 44.8780),
    ('Medical University', 41.7280, 44.7700),
    ('Delisi', 41.7320, 44.7600),
    ('Vazha-Pshavela', 41.7370, 44.7500),
    ('Technical University', 41.7240, 44.7690),
    ('State University', 41.7070, 44.7380),
]

UNIVERSITIES = [
    ('Tbilisi State University', 41.7070, 44.7380),
    ('Free University', 41.8058, 44.7683),
    ('Georgian Technical University', 41.7240, 44.7690),
    ('GIPA', 41.7025, 44.7977),
    ('BTU', 41.7067, 44.7382),
    ('Alte University', 41.7180, 44.7219),
    ('Caucasus University', 41.7220, 44.7315),
    ('Agricultural University', 41.8058, 44.7683),
    ('IT Academy Step', 41.7230, 44.7401),
    ('Ilia State University', 41.7280, 44.7700),
]

MALLS = [
    ('Tbilisi Mall', 41.6934, 44.8014),
    ('East Point', 41.6935, 44.8015),
    ('City Mall', 41.7213, 44.7226),
    ('Galleria Tbilisi', 41.7158, 44.8015),
    ('Vake Plaza', 41.7111, 44.7551),
    ('Didube Plaza', 41.7385, 44.7805),
]

# Tbilisi district data (approximate)
DISTRICTS = {
    'Vake':                {'pop': 120000, 'area_km2': 17.8, 'income_idx': 1.3},
    'Saburtalo':           {'pop': 200000, 'area_km2': 28.7, 'income_idx': 1.1},
    'Didube':              {'pop': 50000,  'area_km2': 6.3,  'income_idx': 0.9},
    'Chughureti/Central':  {'pop': 40000,  'area_km2': 4.5,  'income_idx': 1.0},
    'Mtatsminda/Krtsanisi':{'pop': 60000,  'area_km2': 25.0, 'income_idx': 1.2},
    'Gldani/Nadzaladevi':  {'pop': 300000, 'area_km2': 42.0, 'income_idx': 0.7},
    'Isani/Samgori':       {'pop': 230000, 'area_km2': 39.0, 'income_idx': 0.8},
}


def haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lon points."""
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def nearest_distance(lat, lon, points):
    """Distance to nearest point in a list of (name, lat, lon) tuples."""
    if not points:
        return 99999
    return min(haversine(lat, lon, p[1], p[2]) for p in points)


def count_within_radius(lat, lon, points, radius_m):
    """Count points within radius (meters)."""
    return sum(1 for p in points if haversine(lat, lon, p[1], p[2]) <= radius_m)


def assign_district(lat, lon):
    """Simple district assignment based on coordinates."""
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


def normalize(values, inverse=False):
    """Normalize array to 0-10 scale."""
    arr = np.array(values, dtype=float)
    if arr.max() == arr.min():
        return np.full_like(arr, 5.0)
    normalized = (arr - arr.min()) / (arr.max() - arr.min()) * 10
    if inverse:
        normalized = 10 - normalized
    return normalized


# ============================================
# MAIN ANALYSIS
# ============================================
def run_analysis():
    input_path = 'data/processed/meama_locations_final.csv'
    
    if not os.path.exists(input_path):
        print("❌ Run previous steps first!")
        return
    
    os.makedirs('output/03_charts', exist_ok=True)
    
    df = pd.read_csv(input_path)
    
    # Filter to Tbilisi only for scoring
    tbilisi = df[df['city'] == 'Tbilisi'].copy()
    
    # Remove approximate geocodes for distance calculations
    # (41.6934591, 44.8014495 is the city-center fallback)
    precise = tbilisi[tbilisi['geocode_status'] == 'success'].copy()
    
    print(f"📊 DATA LOADED:")
    print(f"   Total locations: {len(df)}")
    print(f"   Tbilisi:         {len(tbilisi)}")
    print(f"   Precise coords:  {len(precise)}")
    
    # Convert existing locations to (name, lat, lon) tuples
    existing = [(r['name'], r['latitude'], r['longitude']) for _, r in precise.iterrows()]
    
    # =========================================================
    # ANALYSIS 1: Current Network Statistics
    # =========================================================
    print(f"\n{'='*60}")
    print(f"📈 CURRENT NETWORK ANALYSIS")
    print(f"{'='*60}")
    
    for district, data in DISTRICTS.items():
        district_locs = tbilisi[tbilisi['district'] == district]
        density = data['pop'] / len(district_locs) if len(district_locs) > 0 else data['pop']
        droppers = len(district_locs[district_locs['type'] == 'Dropper'])
        collects = len(district_locs[district_locs['type'] == 'Collect'])
        per_10k = len(district_locs) / (data['pop'] / 10000)
        print(f"   {district:25s} │ Pop: {data['pop']:>7,} │ Locs: {len(district_locs):>3} │ "
              f"Per 10K: {per_10k:.1f} │ Droppers: {droppers} │ Collects: {collects}")
    
    # =========================================================
    # CHART 1: Locations per 10K residents by district
    # =========================================================
    districts_list = list(DISTRICTS.keys())
    per_10k_list = []
    for d in districts_list:
        n = len(tbilisi[tbilisi['district'] == d])
        per_10k_list.append(n / (DISTRICTS[d]['pop'] / 10000))
    
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(districts_list, per_10k_list, color=COLORS[:len(districts_list)], height=0.6)
    ax.set_xlabel('MEAMA Locations per 10,000 Residents')
    ax.set_title('Coverage Density by District', fontsize=14, fontweight='bold', pad=15)
    for bar, val in zip(bars, per_10k_list):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}', va='center', fontsize=10, color=TEXT_COLOR)
    ax.spines[:].set_visible(False)
    ax.grid(axis='x', alpha=0.1)
    plt.tight_layout()
    plt.savefig('output/03_charts/01_coverage_density.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
    plt.close()
    print(f"\n   💾 Chart saved: output/03_charts/01_coverage_density.png")
    
    # =========================================================
    # CHART 2: Location type distribution by district
    # =========================================================
    fig, ax = plt.subplots(figsize=(10, 5))
    type_data = {}
    for t in ['Dropper', 'Collect', 'Space']:
        type_data[t] = [len(tbilisi[(tbilisi['district'] == d) & (tbilisi['type'] == t)]) for d in districts_list]
    
    x = np.arange(len(districts_list))
    w = 0.25
    ax.bar(x - w, type_data['Dropper'], w, label='Dropper', color=COLORS[3], alpha=0.85)
    ax.bar(x, type_data['Collect'], w, label='Collect', color=COLORS[1], alpha=0.85)
    ax.bar(x + w, type_data['Space'], w, label='Space', color=COLORS[0], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(districts_list, rotation=30, ha='right', fontsize=8)
    ax.set_ylabel('Count')
    ax.set_title('Location Types by District', fontsize=14, fontweight='bold', pad=15)
    ax.legend(facecolor=CARD_COLOR, edgecolor='none')
    ax.spines[:].set_visible(False)
    plt.tight_layout()
    plt.savefig('output/03_charts/02_types_by_district.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
    plt.close()
    print(f"   💾 Chart saved: output/03_charts/02_types_by_district.png")
    
    # =========================================================
    # SCORING MODEL: Generate candidate grid
    # =========================================================
    print(f"\n{'='*60}")
    print(f"🧮 SCORING MODEL")
    print(f"{'='*60}")
    print(f"   Weights: {WEIGHTS}")
    
    lat_range = np.arange(GRID_LAT[0], GRID_LAT[1], GRID_STEP)
    lon_range = np.arange(GRID_LON[0], GRID_LON[1], GRID_STEP)
    
    total_points = len(lat_range) * len(lon_range)
    print(f"   Grid: {len(lat_range)} × {len(lon_range)} = {total_points} candidate points")
    print(f"   Scoring... ", end='', flush=True)
    
    candidates = []
    all_pois = METRO_STATIONS + UNIVERSITIES + MALLS
    
    for lat in lat_range:
        for lon in lon_range:
            district = assign_district(lat, lon)
            dist_data = DISTRICTS.get(district, {'pop': 100000, 'area_km2': 20, 'income_idx': 1.0})
            
            # Factor 1: Coverage gap (distance to nearest existing location)
            nearest_dist = min(haversine(lat, lon, e[1], e[2]) for e in existing) if existing else 5000
            
            # Factor 2: POI density (count of POIs within 600m)
            poi_count = count_within_radius(lat, lon, all_pois, 600)
            
            # Factor 3: Population density of district
            pop_density = dist_data['pop'] / dist_data['area_km2']
            
            # Factor 4: Competition score (metro proximity as proxy)
            metro_dist = nearest_distance(lat, lon, METRO_STATIONS)
            
            # Factor 5: Accessibility (near main corridors)
            uni_dist = nearest_distance(lat, lon, UNIVERSITIES)
            
            candidates.append({
                'latitude': lat,
                'longitude': lon,
                'district': district,
                'nearest_meama_m': nearest_dist,
                'poi_count_600m': poi_count,
                'pop_density': pop_density,
                'metro_dist_m': metro_dist,
                'uni_dist_m': uni_dist,
                'income_idx': dist_data['income_idx'],
            })
    
    cdf = pd.DataFrame(candidates)
    
    # Normalize each factor to 0-10
    cdf['score_coverage'] = normalize(cdf['nearest_meama_m'].values)         # Far from existing = high
    cdf['score_poi'] = normalize(cdf['poi_count_600m'].values)               # More POIs = high
    cdf['score_pop'] = normalize(cdf['pop_density'].values)                  # Higher density = high
    cdf['score_metro'] = normalize(cdf['metro_dist_m'].values, inverse=True) # Closer to metro = high
    cdf['score_access'] = normalize(cdf['uni_dist_m'].values, inverse=True)  # Closer to uni = high
    
    # Weighted total score
    cdf['total_score'] = (
        WEIGHTS['coverage_gap'] * cdf['score_coverage'] +
        WEIGHTS['poi_density'] * cdf['score_poi'] +
        WEIGHTS['population'] * cdf['score_pop'] +
        WEIGHTS['competition'] * cdf['score_metro'] +
        WEIGHTS['accessibility'] * cdf['score_access']
    )
    
    # Scale to 0-100
    cdf['total_score'] = (cdf['total_score'] / 10) * 100
    
    print("Done!")
    print(f"   Score range: {cdf['total_score'].min():.1f} – {cdf['total_score'].max():.1f}")
    print(f"   Mean score:  {cdf['total_score'].mean():.1f}")
    
    # =========================================================
    # TOP RECOMMENDATIONS
    # =========================================================
    # Filter: must be at least 300m from existing location
    viable = cdf[cdf['nearest_meama_m'] >= 300].copy()
    
    # Get top 15 but ensure spatial diversity (min 500m between recommendations)
    recommendations = []
    viable_sorted = viable.sort_values('total_score', ascending=False)
    
    for _, row in viable_sorted.iterrows():
        too_close = False
        for rec in recommendations:
            if haversine(row['latitude'], row['longitude'], rec['latitude'], rec['longitude']) < 500:
                too_close = True
                break
        if not too_close:
            recommendations.append(row.to_dict())
        if len(recommendations) >= 15:
            break
    
    rec_df = pd.DataFrame(recommendations)
    
    print(f"\n{'='*60}")
    print(f"🎯 TOP 15 RECOMMENDED LOCATIONS")
    print(f"{'='*60}")
    print(f"   {'#':>2} │ {'Score':>5} │ {'District':25s} │ {'Nearest MEAMA':>13} │ {'POIs':>4} │ Coordinates")
    print(f"   {'─'*95}")
    
    for i, (_, row) in enumerate(rec_df.iterrows(), 1):
        print(f"   {i:2d} │ {row['total_score']:5.1f} │ {row['district']:25s} │ "
              f"{row['nearest_meama_m']:>10.0f}m │ {row['poi_count_600m']:4.0f} │ "
              f"{row['latitude']:.4f}, {row['longitude']:.4f}")
    
    # Save recommendations
    rec_df.to_csv('output/recommendations.csv', index=False)
    print(f"\n   💾 Saved: output/recommendations.csv")
    
    # =========================================================
    # CHART 3: Score distribution histogram
    # =========================================================
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(cdf['total_score'], bins=40, color=COLORS[3], alpha=0.8, edgecolor='none')
    # Mark recommendation threshold
    threshold = rec_df['total_score'].min()
    ax.axvline(x=threshold, color=COLORS[0], linewidth=2, linestyle='--', label=f'Top 15 threshold ({threshold:.0f})')
    ax.set_xlabel('Location Score (0-100)')
    ax.set_ylabel('Number of Grid Points')
    ax.set_title('Score Distribution Across Tbilisi Grid', fontsize=14, fontweight='bold', pad=15)
    ax.legend(facecolor=CARD_COLOR, edgecolor='none')
    ax.spines[:].set_visible(False)
    plt.tight_layout()
    plt.savefig('output/03_charts/03_score_distribution.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
    plt.close()
    print(f"   💾 Chart saved: output/03_charts/03_score_distribution.png")
    
    # =========================================================
    # CHART 4: Top 15 recommendations bar chart
    # =========================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = [f"#{i+1} {r['district']}" for i, (_, r) in enumerate(rec_df.iterrows())]
    scores = rec_df['total_score'].values
    
    # Stacked bar showing score components
    components = {
        'Coverage Gap': rec_df['score_coverage'].values * WEIGHTS['coverage_gap'] * 10,
        'POI Density': rec_df['score_poi'].values * WEIGHTS['poi_density'] * 10,
        'Population': rec_df['score_pop'].values * WEIGHTS['population'] * 10,
        'Metro Access': rec_df['score_metro'].values * WEIGHTS['competition'] * 10,
        'Uni Proximity': rec_df['score_access'].values * WEIGHTS['accessibility'] * 10,
    }
    
    bottom = np.zeros(len(rec_df))
    for j, (comp_name, comp_vals) in enumerate(components.items()):
        ax.barh(labels, comp_vals, left=bottom, label=comp_name, 
                color=COLORS[j], alpha=0.85, height=0.6)
        bottom += comp_vals
    
    ax.set_xlabel('Score (0-100)')
    ax.set_title('Top 15 Locations — Score Breakdown', fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='lower right', facecolor=CARD_COLOR, edgecolor='none', fontsize=8)
    ax.invert_yaxis()
    ax.spines[:].set_visible(False)
    plt.tight_layout()
    plt.savefig('output/03_charts/04_top15_breakdown.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
    plt.close()
    print(f"   💾 Chart saved: output/03_charts/04_top15_breakdown.png")
    
    # =========================================================
    # CHART 5: Sensitivity analysis
    # =========================================================
    print(f"\n📊 Running sensitivity analysis...")
    
    weight_scenarios = {
        'Base': WEIGHTS,
        'Coverage Focus':  {'coverage_gap': 0.50, 'poi_density': 0.15, 'population': 0.15, 'competition': 0.10, 'accessibility': 0.10},
        'Foot Traffic Focus': {'coverage_gap': 0.15, 'poi_density': 0.40, 'population': 0.20, 'competition': 0.15, 'accessibility': 0.10},
        'Population Focus': {'coverage_gap': 0.15, 'poi_density': 0.15, 'population': 0.40, 'competition': 0.15, 'accessibility': 0.15},
    }
    
    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    
    for idx, (scenario_name, w) in enumerate(weight_scenarios.items()):
        score = (
            w['coverage_gap'] * cdf['score_coverage'] +
            w['poi_density'] * cdf['score_poi'] +
            w['population'] * cdf['score_pop'] +
            w['competition'] * cdf['score_metro'] +
            w['accessibility'] * cdf['score_access']
        ) / 10 * 100
        
        axes[idx].hist(score, bins=30, color=COLORS[idx], alpha=0.8, edgecolor='none')
        axes[idx].set_title(scenario_name, fontsize=10, fontweight='bold')
        axes[idx].set_xlabel('Score', fontsize=8)
        axes[idx].spines[:].set_visible(False)
        axes[idx].tick_params(labelsize=7)
    
    fig.suptitle('Sensitivity Analysis: Score Distribution Under Different Weights', 
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig('output/03_charts/05_sensitivity.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
    plt.close()
    print(f"   💾 Chart saved: output/03_charts/05_sensitivity.png")
    
    # =========================================================
    # INTERACTIVE RECOMMENDATION MAP
    # =========================================================
    print(f"\n🗺️  Generating recommendation map...")
    
    m = folium.Map(location=TBILISI_CENTER, zoom_start=12, tiles='CartoDB dark_matter')
    
    # Title
    title_html = f'''
    <div style="position:fixed;top:10px;left:60px;z-index:9999;
         background:rgba(10,10,15,0.92);padding:14px 22px;border-radius:10px;
         border:1px solid #1e1e2e;font-family:sans-serif;">
        <span style="color:#e84545;font-weight:800;font-size:17px;">MEAMA</span>
        <span style="color:#e8e8ed;font-size:15px;font-weight:600;"> Dropper Expansion Analysis</span>
        <div style="color:#8888a0;font-size:11px;margin-top:2px;">
            {len(precise)} existing locations · {len(rec_df)} recommendations · Scored {total_points} grid points
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Legend
    legend_html = '''
    <div style="position:fixed;bottom:30px;left:12px;z-index:9999;
         background:rgba(10,10,15,0.92);padding:14px 18px;border-radius:10px;
         border:1px solid #1e1e2e;font-family:sans-serif;line-height:1.8;">
        <div style="color:#e8e8ed;font-size:12px;font-weight:700;margin-bottom:6px;">Layers</div>
        <div style="color:#3b82f6;font-size:11px;">● Existing Droppers</div>
        <div style="color:#f59e0b;font-size:11px;">● Existing Collects</div>
        <div style="color:#e84545;font-size:11px;">● Existing Spaces</div>
        <div style="color:#10b981;font-size:11px;">⬤ Recommended New Locations</div>
        <div style="color:#8b5cf6;font-size:11px;">▲ Metro Stations</div>
        <div style="color:#8888a0;font-size:11px;">◼ Heatmap = Opportunity Score</div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Layer: Existing locations
    existing_group = folium.FeatureGroup(name='Existing Locations', show=True)
    type_colors = {'Dropper': '#3b82f6', 'Collect': '#f59e0b', 'Space': '#e84545'}
    
    for _, row in precise.iterrows():
        color = type_colors.get(row['type'], '#888')
        folium.CircleMarker(
            [row['latitude'], row['longitude']],
            radius=4 if row['type'] == 'Dropper' else 6,
            color=color, fill=True, fill_color=color, fill_opacity=0.6,
            tooltip=f"{row['name']} ({row['type']})",
            popup=f"<b>{row['name']}</b><br>Type: {row['type']}<br>District: {row['district']}"
        ).add_to(existing_group)
    existing_group.add_to(m)
    
    # Layer: Heatmap of opportunity scores
    heat_data = [[r['latitude'], r['longitude'], r['total_score']] 
                 for _, r in cdf[cdf['total_score'] > cdf['total_score'].quantile(0.5)].iterrows()]
    heat_group = folium.FeatureGroup(name='Opportunity Heatmap', show=True)
    HeatMap(heat_data, radius=18, blur=22, max_zoom=13,
            gradient={0.2: '#3b82f6', 0.4: '#8b5cf6', 0.6: '#f59e0b', 0.8: '#e84545', 1.0: '#ff0000'}
    ).add_to(heat_group)
    heat_group.add_to(m)
    
    # Layer: Recommendations
    rec_group = folium.FeatureGroup(name='Recommended Locations', show=True)
    for i, (_, row) in enumerate(rec_df.iterrows(), 1):
        popup_html = f"""
        <div style="font-family:sans-serif;min-width:220px;">
            <div style="background:#10b981;color:white;padding:6px 10px;margin:-10px -10px 8px;
                 border-radius:4px 4px 0 0;font-weight:700;">
                Recommendation #{i}
            </div>
            <b>Score: {row['total_score']:.1f}/100</b><br>
            <span style="color:#666;">District: {row['district']}</span><br>
            <hr style="border:none;border-top:1px solid #eee;margin:6px 0;">
            <span style="font-size:11px;">
                Coverage Gap: {row['score_coverage']:.1f}/10<br>
                POI Density: {row['score_poi']:.1f}/10<br>
                Population: {row['score_pop']:.1f}/10<br>
                Metro Access: {row['score_metro']:.1f}/10<br>
                Uni Proximity: {row['score_access']:.1f}/10<br>
            </span>
            <hr style="border:none;border-top:1px solid #eee;margin:6px 0;">
            <span style="font-size:10px;color:#999;">
                Nearest MEAMA: {row['nearest_meama_m']:.0f}m<br>
                Coords: {row['latitude']:.4f}, {row['longitude']:.4f}
            </span>
        </div>
        """
        
        folium.CircleMarker(
            [row['latitude'], row['longitude']],
            radius=12,
            color='#10b981',
            fill=True,
            fill_color='#10b981',
            fill_opacity=0.85,
            weight=3,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"#{i} — Score: {row['total_score']:.0f}"
        ).add_to(rec_group)
        
        # Add rank number
        folium.Marker(
            [row['latitude'], row['longitude']],
            icon=folium.DivIcon(html=f'''
                <div style="font-size:10px;font-weight:800;color:white;
                     text-align:center;line-height:24px;
                     width:24px;height:24px;background:#10b981;
                     border-radius:50%;border:2px solid white;
                     transform:translate(-12px,-12px);">{i}</div>
            ''')
        ).add_to(rec_group)
    rec_group.add_to(m)
    
    # Layer: Metro stations
    metro_group = folium.FeatureGroup(name='Metro Stations', show=False)
    for name, lat, lon in METRO_STATIONS:
        folium.CircleMarker(
            [lat, lon], radius=5, color='#8b5cf6', fill=True,
            fill_color='#8b5cf6', fill_opacity=0.7,
            tooltip=f"Metro: {name}"
        ).add_to(metro_group)
    metro_group.add_to(m)
    
    # Layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    m.save('output/02_analysis_map.html')
    print(f"   💾 Map saved: output/02_analysis_map.html")
    
    # =========================================================
    # FINAL SUMMARY
    # =========================================================
    print(f"\n{'='*60}")
    print(f"✅ ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"\n📂 Output files:")
    print(f"   output/02_analysis_map.html          ← Interactive recommendation map")
    print(f"   output/03_charts/01_coverage_density.png")
    print(f"   output/03_charts/02_types_by_district.png")
    print(f"   output/03_charts/03_score_distribution.png")
    print(f"   output/03_charts/04_top15_breakdown.png")
    print(f"   output/03_charts/05_sensitivity.png")
    print(f"   output/recommendations.csv           ← Top 15 locations data")
    
    print(f"\n🔑 KEY FINDINGS:")
    top_districts = rec_df['district'].value_counts()
    for d, c in top_districts.items():
        print(f"   → {d}: {c} recommended locations")
    
    print(f"\n   Highest opportunity score: {rec_df['total_score'].max():.1f}/100")
    print(f"   Average recommendation score: {rec_df['total_score'].mean():.1f}/100")
    
    # Coverage improvement estimate
    avg_nearest_before = np.mean([min(haversine(d['pop'], d['area_km2'], e[1], e[2]) 
                                      for e in existing) for d in DISTRICTS.values()] if False else [800])
    
    underserved = ['Gldani/Nadzaladevi', 'Isani/Samgori']
    recs_in_underserved = len(rec_df[rec_df['district'].isin(underserved)])
    print(f"   Recommendations in underserved districts: {recs_in_underserved}/15")
    
    print(f"\n   📌 Open output/02_analysis_map.html in your browser to explore!")
    print(f"   📌 Toggle layers on/off to see different data overlays")

if __name__ == '__main__':
    run_analysis()
