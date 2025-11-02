import asyncio
import os
import json
import time
import csv
from time import sleep
from datetime import datetime

from playwright.async_api import async_playwright, expect, TimeoutError as PlaywrightTimeoutError
from vessel_scrapper import VesselScraper

EMAIL = os.getenv("VESSELFINDER_EMAIL", "sajidahmedsiddiqui66@gmail.com")
PASSWORD = os.getenv("VESSELFINDER_PASSWORD", "$Am8A7Q#MPz7Kg-")

if not EMAIL or not PASSWORD:
    raise ValueError("VESSELFINDER_EMAIL and VESSELFINDER_PASSWORD environment variables must be set.")


def read_vessel_csv(csv_path: str) -> list:
    """Read vessel data from CSV file"""
    vessels = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                vessels.append({
                    'url': row['url'],
                    'name': row['name'],
                    'type': row['type'],
                    'imo': row['imo']
                })
        print(f"✅ Loaded {len(vessels)} vessels from CSV")
        return vessels
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return []


def save_vessel_data(vessel_data: dict, imo: str, mmsi: str):
    """Save vessel data to JSON file with IMO_MMSI naming"""
    try:
        # Create vessel_data directory if it doesn't exist
        os.makedirs('vessel_data', exist_ok=True)

        # Clean IMO and MMSI for filename
        clean_imo = imo.strip()
        clean_mmsi = mmsi.strip()

        # Create filename
        filename = f"vessel_{clean_imo}_{clean_mmsi}.json"
        filepath = os.path.join('vessel_data', filename)

        # Save data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(vessel_data, f, indent=2, ensure_ascii=False)

        return filepath
    except Exception as e:
        print(f"❌ Error saving vessel data: {e}")
        return None


async def get_vessel_details(browser, page, vessel_url: str, vessel_name: str):

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Step 1: Login
            await page.goto("https://www.vesselfinder.com/login")
            print("Filling in login details...")
            await page.locator("#email").fill(EMAIL)
            await page.locator("#password").fill(PASSWORD)
            print("Clicking login button...")
            await page.locator("#loginbtn").click()
            print("Verifying successful login by checking URL...")
            await expect(page).to_have_url("https://www.vesselfinder.com/", timeout=15000)
            print("✅ Login successful!")

            # Step 2: Navigate to the specific vessel page
            vessel_url = "https://www.vesselfinder.com/vessels/details/9648714"
            print(f"Navigating to vessel details page: {vessel_url}")
            await page.goto(vessel_url, wait_until="domcontentloaded")

            print("Waiting for vessel details page to load...")
            await page.wait_for_selector("h1", timeout=15000)

            # --- Step 3: Scroll from top to bottom ---
            print("Scrolling to the top of the page...")

            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1) # Brief pause

            print("Scrolling to the bottom of the page...")

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # --- Step 4: Sleep for 2 seconds ---

            print("Waiting for 2 seconds for any lazy-loaded content...")
            await asyncio.sleep(2)


            print("Getting page HTML content...")
            html_content = await page.content()

            # Step 5: Pass HTML content to VesselScraper
            print("Parsing HTML content with VesselScraper...")
            scraper = VesselScraper()
            vessel_data = scraper.parse_html_content(html_content, vessel_url)

            # Step 6: Save data to JSON file
            json_output = json.dumps(vessel_data, indent=2, ensure_ascii=False)
            print("\n" + "=" * 50)
            print("SCRAPED DATA (JSON OUTPUT):")
            print("=" * 50)
            print(json_output)

            # step 7 Save to file
            output_file = f"vessel_data_{int(time.time())}.json"
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                print(f"\n✓ Data saved to: {output_file}")
            except Exception as e:
                print(f"\n✗ Failed to save to file: {e}")

            return vessel_data

        except PlaywrightTimeoutError as e:
            print(f"❌ A timeout occurred: {e}")
            print("This could mean the page took too long to load or an element wasn't found.")
            await page.screenshot(path="timeout_error.png")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            await page.screenshot(path="unexpected_error.png")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(get_vessel_details())