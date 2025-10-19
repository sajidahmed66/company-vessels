import requests
from bs4 import BeautifulSoup
import csv
import time
import re


def scrape_vesselfinder_ports():
    BASE_URL = "https://www.vesselfinder.com"
    INITIAL_URL = f"{BASE_URL}/ports"
    OUTPUT_FILE = "vesselfinder_ports.csv"

    all_ports_data = []

    try:
        print("Making initial request to determine total pages...")
        response = requests.get(INITIAL_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()  # Raise an exception for bad status codes

        soup = BeautifulSoup(response.text, 'html.parser')

        pagination_text = soup.find('nav', class_='pagination').find('span').text
        match = re.search(r'/ (\d+)', pagination_text)
        if not match:
            print("Could not determine the total number of pages. Exiting.")
            return

        total_pages = int(match.group(1))
        print(f"Found a total of {total_pages} pages to scrape.")

        for page_num in range(1, total_pages + 1):
            current_url = f"{INITIAL_URL}?page={page_num}"
            print(f"Scraping page {page_num} of {total_pages}... ({current_url})")

            time.sleep(1)

            page_response = requests.get(current_url, headers={'User-Agent': 'Mozilla/5.0'})
            page_response.raise_for_status()

            page_soup = BeautifulSoup(page_response.text, 'html.parser')

            results_table = page_soup.find('table', class_='results')
            if not results_table:
                print(f"Could not find results table on page {page_num}. Skipping.")
                continue

            for row in results_table.find('tbody').find_all('tr'):
                try:
                    details_div = row.find('td', class_='v1').find('div', class_='details')
                    port_name = details_div.find('div', class_='row-title').get_text(strip=True)
                    country = details_div.find('div', class_='row-country').get_text(strip=True)
                    locode = row.find('td', class_='v2').get_text(strip=True)
                    port_relative_url = details_div.find('a')['href']
                    port_full_url = f"{BASE_URL}{port_relative_url}"

                    port_data = {
                        'Port Name': port_name,
                        'Country': country,
                        'LOCODE': locode,
                        'URL': port_full_url
                    }
                    all_ports_data.append(port_data)

                except (AttributeError, TypeError) as e:
                    print(f"Skipping a row due to missing data or error: {e}")
                    continue

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    if not all_ports_data:
        print("No data was scraped. Exiting.")
        return

    print(f"\nScraping complete. Total ports found: {len(all_ports_data)}")
    print(f"Saving data to {OUTPUT_FILE}...")

    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            # Define the headers for the CSV file
            fieldnames = ['Port Name', 'Country', 'LOCODE', 'URL']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write the header
            writer.writeheader()

            # Write all the port data
            writer.writerows(all_ports_data)

        print(f"Data successfully saved to {OUTPUT_FILE}")

    except IOError as e:
        print(f"Could not write to file {OUTPUT_FILE}: {e}")


# Run the scraper
if __name__ == "__main__":
    scrape_vesselfinder_ports()