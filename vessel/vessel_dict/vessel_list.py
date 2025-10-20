import requests
from bs4 import BeautifulSoup
import time
import json
import csv  # Import the csv module
import os  # Import the os module for directory operations


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


def scrape_all_vessels(flag_code):
    """
    Main function to scrape all vessels for a given flag code.
    It handles pagination by first finding the total number of pages.
    """
    base_url = f"https://www.vesselfinder.com/vessels?flag={flag_code}"
    print(f"Starting scrape for flag: {flag_code.upper()}")

    # 1. Get the first page to find the total number of pages
    soup = get_page_soup(base_url)
    if not soup:
        return []

    # 2. Find the total number of pages from the pagination bar
    try:
        pagination_controls = soup.find('div', class_='pagination-controls')
        page_text = pagination_controls.find('span').text
        # Example text: "page 1 / 26"
        total_pages = int(page_text.split(' / ')[1])
        print(f"Found {total_pages} pages to scrape.")
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

        print(f"Scraping page {page_num}/{total_pages}: {page_url}")

        # Get the page content
        current_page_soup = get_page_soup(page_url)
        if current_page_soup:
            # Parse vessels from the current page and add them to our list
            page_vessels = parse_vessels_from_soup(current_page_soup)
            all_vessels.extend(page_vessels)
            print(f"  -> Found {len(page_vessels)} vessels on this page.")

        # Be a good web citizen: wait a bit between requests
        time.sleep(2)  # 1-second delay

    print(f"\nScraping complete. Total vessels found: {len(all_vessels)}")
    return all_vessels


if __name__ == "__main__":
    # --- Configuration ---
    # Change this to any flag code you want to scrape (e.g., 'CN', 'US', 'XD')
    FLAG_TO_SCRAPE = 'XD'

    # --- Create vessel_data directory ---
    vessel_data_dir = create_vessel_data_directory()

    # --- Execution ---
    vessel_data = scrape_all_vessels(FLAG_TO_SCRAPE)

    # --- Output ---
    if vessel_data:
        # Print the first 5 results as a sample
        print("\n--- Sample of First 5 Vessels ---")
        print(json.dumps(vessel_data[:5], indent=2))

        # --- Save to JSON ---
        json_filename = os.path.join(vessel_data_dir, f"vessels_{FLAG_TO_SCRAPE.upper()}.json")
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(vessel_data, f, indent=2, ensure_ascii=False)
            print(f"\nAll data saved to {json_filename}")
        except IOError as e:
            print(f"Error writing to JSON file: {e}")

        # --- Save to CSV ---
        csv_filename = os.path.join(vessel_data_dir, f"vessels_{FLAG_TO_SCRAPE.upper()}.csv")
        # Get the headers from the keys of the first dictionary
        headers = vessel_data[0].keys()
        try:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(vessel_data)
            print(f"All data also saved to {csv_filename}")
        except IOError as e:
            print(f"Error writing to CSV file: {e}")
