from datetime import datetime
from bs4 import BeautifulSoup
import requests
import re
import time
import mysql.connector
from urllib.parse import urljoin
import json


def create_database_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host='localhost',  # Change as needed
            database='magic_port',  # Change to your database name
            user='root',  # Change to your username
            password='rootpassword'  # Change to your password
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def create_table_if_not_exists(connection):
    """Create the companies_directory table if it doesn't exist"""
    cursor = connection.cursor()

    create_table_query = """
                         CREATE TABLE IF NOT EXISTS companies_directory \
                         ( \
                             id \
                             INT \
                             AUTO_INCREMENT \
                             PRIMARY \
                             KEY, \
                             company_name \
                             VARCHAR \
                         ( \
                             255 \
                         ),
                             country_name VARCHAR \
                         ( \
                             100 \
                         ),
                             fleet_size VARCHAR \
                         ( \
                             50 \
                         ),
                             company_title VARCHAR \
                         ( \
                             255 \
                         ),
                             magicport_url VARCHAR \
                         ( \
                             500 \
                         ),
                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                             INDEX idx_company_name \
                         ( \
                             company_name \
                         ),
                             INDEX idx_country_name \
                         ( \
                             country_name \
                         )
                             ) \
                         """

    try:
        cursor.execute(create_table_query)
        connection.commit()
        print("Table 'companies_directory' created/verified successfully")
    except mysql.connector.Error as e:
        print(f"Error creating table: {e}")
    finally:
        cursor.close()


def insert_company_data(connection, companies_data):
    """Insert company data into the database"""
    cursor = connection.cursor()

    insert_query = """
                   INSERT INTO companies_directory
                       (company_name, country_name, fleet_size, company_title, magicport_url)
                   VALUES (%s, %s, %s, %s, %s) \
                   """

    try:
        cursor.executemany(insert_query, companies_data)
        connection.commit()
        print(f"Inserted {cursor.rowcount} companies into database")
        return cursor.rowcount
    except mysql.connector.Error as e:
        print(f"Error inserting data: {e}")
        return 0
    finally:
        cursor.close()


def extract_company_data_from_page(url):
    """Extract company data from a single page"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all li elements containing company cards
        company_list_items = soup.find_all('li', class_='col-12')

        companies_data = []

        for li_item in company_list_items:
            try:
                # Find the anchor tag within this li
                card = li_item.find('a', href=True)
                if not card:
                    continue

                # Extract company URL
                company_url = card.get('href')
                if not company_url:
                    continue

                # Make URL absolute
                company_url = urljoin(url, company_url)

                # Validate URL pattern
                pattern = r'^https://magicport\.ai/owners-managers/[^/]+/[^/]+/?$'
                if not re.match(pattern, company_url):
                    continue

                # Extract company title (from title attribute)
                company_title = card.get('title', '').strip()

                # Extract company name (from h3 tag with specific classes)
                company_name_elem = card.find('h3', class_=re.compile(r'.*card__title.*'))
                company_name = company_name_elem.get_text(strip=True) if company_name_elem else ''

                # Extract country (from gray badge)
                country_badge = card.find('span', class_=re.compile(r'.*badge--gray.*'))
                country_name = country_badge.get_text(strip=True) if country_badge else ''

                # Extract fleet size (from warning badge)
                fleet_badge = card.find('span', class_=re.compile(r'.*badge--warning.*'))
                fleet_size = fleet_badge.get_text(strip=True) if fleet_badge else ''

                # Only add if we have essential data
                if company_url and company_name:
                    company_data = {
                        'company_name': company_name,
                        'country_name': country_name,
                        'fleet_size': fleet_size,
                        'company_title': company_title,
                        'magicport_url': company_url
                    }
                    companies_data.append(company_data)
                    print(f"Found: {company_name} - {fleet_size} - {company_url}")

            except Exception as e:
                print(f"Error extracting data from card: {e}")
                continue

        print(f"Extracted {len(companies_data)} companies from this page")
        return companies_data

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []


def get_total_pages(url):
    """Get the total number of pages from the pagination footer"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find the pagination container
        pagination_container = soup.find('ul', class_='pagination')

        if not pagination_container:
            return 1  # Only one page if no pagination

        # Find all pagination links
        pagination_items = pagination_container.find_all('li', class_='pagination__item')

        max_page = 1
        for item in pagination_items:
            # Check for links (not the active span)
            link = item.find('a', class_='pagination__item-link')
            if link and link.get('href'):
                # Extract page number from href
                page_match = re.search(r'page=(\d+)', link['href'])
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page = max(max_page, page_num)

            # Also check span for current page (active page)
            span = item.find('span', class_=re.compile(r'.*pagination__item-link--active.*'))
            if span and span.text.strip().isdigit():
                page_num = int(span.text.strip())
                max_page = max(max_page, page_num)

        return max_page

    except requests.RequestException as e:
        print(f"Error getting total pages: {e}")
        return 1


def scrape_country_to_database(country_code, connection):
    """Scraps company by country"""
    base_url = "https://magicport.ai/owners-managers"
    # additional_params = "role[]=registered_owner&role[]=commercial_manager&role[]=ism_manager&fleetType[]=General%20Cargo&fleetType[]=Tanker&fleetType[]=Container&fleetType[]=Bulk%20Carrier&fleetType[]=Bunkering&fleetType[]=Gas%20Carrier"
    additional_params = "role[]=registered_owner&role[]=commercial_manager&role[]=ism_manager"

    print(f"\n===Scraping {country_code} ===\n{datetime.now()}")

    first_page_url = f"{base_url}?{additional_params}&country[]={country_code}"

    # Get total pages for this country
    total_pages = get_total_pages(first_page_url)
    print(f"Found {total_pages} total pages for {country_code}")

    all_companies_data = []

    # Scrape all pages for this country
    for page in range(1, total_pages + 1):
        if page == 1:
            current_url = first_page_url
        else:
            current_url = f"{first_page_url}&page={page}"

        print(f"{datetime.now()} Scraping {country_code} page {page}/{total_pages}...")


        page_companies = extract_company_data_from_page(current_url)
        all_companies_data.extend(page_companies)

        # Add delay to be respectful
        time.sleep(10)

    # Prepare data for database insertion
    companies_for_db = [
        (
            company['company_name'],
            company['country_name'],
            company['fleet_size'],
            company['company_title'],
            company['magicport_url']
        )
        for company in all_companies_data
    ]

    # Insert into database
    if companies_for_db:
        inserted_count = insert_company_data(connection, companies_for_db)
        print(f"{datetime.now()} Successfully inserted {inserted_count} companies for {country_code}")
    else:
        print(f"No companies found for {country_code}")

    return len(all_companies_data)


def scrape_multiple_countries_to_database(countries):
    """Scrape multiple countries and save to database"""

    # Create database connection
    connection = create_database_connection()
    if not connection:
        print("Failed to connect to database. Exiting.")
        return

    # Create table if not exists
    create_table_if_not_exists(connection)

    total_companies = 0

    try:
        for country_code in countries:
            country_count = scrape_country_to_database(country_code, connection)
            total_companies += country_count
            print(f"Completed {country_code}: {country_count} companies")

    except Exception as e:
        print(f"Error during scraping: {e}")

    finally:
        # Close database connection
        if connection.is_connected():
            connection.close()
        print(f"\nScraping completed. Total companies processed: {total_companies}")


def main():

    print("Starting Magicport scraper with MySQL integration...")
    # Define countries to scrape
    countries = []
    file_path = "countries1.json"
    try:
        # Use 'with open' to ensure the file is properly closed after use.
        # The 'r' mode is for reading the file.
        with open(file_path, 'r') as f:
            # The `json.load()` method reads from a file-like object and
            # converts the JSON data into a Python object.
            countries_list = json.load(f)

        # Use a list comprehension to create a new list containing only the
        # 'value' from each dictionary in the parsed list.
        country_values = [country['value'] for country in countries_list]

        # Print the final list of country values.
        # The output will be a Python list: ['åland-islands', 'albania', ...].
        print(country_values)
        countries = country_values
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' contains invalid JSON.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")



    # Scrape multiple countries
    scrape_multiple_countries_to_database(countries)


if __name__ == "__main__":
    main()