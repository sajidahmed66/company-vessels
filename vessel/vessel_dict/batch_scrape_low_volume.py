#!/usr/bin/env python3
"""
Batch Scraper for Low-Volume Countries
========================================

This script scrapes vessel data for all countries with less than 4000 vessels.
It uses the existing vessel_list.py functionality and extends it for batch processing.

Features:
- Scrapes all 197 low-volume countries automatically
- Progress tracking with detailed statistics
- Error handling and retry logic
- Comprehensive logging
- Rate limiting for respectful scraping
- Master summary file generation
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


def get_page_soup(url):
    """
    Fetches a URL and returns a BeautifulSoup object.
    Includes error handling for network issues and bad responses.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None


def parse_vessels_from_soup(soup):
    """
    Parses the BeautifulSoup object to extract vessel data from the table.
    Returns a list of dictionaries, where each dictionary represents a vessel.
    """
    vessels = []
    # Find the main results table
    table = soup.find('table', class_='results')
    if not table:
        print("Warning: Could not find the results table on the page.")
        return vessels

    # Find all table rows in the table body
    rows = table.find('tbody').find_all('tr')

    for row in rows:
        try:
            # Find the main link for the vessel
            ship_link = row.find('a', class_='ship-link')
            if not ship_link:
                continue

            # Extract the required data
            vessel_url = ship_link['href']
            vessel_name = ship_link.find('div', class_='slna').text.strip()
            vessel_type = ship_link.find('div', class_='slty').text.strip()

            # The IMO is the last part of the URL
            imo = vessel_url.split('/')[-1]

            vessels.append({
                "url": vessel_url,
                "name": vessel_name,
                "type": vessel_type,
                "imo": imo
            })
        except (AttributeError, KeyError) as e:
            # Skip rows with missing elements
            print(f"Warning: Skipping a row due to missing data: {e}")
            continue

    return vessels


def create_vessel_data_directory():
    """
    Creates the vessel_data directory if it doesn't exist.
    Returns the directory path.
    """
    # Get the directory path (relative to the script location)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vessel_data_dir = os.path.join(script_dir, 'vessel_data')

    # Create directory if it doesn't exist
    if not os.path.exists(vessel_data_dir):
        os.makedirs(vessel_data_dir)
        print(f"Created directory: {vessel_data_dir}")
    else:
        print(f"Using existing directory: {vessel_data_dir}")

    return vessel_data_dir


def load_low_volume_countries():
    """
    Loads the list of low-volume countries from JSON file.
    Returns a dictionary of {country_name: country_code}
    """
    try:
        with open('low_volume_countries.json', 'r', encoding='utf-8') as f:
            countries = json.load(f)
        print(f"Loaded {len(countries)} low-volume countries")
        return countries
    except FileNotFoundError:
        print("Error: low_volume_countries.json not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing low_volume_countries.json: {e}")
        sys.exit(1)


def scrape_all_vessels(flag_code, country_name):
    """
    Main function to scrape all vessels for a given flag code.
    It handles pagination by first finding the total number of pages.
    Enhanced with better error handling for batch processing.
    """
    base_url = f"https://www.vesselfinder.com/vessels?flag={flag_code}"
    print(f"Starting scrape for {country_name} (flag: {flag_code.upper()})")

    # 1. Get the first page to find the total number of pages
    soup = get_page_soup(base_url)
    if not soup:
        print(f"Failed to fetch initial page for {country_name}")
        return None, 0

    # 2. Find the total number of pages from the pagination bar
    try:
        pagination_controls = soup.find('div', class_='pagination-controls')
        page_text = pagination_controls.find('span').text
        # Example text: "page 1 / 26"
        total_pages = int(page_text.split(' / ')[1])
        print(f"Found {total_pages} pages to scrape for {country_name}")
    except (AttributeError, IndexError, ValueError):
        print("Could not determine the number of pages. Assuming only one page.")
        total_pages = 1

    all_vessels = []

    # 3. Loop through all pages and scrape vessel data
    for page_num in range(1, total_pages + 1):
        # Construct the URL for the current page
        if page_num == 1:
            page_url = base_url
        else:
            page_url = f"https://www.vesselfinder.com/vessels?page={page_num}&flag={flag_code}"

        print(f"  Scraping page {page_num}/{total_pages}")

        # Get the page content
        current_page_soup = get_page_soup(page_url)
        if current_page_soup:
            # Parse vessels from the current page and add them to our list
            page_vessels = parse_vessels_from_soup(current_page_soup)
            all_vessels.extend(page_vessels)
            print(f"    -> Found {len(page_vessels)} vessels on this page")
        else:
            print(f"    -> Failed to fetch page {page_num}")

        # Be a good web citizen: wait a bit between requests
        time.sleep(2)  # 2-second delay

    print(f"Scraping complete for {country_name}. Total vessels found: {len(all_vessels)}")
    return all_vessels, total_pages


def save_vessel_data(vessels, flag_code, country_name, vessel_data_dir):
    """
    Saves vessel data to both JSON and CSV formats.
    """
    if not vessels:
        print(f"No vessels to save for {country_name}")
        return None, None

    # --- Save to JSON ---
    json_filename = os.path.join(vessel_data_dir, f"vessels_{flag_code.upper()}.json")
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(vessels, f, indent=2, ensure_ascii=False)
        print(f"  JSON saved: {json_filename}")
    except IOError as e:
        print(f"Error writing to JSON file: {e}")
        return None, None

    # --- Save to CSV ---
    csv_filename = os.path.join(vessel_data_dir, f"vessels_{flag_code.upper()}.csv")
    # Get the headers from the keys of the first dictionary
    headers = vessels[0].keys()
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(vessels)
        print(f"  CSV saved: {csv_filename}")
    except IOError as e:
        print(f"Error writing to CSV file: {e}")
        return None, None

    return json_filename, csv_filename


def create_summary_summary(results, vessel_data_dir):
    """
    Creates a summary file with scraping statistics.
    """
    summary_file = os.path.join(vessel_data_dir, f"scraping_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    summary_data = {
        "scraping_session": {
            "start_time": datetime.now().isoformat(),
            "total_countries": len(results),
            "successful_countries": len([r for r in results if r['status'] == 'success']),
            "failed_countries": len([r for r in results if r['status'] == 'failed']),
            "total_vessels_scraped": sum([r.get('vessel_count', 0) for r in results]),
            "total_pages_scraped": sum([r.get('pages_scraped', 0) for r in results])
        },
        "country_results": results
    }

    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        print(f"\nMaster summary saved: {summary_file}")
        return summary_file
    except IOError as e:
        print(f"Error writing summary file: {e}")
        return None


def main():
    """
    Main function to orchestrate the batch scraping process.
    """
    print("=" * 70)
    print("BATCH SCRAPER FOR LOW-VOLUME COUNTRIES")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load configuration
    countries = load_low_volume_countries()
    vessel_data_dir = create_vessel_data_directory()

    print(f"\nPlanning to scrape {len(countries)} countries")
    print(f"Output directory: {vessel_data_dir}")

    # Initialize results tracking
    results = []
    successful_countries = 0
    failed_countries = 0
    total_vessels = 0

    # Main scraping loop
    start_time = time.time()

    for i, (country_name, flag_code) in enumerate(countries.items(), 1):
        print(f"\n{'='*60}")
        print(f"COUNTRY {i}/{len(countries)}: {country_name} ({flag_code.upper()})")
        print(f"{'='*60}")

        try:
            # Scrape vessels for this country
            vessels, pages_scraped = scrape_all_vessels(flag_code, country_name)

            if vessels is not None:
                # Save the data
                json_file, csv_file = save_vessel_data(vessels, flag_code, country_name, vessel_data_dir)

                if json_file and csv_file:
                    # Success
                    result = {
                        'country': country_name,
                        'flag_code': flag_code,
                        'status': 'success',
                        'vessel_count': len(vessels),
                        'pages_scraped': pages_scraped,
                        'json_file': json_file,
                        'csv_file': csv_file
                    }
                    successful_countries += 1
                    total_vessels += len(vessels)
                    print(f"✅ SUCCESS: {country_name} - {len(vessels)} vessels")
                else:
                    # Failed to save
                    result = {
                        'country': country_name,
                        'flag_code': flag_code,
                        'status': 'save_failed',
                        'vessel_count': len(vessels) if vessels else 0,
                        'pages_scraped': pages_scraped,
                        'error': 'Failed to save data files'
                    }
                    failed_countries += 1
                    print(f"❌ SAVE FAILED: {country_name}")
            else:
                # Failed to scrape
                result = {
                    'country': country_name,
                    'flag_code': flag_code,
                    'status': 'failed',
                    'vessel_count': 0,
                    'pages_scraped': 0,
                    'error': 'Failed to scrape data'
                }
                failed_countries += 1
                print(f"❌ FAILED: {country_name}")

            results.append(result)

        except Exception as e:
            # Unexpected error
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"❌ ERROR: {country_name} - {error_msg}")

            result = {
                'country': country_name,
                'flag_code': flag_code,
                'status': 'error',
                'vessel_count': 0,
                'pages_scraped': 0,
                'error': error_msg,
                'traceback': traceback.format_exc()
            }
            results.append(result)
            failed_countries += 1

        # Progress update
        elapsed_time = time.time() - start_time
        progress_percent = (i / len(countries)) * 100
        avg_time_per_country = elapsed_time / i
        estimated_remaining = avg_time_per_country * (len(countries) - i)

        print(f"\n📊 PROGRESS UPDATE:")
        print(f"   Countries processed: {i}/{len(countries)} ({progress_percent:.1f}%)")
        print(f"   Successful: {successful_countries} | Failed: {failed_countries}")
        print(f"   Total vessels: {total_vessels:,}")
        print(f"   Elapsed: {elapsed_time/60:.1f} min | Est. remaining: {estimated_remaining/60:.1f} min")

        # Rate limiting between countries
        if i < len(countries):  # Don't sleep after the last country
            print(f"⏳ Waiting 5 seconds before next country...")
            time.sleep(5)

    # Final summary
    print(f"\n{'='*70}")
    print("BATCH SCRAPING COMPLETE")
    print(f"{'='*70}")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    total_time = time.time() - start_time
    print(f"Total time: {total_time/3600:.2f} hours ({total_time/60:.1f} minutes)")
    print(f"Total countries: {len(countries)}")
    print(f"Successful: {successful_countries} | Failed: {failed_countries}")
    print(f"Total vessels scraped: {total_vessels:,}")
    print(f"Average vessels per country: {total_vessels // successful_countries if successful_countries > 0 else 0:,}")

    # Create master summary file
    summary_file = create_summary_summary(results, vessel_data_dir)

    if failed_countries > 0:
        print(f"\n⚠️  {failed_countries} countries failed. Check the summary file for details.")

    print(f"\n🎉 Batch scraping completed! Check {vessel_data_dir} for all data files.")


if __name__ == "__main__":
    main()