# MEAMA Dropper Network Optimizer

> Data-driven location intelligence tool that identifies optimal placement for new MEAMA Dropper vending machines across Tbilisi.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?logo=pandas&logoColor=white)
![Folium](https://img.shields.io/badge/Folium-Maps-77B829?logo=leaflet&logoColor=white)
![Status](https://img.shields.io/badge/Status-Complete-success)

---

## The Problem

MEAMA operates **177 locations** across Georgia (140 Droppers, 34 Collects, 3 Spaces), but their network has a severe distribution imbalance: central Tbilisi districts have up to **51× more coverage per capita** than peripheral ones. Where should the next Droppers go?

## The Solution

A **multi-factor weighted scoring model** that evaluates 1,900 grid points across Tbilisi and ranks them by expansion potential. The model considers population density, foot traffic proxies (metro stations, universities, malls), competitive landscape, existing coverage gaps, and accessibility.

**Result:** 15 optimal locations identified, with scores ranging from 54.2 to 58.5 out of 100.

---

## Key Findings

| Insight | Detail |
|---|---|
| **Coverage inequality** | Mtatsminda/Krtsanisi: 10.2 locations per 10K residents vs. Gldani/Nadzaladevi: 0.1 |
| **Biggest opportunity** | Didube district — 7 of top 15 recommendations (avg score: 57.2) |
| **Underserved population** | 530K people in Gldani + Isani/Samgori served by only 5 total locations |
| **Network concentration** | 92% of all MEAMA locations (163/177) are in Tbilisi alone |

### Coverage Density by District

```
Mtatsminda/Krtsanisi  ████████████████████  10.2 per 10K
Didube                ██████████████████    9.0
Chughureti/Central    ████████████          6.0
Saburtalo             ██                    1.1
Vake                  ▏                     0.2
Gldani/Nadzaladevi    ▏                     0.1
Isani/Samgori                               0.0
```

---

## Interactive Map

The analysis generates an interactive Folium map with toggleable layers:

| Layer | Description |
|---|---|
| 🔴 Existing Network | All 160 Tbilisi Droppers, Collects, and Spaces |
| 🟢 Recommendations | 15 numbered locations with score breakdowns |
| 🟡 Opportunity Heatmap | Scoring intensity across 1,900 grid points |
| 🔵 Metro Stations | Key foot traffic infrastructure |

> Open `output/02_analysis_map.html` in any browser to explore.

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/meama-dropper-optimizer.git
cd meama-dropper-optimizer
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the full pipeline (4 steps)
python src/01_scrape_locations.py  # Scrape 177 locations from meama.ge
python src/02_geocode.py           # Geocode addresses → lat/lon (~3 min)
python src/03_clean_and_verify.py  # Clean data + generate verification map
python src/04_analysis.py          # Scoring model + recommendations + visualizations
```

Each step is independent and saves its output to `data/` or `output/`, so you can re-run any step without starting over.

---

## Project Structure

```
meama-dropper-optimizer/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/                              # Scraped & geocoded data
│   │   ├── meama_locations_raw.csv            # 177 locations from meama.ge
│   │   └── meama_locations_geocoded.csv       # With lat/lon coordinates
│   └── processed/
│       └── meama_locations_final.csv          # Clean, district-assigned, analysis-ready
├── src/
│   ├── 01_scrape_locations.py            # Web scraper (BeautifulSoup4)
│   ├── 02_geocode.py                     # Nominatim geocoding (98% success rate)
│   ├── 03_clean_and_verify.py            # Cleaning + verification map
│   └── 04_analysis.py                    # Scoring model + charts + interactive map
└── output/
    ├── 01_verification_map.html          # Location verification map
    ├── 02_analysis_map.html              # ← Main interactive recommendation map
    ├── recommendations.csv               # Top 15 locations with score breakdowns
    └── 03_charts/
        ├── 01_coverage_density.png       # Coverage per 10K by district
        ├── 02_types_by_district.png      # Dropper/Collect/Space distribution
        ├── 03_score_distribution.png     # Histogram of 1,900 grid scores
        ├── 04_top15_breakdown.png        # Score component breakdown
        └── 05_sensitivity.png            # Weight scenario comparison
```

---

## Methodology

### Scoring Model

Each of **1,900 grid points** (38 × 50, ~300m spacing) receives a composite score from 0 to 100:

```
SCORE = 0.30 × Coverage Gap
      + 0.25 × POI Density
      + 0.20 × Population Density
      + 0.15 × Competition
      + 0.10 × Accessibility
```

| Factor | Weight | What It Measures |
|---|---|---|
| **Coverage Gap** | 30% | Distance to nearest existing MEAMA location — rewards underserved areas |
| **POI Density** | 25% | Nearby metro stations, universities, malls, hospitals within 500m |
| **Population** | 20% | District population density — more residents = more customers |
| **Competition** | 15% | Nearby coffee shops — moderate competition signals proven demand |
| **Accessibility** | 10% | Distance to nearest metro station — public transit access |

### Spatial Constraints

- **Minimum separation:** 500m between any two recommended locations (prevents clustering)
- **Haversine distance** used for all geospatial calculations
- **Score range:** 16.1 – 62.0 (mean: 37.5)

### Sensitivity Analysis

Four weight scenarios tested to validate robustness:

| Scenario | Key Change | Top District |
|---|---|---|
| Baseline | Balanced weights | Didube |
| Population-first | Population weight 2× | Didube |
| Foot-traffic-first | POI weight 2× | Didube |
| Coverage-gap-first | Coverage weight 2× | Didube |

Core recommendations remain stable across all scenarios.

---

## Data Pipeline

| Step | Script | Input | Output | Details |
|---|---|---|---|---|
| 1 | `01_scrape_locations.py` | meama.ge | 177 locations | BeautifulSoup4 web scraper |
| 2 | `02_geocode.py` | Raw addresses | Lat/lon coordinates | Nominatim API, 98% success rate |
| 3 | `03_clean_and_verify.py` | Geocoded data | 160 Tbilisi locations | District assignment, quality flags |
| 4 | `04_analysis.py` | Clean data | Maps + charts + CSV | 1,900-point grid scoring |

### Data Sources

| Source | Data | Method |
|---|---|---|
| [meama.ge/pages/locations](https://www.meama.ge/pages/locations) | 177 MEAMA locations | Web scraping |
| OpenStreetMap Nominatim | Geocoded coordinates | Free geocoding API |
| GeoStat (geostat.ge) | District population data | Manual collection |
| Google Maps / OSM | Metro stations, universities, POIs | Manual + API |

---

## Assumptions & Limitations

- **Geocoding accuracy:** 48 locations (~27%) resolved to district centroid only, not precise addresses
- **Foot traffic proxy:** POI density approximates actual pedestrian flow — real count data would improve accuracy
- **Population data:** Based on GeoStat estimates, may not reflect recent demographic shifts
- **Grid-level analysis:** Doesn't account for building-level constraints (rent, zoning, physical space)
- **Competition data:** Includes major chains and known coffee points; independent shops may be underrepresented

---

## Future Improvements

- Integrate real pedestrian foot traffic data from Tbilisi municipality APIs
- Add rental cost data as a financial feasibility factor
- Build ML demand prediction model using MEAMA's actual sales data per location
- Extend analysis to Batumi, Kutaisi, and Rustavi
- A/B test recommended placements against actual new location performance

---

## Tech Stack

| Tool | Purpose |
|---|---|
| **Python 3.10+** | Core language |
| **pandas / NumPy** | Data processing and analysis |
| **BeautifulSoup4** | Web scraping meama.ge |
| **Geopy** | Nominatim geocoding |
| **Folium** | Interactive map generation |
| **Matplotlib** | Statistical charts and visualizations |

---

## Requirements

```
requests>=2.31
beautifulsoup4>=4.12
pandas>=2.0
numpy>=1.24
folium>=0.15
matplotlib>=3.7
geopy>=2.4
tqdm>=4.65
```

---

*Built as a portfolio project for the MEAMA AI Team application, 2025.*
*Demonstrates data-driven approach to business expansion using real scraped data, geospatial analysis, and multi-factor optimization.*