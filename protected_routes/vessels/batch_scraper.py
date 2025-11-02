#!/usr/bin/env python3
"""
Batch Vessel Scraper
Processes multiple vessels from CSV file and saves individual vessel data files
"""

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
    """Extract data for a single vessel"""
    try:
        # Step 2: Navigate to the specific vessel page
        full_url = f"https://www.vesselfinder.com{vessel_url}"
        print(f"Navigating to vessel details page: {full_url}")
        await page.goto(full_url, wait_until="domcontentloaded")

        print("Waiting for vessel details page to load...")
        await page.wait_for_selector("h1", timeout=15000)

        # --- Step 3: Scroll from top to bottom ---
        print("Scrolling to the top of the page...")
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)  # Brief pause

        print("Scrolling to the bottom of the page...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # --- Step 4: Sleep for 2 seconds ---
        print("Waiting for 2 seconds for any lazy-loaded content...")
        await asyncio.sleep(2)

        # --- Step 5: Get HTML content ---
        print("Getting page HTML content...")
        html_content = await page.content()

        # --- Step 6: Parse HTML content with VesselScraper ---
        print("Parsing HTML content with VesselScraper...")
        scraper = VesselScraper()
        vessel_data = scraper.parse_html_content(html_content, full_url)

        # --- Step 7: Save vessel data ---
        mmsi = vessel_data.get('MMSI', 'unknown')
        imo = vessel_data.get('imo_number', 'unknown')

        saved_path = save_vessel_data(vessel_data, imo, mmsi)
        if saved_path:
            print(f"✅ Data saved to: {saved_path}")

        return vessel_data, saved_path

    except PlaywrightTimeoutError as e:
        print(f"❌ Timeout occurred for {vessel_name}: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Error processing {vessel_name}: {e}")
        return None, None


async def batch_scrape_vessels(csv_path: str, limit: int = None):
    """Process multiple vessels from CSV file"""

    # Read vessel data from CSV
    vessels = read_vessel_csv(csv_path)
    if not vessels:
        print("❌ No vessels to process")
        return

    # Apply limit if specified
    if limit:
        vessels = vessels[:limit]
        print(f"📊 Processing first {len(vessels)} vessels (limit applied)")

    # Initialize statistics
    stats = {
        'total': len(vessels),
        'success': 0,
        'failed': 0,
        'start_time': datetime.now(),
        'failed_vessels': []
    }

    print(f"🚀 Starting batch processing of {len(vessels)} vessels")
    print(f"⏰ Started at: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Step 1: Login (once for all vessels)
            await page.goto("https://www.vesselfinder.com/login")
            print("🔐 Logging in to VesselFinder...")

            await page.locator("#email").fill(EMAIL)
            await page.locator("#password").fill(PASSWORD)
            await page.locator("#loginbtn").click()

            print("🔍 Verifying login...")
            await expect(page).to_have_url("https://www.vesselfinder.com/", timeout=15000)
            print("✅ Login successful!")

            # Process each vessel
            for i, vessel in enumerate(vessels, 1):
                vessel_name = vessel['name']
                vessel_url = vessel['url']
                vessel_imo = vessel['imo']

                print(f"\n{'='*60}")
                print(f"📋 Processing vessel {i}/{stats['total']}: {vessel_name} (IMO: {vessel_imo})")
                print(f"{'='*60}")

                # Extract vessel data
                vessel_data, saved_path = await get_vessel_details(browser, page, vessel_url, vessel_name)

                # Update statistics
                if vessel_data and saved_path:
                    stats['success'] += 1
                    print(f"✅ Successfully processed: {vessel_name}")
                else:
                    stats['failed'] += 1
                    stats['failed_vessels'].append({
                        'name': vessel_name,
                        'imo': vessel_imo,
                        'url': vessel_url
                    })
                    print(f"❌ Failed to process: {vessel_name}")

                # Brief delay between vessels
                if i < len(vessels):
                    print("⏱️  Waiting 3 seconds before next vessel...")
                    await asyncio.sleep(3)

        finally:
            await browser.close()

    # Generate final report
    end_time = datetime.now()
    duration = end_time - stats['start_time']

    print(f"\n{'='*60}")
    print("📊 BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"⏰ Started:  {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏰ Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Duration: {duration}")
    print(f"✅ Successful: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"📈 Success Rate: {(stats['success']/stats['total']*100):.1f}%")

    if stats['failed_vessels']:
        print(f"\n❌ Failed Vessels ({len(stats['failed_vessels'])}):")
        for vessel in stats['failed_vessels']:
            print(f"   - {vessel['name']} (IMO: {vessel['imo']})")

    # Save failed vessels log
    if stats['failed_vessels']:
        failed_log_path = f"failed_vessels_{int(time.time())}.json"
        with open(failed_log_path, 'w', encoding='utf-8') as f:
            json.dump(stats['failed_vessels'], f, indent=2, ensure_ascii=False)
        print(f"\n📝 Failed vessels log saved to: {failed_log_path}")


if __name__ == "__main__":
    # Path to CSV file
    csv_path = "protected_routes/vessels/vessel_imo_by_country/high_volume_AU_Australia.csv"
    limit = 100
    asyncio.run(batch_scrape_vessels(csv_path, limit=limit))