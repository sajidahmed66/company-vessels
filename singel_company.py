#!/usr/bin/env python3
"""
Enhanced MagicPort Fleet Data Scraper with Database Integration
Usage: python enhanced_scraper.py --company-id 123 --company-name "Neptune Navigators" --company-url "https://..."

Installation:
pip install playwright beautifulsoup4 mysql-connector-python  # or psycopg2 for PostgreSQL
playwright install
"""

import json
import re
import time
import sys
import os
import asyncio
import argparse
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import mysql.connector  # Change to psycopg2 for PostgreSQL
from mysql.connector import Error


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'


class DatabaseManager:
    def __init__(self, db_config):
        self.db_config = db_config
        self.connection = None

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                print(f"{Colors.GREEN}Connected to database{Colors.NC}")
                # Auto-create tables if they don't exist
                self.create_tables_if_not_exist()
                return True
        except Error as e:
            print(f"{Colors.RED}Database connection error: {e}{Colors.NC}")
            return False

    def create_tables_if_not_exist(self):
        """Create database tables if they don't exist"""
        try:
            cursor = self.connection.cursor()

            # Create company_details table
            # company_details_sql = """
            #                       CREATE TABLE IF NOT EXISTS vessel_companies \
            #                       ( \
            #                           id \
            #                           INT \
            #                           AUTO_INCREMENT \
            #                           PRIMARY \
            #                           KEY, \
            #                           company_id \
            #                           INT \
            #                           NOT \
            #                           NULL, \
            #                           company_name \
            #                           VARCHAR \
            #                       ( \
            #                           255 \
            #                       ),
            #                           company_address TEXT,
            #                           total_dwt DECIMAL \
            #                       ( \
            #                           15, \
            #                           2 \
            #                       ),
            #                           fleet_count INT,
            #                           company_website VARCHAR \
            #                       ( \
            #                           500 \
            #                       ),
            #                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            #                           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            #                           INDEX idx_company_id \
            #                       ( \
            #                           company_id \
            #                       )
            #                           ) \
            #                       """


            # Create company_details table
            company_details_sql = """
                                  CREATE TABLE IF NOT EXISTS vessel_companies \
                                  ( \
                                      id \
                                      BIGINT \
                                      UNSIGNED \
                                      AUTO_INCREMENT \
                                      PRIMARY \
                                      KEY, \
                                      name \
                                      VARCHAR \
                                  ( \
                                      255 \
                                  ) \
                                      NOT \
                                      NULL, \
                                      country \
                                      VARCHAR \
                                  ( \
                                      255 \
                                  ),
                                      description TEXT,
                                      address TEXT NOT NULL,
                                      phone VARCHAR \
                                  ( \
                                      255 \
                                  ),
                                      email VARCHAR \
                                  ( \
                                      255 \
                                  ),
                                      website VARCHAR \
                                  ( \
                                      255 \
                                  ),
                                      established YEAR,
                                      type VARCHAR \
                                  ( \
                                      255 \
                                  ),
                                      number_of_employees VARCHAR \
                                  ( \
                                      255 \
                                  ),
                                      total_dwt DECIMAL \
                                  ( \
                                      15, \
                                      2 \
                                  ),
                                      fleet_count INT,
                                      others_data JSON,
                                      created_by BIGINT UNSIGNED,
                                      updated_by BIGINT UNSIGNED,
                                      deleted_by BIGINT UNSIGNED,
                                      created_at TIMESTAMP NULL,
                                      updated_at TIMESTAMP NULL,
                                      deleted_at TIMESTAMP NULL
                                      ) \
                                  COLLATE = utf8mb4_unicode_ci \
                                  """

            cursor.execute(company_details_sql)

            # Create company_fleet_vessels table
            fleet_vessels_sql = """
                                CREATE TABLE IF NOT EXISTS company_fleet_vessels \
                                ( \
                                    id \
                                    INT \
                                    AUTO_INCREMENT \
                                    PRIMARY \
                                    KEY, \
                                    company_id \
                                    INT \
                                    NOT \
                                    NULL, \
                                    vessel_imo \
                                    BIGINT, \
                                    vessel_mmsi \
                                    BIGINT, \
                                    vessel_name \
                                    VARCHAR \
                                ( \
                                    255 \
                                ),
                                    vessel_type VARCHAR \
                                ( \
                                    100 \
                                ),
                                    registered_owner VARCHAR \
                                ( \
                                    255 \
                                ),
                                    registered_owner_company_imo BIGINT,
                                    registered_owner_company_country_slug VARCHAR \
                                ( \
                                    100 \
                                ),
                                    registered_owner_company_name_slug VARCHAR \
                                ( \
                                    255 \
                                ),
                                    registered_owner_total_distinct_vessels INT,
                                    commercial_manager VARCHAR \
                                ( \
                                    255 \
                                ),
                                    commercial_manager_company_country_slug VARCHAR \
                                ( \
                                    100 \
                                ),
                                    commercial_manager_company_imo BIGINT,
                                    commercial_manager_company_name_slug VARCHAR \
                                ( \
                                    255 \
                                ),
                                    commercial_manager_total_distinct_vessels INT,
                                    core_vessel_types_key VARCHAR \
                                ( \
                                    100 \
                                ),
                                    core_vessel_types_name VARCHAR \
                                ( \
                                    100 \
                                ),
                                    dwt DECIMAL \
                                ( \
                                    15, \
                                    2 \
                                ),
                                    flag VARCHAR \
                                ( \
                                    10 \
                                ),
                                    ism_manager VARCHAR \
                                ( \
                                    255 \
                                ),
                                    ism_manager_company_country_slug VARCHAR \
                                ( \
                                    100 \
                                ),
                                    ism_manager_company_imo BIGINT,
                                    ism_manager_company_name_slug VARCHAR \
                                ( \
                                    255 \
                                ),
                                    ism_manager_total_distinct_vessels INT,
                                    last_position_update VARCHAR(255),
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                    INDEX idx_company_id \
                                ( \
                                    company_id \
                                ),
                                    INDEX idx_vessel_imo \
                                ( \
                                    vessel_imo \
                                ),
                                    INDEX idx_vessel_mmsi \
                                ( \
                                    vessel_mmsi \
                                ),
                                    UNIQUE KEY unique_company_vessel \
                                ( \
                                    company_id, \
                                    vessel_imo \
                                )
                                    ) \
                                """
            cursor.execute(fleet_vessels_sql)

            self.connection.commit()
            cursor.close()
            print(f"{Colors.GREEN}Database tables verified/created{Colors.NC}")

        except Error as e:
            print(f"{Colors.YELLOW}Warning: Could not create tables: {e}{Colors.NC}")
            print(f"{Colors.YELLOW}Please create tables manually using the provided schema{Colors.NC}")

    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print(f"{Colors.YELLOW}Database connection closed{Colors.NC}")

    def insert_company_details(self, company_id, company_data):
        """Insert or update company details"""
        try:
            cursor = self.connection.cursor()

            # Ensure required fields have default values
            company_name = company_data.get('company_name') or 'Unknown Company'
            address = company_data.get('address') or 'Address not provided'

            # Check if company details already exist by name
            check_query = "SELECT id FROM vessel_companies WHERE name = %s"
            cursor.execute(check_query, (company_name,))
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                update_query = """
                               UPDATE vessel_companies
                               SET name = %s, \
                                   country = %s, \
                                   address = %s, \
                                   total_dwt = %s, \
                                   fleet_count = %s, \
                                   website = %s, \
                                   updated_at = NOW()
                               WHERE name = %s \
                               """
                cursor.execute(update_query, (
                    company_name,
                    company_data.get('country'),
                    address,
                    company_data.get('total_dwt'),
                    company_data.get('total_vessels'),
                    company_data.get('website'),
                    company_name
                ))
                print(f"{Colors.YELLOW}Updated existing company details for: {company_name}{Colors.NC}")
                return existing[0]  # Return existing company ID
            else:
                # Insert new record
                insert_query = """
                               INSERT INTO vessel_companies
                               (name, country, address, total_dwt, fleet_count, website, created_at, updated_at)
                               VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW()) \
                               """
                cursor.execute(insert_query, (
                    company_name,
                    company_data.get('country'),
                    address,
                    company_data.get('total_dwt'),
                    company_data.get('total_vessels'),
                    company_data.get('website')
                ))
                new_company_id = cursor.lastrowid
                print(f"{Colors.GREEN}Inserted new company details for: {company_name} (ID: {new_company_id}){Colors.NC}")

            self.connection.commit()
            cursor.close()
            return new_company_id if not existing else existing[0]

        except Error as e:
            print(f"{Colors.RED}Error inserting company details: {e}{Colors.NC}")
            self.connection.rollback()
            return False

    def get_company_name(self, company_id):
        """Get company name by company_id"""
        try:
            cursor = self.connection.cursor()
            query = "SELECT name FROM vessel_companies WHERE id = %s"
            cursor.execute(query, (company_id,))
            result = cursor.fetchone()
            cursor.close()
            print(f"{Colors.GREEN}Company name: {result[0]}{Colors.NC}")
            return result[0] if result else None
        except Error as e:
            print(f"{Colors.RED}Error fetching company name: {e}{Colors.NC}")
            return None

    def find_vessel_by_imo(self, vessel_imo):
        """Find existing vessel by IMO number"""
        try:
            cursor = self.connection.cursor()
            query = """
                    SELECT id, company_id, registered_owner 
                    FROM company_fleet_vessels 
                    WHERE vessel_imo = %s
                    """
            cursor.execute(query, (vessel_imo,))
            result = cursor.fetchone()
            cursor.close()
            return result if result else None
        except Error as e:
            print(f"{Colors.RED}Error finding vessel by IMO: {e}{Colors.NC}")
            return None

    def insert_fleet_vessels(self, company_id, vessels_data):
        """Insert fleet vessels data with duplicate handling"""
        try:
            cursor = self.connection.cursor()

            # Get company name for current company_id
            # current_company_name = self.get_company_name(company_id)
            # if not current_company_name:
            #     print(f"{Colors.RED}Could not find company name for ID: {company_id}{Colors.NC}")
            #     return False

            # Clear existing vessels for this company only
            # delete_query = "DELETE FROM company_fleet_vessels WHERE company_id = %s"
            # cursor.execute(delete_query, (company_id,))

            insert_query = """
                           INSERT INTO company_fleet_vessels (company_id, vessel_imo, vessel_mmsi, vessel_name, \
                                                              vessel_type, \
                                                              registered_owner, registered_owner_company_imo, \
                                                              registered_owner_company_country_slug, \
                                                              registered_owner_total_distinct_vessels, \
                                                              commercial_manager, \
                                                              commercial_manager_company_country_slug, \
                                                              commercial_manager_company_imo, \
                                                              commercial_manager_company_name_slug, \
                                                              commercial_manager_total_distinct_vessels, \
                                                              core_vessel_types_key, core_vessel_types_name, dwt, flag, \
                                                              ism_manager, ism_manager_company_country_slug, \
                                                              ism_manager_company_imo, \
                                                              ism_manager_company_name_slug, \
                                                              ism_manager_total_distinct_vessels, \
                                                              last_position_update) \
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, \
                                   %s, %s, %s) \
                           """

            vessels_inserted = 0
            vessels_updated = 0
            
            for vessel in vessels_data:
                vessel_imo = vessel.get('vessel_imo')
                if not vessel_imo:
                    continue
                    
                # Check if vessel already exists by IMO
                existing_vessel = self.find_vessel_by_imo(vessel_imo)
                
                # Extract clean vessel name from HTML
                vessel_name = DatabaseManager.extract_vessel_name(vessel.get('vessel_name', ''))
                
                if existing_vessel:
                    # Vessel exists, check if company names match
                    # existing_vessel_id, existing_company_id, registered_owner = existing_vessel
                    registered_owner = vessel.get('registered_owner')
                    current_company_name = self.get_company_name(company_id)
                    # Compare current company name with registered owner
                    if (registered_owner and current_company_name and
                        registered_owner.lower().strip() == current_company_name.lower().strip()):
                        # Company names match, update with current company_id
                        update_query = """
                                      UPDATE company_fleet_vessels 
                                      SET company_id = %s,
                                          vessel_mmsi = %s,
                                          vessel_name = %s,
                                          vessel_type = %s,
                                          registered_owner = %s,
                                          registered_owner_company_imo = %s,
                                          registered_owner_company_country_slug = %s,
                                          registered_owner_total_distinct_vessels = %s,
                                          commercial_manager = %s,
                                          commercial_manager_company_country_slug = %s,
                                          commercial_manager_company_imo = %s,
                                          commercial_manager_company_name_slug = %s,
                                          commercial_manager_total_distinct_vessels = %s,
                                          core_vessel_types_key = %s,
                                          core_vessel_types_name = %s,
                                          dwt = %s,
                                          flag = %s,
                                          ism_manager = %s,
                                          ism_manager_company_country_slug = %s,
                                          ism_manager_company_imo = %s,
                                          ism_manager_company_name_slug = %s,
                                          ism_manager_total_distinct_vessels = %s,
                                          last_position_update = %s,
                                          updated_at = NOW()
                                      WHERE vessel_imo = %s
                                      """
                        cursor.execute(update_query, (
                            company_id,
                            vessel.get('vessel_mmsi'),
                            vessel_name,
                            vessel.get('vessel_type'),
                            vessel.get('registered_owner'),
                            vessel.get('registered_owner_company_imo'),
                            vessel.get('registered_owner_company_country_slug'),
                            vessel.get('registered_owner_total_distinct_vessels'),
                            vessel.get('commercial_manager'),
                            vessel.get('commercial_manager_company_country_slug'),
                            vessel.get('commercial_manager_company_imo'),
                            vessel.get('commercial_manager_company_name_slug'),
                            vessel.get('commercial_manager_total_distinct_vessels'),
                            vessel.get('core_vessel_types_key'),
                            vessel.get('core_vessel_types_name'),
                            vessel.get('dwt'),
                            vessel.get('flag'),
                            vessel.get('ism_manager'),
                            vessel.get('ism_manager_company_country_slug'),
                            vessel.get('ism_manager_company_imo'),
                            vessel.get('ism_manager_company_name_slug'),
                            vessel.get('ism_manager_total_distinct_vessels'),
                            vessel.get('last_position_update'),
                            vessel_imo
                        ))
                        vessels_updated += 1
                        print(f"{Colors.YELLOW}Updated vessel IMO {vessel_imo} - company name matches registered owner{Colors.NC}")
                    else:
                        # Company names don't match, update other data but keep existing company_id
                        update_query = """
                                      UPDATE company_fleet_vessels 
                                      SET vessel_mmsi = %s,
                                          vessel_name = %s,
                                          vessel_type = %s,
                                          registered_owner = %s,
                                          registered_owner_company_imo = %s,
                                          registered_owner_company_country_slug = %s,
                                          registered_owner_total_distinct_vessels = %s,
                                          commercial_manager = %s,
                                          commercial_manager_company_country_slug = %s,
                                          commercial_manager_company_imo = %s,
                                          commercial_manager_company_name_slug = %s,
                                          commercial_manager_total_distinct_vessels = %s,
                                          core_vessel_types_key = %s,
                                          core_vessel_types_name = %s,
                                          dwt = %s,
                                          flag = %s,
                                          ism_manager = %s,
                                          ism_manager_company_country_slug = %s,
                                          ism_manager_company_imo = %s,
                                          ism_manager_company_name_slug = %s,
                                          ism_manager_total_distinct_vessels = %s,
                                          last_position_update = %s,
                                          updated_at = NOW()
                                      WHERE vessel_imo = %s
                                      """
                        cursor.execute(update_query, (
                            vessel.get('vessel_mmsi'),
                            vessel_name,
                            vessel.get('vessel_type'),
                            vessel.get('registered_owner'),
                            vessel.get('registered_owner_company_imo'),
                            vessel.get('registered_owner_company_country_slug'),
                            vessel.get('registered_owner_total_distinct_vessels'),
                            vessel.get('commercial_manager'),
                            vessel.get('commercial_manager_company_country_slug'),
                            vessel.get('commercial_manager_company_imo'),
                            vessel.get('commercial_manager_company_name_slug'),
                            vessel.get('commercial_manager_total_distinct_vessels'),
                            vessel.get('core_vessel_types_key'),
                            vessel.get('core_vessel_types_name'),
                            vessel.get('dwt'),
                            vessel.get('flag'),
                            vessel.get('ism_manager'),
                            vessel.get('ism_manager_company_country_slug'),
                            vessel.get('ism_manager_company_imo'),
                            vessel.get('ism_manager_company_name_slug'),
                            vessel.get('ism_manager_total_distinct_vessels'),
                            vessel.get('last_position_update'),
                            vessel_imo
                        ))
                        vessels_updated += 1
                        # print(f"{Colors.YELLOW}Updated vessel IMO {vessel_imo} data - kept existing company_id {existing_company_id}{Colors.NC}")
                else:
                    # Vessel doesn't exist, create new record
                    cursor.execute(insert_query, (
                        company_id,
                        vessel.get('vessel_imo'),
                        vessel.get('vessel_mmsi'),
                        vessel_name,
                        vessel.get('vessel_type'),
                        vessel.get('registered_owner'),
                        vessel.get('registered_owner_company_imo'),
                        vessel.get('registered_owner_company_country_slug'),
                        vessel.get('registered_owner_total_distinct_vessels'),
                        vessel.get('commercial_manager'),
                        vessel.get('commercial_manager_company_country_slug'),
                        vessel.get('commercial_manager_company_imo'),
                        vessel.get('commercial_manager_company_name_slug'),
                        vessel.get('commercial_manager_total_distinct_vessels'),
                        vessel.get('core_vessel_types_key'),
                        vessel.get('core_vessel_types_name'),
                        vessel.get('dwt'),
                        vessel.get('flag'),
                        vessel.get('ism_manager'),
                        vessel.get('ism_manager_company_country_slug'),
                        vessel.get('ism_manager_company_imo'),
                        vessel.get('ism_manager_company_name_slug'),
                        vessel.get('ism_manager_total_distinct_vessels'),
                        vessel.get('last_position_update')
                    ))
                    vessels_inserted += 1

            self.connection.commit()
            cursor.close()
            print(f"{Colors.GREEN}Processed vessels for company ID {company_id}: {vessels_inserted} inserted, {vessels_updated} updated{Colors.NC}")
            return True

        except Error as e:
            print(f"{Colors.RED}Error inserting fleet vessels: {e}{Colors.NC}")
            self.connection.rollback()
            return False

    @staticmethod
    def extract_vessel_name(vessel_name_html):
        """Extract clean vessel name from HTML"""
        if not vessel_name_html:
            return None

        soup = BeautifulSoup(vessel_name_html, 'html.parser')
        span = soup.find('span')
        if span:
            return span.get_text(strip=True)

        # Fallback: try to extract text from the entire HTML
        return soup.get_text(strip=True)


class EnhancedMagicPortScraper:
    def __init__(self, company_id, company_name, company_url, db_config, headless=True):
        self.company_id = company_id
        self.company_name = company_name
        self.company_url = company_url
        self.headless = headless
        self.base_url = "https://magicport.ai"

        # Database manager
        self.db_manager = DatabaseManager(db_config)

        # Extract company slug from URL for file naming
        parsed_url = urlparse(self.company_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) >= 3:
            self.company_slug = path_parts[-1]
        else:
            self.company_slug = company_name.lower().replace(' ', '-')

    def log(self, message, color=Colors.NC):
        print(f"{color}{message}{Colors.NC}")

    async def setup_browser(self):
        """Initialize browser with anti-detection settings"""
        self.playwright = await async_playwright().start()

        # Launch browser with realistic settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        # Create context with realistic user agent and viewport
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York'
        )

        # Create page
        self.page = await self.context.new_page()

        # Add extra stealth measures
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            window.chrome = {
                runtime: {},
            };
        """)

    async def establish_session(self):
        """Step 0: Visit homepage first to establish session"""
        self.log("Step 0: Establishing session...", Colors.YELLOW)

        try:
            # Navigate to homepage with realistic behavior - increased timeout
            self.log(f"Connecting to {self.base_url}...", Colors.YELLOW)
            await self.page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for page to be ready
            await asyncio.sleep(3)
            
            # Try to wait for network idle with fallback
            try:
                await self.page.wait_for_load_state('networkidle', timeout=15000)
            except:
                self.log("Network idle timeout, continuing anyway...", Colors.YELLOW)

            # Simulate human behavior - scroll a bit
            await self.page.evaluate("window.scrollTo(0, 100)")
            await asyncio.sleep(2)

            self.log("Session established successfully", Colors.GREEN)
            return True

        except Exception as e:
            self.log(f"Error establishing session: {e}", Colors.RED)
            self.log("This could be due to network issues or site blocking", Colors.YELLOW)
            return False

    async def extract_company_info(self):
        """Extract company information from the current page"""
        self.log("Extracting company information...", Colors.YELLOW)

        try:
            # Get page HTML content
            html_content = await self.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            company_info = {
                'company_name': None,
                'address': None,
                'country': None,
                'total_vessels': None,
                'total_dwt': None,
                'website': None
            }

            # Extract company name from title or h1
            title_element = soup.find('h1', class_='single__header-title')
            if title_element:
                company_info['company_name'] = title_element.get_text(strip=True)

            # Extract vessel count using Playwright for dynamic content
            vessel_count = await self.page.evaluate("""
                () => {
                    // Look for elements with data-counter attribute containing vessel count
                    const statsCards = document.querySelectorAll('.card--stats-2');
                    for (let card of statsCards) {
                        const title = card.querySelector('h3');
                        if (title && title.textContent.includes('Total Vessels')) {
                            const counter = card.querySelector('[data-counter]');
                            if (counter) {
                                return counter.getAttribute('data-counter');
                            }
                        }
                    }
                    return null;
                }
            """)
            if vessel_count:
                company_info['total_vessels'] = vessel_count

            # Extract DWT using Playwright
            dwt_count = await self.page.evaluate("""
                () => {
                    const statsCards = document.querySelectorAll('.card--stats-2');
                    for (let card of statsCards) {
                        const title = card.querySelector('h3');
                        if (title && title.textContent.includes('Total DWT')) {
                            const counter = card.querySelector('[data-counter]');
                            if (counter) {
                                return counter.getAttribute('data-counter');
                            }
                        }
                    }
                    return null;
                }
            """)
            if dwt_count:
                company_info['total_dwt'] = dwt_count

            # Extract website and address from contact information
            contact_info = await self.page.evaluate("""
                () => {
                    const listItems = document.querySelectorAll('li.list__item');
                    const info = { website: null, address: null };

                    for (let item of listItems) {
                        const icon = item.querySelector('svg use');
                        const label = item.querySelector('.list__item-label');

                        if (icon && label) {
                            const iconHref = icon.getAttribute('xlink:href') || '';
                            const text = label.textContent.trim();

                            // Check for website (world icon or http text)
                            if (iconHref.includes('world') || text.startsWith('http')) {
                                info.website = text;
                            }

                            // Check for address (map icon)
                            if (iconHref.includes('map')) {
                                info.address = text;
                            }
                        }
                    }

                    return info;
                }
            """)

            if contact_info['website']:
                company_info['website'] = contact_info['website']
            if contact_info['address']:
                company_info['address'] = contact_info['address']

            # Extract country from breadcrumb or URL
            current_url = self.page.url
            url_parts = current_url.split('/')
            if 'owners-managers' in url_parts:
                try:
                    country_index = url_parts.index('owners-managers') + 1
                    if country_index < len(url_parts):
                        country_slug = url_parts[country_index]
                        # Convert slug to proper country name
                        country_name = country_slug.replace('-', ' ').title()
                        company_info['country'] = country_name
                except:
                    pass

            # Clean up the data
            for key, value in company_info.items():
                if isinstance(value, str):
                    company_info[key] = value.strip()

            # Store as instance variable for database saving
            self.company_info = company_info

            # Print company information
            self.print_company_info(company_info)

            return company_info

        except Exception as e:
            self.log(f"Error extracting company info: {e}", Colors.RED)
            return None

    def print_company_info(self, company_info):
        """Print the extracted company information in a formatted way"""
        print("\n" + "=" * 60)
        print(f"{Colors.GREEN}COMPANY INFORMATION{Colors.NC}")
        print("=" * 60)

        print(f"Company Name: {Colors.YELLOW}{company_info.get('company_name') or 'Not found'}{Colors.NC}")
        print(f"Address: {Colors.YELLOW}{company_info.get('address') or 'Not found'}{Colors.NC}")
        print(f"Country: {Colors.YELLOW}{company_info.get('country') or 'Not found'}{Colors.NC}")
        print(f"Total Vessels: {Colors.YELLOW}{company_info.get('total_vessels') or 'Not found'}{Colors.NC}")
        print(f"Total DWT: {Colors.YELLOW}{company_info.get('total_dwt') or 'Not found'}{Colors.NC}")
        print(f"Website: {Colors.YELLOW}{company_info.get('website') or 'Not found'}{Colors.NC}")

        print("=" * 60 + "\n")

    async def fetch_company_page(self):
        """Step 1: Navigate to company page and extract CSRF token and fleet route"""
        self.log("Step 1: Fetching company page...", Colors.YELLOW)

        try:
            # Navigate to company page with more robust settings
            self.log(f"Navigating to: {self.company_url}", Colors.YELLOW)

            # Try multiple wait strategies
            try:
                await self.page.goto(self.company_url, wait_until='domcontentloaded', timeout=60000)
                await self.page.wait_for_load_state('networkidle', timeout=30000)
            except Exception as e:
                self.log(f"Network idle timeout, trying basic load: {e}", Colors.YELLOW)
                await self.page.goto(self.company_url, wait_until='commit', timeout=60000)
                await asyncio.sleep(5)

            # Check if page loaded successfully
            current_url = self.page.url
            self.log(f"Current URL: {current_url}", Colors.YELLOW)

            # Get page title for debugging
            title = await self.page.title()
            self.log(f"Page title: {title}", Colors.YELLOW)

            # Check for error pages or redirects
            if "404" in title.lower() or "not found" in title.lower():
                self.log("Page not found - check URL", Colors.RED)
                return None, None

            # Wait a bit for any dynamic content
            await asyncio.sleep(3)

            # Extract company information here
            await self.extract_company_info()

            # Extract CSRF token using multiple methods
            csrf_token = None

            # Method 1: Look for meta tag
            try:
                csrf_element = await self.page.query_selector('meta[name="csrf-token"]')
                if csrf_element:
                    csrf_token = await csrf_element.get_attribute('content')
                    self.log(f"CSRF token found via meta tag: {csrf_token[:20]}...", Colors.GREEN)
            except:
                pass

            # Method 2: Look for _token meta tag
            if not csrf_token:
                try:
                    csrf_element = await self.page.query_selector('meta[name="_token"]')
                    if csrf_element:
                        csrf_token = await csrf_element.get_attribute('content')
                        self.log(f"CSRF token found via _token meta tag: {csrf_token[:20]}...", Colors.GREEN)
                except:
                    pass

            # Method 3: Extract from JavaScript
            if not csrf_token:
                try:
                    csrf_token = await self.page.evaluate("""
                        () => {
                            // Look for common CSRF token patterns in scripts
                            const scripts = document.querySelectorAll('script');
                            for (let script of scripts) {
                                if (script.textContent) {
                                    const csrfMatch = script.textContent.match(/csrf[_-]?token["\']?\\s*[:=]\\s*["']([^"']+)["']/i);
                                    if (csrfMatch) return csrfMatch[1];

                                    const tokenMatch = script.textContent.match(/_token["\']?\\s*[:=]\\s*["']([^"']+)["']/i);
                                    if (tokenMatch) return tokenMatch[1];
                                }
                            }

                            // Look for window variables
                            if (window.Laravel && window.Laravel.csrfToken) {
                                return window.Laravel.csrfToken;
                            }

                            // Look for other common patterns
                            if (window.csrfToken) return window.csrfToken;
                            if (window._token) return window._token;

                            return null;
                        }
                    """)
                    if csrf_token:
                        self.log(f"CSRF token found in JavaScript: {csrf_token[:20]}...", Colors.GREEN)
                except:
                    pass

            # Method 4: Look for hidden input fields
            if not csrf_token:
                try:
                    csrf_input = await self.page.query_selector('input[name*="csrf"], input[name*="_token"]')
                    if csrf_input:
                        csrf_token = await csrf_input.get_attribute('value')
                        self.log(f"CSRF token found in input field: {csrf_token[:20]}...", Colors.GREEN)
                except:
                    pass

            # If still no token, continue without token
            if not csrf_token:
                self.log("Warning: Could not extract CSRF token, continuing anyway...", Colors.YELLOW)
                csrf_token = ""

            # Extract fleet route
            fleet_route = None
            try:
                fleet_element = await self.page.query_selector('[data-route*="fleet"]')
                if fleet_element:
                    fleet_route = await fleet_element.get_attribute('data-route')
                    self.log(f"Fleet route: {fleet_route}", Colors.GREEN)
                else:
                    # Look for any data-route attributes
                    routes = await self.page.evaluate("""
                        () => {
                            const elements = document.querySelectorAll('[data-route]');
                            return Array.from(elements).map(el => el.getAttribute('data-route'));
                        }
                    """)

                    self.log("Fleet route not found. Available data-routes:", Colors.YELLOW)
                    for route in routes[:5]:
                        self.log(f"  {route}", Colors.YELLOW)
                        if 'fleet' in route.lower() or 'vessel' in route.lower() or 'ship' in route.lower():
                            fleet_route = route
                            self.log(f"Using similar route: {fleet_route}", Colors.YELLOW)
                            break

                    if not fleet_route and routes:
                        # Try first available route as fallback
                        fleet_route = routes[0]
                        self.log(f"Using first available route as fallback: {fleet_route}", Colors.YELLOW)

                    # Manual route construction as last resort
                    if not fleet_route:
                        # Extract company ID from URL and construct route
                        import re
                        url_match = re.search(r'/owners-managers/([^/]+)/([^/]+)', self.company_url)
                        if url_match:
                            country = url_match.group(1)
                            company = url_match.group(2)
                            fleet_route = f"https://magicport.ai/owners-managers/{country}/{company}/fleets"
                            self.log(f"Constructed fleet route: {fleet_route}", Colors.YELLOW)
            except:
                pass

            if not fleet_route:
                self.log("Error: Could not find or construct fleet data route", Colors.RED)
                return csrf_token, None

            return csrf_token, fleet_route

        except Exception as e:
            self.log(f"Error fetching company page: {e}", Colors.RED)
            return None, None

    async def fetch_fleet_data(self, csrf_token, fleet_route):
        """Step 2: Fetch fleet data using AJAX request"""
        self.log("Step 2: Fetching fleet data...", Colors.YELLOW)

        # Simulate human behavior - wait and scroll
        await asyncio.sleep(3)
        await self.page.evaluate("window.scrollTo(0, 200)")

        try:
            # Prepare the AJAX request data
            post_data = {
                'draw': '1',
                'columns[0][data]': '0',
                'columns[0][name]': '',
                'columns[0][searchable]': 'true',
                'columns[0][orderable]': 'true',
                'columns[0][search][value]': '',
                'columns[0][search][regex]': 'false',
                'start': '0',
                'length': '25',
                'search[value]': '',
                'search[regex]': 'false',
                'order[0][column]': '0',
                'order[0][dir]': 'asc'
            }

            # Make the AJAX request using page.evaluate to execute in browser context
            fleet_data = await self.page.evaluate("""
                async (args) => {
                    const [fleetRoute, csrfToken, postData] = args;

                    const formData = new URLSearchParams();
                    for (const [key, value] of Object.entries(postData)) {
                        formData.append(key, value);
                    }

                    const response = await fetch(fleetRoute, {
                        method: 'POST',
                        headers: {
                            'Accept': 'application/json, text/javascript, */*; q=0.01',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-CSRF-TOKEN': csrfToken,
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: formData
                    });

                    const data = await response.json();
                    return {
                        status: response.status,
                        data: data
                    };
                }
            """, [fleet_route, csrf_token, post_data])

            if fleet_data['status'] == 200:
                response_data = fleet_data['data']

                # Check for anti-bot protection
                if response_data.get('error') == 'Attack !':
                    self.log("Anti-bot protection triggered. Trying alternative approach...", Colors.RED)
                    return await self.try_alternative_approach(csrf_token, fleet_route)

                self.log("Success! Fleet data retrieved", Colors.GREEN)
                return response_data
            else:
                self.log(f"HTTP Error: {fleet_data['status']}", Colors.RED)
                return None

        except Exception as e:
            self.log(f"Error fetching fleet data: {e}", Colors.RED)
            return await self.try_alternative_approach(csrf_token, fleet_route)

    async def try_alternative_approach(self, csrf_token, fleet_route):
        """Try alternative approach with minimal parameters"""
        self.log("Trying minimal parameter approach...", Colors.YELLOW)
        await asyncio.sleep(5)

        try:
            minimal_data = {
                'draw': '1',
                'start': '0',
                'length': '10'
            }

            fleet_data = await self.page.evaluate("""
                async (args) => {
                    const [fleetRoute, csrfToken, postData] = args;

                    const formData = new URLSearchParams();
                    for (const [key, value] of Object.entries(postData)) {
                        formData.append(key, value);
                    }

                    const response = await fetch(fleetRoute, {
                        method: 'POST',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRF-TOKEN': csrfToken,
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: formData
                    });

                    const data = await response.json();
                    return {
                        status: response.status,
                        data: data
                    };
                }
            """, [fleet_route, csrf_token, minimal_data])

            if fleet_data['data'].get('error') == 'Attack !':
                self.log("Still being blocked. This endpoint likely requires subscription access.", Colors.RED)
                self.log(f"Response: {fleet_data['data']}", Colors.RED)
                return None

            self.log("Success with alternative approach!", Colors.GREEN)
            return fleet_data['data']

        except Exception as e:
            self.log(f"Alternative approach failed: {e}", Colors.RED)
            return None

    async def scrape_and_save_to_database(self):
        """Main method that scrapes data and saves to database"""
        self.log(f"Enhanced MagicPort Scraper - Company ID: {self.company_id}", Colors.YELLOW)
        self.log("=" * 60, Colors.YELLOW)

        # Connect to database
        if not self.db_manager.connect():
            self.log("Failed to connect to database", Colors.RED)
            return False

        try:
            # Setup browser
            await self.setup_browser()

            # Step 0: Establish session
            if not await self.establish_session():
                return False

            # Step 1: Fetch company page and extract company info + tokens
            csrf_token, fleet_route = await self.fetch_company_page()
            if not csrf_token or not fleet_route:
                return False

            # Save company details to database and get the actual database company ID
            database_company_id = None
            if hasattr(self, 'company_info') and self.company_info:
                database_company_id = self.db_manager.insert_company_details(self.company_id, self.company_info)
                if not database_company_id:
                    self.log("Failed to save company details", Colors.RED)
                    return False

            # Step 2: Fetch fleet data
            fleet_data = await self.fetch_fleet_data(csrf_token, fleet_route)
            if not fleet_data:
                print("Error fetching fleet data")
                return False

            # Save fleet data to database using the actual database company ID
            if 'data' in fleet_data and fleet_data['data'] and database_company_id:
                success = self.db_manager.insert_fleet_vessels(database_company_id, fleet_data['data'])
                if not success:
                    self.log("Failed to save fleet vessels", Colors.RED)
                    return False

            # Also save JSON backup
            self.save_json_backup(fleet_data)

            self.log("Script completed successfully - data saved to database!", Colors.GREEN)
            return True

        except Exception as e:
            self.log(f"Unexpected error: {e}", Colors.RED)
            return False

        finally:
            # Cleanup
            self.db_manager.disconnect()
            try:
                await self.browser.close()
                await self.playwright.stop()
            except:
                pass

    def save_json_backup(self, data):
        """Save JSON backup file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create fleet_data directory if it doesn't exist
        if not os.path.exists('fleet_data'):
            os.makedirs('fleet_data')

        filename = f"fleet_data/{self.company_slug}_fleet_data_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log(f"JSON backup saved to {filename}", Colors.GREEN)
        except Exception as e:
            self.log(f"Error saving JSON backup: {e}", Colors.RED)


def main():
    parser = argparse.ArgumentParser(description='Enhanced MagicPort Fleet Data Scraper')
    parser.add_argument('--company-id', required=True, type=int, help='Company ID')
    parser.add_argument('--company-name', required=True, help='Company Name')
    parser.add_argument('--company-url', required=True, help='Company URL')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')

    # Database configuration arguments
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', default=3306, type=int, help='Database port')
    parser.add_argument('--db-name', default='magic_port', help='Database name')
    parser.add_argument('--db-user', default='root', help='Database user')
    parser.add_argument('--db-password', default='rootpassword', help='Database password')

    args = parser.parse_args()

    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'magic_port',
        'user': 'root',
        'password': 'rootpassword'
    }

    async def run_scraper():
        scraper = EnhancedMagicPortScraper(
            company_id=args.company_id,
            company_name=args.company_name,
            company_url=args.company_url,
            db_config=db_config,
            headless=not args.visible
        )

        try:
            success = await scraper.scrape_and_save_to_database()
            sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Script interrupted by user{Colors.NC}")
            sys.exit(1)

    asyncio.run(run_scraper())


if __name__ == "__main__":
    main()