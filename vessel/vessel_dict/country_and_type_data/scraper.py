import json
import requests
from bs4 import BeautifulSoup
import time
import os

# --- Configuration ---
INPUT_FILE = 'country.json'
OUTPUT_FILE = '../_unsorted/country_wise_count.json'
BASE_URL = 'https://www.vesselfinder.com/vessels?flag='
# A delay between requests to be polite to the server
REQUEST_DELAY = 1  # seconds


def scrape_ship_counts():
    """
    Reads country data, scrapes ship counts from Vesselfinder,
    and saves the results to a JSON file.
    """
    # Check if the input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: The file '{INPUT_FILE}' was not found.")
        print("Please make sure it's in the same directory as the script.")
        return

    # Load country data from the JSON file
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            countries = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{INPUT_FILE}'. Please check its format.")
        return

    results = {}
    total_countries = len(countries)

    print(f"Found {total_countries} entries. Starting scrape...")

    # Iterate over each country and its code
    for i, (country_name, country_code) in enumerate(countries.items()):
        # Skip the "Any flag" option as it doesn't have a specific page
        if country_code == '-':
            print(f"({i + 1}/{total_countries}) Skipping '{country_name}'")
            continue

        # Construct the full URL. The code needs to be uppercase.
        url = f"{BASE_URL}{country_code.upper()}"

        print(f"({i + 1}/{total_countries}) Fetching data for {country_name} from {url}...")

        try:
            # Add a User-Agent header to mimic a browser and avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)

            # Check if the request was successful
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find the div with the specific class
                count_element = soup.find('div', class_='pagination-totals')

                if count_element:
                    # Extract the text, e.g., "8,941 ships"
                    count_text = count_element.text
                    # Split the text and take the first part (the number)
                    number_str = count_text.split(' ')[0]
                    # Remove commas and convert to integer
                    count = int(number_str.replace(',', ''))

                    results[country_name] = count
                    print(f"  -> Success: Found {count} ships.")
                else:
                    # This can happen if a country has no ships or the page structure changed
                    print(f"  -> Warning: Could not find ship count element for {country_name}. Setting count to 0.")
                    results[country_name] = 0
            else:
                print(f"  -> Error: Failed to retrieve page for {country_name}. Status code: {response.status_code}")
                results[country_name] = 0  # Set to 0 on failure

        except requests.exceptions.RequestException as e:
            print(f"  -> Error: An exception occurred for {country_name}: {e}")
            results[country_name] = 0  # Set to 0 on exception

        # Wait for a bit before the next request
        time.sleep(REQUEST_DELAY)

    # Save the results to the output file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nScraping complete. Results saved to '{OUTPUT_FILE}'")
    except IOError as e:
        print(f"\nError: Could not write to output file '{OUTPUT_FILE}': {e}")


if __name__ == "__main__":
    scrape_ship_counts()