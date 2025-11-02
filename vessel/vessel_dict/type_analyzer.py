#!/usr/bin/env python3
"""
Vessel Type Analyzer for High-Volume Countries
===============================================

This script analyzes vessel distribution by type for high-volume countries
to determine optimal scraping strategies with smart constraints.

Features:
- Tests vessel counts for each type filter per country
- Applies 4,000 vessel caps for "Other" types
- Generates optimal scraping plans per country
- Provides detailed coverage estimates
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
import sys
from datetime import datetime
import traceback


def get_page_soup(url):
    """
    Fetches a URL and returns a BeautifulSoup object.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None


def count_vessels_for_type(flag_code, type_code=None):
    """
    Counts vessels for a specific country and type filter.
    Returns vessel count and number of pages.
    """
    if type_code:
        url = f"https://www.vesselfinder.com/vessels?type={type_code}&flag={flag_code}"
        type_name = get_type_name(type_code)
        print(f"  Testing {type_name} for {flag_code.upper()}...")
    else:
        url = f"https://www.vesselfinder.com/vessels?flag={flag_code}"
        print(f"  Testing all vessels for {flag_code.upper()}...")

    soup = get_page_soup(url)
    if not soup:
        return 0, 0, "Failed to fetch page"

    try:
        # Try to find pagination info
        pagination_controls = soup.find('div', class_='pagination-controls')
        if pagination_controls:
            page_text = pagination_controls.find('span').text
            # Example: "page 1 / 26"
            parts = page_text.split(' / ')
            if len(parts) >= 2:
                total_pages = int(parts[1])
                # Estimate vessels: pages × 20 vessels per page (average)
                estimated_vessels = min(total_pages * 20, 4000)  # Cap at 4,000 for estimation
                return estimated_vessels, total_pages, "Success"

        # If no pagination, look for results count
        results_info = soup.find('div', class_='results-info')
        if results_info:
            text = results_info.text
            # Look for numbers in the text
            import re
            numbers = re.findall(r'\d+', text.replace(',', ''))
            if numbers:
                return int(numbers[0]), 1, "Direct count found"

        # If no count found, return 0
        return 0, 0, "No count found"

    except Exception as e:
        return 0, 0, f"Error parsing page: {e}"


def load_high_volume_countries():
    """Load the list of high-volume countries."""
    try:
        with open('_unsorted/high_volume_countries.json', 'r', encoding='utf-8') as f:
            countries = json.load(f)
        print(f"Loaded {len(countries)} high-volume countries")
        return countries
    except FileNotFoundError:
        print("Error: high_volume_countries.json not found in _unsorted directory")
        sys.exit(1)


def load_type_definitions():
    """Load vessel type definitions and categorize them."""
    try:
        with open('country_and_type_data/type.json', 'r', encoding='utf-8') as f:
            types = json.load(f)

        # Categorize types
        commercial_types = {}
        other_types = {}

        # Process Cargo types
        if 'Cargo' in types:
            for name, code in types['Cargo'].items():
                commercial_types[name] = code

        # Process Tanker types
        if 'Tankers' in types:
            for name, code in types['Tankers'].items():
                commercial_types[name] = code

        # Process Passenger types
        if 'Passenger/Cruise' in types:
            for name, code in types['Passenger/Cruise'].items():
                commercial_types[name] = code

        # Process Other types
        if 'Other' in types:
            for name, code in types['Other'].items():
                other_types[name] = code

        print(f"Loaded {len(commercial_types)} commercial types and {len(other_types)} other types")
        return commercial_types, other_types, types

    except FileNotFoundError:
        print("Error: type.json not found")
        sys.exit(1)


def get_type_name(type_code):
    """Get type name from type code."""
    # This is a simplified mapping - could be enhanced
    type_mapping = {
        "4": "All Cargo Vessels", "401": "Bulk carrier", "402": "General Cargo",
        "403": "Container Ship", "404": "Reefer", "405": "Ro-Ro",
        "406": "Vehicles Carrier", "6": "All Tankers", "601": "Crude Oil Tanker",
        "602": "Oil Products Tanker", "603": "Chemical/Oil Tanker", "604": "LNG Tanker",
        "605": "LPG Tanker", "3": "All Passenger/Cruise Ships", "301": "Cruise Ship",
        "302": "Passenger/Cargo Ship", "303": "Passenger/Ro-Ro Ship", "304": "Passenger Ship",
        "5": "Fishing ships", "8": "Yachts/Sailing Vessels", "7": "Military",
        "2": "Tugs", "0": "Other type/ Auxiliary", "1": "Unknown"
    }
    return type_mapping.get(type_code, f"Type {type_code}")


def is_other_type(type_code):
    """Check if a type is in the 'Other' category (subject to 4,000 cap)."""
    other_type_codes = {"0", "1", "2", "5", "7", "8"}
    return type_code in other_type_codes


def analyze_country_types(country_name, flag_code, commercial_types, other_types):
    """
    Analyze vessel distribution for a single country.
    """
    print(f"\n{'='*60}")
    print(f"ANALYZING: {country_name} ({flag_code.upper()})")
    print(f"{'='*60}")

    analysis = {
        "country": country_name,
        "flag_code": flag_code,
        "analysis_date": datetime.now().isoformat(),
        "total_vessels_estimated": 0,
        "commercial_types": {},
        "other_types": {},
        "scraping_plan": []
    }

    # Test commercial types
    print("Testing COMMERCIAL types (full scraping):")
    commercial_total = 0
    for type_name, type_code in commercial_types.items():
        vessels, pages, status = count_vessels_for_type(flag_code, type_code)
        if vessels > 0:
            analysis["commercial_types"][type_name] = {
                "code": type_code,
                "vessels_found": vessels,
                "pages_required": pages,
                "status": status,
                "scraping_strategy": "full" if vessels <= 4000 else "split_needed"
            }
            commercial_total += vessels
            print(f"    {type_name}: {vessels:,} vessels ({pages} pages)")
        time.sleep(1)  # Rate limiting

    # Test other types (with 4,000 cap)
    print("\nTesting OTHER types (max 4,000 vessels each):")
    other_total = 0
    for type_name, type_code in other_types.items():
        vessels, pages, status = count_vessels_for_type(flag_code, type_code)
        if vessels > 0:
            # Apply 4,000 cap for other types
            capped_vessels = min(vessels, 4000)
            analysis["other_types"][type_name] = {
                "code": type_code,
                "actual_vessels": vessels,
                "scrape_vessels": capped_vessels,
                "pages_required": min(pages, 200),  # Cap at 200 pages
                "status": status,
                "scraping_strategy": "capped_4000" if vessels > 4000 else "full"
            }
            other_total += capped_vessels
            if vessels > 4000:
                print(f"    {type_name}: {vessels:,} total → scraping {capped_vessels:,} (CAPPED)")
            else:
                print(f"    {type_name}: {capped_vessels:,} vessels (full)")
        time.sleep(1)  # Rate limiting

    analysis["total_vessels_estimated"] = commercial_total + other_total
    analysis["vessels_to_scrape"] = commercial_total + other_total
    analysis["coverage_estimate"] = f"{((commercial_total + other_total) / (commercial_total + sum(t.get('actual_vessels', 0) for t in analysis['other_types'].values())) * 100):.1f}%" if analysis['other_types'] else "100%"

    print(f"\nSUMMARY for {country_name}:")
    print(f"  Commercial vessels: {commercial_total:,}")
    print(f"  Other vessels (capped): {other_total:,}")
    print(f"  Total to scrape: {analysis['vessels_to_scrape']:,}")
    print(f"  Coverage estimate: {analysis['coverage_estimate']}")

    return analysis


def generate_scraping_plan(analysis):
    """Generate optimal scraping plan based on analysis."""
    plan = []

    # Add commercial types
    for type_name, type_data in analysis["commercial_types"].items():
        if type_data["vessels_found"] > 0:
            if type_data["scraping_strategy"] == "split_needed":
                # This type needs to be split further - recommend sub-types
                plan.append({
                    "type_name": type_name,
                    "type_code": type_data["code"],
                    "strategy": "split_into_subtypes",
                    "vessels_estimated": type_data["vessels_found"],
                    "priority": "high"
                })
            else:
                plan.append({
                    "type_name": type_name,
                    "type_code": type_data["code"],
                    "strategy": "scrape_full",
                    "vessels_estimated": type_data["vessels_found"],
                    "pages_required": type_data["pages_required"],
                    "priority": "high"
                })

    # Add other types (capped)
    for type_name, type_data in analysis["other_types"].items():
        if type_data["scrape_vessels"] > 0:
            plan.append({
                "type_name": type_name,
                "type_code": type_data["code"],
                "strategy": "scrape_capped",
                "vessels_estimated": type_data["scrape_vessels"],
                "pages_required": type_data["pages_required"],
                "priority": "medium"
            })

    # Sort by priority and vessel count (largest first)
    plan.sort(key=lambda x: (x["priority"] != "high", -x["vessels_estimated"]))

    return plan


def save_analysis_results(all_analyses):
    """Save comprehensive analysis results."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save detailed analysis
    detailed_file = f"type_analysis_detailed_{timestamp}.json"
    try:
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(all_analyses, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed analysis saved: {detailed_file}")
    except IOError as e:
        print(f"Error saving detailed analysis: {e}")

    # Save summary for quick reference
    summary_data = []
    for analysis in all_analyses:
        summary_data.append({
            "country": analysis["country"],
            "flag_code": analysis["flag_code"],
            "vessels_to_scrape": analysis["vessels_to_scrape"],
            "coverage_estimate": analysis["coverage_estimate"],
            "commercial_types_count": len(analysis["commercial_types"]),
            "other_types_count": len(analysis["other_types"]),
            "scraping_plan_items": len(analysis.get("scraping_plan", []))
        })

    summary_file = f"type_analysis_summary_{timestamp}.json"
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        print(f"Analysis summary saved: {summary_file}")
    except IOError as e:
        print(f"Error saving summary: {e}")

    return detailed_file, summary_file


def main():
    """Main function to analyze vessel types for high-volume countries."""
    print("=" * 70)
    print("VESSEL TYPE ANALYZER FOR HIGH-VOLUME COUNTRIES")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load data
    countries = load_high_volume_countries()
    commercial_types, other_types, all_types = load_type_definitions()

    print(f"\nPlanning to analyze {len(countries)} high-volume countries")
    print(f"Commercial types: {len(commercial_types)} | Other types: {len(other_types)}")

    all_analyses = []
    start_time = time.time()

    # Analyze each country
    for i, (country_name, flag_code) in enumerate(countries.items(), 1):
        print(f"\n{'#'*70}")
        print(f"COUNTRY {i}/{len(countries)}: {country_name}")
        print(f"{'#'*70}")

        try:
            analysis = analyze_country_types(country_name, flag_code, commercial_types, other_types)
            analysis["scraping_plan"] = generate_scraping_plan(analysis)
            all_analyses.append(analysis)

            # Progress update
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            est_remaining = avg_time * (len(countries) - i)
            print(f"\nPROGRESS: {i}/{len(countries)} completed")
            print(f"Elapsed: {elapsed/60:.1f} min | Est. remaining: {est_remaining/60:.1f} min")

        except Exception as e:
            print(f"ERROR analyzing {country_name}: {e}")
            traceback.print_exc()
            continue

        # Rate limiting between countries
        if i < len(countries):
            print("Waiting 3 seconds before next country...")
            time.sleep(3)

    # Save results
    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")

    detailed_file, summary_file = save_analysis_results(all_analyses)

    total_time = time.time() - start_time
    print(f"Total analysis time: {total_time/60:.1f} minutes")
    print(f"Countries analyzed: {len(all_analyses)}/{len(countries)}")

    # Calculate totals
    total_vessels_to_scrape = sum(a["vessels_to_scrape"] for a in all_analyses)
    print(f"Total vessels to scrape: {total_vessels_to_scrape:,}")

    print(f"\nFiles created:")
    print(f"  - Detailed analysis: {detailed_file}")
    print(f"  - Summary: {summary_file}")
    print(f"\n✅ Type analysis complete! Ready for high-volume country scraping.")


if __name__ == "__main__":
    main()