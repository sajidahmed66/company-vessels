# -*- coding: utf-8 -*-
import asyncio
import time
import json
import re
import os
from datetime import datetime
from single_port import SinglePortScrapper

# List of URLs to scrape
PORT_URLS = [
    'https://magicport.ai/ports/albania/vlore-port-alvoa',
    'https://magicport.ai/ports/albania/shengjin-port-alshg',
    'https://magicport.ai/ports/albania/sarande-port-alsar',
    'https://magicport.ai/ports/albania/romano-port-alrom',
    'https://magicport.ai/ports/albania/durres-port-aldrz',
    'https://magicport.ai/ports/algeria/el-kala-port-dzqlk',
    'https://magicport.ai/ports/algeria/cherchell-port-dzche',
    'https://magicport.ai/ports/algeria/alger-port-dzalg',
    'https://magicport.ai/ports/algeria/annaba-port-dzaae',
    'https://magicport.ai/ports/algeria/bethioua-port-dzbha'
]

async def scrape_single_port(url):
    """Scrape a single port with time logging and file saving"""
    # Start time logging
    start_time = datetime.now()
    print(f"🚀 Starting scrape for: {url}")
    print(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Create scraper instance
    scraper = SinglePortScrapper(port_url=url, headless=True)

    # Run scraping process
    result = await scraper.scrape()

    if result:
        # End time logging
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n✅ Scraping completed successfully!")
        print(f"⏱️  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total duration: {duration.total_seconds():.2f} seconds")

        # Print JSON output
        scraper.print_json_output()

        # Save to file with format country_port_name_unlocode.json
        if result.get("country") and result.get("port_name") and result.get("unlocode"):
            # Clean up the strings for filename
            country = re.sub(r'[^\w\s-]', '', result["country"]).strip().replace(' ', '_')
            port_name = re.sub(r'[^\w\s-]', '', result["port_name"]).strip().replace(' ', '_')
            unlocode = re.sub(r'[^\w\s-]', '', result["unlocode"]).strip()

            filename = f"ports_data/{country}_{port_name}_{unlocode}.json"
        else:
            # Fallback to timestamp if required data is missing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ports_data/port_data_{timestamp}.json"

        try:
            # Ensure the ports_data directory exists
            os.makedirs('ports_data', exist_ok=True)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Data also saved to: {filename}")
        except Exception as e:
            print(f"❌ Error saving to file: {e}")

        return True
    else:
        # End time logging for failed case
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n❌ Scraping failed!")
        print(f"⏱️  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total duration: {duration.total_seconds():.2f} seconds")
        return False

async def scrape_port_with_retry(url, max_retries=3):
    """Scrape a single port with retry logic"""
    for attempt in range(max_retries):
        try:
            success = await scrape_single_port(url)
            if success:
                return True
            else:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⏳ Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"❌ Error scraping {url} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)

    print(f"💀 All attempts failed for: {url}")
    return False

async def main():
    """Main function to scrape all ports"""
    print("🚀 Starting MagicPort Batch Scraper")
    print(f"📋 Total ports to scrape: {len(PORT_URLS)}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    start_time = time.time()
    success_count = 0
    failed_urls = []

    for i, url in enumerate(PORT_URLS, 1):
        print(f"\n🔄 Progress: {i}/{len(PORT_URLS)} ports")

        success = await scrape_port_with_retry(url)

        if success:
            success_count += 1
        else:
            failed_urls.append(url)

        # Add a small delay between requests to be respectful
        if i < len(PORT_URLS):
            await asyncio.sleep(1)

    # Summary
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / len(PORT_URLS)

    print("\n" + "="*60)
    print("📊 BATCH SCRAPING SUMMARY")
    print("="*60)
    print(f"✅ Successfully scraped: {success_count}/{len(PORT_URLS)} ports")
    print(f"❌ Failed: {len(failed_urls)} ports")
    print(f"⏱️  Total time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print(f"⚡ Average time per port: {avg_time:.2f} seconds")
    print(f"🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if failed_urls:
        print(f"\n❌ Failed URLs:")
        for url in failed_urls:
            print(f"  - {url}")

    print(f"\n📁 Files saved in ports_data/ directory with format: country_port_name_unlocode.json")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())