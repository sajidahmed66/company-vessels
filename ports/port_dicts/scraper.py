#!/usr/bin/env python3
"""
MagicPort Port Scraper - CLI Tool
Scrapes port data from https://magicport.ai/ports and stores in MySQL database.

Usage: python scraper.py [start_page] [batch_pages]
"""

import sys
import argparse
import requests
from bs4 import BeautifulSoup
import json
import time
import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Optional, Tuple

# Database configuration (same as existing codebase)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'magic_port_updated',
    'user': 'root',
    'password': 'rootpassword'
}

# Base URL for MagicPort ports
BASE_URL = "https://magicport.ai"
PORTS_URL = f"{BASE_URL}/ports"

# Script directory for relative paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "mc-port-data"
LOG_FILE = SCRIPT_DIR / "port-mp.log"
ERROR_LOG_FILE = SCRIPT_DIR / "port-mp.error.log"


class MagicPortScraper:
    def __init__(self, start_page: int = 1, batch_pages: int = None):
        self.start_page = start_page
        self.batch_pages = batch_pages
        self.session = requests.Session()

        # Setup headers to mimic real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Setup logging
        self.setup_logging()

        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

    def setup_logging(self):
        """Setup logging configuration"""
        # Setup main logger
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Setup error logger
        self.error_logger = logging.getLogger('error_logger')
        self.error_logger.setLevel(logging.ERROR)
        error_handler = logging.FileHandler(ERROR_LOG_FILE, mode='a', encoding='utf-8')
        error_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self.error_logger.addHandler(error_handler)

    def create_database_connection(self) -> Optional[mysql.connector.connection.MySQLConnection]:
        """Create MySQL database connection"""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                self.logger.info("Database connection established")
                return connection
        except Error as e:
            self.logger.error(f"Database connection failed: {e}")
            self.error_logger.error(f"Database connection failed: {e}")
            return None

    def create_table_if_not_exists(self, connection: mysql.connector.connection.MySQLConnection) -> bool:
        """Create port_dicts table if it doesn't exist"""
        try:
            cursor = connection.cursor()

            # Read SQL from file
            sql_file = SCRIPT_DIR.parent.parent / "create_port_dicts_table.sql"
            if sql_file.exists():
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_query = f.read()
            else:
                # Fallback SQL definition
                sql_query = """
                CREATE TABLE IF NOT EXISTS port_dicts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    port_name VARCHAR(255) NOT NULL,
                    country VARCHAR(100) NOT NULL,
                    unlocode VARCHAR(10),
                    url TEXT NOT NULL,
                    is_active TINYINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_port_name (port_name),
                    INDEX idx_country (country),
                    INDEX idx_unlocode (unlocode),
                    INDEX idx_is_active (is_active),
                    UNIQUE KEY unique_port_url (port_name, country, url(255))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """

            cursor.execute(sql_query)
            connection.commit()
            cursor.close()
            self.logger.info("Database table verified/created successfully")
            return True

        except Error as e:
            self.logger.error(f"Error creating table: {e}")
            self.error_logger.error(f"Error creating table: {e}")
            return False

    def get_total_pages(self) -> int:
        """Get total number of pages from MagicPort"""
        try:
            self.logger.info("Determining total pages...")
            response = self.session.get(PORTS_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for pagination information
            # Try multiple selectors to find pagination
            pagination_selectors = [
                'nav.pagination span',
                '.pagination__info',
                '[data-pagination]',
                '.pagination-info'
            ]

            for selector in pagination_selectors:
                pagination_element = soup.select_one(selector)
                if pagination_element:
                    text = pagination_element.get_text().strip()
                    # Look for patterns like "Page 1 of 342" or "1-342"
                    import re
                    match = re.search(r'of\s+(\d+)|/(\d+)', text)
                    if match:
                        total_pages = int(match.group(1) or match.group(2))
                        self.logger.info(f"Found {total_pages} total pages")
                        return total_pages

            # Fallback: Try to find the last page link
            page_links = soup.select('a[href*="page="]')
            if page_links:
                page_numbers = []
                for link in page_links:
                    href = link.get('href', '')
                    import re
                    match = re.search(r'page=(\d+)', href)
                    if match:
                        page_numbers.append(int(match.group(1)))

                if page_numbers:
                    total_pages = max(page_numbers)
                    self.logger.info(f"Found {total_pages} total pages (from page links)")
                    return total_pages

            self.logger.warning("Could not determine total pages, defaulting to 342")
            return 342  # Default as per specification

        except Exception as e:
            self.logger.error(f"Error getting total pages: {e}")
            self.error_logger.error(f"Error getting total pages: {e}")
            return 342  # Default fallback

    def scrape_page(self, page_num: int) -> Tuple[List[Dict], Optional[str]]:
        """Scrape a single page of port data"""
        url = f"{PORTS_URL}?sort_type=asc&page={page_num}"

        try:
            self.logger.info(f"Scraping page {page_num}: {url}")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            ports_data = []

            # Look for port entries - MagicPort uses card__content structure
            # Try multiple selectors to find port entries
            port_selectors = [
                '.card__content',
                '.port-card',
                '.port-item',
                '[data-port]',
                'a[href*="/ports/"]',
                '.card--port'
            ]

            for selector in port_selectors:
                port_elements = soup.select(selector)
                if port_elements:
                    self.logger.info(f"Found {len(port_elements)} port elements using selector: {selector}")

                    for element in port_elements:
                        try:
                            port_data = self.extract_port_data(element)
                            if port_data:
                                ports_data.append(port_data)
                        except Exception as e:
                            self.logger.warning(f"Error extracting port data: {e}")
                            continue

                    if ports_data:  # If we found data, break the selector loop
                        break

            if not ports_data:
                # Fallback: Look for any links to port pages
                port_links = soup.select('a[href*="/ports/"]')
                for link in port_links:
                    try:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)

                        if href and text and len(text) > 3:
                            # Extract country from URL if possible
                            url_parts = href.strip('/').split('/')
                            country = "Unknown"
                            if len(url_parts) >= 3:
                                country = url_parts[-2].replace('-', ' ').title()

                            port_data = {
                                'port_name': text,
                                'country': country,
                                'unlocode': '',
                                'url': BASE_URL + href if href.startswith('/') else href
                            }
                            ports_data.append(port_data)
                    except Exception as e:
                        continue

            self.logger.info(f"Extracted {len(ports_data)} ports from page {page_num}")
            return ports_data, url

        except requests.RequestException as e:
            error_msg = f"Network error scraping page {page_num}: {e}"
            self.logger.error(error_msg)
            self.error_logger.error(error_msg)
            return [], url
        except Exception as e:
            error_msg = f"Unexpected error scraping page {page_num}: {e}"
            self.logger.error(error_msg)
            self.error_logger.error(error_msg)
            return [], url

    def extract_port_data(self, element) -> Optional[Dict]:
        """Extract port data from a single HTML element"""
        try:
            # Get the main link - could be the element itself or a child
            link = element.find('a') if element.name != 'a' else element
            href = link.get('href', '') if link else ''

            # If no link found in element, try to find the parent/ancestor link
            if not href:
                parent_link = element.find_parent('a')
                if parent_link:
                    href = parent_link.get('href', '')

            if not href:
                # As a last resort, construct URL from port data if we have enough info
                # This might happen if we have card content without direct link
                port_name = element.select_one('.card__title')
                if port_name:
                    port_name_text = port_name.get_text(strip=True).lower().replace(' ', '-').replace("'", "")
                    country = element.select_one('.badge--gray')
                    country_text = country.get_text(strip=True).lower().replace(' ', '-') if country else 'unknown'
                    unlocode = element.select_one('.badge--warning')
                    unlocode_text = unlocode.get_text(strip=True).lower() if unlocode else ''
                    if unlocode_text:
                        href = f"/ports/{country_text}/{port_name_text}-port-{unlocode_text}"
                else:
                    return None

            # Extract port name
            port_name = ""
            name_selectors = ['.card__title', 'h3', '.port-name', 'h4', '.title']
            for selector in name_selectors:
                name_elem = element.select_one(selector)
                if name_elem:
                    port_name = name_elem.get_text(strip=True)
                    break

            if not port_name:
                port_name = link.get_text(strip=True)

            # Extract country - look for gray badge specifically
            country = ""
            country_elem = element.select_one('.badge--gray')
            if country_elem:
                country = country_elem.get_text(strip=True)

            # Fallback to broader badge search if gray badge not found
            if not country:
                country_selectors = ['.country', '.badge', '.tag', '[data-country]']
                for selector in country_selectors:
                    country_elem = element.select_one(selector)
                    if country_elem:
                        country = country_elem.get_text(strip=True)
                        # Make sure it's not the UNLOCODE badge (usually 5 characters)
                        if len(country) > 5:  # Countries are usually longer than UNLOCODEs
                            break

            # Extract UNLOCODE - look for warning badge specifically (contains UNLOCODE)
            unlocode = ""
            unlocode_elem = element.select_one('.badge--warning')
            if unlocode_elem:
                unlocode = unlocode_elem.get_text(strip=True)

            # Fallback to extract from URL if not found in HTML
            if not unlocode:
                import re
                match = re.search(r'-([a-z]{2}[a-z0-9]{3})$', href)
                if match:
                    unlocode = match.group(1).upper()

            # Construct full URL
            full_url = BASE_URL + href if href.startswith('/') else href

            return {
                'port_name': port_name,
                'country': country,
                'unlocode': unlocode,
                'url': full_url
            }

        except Exception as e:
            self.logger.warning(f"Error extracting port data from element: {e}")
            return None

    def save_json_data(self, page_num: int, ports_data: List[Dict], url: str):
        """Save port data to JSON file"""
        json_data = {
            'page': page_num,
            'url': url,
            'data': ports_data,
            'scraped_at': datetime.now().isoformat()
        }

        filename = DATA_DIR / f"page_{page_num}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"JSON data saved to {filename}")
        except Exception as e:
            error_msg = f"Error saving JSON data for page {page_num}: {e}"
            self.logger.error(error_msg)
            self.error_logger.error(error_msg)

    def insert_data_to_database(self, ports_data: List[Dict]) -> int:
        """Insert port data into database with retry mechanism"""
        if not ports_data:
            return 0

        connection = self.create_database_connection()
        if not connection:
            return 0

        inserted_count = 0

        try:
            cursor = connection.cursor()

            insert_query = """
            INSERT INTO port_dicts (port_name, country, unlocode, url, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            country = VALUES(country),
            unlocode = VALUES(unlocode),
            updated_at = CURRENT_TIMESTAMP
            """

            for port in ports_data:
                try:
                    values = (
                        port['port_name'],
                        port['country'],
                        port['unlocode'],
                        port['url'],
                        0  # is_active default
                    )

                    cursor.execute(insert_query, values)
                    inserted_count += 1

                except Error as e:
                    error_msg = f"Error inserting port '{port['port_name']}': {e}"
                    self.logger.warning(error_msg)
                    self.error_logger.error(error_msg)
                    continue

            connection.commit()
            cursor.close()

        except Exception as e:
            error_msg = f"Database operation failed: {e}"
            self.logger.error(error_msg)
            self.error_logger.error(error_msg)
            if connection:
                connection.rollback()
        finally:
            if connection and connection.is_connected():
                connection.close()

        return inserted_count

    def run(self) -> int:
        """Main execution method"""
        self.logger.info(f"Starting MagicPort scraper from page {self.start_page}")

        # Validate database connection
        connection = self.create_database_connection()
        if not connection:
            self.logger.error("Cannot proceed without database connection")
            return 1
        connection.close()

        # Create table if not exists
        connection = self.create_database_connection()
        if not connection:
            return 1

        if not self.create_table_if_not_exists(connection):
            connection.close()
            return 1
        connection.close()

        # Get total pages
        total_pages = self.get_total_pages()

        # Calculate end page
        if self.batch_pages:
            end_page = min(self.start_page + self.batch_pages - 1, total_pages)
        else:
            end_page = total_pages

        self.logger.info(f"Scraping pages {self.start_page} to {end_page} of {total_pages}")

        total_inserted = 0

        # Process each page
        for page_num in range(self.start_page, end_page + 1):
            try:
                # Scrape page data
                ports_data, url = self.scrape_page(page_num)

                if not ports_data:
                    self.logger.warning(f"No data found on page {page_num}")
                    continue

                # Save JSON backup
                self.save_json_data(page_num, ports_data, url)

                # Insert to database with retry
                inserted = self.insert_data_to_database(ports_data)
                total_inserted += inserted

                # Log progress
                batch_info = f"Batch {((page_num - self.start_page) // 10) + 1}" if self.batch_pages else "Main"
                self.logger.info(f"[{batch_info}] Page {page_num} completed: {inserted} records inserted")

                # Rate limiting - 3 second delay
                if page_num < end_page:
                    time.sleep(3)

            except KeyboardInterrupt:
                self.logger.info("Scraping interrupted by user")
                return 0
            except Exception as e:
                error_msg = f"Unexpected error processing page {page_num}: {e}"
                self.logger.error(error_msg)
                self.error_logger.error(error_msg)
                continue

        self.logger.info(f"Scraping completed. Total records inserted: {total_inserted}")
        return 0


def main():
#     """Main entry point"""
#     parser = argparse.ArgumentParser(
#         description='MagicPort Port Scraper - Scrape port data from magicport.ai',
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
# Examples:
#   python scraper.py                    # Scrape all pages
#   python scraper.py 50                 # Start from page 50
#   python scraper.py 1 10              # Scrape pages 1-10
#   python scraper.py 100 5             # Scrape pages 100-104
#         """
#     )
#
#     parser.add_argument(
#         'start_page',
#         nargs='?',
#         type=int,
#         default=1,
#         help='Page number to start scraping from (default: 1)'
#     )
#
#     parser.add_argument(
#         'batch_pages',
#         nargs='?',
#         type=int,
#         help='Number of pages to scrape in this batch (default: all remaining pages)'
#     )
#
#     args = parser.parse_args()
#
#     # Validate arguments
#     if args.start_page < 1:
#         print("Error: start_page must be greater than 0", file=sys.stderr)
#         return 2
#
#     if args.batch_pages is not None and args.batch_pages < 1:
#         print("Error: batch_pages must be greater than 0", file=sys.stderr)
#         return 3
#
    # Create and run scraper
    scraper = MagicPortScraper(
        start_page=100,
        batch_pages=350
    )

    try:
        exit_code = scraper.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()