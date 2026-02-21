# MEAMA Dropper Network Optimizer

> Data-driven location intelligence for optimal MEAMA Dropper placement across Tbilisi.

A multi-factor scoring model that analyzes population density, foot traffic, competitive landscape, and existing network coverage to recommend where MEAMA should place its next vending machines.

---

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/YOUR_USERNAME/meama-dropper-optimizer.git
cd meama-dropper-optimizer
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Run the pipeline step by step
python src/01_scrape_locations.py    # Scrape locations from meama.ge
python src/02_geocode.py             # Convert addresses to coordinates (~2-3 min)
python src/03_clean_and_verify.py    # Clean data + generate verification map
python src/04_analysis.py            # Run scoring model + generate recommendations
```

## Project Structure

```
meama-dropper-optimizer/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                    # Scraped and geocoded data
│   └── processed/              # Clean, analysis-ready data
├── src/
│   ├── 01_scrape_locations.py  # Step 1: Scrape meama.ge
│   ├── 02_geocode.py           # Step 2: Address → lat/lon
│   ├── 03_clean_and_verify.py  # Step 3: Clean + verification map
│   └── 04_analysis.py          # Step 4: Scoring model + recommendations
├── notebooks/                  # Jupyter notebooks for exploration
└── output/
    ├── 01_verification_map.html
    └── (more outputs from step 4)
```

## Methodology

[To be completed after analysis]

## Data Sources

- **MEAMA Locations**: Scraped from [meama.ge/pages/locations](https://www.meama.ge/pages/locations)
- **Geocoding**: OpenStreetMap Nominatim (free)
- **District Demographics**: GeoStat (geostat.ge)
- **Competitors**: Google Maps

## Author

Built as a portfolio project for the MEAMA AI Team application, 2025.
