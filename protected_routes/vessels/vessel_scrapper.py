#!/usr/bin/env python3
"""
VesselFinder Web Scraper
Scrapes vessel information from VesselFinder.com
Returns data in JSON format for the specified sections:
1) ship-section text-section
2) ship-section general data
"""

from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, Any, Optional
import urllib.parse

class VesselScraper:

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def flatten_json(self, nested_dict: Dict[str, Any], parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
        flattened = {}

        preserve_keys = {'url', 'scraped_at', 'error'}

        for key, value in nested_dict.items():
            if isinstance(value, dict):
                flattened.update(self.flatten_json(value, key, separator))

            elif isinstance(value, list):

                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flattened.update(self.flatten_json(item, f"{key}[{i}]", separator))
                    else:
                        if key in preserve_keys or not parent_key:
                            flattened[f"{key}[{i}]"] = item
                        else:
                            flattened[key] = item
            else:
                if key in preserve_keys or not parent_key:
                    flattened[key] = value
                else:
                    flattened[key] = value

        return flattened

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
                    # Special handling for combined fields like "IMO / MMSI" or "Length / Beam"
                    if "/" in key and any(field in key.upper() for field in ["IMO", "MMSI", "LENGTH", "BEAM"]):
                        self._split_combined_field(key, value, data)
                    else:
                        data[key] = value

        return data

    def _split_combined_field(self, key: str, value: str, data: Dict[str, str]):
        """Split combined fields like 'IMO / MMSI' into separate fields"""
        if "/" in key:
            parts = [part.strip() for part in key.split("/")]
            if "/" in value:
                value_parts = [part.strip() for part in value.split("/")]

                # Match each key with its corresponding value
                for i, part_key in enumerate(parts):
                    if i < len(value_parts):
                        cleaned_key = self.clean_text(part_key)
                        cleaned_value = self.clean_text(value_parts[i])

                        # Clean units from values (like 'm' from measurements)
                        if cleaned_key and cleaned_value:
                            cleaned_value = self._clean_value_units(cleaned_value)
                            data[cleaned_key] = cleaned_value
            else:
                # If value doesn't have slashes, use same value for all keys
                for part_key in parts:
                    cleaned_key = self.clean_text(part_key)
                    if cleaned_key:
                        cleaned_value = self._clean_value_units(value)
                        data[cleaned_key] = cleaned_value

    def _clean_value_units(self, value: str) -> str:
        """Remove units from values (like 'm' from '488 / 74 m')"""
        cleaned = value.strip()

        # Remove common units
        units_to_remove = ['m', 'kn', '°', 't', 'bbl', 'm³']
        for unit in units_to_remove:
            if cleaned.endswith(unit):
                cleaned = cleaned[:-len(unit)].strip()

        return cleaned

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

    def is_restricted_data(self, element) -> bool:
        """Check if data element is restricted/premium placeholder"""
        if not element:
            return True

        # Check for restricted placeholder icons
        restricted_icons = element.find_all('i', class_=re.compile(r'nd.*ttt[23]', re.I))
        if restricted_icons:
            return True

        # Check for common restricted indicators
        text = self.clean_text(element.get_text())
        restricted_indicators = ['-', 'Restricted', 'Premium', 'Available with PREMIUM']

        return any(indicator.lower() in text.lower() for indicator in restricted_indicators)

    def extract_management_entity(self, entity_name: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract a single management entity (owner, manager, etc.) with nested details"""
        entity_data = {
            "name": "RESTRICTED - PREMIUM DATA",
            "address": "RESTRICTED - PREMIUM DATA",
            "website": "RESTRICTED - PREMIUM DATA",
            "email": "-"
        }

        # Look for the entity name in the table
        entity_cell = soup.find('td', string=re.compile(entity_name, re.I))
        if entity_cell:
            # Find the data cell (usually the next cell or in the same row)
            entity_row = entity_cell.find_parent('tr')
            if entity_row:
                data_cells = entity_row.find_all('td')
                if len(data_cells) >= 2:
                    data_cell = data_cells[1]

                    # Check if data is restricted
                    if self.is_restricted_data(data_cell):
                        return entity_data

                    # Extract actual data
                    entity_text = self.clean_text(data_cell.get_text())
                    if entity_text and entity_text != '-':
                        entity_data["name"] = entity_text

                    # Look for nested table with details (address, website, email)
                    nested_table = data_cell.find('table')
                    if nested_table:
                        nested_data = self.extract_table_data(nested_table)
                        entity_data.update(nested_data)

        return entity_data

    def extract_management_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract management information section"""
        management_data = {}

        # Look for Management section
        management_section = soup.find('h2', string=re.compile(r'MANAGEMENT', re.I))
        if not management_section:
            # Try to find management-related sections
            management_section = soup.find('h2', string=re.compile(r'(Management|Owner|Manager)', re.I))

        if management_section:
            container = management_section.find_parent()
            if container:
                # Extract all management entities
                management_data["registered_owner"] = self.extract_management_entity("Registered Owner", container)
                management_data["manager"] = self.extract_management_entity("Manager", container)
                management_data["ism_manager"] = self.extract_management_entity("ISM Manager", container)

                # Extract other management fields
                table = container.find('table') or container.find_next('table')
                if table:
                    table_data = self.extract_table_data(table)

                    # Add specific management fields
                    management_data["p&i_club"] = table_data.get("P&I Club", "RESTRICTED - PREMIUM DATA")
                    management_data["classification_society"] = table_data.get("Classification Society", "RESTRICTED - PREMIUM DATA")
                    management_data["last_survey"] = table_data.get("Last Survey", "RESTRICTED - PREMIUM DATA")
                    management_data["next_survey"] = table_data.get("Next Survey", "RESTRICTED - PREMIUM DATA")

        return management_data

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

    def scrape_vessel_data(self, html_content: str, url: str) -> Dict[str, Any]:
        """Main scraping function - accepts HTML content directly and returns flattened JSON with nested management"""
        soup = BeautifulSoup(html_content, 'html.parser')
        if not soup:
            return {"error": "Failed to parse HTML content"}

        # Start with flattened structure
        result = {
            "url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            # Extract basic vessel info (flattened)
            print("Extracting basic vessel information...")
            general_info = self.extract_general_ship_info(soup)
            result.update(general_info)

            # Extract vessel particulars (flattened)
            print("Extracting vessel particulars...")
            vessel_particulars = self.extract_vessel_particulars(soup)
            result.update(vessel_particulars)

            # Extract voyage data (flattened)
            print("Extracting voyage data...")
            voyage_data = self.extract_voyage_data(soup)
            result.update(voyage_data)

            # Extract management information (nested - only exception)
            print("Extracting management information...")
            management_data = self.extract_management_info(soup)
            result["management"] = management_data

            # Extract additional table data (flattened)
            print("Extracting additional sections...")
            all_tables = soup.find_all('table')
            for i, table in enumerate(all_tables):
                table_data = self.extract_table_data(table)
                if table_data and len(table_data) > 0:
                    result.update(table_data)

            # Extract ship text/descriptions (flattened)
            print("Extracting text sections...")
            text_sections = self.extract_ship_text_section(soup)
            if text_sections:
                result.update(text_sections)

        except Exception as e:
            result["error"] = f"Error during scraping: {str(e)}"
            print(f"Error during scraping: {e}")

        return result

    def get_flattened_data(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Scrape vessel data from HTML content and return flattened dictionary

        Args:
            html_content: HTML content string to parse
            url: URL for metadata purposes

        Returns:
            Flattened dictionary with all nested data as dot-notation keys
        """
        scraped_data = self.scrape_vessel_data(html_content, url)
        return self.flatten_json(scraped_data)

    def parse_html_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Parse HTML content and return structured vessel data with nested sections

        Args:
            html_content: HTML content string to parse
            url: URL for metadata purposes

        Returns:
            Structured dictionary with nested vessel data sections
        """
        return self.scrape_vessel_data(html_content, url)

