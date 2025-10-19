import json
import re
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


class MagicPortScraper:
    """Scraper for MagicPort port pages with vessel data extraction"""

    def __init__(self, port_url, headless=True):
        self.port_url = port_url
        self.headless = headless
        self.browser = None
        self.page = None
        self.port_data = {}

    async def setup_browser(self):
        """Initialize Playwright browser with stealth settings"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()

        # Set realistic viewport and user agent
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        await self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    async def close_browser(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
            await self.playwright.stop()

    async def navigate_to_port_page(self):
        """Navigate to the port page and wait for content to load"""
        try:
            print(f"Navigating to: {self.port_url}")
            await self.page.goto(self.port_url, wait_until="networkidle")
            await self.page.wait_for_timeout(5000)  # Allow dynamic content to load
            # Wait for page to be fully loaded
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            return False

    def extract_basic_port_info(self, soup):
        """Extract basic port information from the header section"""
        port_info = {}

        # Extract port name and country from header
        header_title = soup.find("h1", class_="single__header-title")
        if header_title:
            port_info["port_name"] = header_title.get_text(strip=True)

        header_subtitle = soup.find("span", class_="text-style--small")
        if header_subtitle:
            subtitle_text = header_subtitle.get_text(strip=True)
            # Extract country and unlocode from subtitle
            country_match = re.search(r'([^(]+)\(([^)]+)\)', subtitle_text)
            if country_match:
                port_info["country"] = country_match.group(1).strip()
                port_info["unlocode"] = country_match.group(2).strip()

        # Extract coordinates from port information table
        coord_row = soup.find("th", string=re.compile(r"Latitude.*Longitude", re.I))
        if coord_row:
            coord_cell = coord_row.find_next_sibling("td")
            if coord_cell:
                coord_text = coord_cell.get_text(strip=True)
                port_info["coordinates"] = coord_text

        # Extract port usage statistics
        usage_row = soup.find("th", string="Port Usage")
        if usage_row:
            usage_cell = usage_row.find_next_sibling("td")
            if usage_cell:
                # Extract progress bar data
                progress_bars = usage_cell.find_all("span", class_=re.compile(r"progress-bar__track"))
                usage_stats = {}
                for bar in progress_bars:
                    class_list = bar.get("class", [])
                    style = bar.get("style", "")
                    if "progress-bar__track--cargo" in class_list:
                        width = re.search(r'width:\s*([\d.]+)%', style)
                        if width:
                            usage_stats["cargo"] = float(width.group(1))
                    elif "progress-bar__track--tanker" in class_list:
                        width = re.search(r'width:\s*([\d.]+)%', style)
                        if width:
                            usage_stats["tanker"] = float(width.group(1))
                    elif "progress-bar__track--passenger" in class_list:
                        width = re.search(r'width:\s*([\d.]+)%', style)
                        if width:
                            usage_stats["passenger"] = float(width.group(1))
                port_info["port_usage"] = usage_stats

        # Extract additional port details
        unlocode_row = soup.find("th", string="Unlocode")
        if unlocode_row:
            unlocode_cell = unlocode_row.find_next_sibling("td")
            if unlocode_cell:
                port_info["unlocode"] = unlocode_cell.get_text(strip=True)

        country_row = soup.find("th", string="Country")
        if country_row:
            country_cell = country_row.find_next_sibling("td")
            if country_cell:
                port_info["country"] = country_cell.get_text(strip=True)

        return port_info

    def extract_port_information_div(self, soup):
        """Extract port information from the Port Information div/table"""
        port_info = {}

        # Find the section containing "Port Information" text
        port_info_section = soup.find("span", string=re.compile(r"Port Information", re.I))
        if not port_info_section:
            # Try alternative search
            port_info_section = soup.find("h2", string=re.compile(r"Port Information", re.I))

        if port_info_section:
            # Find the containing table
            table = port_info_section.find_parent("table")
            if not table:
                # Try finding the next table element
                table = port_info_section.find_next("table")

            if table:
                # Extract data from table rows
                rows = table.find_all("tr")
                for row in rows:
                    th = row.find("th")
                    td = row.find("td")
                    if th and td:
                        label = th.get_text(strip=True)

                        if label == "Port Usage":
                            # Extract progress bar data for port usage
                            progress_bars = td.find_all("span", class_=re.compile(r"progress-bar__track"))
                            usage_stats = {}
                            for bar in progress_bars:
                                class_list = bar.get("class", [])
                                style = bar.get("style", "")
                                if "progress-bar__track--cargo" in class_list:
                                    width = re.search(r'width:\s*([\d.]+)%', style)
                                    if width:
                                        usage_stats["cargo"] = float(width.group(1))
                                elif "progress-bar__track--tanker" in class_list:
                                    width = re.search(r'width:\s*([\d.]+)%', style)
                                    if width:
                                        usage_stats["tanker"] = float(width.group(1))
                                elif "progress-bar__track--passenger" in class_list:
                                    width = re.search(r'width:\s*([\d.]+)%', style)
                                    if width:
                                        usage_stats["passenger"] = float(width.group(1))
                            port_info["port_usage"] = usage_stats
                        elif label == "Unlocode":
                            port_info["unlocode"] = td.get_text(strip=True)
                        elif label == "Latitude / Longitude":
                            port_info["coordinates"] = td.get_text(strip=True)
                        elif label == "Country":
                            port_info["country"] = td.get_text(strip=True)
                        else:
                            # Handle any other fields
                            port_info[label.lower().replace(" ", "_")] = td.get_text(strip=True)

        return port_info

    # def extract_vessel_table_data(self, soup, table_id):
    #     # i do not need this
    #     """Extract vessel data from tables (both current and historical)"""
    #     vessels = []
    #
    #     table = soup.find("table", {"id": table_id})
    #     if not table:
    #         print(f"Table {table_id} not found")
    #         return vessels
    #
    #     tbody = table.find("tbody")
    #     if not tbody:
    #         print(f"No tbody found in table {table_id}")
    #         return vessels
    #
    #     rows = tbody.find_all("tr")
    #     print(f"Found {len(rows)} vessels in table {table_id}")
    #
    #     for row in rows:
    #         vessel = {}
    #
    #         # Extract vessel name and flag
    #         name_cell = row.find("td")
    #         if name_cell:
    #             name_link = name_cell.find("a")
    #             if name_link:
    #                 vessel["name"] = name_link.get_text(strip=True)
    #                 vessel["vessel_url"] = name_link.get("href", "")
    #
    #             flag_img = name_cell.find("img")
    #             if flag_img:
    #                 vessel["flag"] = flag_img.get("alt", "")
    #
    #         # Extract IMO, Type, DWT, ETA from other cells
    #         cells = row.find_all("td")
    #         if len(cells) >= 5:
    #             vessel["imo"] = cells[1].get_text(strip=True)
    #             vessel["type"] = cells[2].get_text(strip=True)
    #             vessel["dwt"] = cells[3].get_text(strip=True)
    #             vessel["eta"] = cells[4].get_text(strip=True)
    #
    #         if vessel.get("name"):
    #             vessels.append(vessel)
    #
    #     return vessels
    #
    # def extract_port_characteristics(self, soup):
    #     """Extract port restrictions, equipment, and navigation facilities"""
    #     characteristics = {
    #         "restrictions": {},
    #         "equipment": {},
    #         "navigation": {},
    #         "communication": {}
    #     }
    #
    #     # Extract restrictions - simplified approach
    #     restrictions_section = soup.find("span", string=re.compile(r"Restrictions", re.I))
    #     if restrictions_section:
    #         restrictions_list = restrictions_section.find_next("ul", class_="list--condition")
    #         if restrictions_list:
    #             for item in restrictions_list.find_all("li"):
    #                 label = item.find("span", class_="list__item-label")
    #                 if label:
    #                     # For now, just mark all as false since they have close icons
    #                     restriction_name = label.get_text(strip=True)
    #                     characteristics["restrictions"][restriction_name] = False
    #
    #     # Extract port equipment - simplified approach
    #     equipment_section = soup.find("span", string=re.compile(r"Port Equipment", re.I))
    #     if equipment_section:
    #         equipment_data = {}
    #         category_titles = equipment_section.find_all_next("h4", class_="text-style--normal")
    #
    #         for title in category_titles:
    #             category = title.get_text(strip=True)
    #             category_data = {}
    #             equipment_list = title.find_next("ul", class_="list--condition")
    #             if equipment_list:
    #                 for item in equipment_list.find_all("li"):
    #                     label = item.find("span", class_="list__item-label")
    #                     if label:
    #                         item_name = label.get_text(strip=True)
    #                         category_data[item_name] = False  # All have close icons
    #             equipment_data[category] = category_data
    #
    #         characteristics["equipment"] = equipment_data
    #
    #     # Extract navigation facilities - simplified approach
    #     navigation_section = soup.find("span", string=re.compile(r"Navigation", re.I))
    #     if navigation_section:
    #         navigation_list = navigation_section.find_next("ul", class_="list--condition")
    #         if navigation_list:
    #             for item in navigation_list.find_all("li"):
    #                 label = item.find("span", class_="list__item-label")
    #                 if label:
    #                     navigation_name = label.get_text(strip=True)
    #                     characteristics["navigation"][navigation_name] = False  # All have close icons
    #
    #     # Extract communication options - simplified approach
    #     comm_section = soup.find("span", string=re.compile(r"Communication", re.I))
    #     if comm_section:
    #         comm_list = comm_section.find_next("ul", class_="list--condition")
    #         if comm_list:
    #             for item in comm_list.find_all("li"):
    #                 label = item.find("span", class_="list__item-label")
    #                 if label:
    #                     comm_name = label.get_text(strip=True)
    #                     characteristics["communication"][comm_name] = False  # All have close icons
    #
    #     return characteristics
    #
    # def extract_service_providers(self, soup):
    #     """Extract service providers (agents, suppliers, shipyards)"""
    #     providers = {
    #         "ship_agents": [],
    #         "service_providers": [],
    #         "suppliers": [],
    #         "shipyards": []
    #     }
    #
    #     provider_sections = [
    #         ("ship_agents", "Ship Agents"),
    #         ("service_providers", "Service Providers"),
    #         ("suppliers", "Suppliers"),
    #         ("shipyards", "Shipyards")
    #     ]
    #
    #     for provider_type, section_title in provider_sections:
    #         section = soup.find("h2", string=re.compile(section_title, re.I))
    #         if section:
    #             cards = section.find_all("div", class_="card--company")
    #             for card in cards:
    #                 provider = {}
    #
    #                 # Extract name and URL
    #                 name_link = card.find("a", class_="card__title")
    #                 if name_link:
    #                     provider["name"] = name_link.get_text(strip=True)
    #                     provider["url"] = name_link.get("href", "")
    #
    #                 # Extract image
    #                 img = card.find("img", class_="card__image-item")
    #                 if img:
    #                     provider["image_url"] = img.get("src", "")
    #
    #                 providers[provider_type].append(provider)
    #
    #     return providers
    #
    # def extract_nearby_ports(self, soup):
    #     """Extract nearby ports information"""
    #     nearby_ports = []
    #
    #     section = soup.find("h2", string=re.compile(r"Nearby Ports", re.I))
    #     if section:
    #         table = section.find_next("table")
    #         if table:
    #             tbody = table.find("tbody")
    #             if tbody:
    #                 rows = tbody.find_all("tr")
    #                 for row in rows:
    #                     port_info = {}
    #
    #                     # Extract port name and URL
    #                     name_cell = row.find("td")
    #                     if name_cell:
    #                         name_link = name_cell.find("a")
    #                         if name_link:
    #                             port_info["name"] = name_link.get_text(strip=True)
    #                             port_info["url"] = name_link.get("href", "")
    #
    #                     # Extract coordinates
    #                     cells = row.find_all("td")
    #                     if len(cells) >= 2:
    #                         port_info["coordinates"] = cells[1].get_text(strip=True)
    #
    #                     if port_info.get("name"):
    #                         nearby_ports.append(port_info)
    #
    #     return nearby_ports
    #
    # def extract_depths(self, soup):
    #     """Extract depth information"""
    #     depths = {}
    #
    #     # Extract depths - simplified approach
    #     depths_section = soup.find("caption", string=re.compile(r"Depths", re.I))
    #     if depths_section:
    #         table = depths_section.find_parent("table")
    #         if table:
    #             rows = table.find_all("tr")
    #             for row in rows:
    #                 th = row.find("th")
    #                 td = row.find("td")
    #                 if th and td:
    #                     depth_type = th.get_text(strip=True)
    #                     depth_value = td.get_text(strip=True)
    #                     if depth_value == "-":
    #                         depth_value = None
    #                     depths[depth_type] = depth_value
    #
    #     return depths
    #
    # def extract_port_characteristics_basic(self, soup):
    #     """Extract basic port characteristics (Harbour Type, Harbour Size)"""
    #     characteristics = {}
    #
    #     # Extract port characteristics - simplified approach
    #     char_section = soup.find("caption", string=re.compile(r"Port Characteristics", re.I))
    #     if char_section:
    #         table = char_section.find_parent("table")
    #         if table:
    #             rows = table.find_all("tr")
    #             for row in rows:
    #                 th = row.find("th")
    #                 td = row.find("td")
    #                 if th and td:
    #                     char_type = th.get_text(strip=True)
    #                     char_value = td.get_text(strip=True)
    #                     if char_value == "-":
    #                         char_value = None
    #                     characteristics[char_type] = char_value
    #
    #     return characteristics

    async def wait_for_vessel_data(self):
        """Wait for vessel data tables to load"""
        try:
            # Wait for the vessel tables to be populated
            print("Waiting for vessel data to load...")
            await self.page.wait_for_selector("#table-port-vessels-port tbody tr", timeout=15000)
            await self.page.wait_for_timeout(2000)  # Additional wait for complete loading
            print("Vessel data loaded successfully")
            return True
        except Exception as e:
            print(f"Timeout waiting for vessel data: {e}")
            return False

    async def extract_all_data(self):
        """Main method to extract all port data"""
        try:
            # Get page HTML
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Save HTML for debugging
            with open('debug_page_content.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("Saved page HTML to debug_page_content.html for inspection")

            print("Extracting port data...")

            # Extract all data sections with the required structure
            basic_info = self.extract_basic_port_info(soup)
            port_info_div = self.extract_port_information_div(soup)

            # Merge data from both extraction methods
            self.port_data = {
                "port_name": basic_info.get("port_name"),
                "country": port_info_div.get("country", basic_info.get("country")),
                "unlocode": port_info_div.get("unlocode", basic_info.get("unlocode")),
                "port_information": {
                    "coordinates": port_info_div.get("coordinates", basic_info.get("coordinates")),
                    "port_usage": port_info_div.get("port_usage", basic_info.get("port_usage"))
                },
                "scraped_at": datetime.now().isoformat(),
                "source_url": self.port_url
            }

            print(f"Port Information extracted from div:")
            print(f"  - Name: {basic_info.get('port_name')}")
            print(f"  - Country: {port_info_div.get('country', 'N/A')}")
            print(f"  - Unlocode: {port_info_div.get('unlocode', 'N/A')}")
            print(f"  - Coordinates: {port_info_div.get('coordinates', 'N/A')}")
            print(f"  - Port Usage: {len(port_info_div.get('port_usage', {}))} categories")

            print("Data extraction completed")
            return True
        except Exception as e:
            print(f"Data extraction error: {e}")
            return False

    async def scrape(self):
        """Main scraping workflow"""
        print(f"Starting scrape for: {self.port_url}")

        try:
            # Setup browser
            await self.setup_browser()

            # Navigate to page
            if not await self.navigate_to_port_page():
                print("Failed to navigate to port page")
                return None

            # Extract data
            if not await self.extract_all_data():
                print("Failed to extract data")
                return None

            print(f"Successfully scraped port data")
            print(f"Current vessels: {len(self.port_data.get('current_vessels', []))}")
            print(f"Historical vessels: {len(self.port_data.get('historical_vessels', []))}")
            print(f"Service providers categories: {len([k for k, v in self.port_data.get('service_providers', {}).items() if v])}")

            return self.port_data

        except Exception as e:
            print(f"Scraping error: {e}")
            return None
        finally:
            await self.close_browser()

    def print_json_output(self, data=None):
        """Print data as formatted JSON"""
        if data is None:
            data = self.port_data

        print("\n" + "="*50)
        print("SCRAPED PORT DATA (JSON OUTPUT)")
        print("="*50)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("="*50)


async def main():
    """Main function for standalone execution"""
    # Start time logging
    start_time = datetime.now()
    print(f"🚀 MagicPort Port Scraper Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Static URL for testing
    # port_url = "https://magicport.ai/ports/china/shanghai-port-cnshg"
    port_url = "https://magicport.ai/ports/iran/abadan-port-irabd"

    print(f"📍 Target URL: {port_url}")
    print("-" * 50)

    # Create scraper instance
    scraper = MagicPortScraper(
        port_url=port_url,
        headless=True
    )

    # Run scraping process
    result = await scraper.scrape()

    if result:
        # End time logging
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n✅ Scraping completed successfully!")
        print(f"⏱️  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total duration: {duration.total_seconds():.2f} seconds")
        print("-" * 50)

        # Print JSON output
        scraper.print_json_output()

        # Optionally save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"port_data_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Data also saved to: {filename}")
        except Exception as e:
            print(f"❌ Error saving to file: {e}")

        return 0
    else:
        # End time logging for failed case
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n❌ Scraping failed!")
        print(f"⏱️  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total duration: {duration.total_seconds():.2f} seconds")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)