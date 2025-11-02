#!/usr/bin/env python3
"""
High-Volume Countries Vessel Scraper with Type Constraints
=========================================================

This script scrapes vessel data for high-volume countries using intelligent
type filtering with smart constraints for commercial vs "other" vessel types.

Features:
- Handles all 44 high-volume countries with 4,000+ vessels each
- Applies 4,000 vessel caps for "Other" types (Fishing, Yachts, Military, etc.)
- Full scraping for commercial types (Cargo, Tankers, Passenger)
- Intelligent duplicate removal across type combinations
- Comprehensive progress tracking and coverage reporting
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import csv
import os
import sys
from datetime import datetime
import traceback
from typing import Dict, List, Tuple, Any


class HighVolumeScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.commercial_types = {}
        self.other_types = {}
        self.load_type_definitions()

    def load_type_definitions(self):
        """Load and categorize vessel types."""
        try:
            with open('country_and_type_data/type.json', 'r', encoding='utf-8') as f:
                types = json.load(f)

            # Process commercial types
            if 'Cargo' in types:
                for name, code in types['Cargo'].items():
                    self.commercial_types[name] = code

            if 'Tankers' in types:
                for name, code in types['Tankers'].items():
                    self.commercial_types[name] = code

            if 'Passenger/Cruise' in types:
                for name, code in types['Passenger/Cruise'].items():
                    self.commercial_types[name] = code

            # Process other types (subject to 4,000 cap)
            if 'Other' in types:
                for name, code in types['Other'].items():
                    self.other_types[name] = code

            print(f"Loaded {len(self.commercial_types)} commercial types and {len(self.other_types)} other types")

        except FileNotFoundError:
            print("Error: type.json not found")
            sys.exit(1)

    def get_page_soup(self, url: str):
        """Fetch and parse a web page."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {url}: {e}")
            return None

    def count_vessels_for_type(self, flag_code: str, type_code: str = None) -> Tuple[int, int, str]:
        """Count vessels for a specific country and type filter."""
        if type_code:
            url = f"https://www.vesselfinder.com/vessels?type={type_code}&flag={flag_code}"
        else:
            url = f"https://www.vesselfinder.com/vessels?flag={flag_code}"

        soup = self.get_page_soup(url)
        if not soup:
            return 0, 0, "Failed to fetch page"

        try:
            # Try to find pagination info
            pagination_controls = soup.find('div', class_='pagination-controls')
            if pagination_controls:
                page_text = pagination_controls.find('span').text
                parts = page_text.split(' / ')
                if len(parts) >= 2:
                    total_pages = int(parts[1])
                    estimated_vessels = min(total_pages * 20, 4000)  # Cap at 4,000
                    return estimated_vessels, total_pages, "Success"

            # Alternative: look for results info
            results_info = soup.find('div', class_='results-info')
            if results_info:
                text = results_info.text
                import re
                numbers = re.findall(r'\d+', text.replace(',', ''))
                if numbers:
                    return int(numbers[0]), 1, "Direct count found"

            return 0, 0, "No count found"

        except Exception as e:
            return 0, 0, f"Error parsing page: {e}"

    def parse_vessels_from_soup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract vessel data from a page."""
        vessels = []
        table = soup.find('table', class_='results')
        if not table:
            return vessels

        rows = table.find('tbody').find_all('tr')
        for row in rows:
            try:
                ship_link = row.find('a', class_='ship-link')
                if not ship_link:
                    continue

                vessel_url = ship_link['href']
                vessel_name = ship_link.find('div', class_='slna').text.strip()
                vessel_type = ship_link.find('div', class_='slty').text.strip()
                imo = vessel_url.split('/')[-1]

                vessels.append({
                    "url": vessel_url,
                    "name": vessel_name,
                    "type": vessel_type,
                    "imo": imo
                })
            except (AttributeError, KeyError) as e:
                continue

        return vessels

    def scrape_type_combination(self, flag_code: str, type_code: str, type_name: str,
                               max_vessels: int = None, max_pages: int = None) -> Dict[str, Any]:
        """Scrape vessels for a specific type combination with constraints."""
        print(f"    Scraping {type_name} for {flag_code.upper()}...")

        if type_code:
            base_url = f"https://www.vesselfinder.com/vessels?type={type_code}&flag={flag_code}"
        else:
            base_url = f"https://www.vesselfinder.com/vessels?flag={flag_code}"

        # Get first page to determine pagination
        soup = self.get_page_soup(base_url)
        if not soup:
            return {
                "success": False,
                "error": "Failed to fetch initial page",
                "vessels": []
            }

        # Determine number of pages
        try:
            pagination_controls = soup.find('div', class_='pagination-controls')
            if pagination_controls:
                page_text = pagination_controls.find('span').text
                total_pages = int(page_text.split(' / ')[1])
            else:
                total_pages = 1
        except:
            total_pages = 1

        # Apply constraints
        if max_pages:
            total_pages = min(total_pages, max_pages)
        if max_vessels:
            max_pages_allowed = (max_vessels + 19) // 20  # 20 vessels per page
            total_pages = min(total_pages, max_pages_allowed)

        print(f"      Found {total_pages} pages to scrape")

        all_vessels = []
        vessels_collected = 0

        for page_num in range(1, total_pages + 1):
            # Check vessel count constraint
            if max_vessels and vessels_collected >= max_vessels:
                print(f"      Reached vessel limit ({max_vessels}), stopping")
                break

            # Construct page URL
            if page_num == 1:
                page_url = base_url
            else:
                if type_code:
                    page_url = f"https://www.vesselfinder.com/vessels?page={page_num}&type={type_code}&flag={flag_code}"
                else:
                    page_url = f"https://www.vesselfinder.com/vessels?page={page_num}&flag={flag_code}"

            # Scrape page
            current_page_soup = self.get_page_soup(page_url)
            if current_page_soup:
                page_vessels = self.parse_vessels_from_soup(current_page_soup)

                # Apply vessel limit for this page
                if max_vessels and vessels_collected + len(page_vessels) > max_vessels:
                    page_vessels = page_vessels[:max_vessels - vessels_collected]

                all_vessels.extend(page_vessels)
                vessels_collected += len(page_vessels)
                print(f"        Page {page_num}: {len(page_vessels)} vessels (total: {vessels_collected})")

            # Rate limiting
            time.sleep(2)

        return {
            "success": True,
            "vessels": all_vessels,
            "vessel_count": len(all_vessels),
            "pages_scraped": total_pages,
            "type_code": type_code,
            "type_name": type_name
        }

    def remove_duplicates(self, vessel_lists: List[List[Dict]]) -> List[Dict]:
        """Remove duplicate vessels across multiple type combinations using IMO numbers."""
        seen_imos = set()
        unique_vessels = []
        duplicate_count = 0

        for vessel_list in vessel_lists:
            for vessel in vessel_list:
                imo = vessel.get('imo', '')
                if imo and imo not in seen_imos:
                    seen_imos.add(imo)
                    unique_vessels.append(vessel)
                elif imo:
                    duplicate_count += 1

        print(f"    Removed {duplicate_count} duplicate vessels")
        return unique_vessels

    def create_output_directory(self):
        """Create output directory for vessel data."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        vessel_data_dir = os.path.join(script_dir, 'vessel_data', 'high_volume')

        if not os.path.exists(vessel_data_dir):
            os.makedirs(vessel_data_dir)
            print(f"Created directory: {vessel_data_dir}")

        return vessel_data_dir

    def save_country_data(self, country_name: str, flag_code: str, vessels: List[Dict],
                         scraping_results: List[Dict], vessel_data_dir: str) -> Tuple[str, str]:
        """Save scraped vessel data for a country."""
        if not vessels:
            return None, None

        # Save JSON
        json_filename = os.path.join(vessel_data_dir, f"high_volume_{flag_code.upper()}_{country_name.replace(' ', '_')}.json")

        country_data = {
            "country": country_name,
            "flag_code": flag_code,
            "scraping_date": datetime.now().isoformat(),
            "total_vessels_scraped": len(vessels),
            "scraping_results": scraping_results,
            "vessels": vessels
        }

        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(country_data, f, indent=2, ensure_ascii=False)
            print(f"    JSON saved: {json_filename}")
        except IOError as e:
            print(f"    Error saving JSON: {e}")
            return None, None

        # Save CSV
        csv_filename = os.path.join(vessel_data_dir, f"high_volume_{flag_code.upper()}_{country_name.replace(' ', '_')}.csv")
        if vessels:
            headers = vessels[0].keys()
            try:
                with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(vessels)
                print(f"    CSV saved: {csv_filename}")
            except IOError as e:
                print(f"    Error saving CSV: {e}")
                return None, None

        return json_filename, csv_filename

    def scrape_country(self, country_name: str, flag_code: str) -> Dict[str, Any]:
        """Scrape all vessel data for a high-volume country using type filtering."""
        print(f"\n{'='*70}")
        print(f"SCRAPING COUNTRY: {country_name} ({flag_code.upper()})")
        print(f"{'='*70}")

        scraping_results = []
        all_vessel_lists = []

        # Test commercial types
        print("Scraping COMMERCIAL types (full coverage):")
        commercial_total = 0
        for type_name, type_code in self.commercial_types.items():
            vessels, pages, status = self.count_vessels_for_type(flag_code, type_code)
            if vessels > 0:
                result = self.scrape_type_combination(flag_code, type_code, type_name)
                if result["success"]:
                    scraping_results.append({
                        "type_name": type_name,
                        "type_code": type_code,
                        "category": "commercial",
                        "vessels_found": result["vessel_count"],
                        "pages_scraped": result["pages_scraped"],
                        "status": "success"
                    })
                    all_vessel_lists.append(result["vessels"])
                    commercial_total += result["vessel_count"]
                    print(f"      ✓ {type_name}: {result['vessel_count']:,} vessels")
                else:
                    scraping_results.append({
                        "type_name": type_name,
                        "type_code": type_code,
                        "category": "commercial",
                        "vessels_found": 0,
                        "pages_scraped": 0,
                        "status": "failed",
                        "error": result.get("error", "Unknown error")
                    })
                    print(f"      ✗ {type_name}: Failed")

            time.sleep(1)  # Rate limiting between types

        # Test other types (with 4,000 cap)
        print(f"\nScraping OTHER types (max 4,000 vessels each):")
        other_total = 0
        for type_name, type_code in self.other_types.items():
            vessels, pages, status = self.count_vessels_for_type(flag_code, type_code)
            if vessels > 0:
                # Apply 4,000 cap for other types
                result = self.scrape_type_combination(flag_code, type_code, type_name,
                                                     max_vessels=4000, max_pages=200)
                if result["success"]:
                    scraping_results.append({
                        "type_name": type_name,
                        "type_code": type_code,
                        "category": "other",
                        "actual_vessels_available": vessels,
                        "vessels_scraped": result["vessel_count"],
                        "pages_scraped": result["pages_scraped"],
                        "capped": vessels > 4000,
                        "status": "success"
                    })
                    all_vessel_lists.append(result["vessels"])
                    other_total += result["vessel_count"]
                    if vessels > 4000:
                        print(f"      ✓ {type_name}: {result['vessel_count']:,} vessels (CAPPED from {vessels:,})")
                    else:
                        print(f"      ✓ {type_name}: {result['vessel_count']:,} vessels")
                else:
                    scraping_results.append({
                        "type_name": type_name,
                        "type_code": type_code,
                        "category": "other",
                        "vessels_found": 0,
                        "pages_scraped": 0,
                        "status": "failed",
                        "error": result.get("error", "Unknown error")
                    })
                    print(f"      ✗ {type_name}: Failed")

            time.sleep(1)  # Rate limiting between types

        # Remove duplicates across all type combinations
        print(f"\nRemoving duplicates across type combinations...")
        unique_vessels = self.remove_duplicates(all_vessel_lists)

        # Calculate coverage statistics
        total_available = commercial_total + sum(r.get('actual_vessels_available', r.get('vessels_found', 0))
                                                for r in scraping_results if r.get('category') == 'other')
        coverage_percentage = (len(unique_vessels) / total_available * 100) if total_available > 0 else 0

        print(f"\nSUMMARY for {country_name}:")
        print(f"  Commercial vessels: {commercial_total:,}")
        print(f"  Other vessels (capped): {other_total:,}")
        print(f"  Total unique vessels: {len(unique_vessels):,}")
        print(f"  Coverage estimate: {coverage_percentage:.1f}%")

        return {
            "country": country_name,
            "flag_code": flag_code,
            "success": True,
            "vessels": unique_vessels,
            "vessel_count": len(unique_vessels),
            "scraping_results": scraping_results,
            "commercial_vessels": commercial_total,
            "other_vessels": other_total,
            "coverage_percentage": coverage_percentage
        }

    def load_high_volume_countries(self) -> Dict[str, str]:
        """Load the list of high-volume countries."""
        try:
            with open('_unsorted/high_volume_countries.json', 'r', encoding='utf-8') as f:
                countries = json.load(f)
            print(f"Loaded {len(countries)} high-volume countries")
            return countries
        except FileNotFoundError:
            print("Error: high_volume_countries.json not found")
            sys.exit(1)

    def create_master_summary(self, all_results: List[Dict], vessel_data_dir: str):
        """Create comprehensive summary of all scraping results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = os.path.join(vessel_data_dir, f"high_volume_scraping_summary_{timestamp}.json")

        summary_data = {
            "scraping_session": {
                "start_time": datetime.now().isoformat(),
                "total_countries": len(all_results),
                "successful_countries": len([r for r in all_results if r.get('success', False)]),
                "failed_countries": len([r for r in all_results if not r.get('success', False)]),
                "total_vessels_scraped": sum([r.get('vessel_count', 0) for r in all_results]),
                "total_commercial_vessels": sum([r.get('commercial_vessels', 0) for r in all_results]),
                "total_other_vessels": sum([r.get('other_vessels', 0) for r in all_results]),
                "average_coverage": sum([r.get('coverage_percentage', 0) for r in all_results]) / len(all_results) if all_results else 0
            },
            "country_results": all_results
        }

        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            print(f"\nMaster summary saved: {summary_file}")
            return summary_file
        except IOError as e:
            print(f"Error saving master summary: {e}")
            return None

    def main(self):
        """Main scraping execution."""
        print("=" * 80)
        print("HIGH-VOLUME COUNTRIES VESSEL SCRAPER WITH TYPE CONSTRAINTS")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Load countries and create output directory
        countries = self.load_high_volume_countries()
        vessel_data_dir = self.create_output_directory()

        print(f"\nPlanning to scrape {len(countries)} high-volume countries")
        print(f"Output directory: {vessel_data_dir}")

        all_results = []
        start_time = time.time()

        # Process each country
        for i, (country_name, flag_code) in enumerate(countries.items(), 1):
            print(f"\n{'#'*80}")
            print(f"COUNTRY {i}/{len(countries)}: {country_name} ({flag_code.upper()})")
            print(f"{'#'*80}")

            try:
                result = self.scrape_country(country_name, flag_code)

                if result["success"]:
                    # Save the data
                    json_file, csv_file = self.save_country_data(
                        country_name, flag_code, result["vessels"],
                        result["scraping_results"], vessel_data_dir
                    )

                    result["json_file"] = json_file
                    result["csv_file"] = csv_file

                    print(f"✅ SUCCESS: {country_name} - {result['vessel_count']:,} vessels")
                else:
                    print(f"❌ FAILED: {country_name}")

                all_results.append(result)

            except Exception as e:
                print(f"❌ ERROR: {country_name} - {e}")
                traceback.print_exc()
                all_results.append({
                    "country": country_name,
                    "flag_code": flag_code,
                    "success": False,
                    "error": str(e)
                })

            # Progress update
            elapsed = time.time() - start_time
            progress_percent = (i / len(countries)) * 100
            avg_time_per_country = elapsed / i
            est_remaining = avg_time_per_country * (len(countries) - i)

            successful = len([r for r in all_results if r.get('success', False)])
            total_vessels = sum([r.get('vessel_count', 0) for r in all_results])

            print(f"\n📊 PROGRESS UPDATE:")
            print(f"   Countries: {i}/{len(countries)} ({progress_percent:.1f}%)")
            print(f"   Successful: {successful} | Total vessels: {total_vessels:,}")
            print(f"   Elapsed: {elapsed/3600:.1f}h | Est. remaining: {est_remaining/3600:.1f}h")

            # Rate limiting between countries
            if i < len(countries):
                print(f"⏳ Waiting 10 seconds before next country...")
                time.sleep(10)

        # Final summary
        print(f"\n{'='*80}")
        print("HIGH-VOLUME SCRAPING COMPLETE")
        print(f"{'='*80}")

        total_time = time.time() - start_time
        successful = len([r for r in all_results if r.get('success', False)])
        total_vessels = sum([r.get('vessel_count', 0) for r in all_results])

        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total time: {total_time/3600:.2f} hours")
        print(f"Countries processed: {successful}/{len(countries)}")
        print(f"Total vessels scraped: {total_vessels:,}")

        # Create master summary
        summary_file = self.create_master_summary(all_results, vessel_data_dir)

        print(f"\n🎉 High-volume scraping completed!")
        print(f"📁 Data saved in: {vessel_data_dir}")
        if summary_file:
            print(f"📊 Master summary: {summary_file}")


if __name__ == "__main__":
    scraper = HighVolumeScraper()
    scraper.main()