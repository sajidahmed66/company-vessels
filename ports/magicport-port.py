import json
import re
import asyncio
import os
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
        """Initialize Playwright browser with optimized settings"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-extensions',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
        )
        self.page = await self.browser.new_page()

        # Set minimal required headers
        await self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
            await self.page.goto(self.port_url, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(2000)  # Reduced wait time for dynamic content
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
                            # Skip port usage as requested
                            continue
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

    def extract_depths_from_div(self, soup):
        """Extract depth information from the Depths div/table"""
        depths = {}

        # Find the section containing "Depths" text
        depths_section = soup.find("span", string=re.compile(r"Depths", re.I))
        if not depths_section:
            # Try alternative search - look for caption with "Depths"
            depths_section = soup.find("caption", string=re.compile(r"Depths", re.I))

        if depths_section:
            # Find the containing table
            table = depths_section.find_parent("table")
            if not table:
                # Try finding the next table element
                table = depths_section.find_next("table")

            if table:
                # Extract data from table rows
                rows = table.find_all("tr")
                for row in rows:
                    th = row.find("th")
                    td = row.find("td")
                    if th and td:
                        label = th.get_text(strip=True)
                        value = td.get_text(strip=True)

                        # Convert "-" to None for missing values
                        if value == "-":
                            value = None

                        # Map common depth labels to standardized keys
                        if "Channel Depth" in label:
                            depths["channel_depth"] = value
                        elif "Anchorage Depth" in label:
                            depths["anchorage_depth"] = value
                        elif "Cargo Pier Depth" in label:
                            depths["cargo_pier_depth"] = value
                        elif "Oil Depth" in label:
                            depths["oil_depth"] = value
                        elif "Offshore Maximum Vessel Draft" in label:
                            depths["offshore_max_vessel_draft"] = value
                        else:
                            # Use lowercase with underscores for other labels
                            depths[label.lower().replace(" ", "_")] = value

        return depths

    def extract_port_characteristics_from_div(self, soup):
        """Extract port characteristics from the Port Characteristics div/table"""
        characteristics = {}

        # Find the section containing "Port Characteristics" text
        char_section = soup.find("span", string=re.compile(r"Port Characteristics", re.I))
        if not char_section:
            # Try alternative search - look for caption with "Port Characteristics"
            char_section = soup.find("caption", string=re.compile(r"Port Characteristics", re.I))

        if char_section:
            # Find the containing table
            table = char_section.find_parent("table")
            if not table:
                # Try finding the next table element
                table = char_section.find_next("table")

            if table:
                # Extract data from table rows
                rows = table.find_all("tr")
                for row in rows:
                    th = row.find("th")
                    td = row.find("td")
                    if th and td:
                        label = th.get_text(strip=True)
                        value = td.get_text(strip=True)

                        # Convert "-" to None for missing values
                        if value == "-":
                            value = None

                        # Map common characteristic labels to standardized keys
                        if "Harbour Type" in label:
                            characteristics["harbour_type"] = value
                        elif "Harbour Size" in label:
                            characteristics["harbour_size"] = value
                        else:
                            # Use lowercase with underscores for other labels
                            characteristics[label.lower().replace(" ", "_")] = value

        return characteristics

    def extract_restrictions_from_div(self, soup):
        """Extract restrictions from the Restrictions div/ul"""
        restrictions = {}

        # Find the section containing "Restrictions" text
        restrictions_section = soup.find("span", string=re.compile(r"Restrictions", re.I))
        if restrictions_section:
            # Find the containing div/section
            section_container = restrictions_section.find_parent("section") or restrictions_section.find_parent("div")
            if section_container:
                # Find the list with class list--condition
                restrictions_list = section_container.find("ul", class_="list--condition")
                if restrictions_list:
                    # Extract all list items
                    list_items = restrictions_list.find_all("li", class_="list__item")

                    for item in list_items:
                        # Extract restriction name
                        label_span = item.find("span", class_="list__item-label")
                        if label_span:
                            restriction_name = label_span.get_text(strip=True)

                            # Determine restriction status by checking the SVG icon
                            svg_icon = item.find("svg", class_="list__item-icon")
                            if svg_icon:
                                use_element = svg_icon.find("use")
                                if use_element:
                                    icon_href = use_element.get("xlink:href", "")
                                    # Check if restriction exists based on icon
                                    if "icon-close-circle" in icon_href:
                                        # Restriction exists (not available)
                                        restrictions[restriction_name] = False
                                    elif "icon-check-circle" in icon_href:
                                        # No restriction (available)
                                        restrictions[restriction_name] = True
                                    else:
                                        # Default to False if icon not recognized
                                        restrictions[restriction_name] = False
                            else:
                                # Default to False if no icon found
                                restrictions[restriction_name] = False

        return restrictions

    def extract_port_equipment_from_div(self, soup):
        """Extract port equipment from the Port Equipment div"""
        equipment_data = {}

        # Find the section containing "Port Equipment" text
        equipment_section = soup.find("span", string=re.compile(r"Port Equipment", re.I))
        if equipment_section:
            # Find the containing section
            section_container = equipment_section.find_parent("section")
            if section_container:
                # Find all equipment category sections (h4 elements)
                category_headers = section_container.find_all("h4", class_="box__inline-title")

                for header in category_headers:
                    category_name = header.get_text(strip=True)
                    category_data = {}

                    # Find the next ul list for this category
                    equipment_list = header.find_next("ul", class_="list--condition")
                    if equipment_list:
                        # Extract all list items
                        list_items = equipment_list.find_all("li", class_="list__item")

                        for item in list_items:
                            # Extract item label
                            label_span = item.find("span", class_="list__item-label")
                            if label_span:
                                item_name = label_span.get_text(strip=True)

                                # Check if this is a boolean item (has SVG icon) or text value item
                                svg_icon = item.find("svg", class_="list__item-icon")
                                value_span = item.find("span", class_="list__item-value")

                                if svg_icon:
                                    # Boolean item - check the SVG icon
                                    use_element = svg_icon.find("use")
                                    if use_element:
                                        icon_href = use_element.get("xlink:href", "")
                                        # Check if equipment is available based on icon
                                        if "icon-check-circle" in icon_href:
                                            # Equipment available
                                            category_data[item_name] = True
                                        elif "icon-close-circle" in icon_href:
                                            # Equipment not available
                                            category_data[item_name] = False
                                        else:
                                            # Default to False if icon not recognized
                                            category_data[item_name] = False
                                    else:
                                        category_data[item_name] = False
                                elif value_span:
                                    # Text value item
                                    value_text = value_span.get_text(strip=True)
                                    if value_text == "-":
                                        value_text = None
                                    category_data[item_name] = value_text

                    if category_data:  # Only add category if it has data
                        equipment_data[category_name] = category_data

        return equipment_data

    def extract_navigation_from_div(self, soup):
        """Extract navigation from the Navigation div/ul"""
        navigation = {}

        # Find the section containing "Navigation" text - be more specific to avoid cookie dialog
        navigation_section = soup.find("span", class_="box__title-label", string=re.compile(r"Navigation", re.I))
        if not navigation_section:
            # Try alternative search - look for h2 with Navigation
            navigation_section = soup.find("h2", string=re.compile(r"Navigation", re.I))

        if navigation_section:
            # Find the containing section
            section_container = navigation_section.find_parent("section")
            if section_container:
                # Find the list with class list--condition
                navigation_list = section_container.find("ul", class_="list--condition")
                if navigation_list:
                    # Extract all list items
                    list_items = navigation_list.find_all("li", class_="list__item")

                    for item in list_items:
                        # Extract navigation feature name
                        label_span = item.find("span", class_="list__item-label")
                        if label_span:
                            feature_name = label_span.get_text(strip=True)

                            # Determine feature status by checking the SVG icon
                            svg_icon = item.find("svg", class_="list__item-icon")
                            if svg_icon:
                                use_element = svg_icon.find("use")
                                if use_element:
                                    icon_href = use_element.get("xlink:href", "")
                                    # Check if feature is available based on icon
                                    if "icon-check-circle" in icon_href:
                                        # Feature available
                                        navigation[feature_name] = True
                                    elif "icon-close-circle" in icon_href:
                                        # Feature not available
                                        navigation[feature_name] = False
                                    else:
                                        # Default to False if icon not recognized
                                        navigation[feature_name] = False
                            else:
                                # Default to False if no icon found
                                navigation[feature_name] = False

        return navigation

    def extract_communication_from_div(self, soup):
        """Extract communication from the Communication div/ul"""
        communication = {}

        # Find the section containing "Communication" text
        communication_section = soup.find("span", string=re.compile(r"Communication", re.I))
        if communication_section:
            # Find the containing section
            section_container = communication_section.find_parent("section")
            if section_container:
                # Find the list with class list--condition
                communication_list = section_container.find("ul", class_="list--condition")
                if communication_list:
                    # Extract all list items
                    list_items = communication_list.find_all("li", class_="list__item")

                    for item in list_items:
                        # Extract communication service name
                        label_span = item.find("span", class_="list__item-label")
                        if label_span:
                            service_name = label_span.get_text(strip=True)

                            # Determine service status by checking the SVG icon
                            svg_icon = item.find("svg", class_="list__item-icon")
                            if svg_icon:
                                use_element = svg_icon.find("use")
                                if use_element:
                                    icon_href = use_element.get("xlink:href", "")
                                    # Check if service is available based on icon
                                    if "icon-check-circle" in icon_href:
                                        # Service available
                                        communication[service_name] = True
                                    elif "icon-close-circle" in icon_href:
                                        # Service not available
                                        communication[service_name] = False
                                    else:
                                        # Default to False if icon not recognized
                                        communication[service_name] = False
                            else:
                                # Default to False if no icon found
                                communication[service_name] = False

        return communication

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

            print("Extracting port data...")

            # Extract all data sections with the required structure
            basic_info = self.extract_basic_port_info(soup)
            port_info_div = self.extract_port_information_div(soup)
            depths_data = self.extract_depths_from_div(soup)
            characteristics_data = self.extract_port_characteristics_from_div(soup)
            restrictions_data = self.extract_restrictions_from_div(soup)
            equipment_data = self.extract_port_equipment_from_div(soup)
            navigation_data = self.extract_navigation_from_div(soup)
            communication_data = self.extract_communication_from_div(soup)

            # Merge data from both extraction methods
            self.port_data = {
                "port_name": basic_info.get("port_name"),
                "country": port_info_div.get("country", basic_info.get("country")),
                "unlocode": port_info_div.get("unlocode", basic_info.get("unlocode")),
                "coordinates": port_info_div.get("coordinates", basic_info.get("coordinates")),
                "depths": depths_data,
                "port_characteristics": characteristics_data,
                "restrictions": restrictions_data,
                "port_equipment": equipment_data,
                "navigation": navigation_data,
                "communication": communication_data,
                "scraped_at": datetime.now().isoformat(),
                "source_url": self.port_url
            }

            print(f"Port Information extracted from div:")
            print(f"  - Name: {basic_info.get('port_name')}")
            print(f"  - Country: {port_info_div.get('country', 'N/A')}")
            print(f"  - Unlocode: {port_info_div.get('unlocode', 'N/A')}")
            print(f"  - Coordinates: {port_info_div.get('coordinates', 'N/A')}")

            print(f"Depths extracted:")
            for key, value in depths_data.items():
                print(f"  - {key}: {value}")

            print(f"Port Characteristics extracted:")
            for key, value in characteristics_data.items():
                print(f"  - {key}: {value}")

            print(f"Restrictions extracted:")
            for key, value in restrictions_data.items():
                print(f"  - {key}: {value}")

            print(f"Port Equipment extracted:")
            for category, items in equipment_data.items():
                print(f"  - {category}:")
                for item_name, item_value in items.items():
                    print(f"    * {item_name}: {item_value}")

            print(f"Navigation extracted:")
            for key, value in navigation_data.items():
                print(f"  - {key}: {value}")

            print(f"Communication extracted:")
            for key, value in communication_data.items():
                print(f"  - {key}: {value}")

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

        # Save to file with format country_port_name_unlocode.json in ports directory
        if result.get("country") and result.get("port_name") and result.get("unlocode"):
            # Clean up the strings for filename
            country = re.sub(r'[^\w\s-]', '', result["country"]).strip().replace(' ', '_')
            port_name = re.sub(r'[^\w\s-]', '', result["port_name"]).strip().replace(' ', '_')
            unlocode = re.sub(r'[^\w\s-]', '', result["unlocode"]).strip()

            filename = f"ports_data/{country}_{port_name}_{unlocode}.json"
        else:
            # Fallback to timestamp if required data is missing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ports/port_data_{timestamp}.json"

        try:
            # Ensure the ports directory exists
            os.makedirs('ports_data', exist_ok=True)

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