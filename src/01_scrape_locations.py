"""
Step 1 (FIXED): Scrape MEAMA locations from meama.ge/pages/locations
=====================================================================
Run: python3 src/01_scrape_locations.py

Output: data/raw/meama_locations_raw.csv
"""

import requests
from bs4 import BeautifulSoup
import csv
import re
import os

def classify_type(h2_text, h3_text):
    """Determine location type from h2 name and h3 content."""
    h2 = h2_text.lower()
    h3 = h3_text.lower()
    
    if 'სივრცე' in h2 or 'space' in h2:
        return 'Space'
    elif 'ქოლექთ' in h2 or 'collect' in h2:
        return 'Collect'
    elif 'დროფერი' in h3 or 'dispenser' in h2 or 'dispnser' in h2:
        return 'Dropper'
    else:
        return 'Dropper'  # Default for location-items that don't match

def extract_city_from_name(h2_text):
    """Extract city from h2 text like 'მეამა ქოლექთი • თბილისი'."""
    cities = {
        'თბილისი': 'Tbilisi',
        'ბათუმი': 'Batumi',
        'რუსთავი': 'Rustavi',
        'ქუთაისი': 'Kutaisi',
        'გორი': 'Gori',
        'თელავი': 'Telavi',
        'ფოთი': 'Poti',
        'მცხეთა': 'Mtskheta',
        'ნატახტარი': 'Natakhtari',
        'კლდიაშვილი': 'Tbilisi',
        'ჩიტაია': 'Tbilisi',
        'მარჯანიშვილი': 'Tbilisi',
        'მელიქიშვილი': 'Tbilisi',
        'ვაზისუბანი': 'Tbilisi',
        'ჭოველიძე': 'Tbilisi',
        'ყაზბეგი': 'Tbilisi',
        'ნაფარეული': 'Tbilisi',
        'ლილო': 'Tbilisi',
        'თავისუფალი უნივერსიტეტი': 'Tbilisi',
    }
    for geo_name, eng_name in cities.items():
        if geo_name in h2_text:
            return eng_name
    return 'Tbilisi'  # Default

def extract_city_from_address(address):
    """Extract city from address text."""
    if 'რუსთავ' in address:
        return 'Rustavi'
    if 'ქუთაის' in address:
        return 'Kutaisi'
    if 'ბათუმ' in address:
        return 'Batumi'
    if 'გორი' in address:
        return 'Gori'
    if 'თელავ' in address:
        return 'Telavi'
    if 'ფოთ' in address:
        return 'Poti'
    if 'მცხეთ' in address:
        return 'Mtskheta'
    if 'ნატახტარ' in address:
        return 'Natakhtari'
    return None

def clean_address(address):
    """Clean up address string."""
    address = re.sub(r'^ქ\.?\s*თბილისი\s*,?\s*', '', address)
    address = re.sub(r'^თბილისი\s*,?\s*', '', address)
    address = address.strip().strip(',').strip()
    return address

def clean_name(name):
    """Clean up location name."""
    # Remove "dispenser" / "dispnser" tags
    name = re.sub(r'\s*["""]?\s*(?:dispenser|dispnser)\s*["""]?\s*', '', name, flags=re.IGNORECASE)
    name = name.strip().strip('"').strip('"').strip('"').strip()
    return name

def scrape_meama_locations():
    """Scrape all locations from MEAMA website."""
    
    print("🔍 Fetching meama.ge/pages/locations ...")
    
    url = "https://www.meama.ge/pages/locations"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Use saved HTML if available, otherwise fetch
    html_path = 'data/raw/locations_page.html'
    if os.path.exists(html_path):
        print(f"📄 Using cached HTML from {html_path}")
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
    else:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
        os.makedirs('data/raw', exist_ok=True)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"💾 Raw HTML saved to {html_path}")
    
    print(f"✅ HTML loaded ({len(html)} bytes)")
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # =========================================================
    # KEY INSIGHT: All location cards have class "location-item"
    # Inside each: h2 (name), text (address), h3 (hours/type)
    # =========================================================
    
    location_items = soup.find_all('div', class_='location-item')
    print(f"📋 Found {len(location_items)} location-item divs")
    
    locations = []
    
    for item in location_items:
        # Extract h2 (name)
        h2 = item.find('h2')
        if not h2:
            continue
        name_raw = h2.get_text(strip=True)
        if not name_raw or len(name_raw) < 2:
            continue
        
        # Extract h3 (hours or type indicator)
        h3 = item.find('h3')
        h3_text = h3.get_text(strip=True) if h3 else ''
        
        # Classify type
        loc_type = classify_type(name_raw, h3_text)
        
        # Extract address: text content between h2 and h3
        # Look for all text nodes in the parent div that aren't h2 or h3
        address = ''
        parent_div = h2.parent  # div.cursor-pointer
        if parent_div:
            # Get all text that isn't the h2 or h3
            for child in parent_div.children:
                if child == h2 or child == h3:
                    continue
                text = ''
                if hasattr(child, 'get_text'):
                    text = child.get_text(strip=True)
                else:
                    text = str(child).strip()
                
                # Filter: address should have Georgian chars or street-like content
                if text and len(text) > 3 and text != name_raw and text != h3_text:
                    # Skip if it's just a type label or hours duplicate
                    if text not in ['დროფერი', 'ქოლექთი', 'სივრცე']:
                        address = text
                        break
        
        # If still no address, try looking deeper in nested divs
        if not address:
            for div in item.find_all('div'):
                texts = div.find_all(string=True, recursive=False)
                for t in texts:
                    t = t.strip()
                    if t and len(t) > 3 and t != name_raw and t != h3_text:
                        if t not in ['დროფერი', 'ქოლექთი', 'სივრცე']:
                            address = t
                            break
                if address:
                    break
        
        # Determine city
        city = extract_city_from_name(name_raw)
        addr_city = extract_city_from_address(address)
        if addr_city:
            city = addr_city
        
        # Clean up
        name_clean = clean_name(name_raw)
        address_clean = clean_address(address)
        
        # Determine hours
        if loc_type == 'Dropper':
            hours = 'N/A'  # Droppers don't list hours, h3 just says "დროფერი"
        else:
            hours = h3_text
        
        # Build geocoding address
        if address_clean:
            geocode_addr = address_clean + ', ' + city + ', Georgia'
        else:
            geocode_addr = city + ', Georgia'
        
        locations.append({
            'name': name_clean,
            'name_raw': name_raw,
            'address_raw': address,
            'address_clean': address_clean,
            'address_for_geocoding': geocode_addr,
            'type': loc_type,
            'city': city,
            'hours': hours,
        })
    
    # =========================================================
    # DEDUPLICATE by name + address
    # =========================================================
    seen = set()
    unique_locations = []
    for loc in locations:
        key = (loc['name'], loc['address_raw'])
        if key not in seen:
            seen.add(key)
            unique_locations.append(loc)
    
    # =========================================================
    # PRINT RESULTS
    # =========================================================
    print(f"\n{'='*60}")
    print(f"📊 EXTRACTION RESULTS:")
    print(f"   Total extracted:  {len(unique_locations)}")
    
    type_counts = {}
    city_counts = {}
    for loc in unique_locations:
        type_counts[loc['type']] = type_counts.get(loc['type'], 0) + 1
        city_counts[loc['city']] = city_counts.get(loc['city'], 0) + 1
    
    print(f"\n   By type:")
    for t, c in sorted(type_counts.items()):
        print(f"     {t:10s} → {c}")
    
    print(f"\n   By city:")
    for t, c in sorted(city_counts.items(), key=lambda x: -x[1]):
        print(f"     {t:12s} → {c}")
    
    # Show sample of each type
    for loc_type in ['Space', 'Collect', 'Dropper']:
        samples = [l for l in unique_locations if l['type'] == loc_type][:3]
        if samples:
            print(f"\n   Sample {loc_type}s:")
            for s in samples:
                name = s['name'][:40]
                addr = s['address_clean'][:50]
                print(f'     📍 {name:40s} │ {addr}')
    
    # Show locations with missing addresses
    no_addr = [l for l in unique_locations if not l['address_clean']]
    if no_addr:
        print(f"\n   ⚠️  {len(no_addr)} locations have no address:")
        for l in no_addr[:5]:
            print(f"     - {l['name']}")
    
    # =========================================================
    # SAVE TO CSV
    # =========================================================
    output_path = 'data/raw/meama_locations_raw.csv'
    fieldnames = ['name', 'name_raw', 'address_raw', 'address_clean', 
                  'address_for_geocoding', 'type', 'city', 'hours']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_locations)
    
    print(f"\n✅ Saved to {output_path}")
    print(f"\n🔜 Next step: Run python3 src/02_geocode.py")
    
    return unique_locations

if __name__ == '__main__':
    locations = scrape_meama_locations()
