import asyncio
import re  # <-- 1. Import the 're' module
from playwright.async_api import async_playwright, expect
from bs4 import BeautifulSoup
from pprint import pprint


async def scrape_vessel_navigation_data_with_playwright(url):

    vessel_data = {}

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)

            reported_destination_locator = page.locator("th:has-text('Reported Destination') + td")

            print("Waiting for the 'Reported Destination' data to load...")
            await expect(reported_destination_locator).to_have_text(re.compile(r".+"))  # <-- 2. Use re.compile()
            print("Data loaded. Proceeding with scraping.")

            page_source = await page.content()
            soup = BeautifulSoup(page_source, 'html.parser')

            navigation_title = soup.find('span', class_='box__title-label', string='Navigation Data')
            if not navigation_title:
                print("Could not find the 'Navigation Data' section.")
                return None

            navigation_table = navigation_title.find_parent('table')
            if not navigation_table:
                print("Found the 'Navigation Data' title, but could not find the associated table.")
                return None

            for row in navigation_table.find('tbody').find_all('tr'):
                key_element = row.find('th')
                value_element = row.find('td')

                if key_element and value_element:
                    key = key_element.get_text(strip=True)

                    if value_element.find('span', class_='table__lock'):
                        continue

                    value = value_element.get_text(strip=True)
                    vessel_data[key] = value

        except Exception as e:
            print(f"An error occurred during the scraping process: {e}")
            return None
        finally:
            await browser.close()

    return vessel_data


# --- Main execution block ---
if __name__ == "__main__":
    base_domain = "https://magicport.ai"
    vessel_type = "bulk-carrier"
    vessel_name = "andria"
    vessel_mmsi = "249134000"
    target_url = f"{base_domain}/vessels/{vessel_type}/{vessel_name}-mmsi-{vessel_mmsi}"

    print(f"Scraping data from: {target_url}\n")

    scraped_data = asyncio.run(scrape_vessel_navigation_data_with_playwright(target_url))

    if scraped_data:
        print("\nScraping Successful! Here is the Navigation Data:")
        pprint(scraped_data)
    else:
        print("\nFailed to retrieve data.")