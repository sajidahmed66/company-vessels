#!/usr/bin/env python3
"""
VesselFinder Web Scraper
Scrapes vessel information from VesselFinder.com
Returns data in JSON format for the specified sections:
1) ship-section text-section
2) ship-section general data
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, Any, Optional
import sys
import urllib.parse


class VesselScraper:
    def __init__(self):
        self.session = requests.Session()
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse the webpage"""
        try:
            print(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            return None

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def extract_table_data(self, table) -> Dict[str, str]:
        """Extract data from HTML table"""
        data = {}

        if not table:
            return data

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = self.clean_text(cells[0].get_text())
                value = self.clean_text(cells[1].get_text())
                if key and value:
                    data[key] = value

        return data

    def extract_vessel_particulars(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract vessel particulars section"""
        particulars = {}

        # Look for vessel particulars section
        particulars_section = soup.find('h2', string=re.compile(r'VESSEL PARTICULARS', re.I))
        if particulars_section:
            # Find the parent container
            container = particulars_section.find_parent()
            if container:
                # Look for table or structured data
                table = container.find('table') or container.find_next('table')
                if table:
                    particulars.update(self.extract_table_data(table))

                # Also look for any div with vessel data
                data_divs = container.find_all('div', class_=re.compile(r'ship|vessel|data', re.I))
                for div in data_divs:
                    text = self.clean_text(div.get_text())
                    if text and len(text) > 5:  # Avoid empty or very short strings
                        # Try to extract key-value pairs from text
                        lines = text.split('\n')
                        for line in lines:
                            if ':' in line:
                                parts = line.split(':', 1)
                                if len(parts) == 2:
                                    key = self.clean_text(parts[0])
                                    value = self.clean_text(parts[1])
                                    if key and value:
                                        particulars[key] = value

        # Try to extract vessel image URL (e.g., <img class="main-photo" ...>)
        try:
            img = soup.find('img', class_=re.compile(r'main[-_]?photo', re.I))
            if img and img.get('src'):
                src = img.get('src').strip()
                # Normalize to absolute URL if needed
                if not re.match(r'^https?://', src):
                    src = urllib.parse.urljoin('https://www.vesselfinder.com', src)
                particulars['vessel_image_url'] = src
        except Exception:
            pass

        return particulars

    def extract_voyage_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract voyage data section"""
        voyage_data = {}

        # Look for voyage data section
        voyage_section = soup.find('h2', string=re.compile(r'VOYAGE DATA', re.I))
        if voyage_section:
            container = voyage_section.find_parent()
            if container:
                # Find table with voyage information
                table = container.find('table') or container.find_next('table')
                if table:
                    voyage_data.update(self.extract_table_data(table))

                # Look for specific voyage information in text
                text_content = container.get_text()

                # Extract destination
                destination_match = re.search(r'Destination[:\s]*([^,]+(?:,[^,]+)*)', text_content, re.I)
                if destination_match:
                    voyage_data['Destination'] = self.clean_text(destination_match.group(1))

                # Extract ETA
                eta_match = re.search(r'ETA[:\s]*([^(]+)', text_content, re.I)
                if eta_match:
                    voyage_data['ETA'] = self.clean_text(eta_match.group(1))

                # Extract course and speed
                course_speed_match = re.search(r'Course[/\s]*Speed[:\s]*([\d.]+°[/\s]*[\d.]+\s*kn)', text_content, re.I)
                if course_speed_match:
                    voyage_data['Course/Speed'] = self.clean_text(course_speed_match.group(1))

        return voyage_data

    def extract_ship_text_section(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract ship text sections (descriptions, summaries)"""
        text_sections = {}

        # Look for the main description/summary
        # This is usually in the first paragraph or text section
        main_content = soup.find('div', class_=re.compile(r'content|main|description', re.I))
        if main_content:
            paragraphs = main_content.find_all('p')
            descriptions = []
            for p in paragraphs:
                text = self.clean_text(p.get_text())
                if text and len(text) > 20:  # Filter out very short text
                    descriptions.append(text)

            if descriptions:
                text_sections['description'] = descriptions

        # Look for any other text sections
        text_divs = soup.find_all('div', class_=re.compile(r'text|info|detail', re.I))
        for i, div in enumerate(text_divs):
            text = self.clean_text(div.get_text())
            if text and len(text) > 20:
                text_sections[f'text_section_{i + 1}'] = text

        return text_sections

    def extract_general_ship_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract general ship information from various sections"""
        ship_info = {}

        # Extract title and basic info
        title = soup.find('h1')
        if title:
            ship_info['vessel_name'] = self.clean_text(title.get_text())

        # Extract subtitle (usually vessel type and IMO)
        subtitle = soup.find('h2')
        if subtitle:
            subtitle_text = self.clean_text(subtitle.get_text())
            ship_info['vessel_type_and_imo'] = subtitle_text

            # Try to extract IMO number
            imo_match = re.search(r'IMO\s*(\d+)', subtitle_text, re.I)
            if imo_match:
                ship_info['imo_number'] = imo_match.group(1)

        # Look for meta information or structured data
        meta_info = soup.find_all('div', class_=re.compile(r'meta|info|data', re.I))
        for div in meta_info:
            text = self.clean_text(div.get_text())
            # Look for specific patterns
            if 'current position' in text.lower():
                ship_info['position_info'] = text
            elif 'sailing' in text.lower() and 'speed' in text.lower():
                ship_info['navigation_info'] = text

        return ship_info

    def scrape_vessel_data(self, url: str) -> Dict[str, Any]:
        """Main scraping function"""
        soup = self.fetch_page(url)
        if not soup:
            return {"error": "Failed to fetch webpage"}

        result = {
            "url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sections": {
                "ship_text_section": {},
                "ship_section_data": {}
            }
        }

        try:
            # Extract ship text sections
            print("Extracting ship text sections...")
            text_sections = self.extract_ship_text_section(soup)
            general_info = self.extract_general_ship_info(soup)

            result["sections"]["ship_text_section"] = {
                **text_sections,
                **general_info
            }

            # Extract ship data sections
            print("Extracting ship data sections...")
            vessel_particulars = self.extract_vessel_particulars(soup)
            voyage_data = self.extract_voyage_data(soup)

            result["sections"]["ship_section_data"] = {
                "vessel_particulars": vessel_particulars,
                "voyage_data": voyage_data
            }

            # Additional sections that might be useful
            print("Extracting additional sections...")

            # Look for any other structured data sections
            all_tables = soup.find_all('table')
            additional_data = {}

            for i, table in enumerate(all_tables):
                table_data = self.extract_table_data(table)
                if table_data:  # Only add if table has data
                    additional_data[f'table_{i + 1}'] = table_data

            if additional_data:
                result["sections"]["additional_tables"] = additional_data

        except Exception as e:
            result["error"] = f"Error during scraping: {str(e)}"
            print(f"Error during scraping: {e}")

        return result


def main():
    """Main function"""
    # Default URL
    url = "https://www.vesselfinder.com/vessels/details/9289984"

    # Allow custom URL from command line
    if len(sys.argv) > 1:
        url = sys.argv[1]

    print(f"VesselFinder Scraper")
    print(f"Target URL: {url}")
    print("-" * 50)

    scraper = VesselScraper()
    data = scraper.scrape_vessel_data(url)

    # Output JSON
    json_output = json.dumps(data, indent=2, ensure_ascii=False)
    print("\n" + "=" * 50)
    print("SCRAPED DATA (JSON OUTPUT):")
    print("=" * 50)
    print(json_output)

    # Save to file
    output_file = f"vessel_data_{int(time.time())}.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"\n✓ Data saved to: {output_file}")
    except Exception as e:
        print(f"\n✗ Failed to save to file: {e}")


if __name__ == "__main__":
    main()
