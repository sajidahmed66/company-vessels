#!/usr/bin/env python3
"""
MagicPort Fleet Data Scraper with Playwright
Usage: python magicport_scraper.py [company-url]

Installation:
pip install playwright beautifulsoup4
playwright install
"""

import json
import re
import time
import sys
import asyncio
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'


class MagicPortScraperPlaywright:
    def __init__(self, company_url=None, headless=True):
        self.base_url = "https://magicport.ai"
        self.company_url = company_url or "https://magicport.ai/owners-managers/azerbaijan/neptune-navigators-llc"
        self.company_name = "neptune-navigators-llc"
        self.headless = headless

        # Extract company name from URL
        parsed_url = urlparse(self.company_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) >= 3:
            self.company_name = path_parts[-1]

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
            # Navigate to homepage with realistic behavior
            await self.page.goto(self.base_url, wait_until='networkidle', timeout=30000)

            # Simulate human behavior - scroll a bit
            await self.page.evaluate("window.scrollTo(0, 100)")
            await asyncio.sleep(2)

            self.log("Session established successfully", Colors.GREEN)
            return True

        except Exception as e:
            self.log(f"Error establishing session: {e}", Colors.RED)
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

            # # Alternative: extract from address
            # if not company_info['country'] and company_info['address']:
            #     address_lower = company_info['address'].lower()
            #     # Common country patterns in addresses
            #     country_patterns = {
            #         'argentina': 'Argentina',
            #         'buenos aires': 'Argentina',
            #         'usa': 'United States',
            #         'united states': 'United States',
            #         'uk': 'United Kingdom',
            #         'united kingdom': 'United Kingdom',
            #         'germany': 'Germany',
            #         'france': 'France',
            #         'norway': 'Norway',
            #         'greece': 'Greece',
            #         'singapore': 'Singapore',
            #         'china': 'China',
            #         'japan': 'Japan',
            #         'south korea': 'South Korea',
            #         'azerbaijan': 'Azerbaijan'
            #     }
            #
            #     for pattern, country in country_patterns.items():
            #         if pattern in address_lower:
            #             company_info['country'] = country
            #             break

            # Clean up the data
            for key, value in company_info.items():
                if isinstance(value, str):
                    company_info[key] = value.strip()

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

            # If still no token, save page for debugging
            if not csrf_token:
                html_content = await self.page.content()
                debug_filename = f"debug_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                # Show available meta tags
                meta_tags = await self.page.evaluate("""
                    () => {
                        const metas = document.querySelectorAll('meta');
                        return Array.from(metas).slice(0, 10).map(meta => {
                            const attrs = {};
                            for (let attr of meta.attributes) {
                                attrs[attr.name] = attr.value;
                            }
                            return attrs;
                        });
                    }
                """)

                self.log("No CSRF token found. Available meta tags:", Colors.YELLOW)
                for meta in meta_tags:
                    self.log(f"  {meta}", Colors.YELLOW)

                self.log(f"Page HTML saved to {debug_filename} for debugging", Colors.YELLOW)
                self.log("Warning: Could not extract CSRF token, continuing anyway...", Colors.YELLOW)
                # Don't return None, continue without token
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
            print(fleet_route, csrf_token, post_data)

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

    def save_data(self, data):
        """Save the scraped data to a JSON file"""
        if not data:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.company_name}_fleet_data_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.log(f"Data saved to {filename}", Colors.GREEN)
            return filename

        except IOError as e:
            self.log(f"Error saving data: {e}", Colors.RED)
            return None

    async def scrape(self):
        """Main scraping method"""
        self.log("MagicPort Fleet Data Scraper - Playwright", Colors.YELLOW)
        self.log("===========================================", Colors.YELLOW)

        try:
            # Setup browser
            await self.setup_browser()

            # Step 0: Establish session
            if not await self.establish_session():
                return None

            # Step 1: Fetch company page and extract tokens
            csrf_token, fleet_route = await self.fetch_company_page()
            if not csrf_token or not fleet_route:
                return None

            # Step 2: Fetch fleet data
            fleet_data = await self.fetch_fleet_data(csrf_token, fleet_route)
            if not fleet_data:
                return None

            # Display and save data
            print(json.dumps(fleet_data, indent=2))
            filename = self.save_data(fleet_data)

            self.log("Script completed successfully.", Colors.GREEN)
            return fleet_data

        finally:
            # Cleanup
            try:
                await self.browser.close()
                await self.playwright.stop()
            except:
                pass

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'browser'):
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except:
            pass


async def main():
    """Main function"""
    company_url = None
    if len(sys.argv) > 1:
        company_url = sys.argv[1]

    # Option to run in non-headless mode for debugging
    headless = True
    if len(sys.argv) > 2 and sys.argv[2] == '--visible':
        headless = False

    scraper = MagicPortScraperPlaywright(company_url, headless=headless)

    try:
        result = await scraper.scrape()
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Script interrupted by user{Colors.NC}")
        await scraper.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {e}{Colors.NC}")
        await scraper.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())