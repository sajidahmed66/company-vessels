from datetime import datetime
from time import sleep

import mysql.connector
from vessel_scrap import VesselScraper
import json
import logging
import os
import html
import re

def create_database_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='magic_port_updated',
            user='root',
            password='rootpassword'
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_vessel():
    """Get first vessel from company_fleet_vessels"""
    try:
        connection = create_database_connection()
        cursor = connection.cursor()
        sql_query = "SELECT * FROM company_fleet_vessels WHERE is_processed = FALSE AND id < 60000 LIMIT 1"

        cursor.execute(sql_query)
        record = cursor.fetchall()
        if connection:
            cursor.close()
            connection.close()
        return record
    except mysql.connector.Error as e:
        print(f"Error getting vessel: {e}")
        return None

def create_vessel_payload(vessel_record, flattened_data):
    """Create vessel payload for vessel table from fleet data and scraped data"""

    # Unpack vessel record from company_fleet_vessels
    (id, company_id, vessel_imo, vessel_mmsi, vessel_name, vessel_type,
     registered_owner, registered_owner_company_imo, registered_owner_company_country_slug,
     registered_owner_company_name_slug, registered_owner_total_distinct_vessels,
     commercial_manager, commercial_manager_company_country_slug,
     commercial_manager_company_imo, commercial_manager_company_name_slug,
     commercial_manager_total_distinct_vessels, core_vessel_types_key,
     core_vessel_types_name, dwt, flag, ism_manager,
     ism_manager_company_country_slug, ism_manager_company_imo,
     ism_manager_company_name_slug, ism_manager_total_distinct_vessels,
     last_position_update, created_at, updated_at, is_processed) = vessel_record
    # Get company ID by looking up the registered owner name in vessel_companies table
    # Use registered_owner_company_country_slug as country if available
    owner_country = registered_owner_company_country_slug if registered_owner_company_country_slug else None
    owner_company_id = get_company_id_or_create(registered_owner, owner_country)

    # Get manager company ID by looking up the manager name
    manager_name = commercial_manager or ism_manager
    # Use appropriate country based on which manager is being used
    if commercial_manager:
        manager_country = commercial_manager_company_country_slug
    else:
        manager_country = ism_manager_company_country_slug if ism_manager else None

    manager_company_id = get_company_id_or_create(manager_name, manager_country)

    # Create payload mapping fleet + scraped data to vessels table
    payload = {
        # From fleet data - using registered_owner to lookup company_id from vessel_companies
        'company_id': owner_company_id,
        'imo': vessel_imo,
        'mmsi': str(vessel_mmsi) if vessel_mmsi else None,
        'name': vessel_name,
        'owner': registered_owner,
        'manager': manager_name,  # Manager company name
        'manager_company_id': manager_company_id,  # Manager company ID from vessel_companies table
        'flag': flag,
        'type_name': vessel_type,
        'deadweight_tonnage': int(dwt) if dwt else None,

        # From scraped data (flattened) - using actual VesselFinder field names
        'image_url': flattened_data.get('vessel_image_url'),
        'built': parse_year(flattened_data.get('Year of Build')),
        'length': parse_numeric(flattened_data.get('Length Overall (m)')),  # ✅ Available
        'beam': parse_numeric(flattened_data.get('Beam (m)')),  # ✅ Available
        'maxdraught': None,  # ❌ Not available in this vessel's data
        'gross_tonnage': parse_numeric(flattened_data.get('Gross Tonnage')),
        'status': flattened_data.get('Status'),
        'draught': parse_numeric(flattened_data.get('Draught')),
    }

    return payload

def setup_error_logger():
    """Setup daily error logger for vessel parsing errors"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"vessel_parse_error_{today}.log"

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    log_filepath = os.path.join('logs', log_filename)

    # Configure logger
    logger = logging.getLogger('vessel_parser')
    logger.setLevel(logging.ERROR)

    # Remove existing handlers to avoid duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create file handler
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.ERROR)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    return logger

def setup_company_logger():
    """Setup daily logger for new company creation"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"new-company-{today}.log"

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    log_filepath = os.path.join('logs', log_filename)

    # Configure logger
    logger = logging.getLogger('company_creator')
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create file handler
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    return logger

def log_vessel_error(logger, vessel_id, vessel_imo, vessel_mmsi, error_reason):
    """Log vessel parsing error with details"""
    error_msg = f"Vessel ID: {vessel_id}, IMO: {vessel_imo}, MMSI: {vessel_mmsi}, Error: {error_reason}"
    logger.error(error_msg)

def decode_html_entities(text):
    """Decode HTML entities like &amp; to & etc."""
    if not text:
        return text
    return html.unescape(text)

def create_company_entry(company_name, country=None):
    """Create a new company entry in vessel_companies table"""
    try:
        connection = create_database_connection()
        if not connection:
            return None

        cursor = connection.cursor()

        # Capitalize the first letter of country if provided
        formatted_country = country.capitalize() if country else None

        # Insert new company with name and country
        insert_query = """
            INSERT INTO vessel_companies (name, country, address, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
        """

        # Use formatted country if provided, otherwise NULL
        # Use empty string for address as it's NOT NULL
        cursor.execute(insert_query, (company_name, formatted_country, ''))
        connection.commit()

        # Get the inserted company ID
        company_id = cursor.lastrowid

        cursor.close()
        connection.close()

        # Log the new company creation
        company_logger = setup_company_logger()
        log_msg = f"Created new company - ID: {company_id}, Name: '{company_name}', Country: '{formatted_country}'"
        company_logger.info(log_msg)

        print(f"✅ Created new company: '{company_name}' with ID: {company_id}")
        return company_id

    except mysql.connector.Error as e:
        print(f"❌ Error creating company entry: {e}")
        return None

def get_company_id_or_create(company_name, country=None):
    """Get company ID from vessel_companies table by matching name, create if not found"""
    if not company_name:
        return None

    # Decode HTML entities before matching
    decoded_name = decode_html_entities(company_name)

    try:
        connection = create_database_connection()
        if not connection:
            return None

        cursor = connection.cursor()

        # First try exact match with decoded name
        query = "SELECT id FROM vessel_companies WHERE name = %s"
        cursor.execute(query, (decoded_name,))
        result = cursor.fetchone()

        if not result:
            # Try case-insensitive match with decoded name
            query = "SELECT id FROM vessel_companies WHERE LOWER(name) = LOWER(%s)"
            cursor.execute(query, (decoded_name,))
            result = cursor.fetchone()

        if not result:
            # Try exact match with original name (fallback)
            query = "SELECT id FROM vessel_companies WHERE name = %s"
            cursor.execute(query, (company_name,))
            result = cursor.fetchone()

        if not result:
            # Try case-insensitive match with original name (fallback)
            query = "SELECT id FROM vessel_companies WHERE LOWER(name) = LOWER(%s)"
            cursor.execute(query, (company_name,))
            result = cursor.fetchone()

        cursor.close()
        connection.close()

        # If no company found, create a new entry
        if not result:
            print(f"🔄 Company '{company_name}' not found, creating new entry...")
            return create_company_entry(decoded_name, country)

        return result[0]

    except mysql.connector.Error as e:
        print(f"Error getting company ID: {e}")
        return None

def get_manager_company_id(manager_name):
    """Get manager company ID from vessel_companies table by matching name"""
    return get_company_id_or_create(manager_name)

def parse_year(value):
    """Parse year value, ensuring it's within MySQL YEAR type range (1901-2155)"""
    if not value:
        return None

    # Try to extract year from various formats (including historical years)
    year_match = re.search(r'\b(1[8-9]|20|21)\d{2}\b', str(value))
    if year_match:
        try:
            year = int(year_match.group())
            # MySQL YEAR type accepts 1901-2155, but we want to preserve historical data
            if 1800 <= year <= 2155:
                if year < 1901:
                    print(f"⚠️  Historical year {year} (before 1901) - MySQL YEAR limitation, setting to NULL")
                    print(f"💡 Consider changing 'built' column to SMALLINT to store historical years")
                    return None
                return year
            else:
                print(f"⚠️  Year {year} out of valid range (1800-2155), setting to NULL")
                return None
        except ValueError:
            pass

    print(f"⚠️  Could not parse year from '{value}', setting to NULL")
    return None

def parse_numeric(value):
    """Parse numeric value from string, extracting numbers and converting to float"""
    if not value:
        return None

    # Extract numeric part from strings like "225.50 m" or "75,375 t"
    import re
    numeric_match = re.search(r'[\d,]+\.?\d*', str(value).replace(',', ''))
    if numeric_match:
        try:
            return float(numeric_match.group())
        except ValueError:
            pass
    return None

def process_vessel():
    """Process a single vessel with comprehensive error handling"""
    # Setup error logger
    error_logger = setup_error_logger()

    vessel_data = get_vessel()
    if not vessel_data:
        print("No vessel found")
        return

    # Get first record from fetchall() result
    vessel_record = vessel_data[0]

    # Print ALL company fleet vessel data
    print("\n" + "="*50)
    print("COMPANY FLEET VESSEL DATA:")
    print("="*50)
    print(f"Full record: {vessel_record}")

    # Based on company_fleet_vessels table structure
    (id, company_id, vessel_imo, vessel_mmsi, vessel_name, vessel_type,
     registered_owner, registered_owner_company_imo, registered_owner_company_country_slug,
     registered_owner_company_name_slug, registered_owner_total_distinct_vessels,
     commercial_manager, commercial_manager_company_country_slug,
     commercial_manager_company_imo, commercial_manager_company_name_slug,
     commercial_manager_total_distinct_vessels, core_vessel_types_key,
     core_vessel_types_name, dwt, flag, ism_manager,
     ism_manager_company_country_slug, ism_manager_company_imo,
     ism_manager_company_name_slug, ism_manager_total_distinct_vessels,
     last_position_update, created_at, updated_at, is_processed) = vessel_record

    print("\n" + "="*50)
    print(f"\nProcessing vessel: {vessel_name} (IMO: {vessel_imo})")

    try:
        # Scrape vessel data
        scraper = VesselScraper()
        url = f"https://www.vesselfinder.com/vessels/details/{vessel_imo}"

        print(f"Scraping data from: {url}")
        scraped_data = scraper.scrape_vessel_data(url)

        # Check if scraping returned an error
        if "error" in scraped_data:
            error_reason = f"Scraping failed: {scraped_data['error']}"
            print(f"❌ {error_reason}")
            log_vessel_error(error_logger, id, vessel_imo, vessel_mmsi, error_reason)
            mark_vessel_as_processed(id)
            return

        # Flatten the scraped data
        flattened_data = scraper.flatten_json(scraped_data)

        # Create payload
        payload = create_vessel_payload(vessel_record, flattened_data)

        # Attempt to upsert vessel data
        result = upsert_vessel_data(payload)

        if result:
            print("SCRAPED DATA (JSON OUTPUT): ", payload)
            print(f"✅ Successfully processed vessel: {vessel_name} (IMO: {vessel_imo})")
            mark_vessel_as_processed(id)
        else:
            error_reason = "Failed to upsert vessel data to database"
            print(f"❌ {error_reason}")
            log_vessel_error(error_logger, id, vessel_imo, vessel_mmsi, error_reason)
            mark_vessel_as_processed(id)

    except Exception as e:
        error_reason = f"Unexpected error during processing: {str(e)}"
        print(f"❌ {error_reason}")
        log_vessel_error(error_logger, id, vessel_imo, vessel_mmsi, error_reason)
        # Mark as processed even on failure to prevent infinite loops
        mark_vessel_as_processed(id)
        print(f"⚠️ Vessel ID {id} marked as processed despite error to continue workflow")

def create_vessels_tables_if_not_exist():
    """Create database tables if they don't exist"""
    try:
        connection = create_database_connection()
        if connection.is_connected():
            print("Connected to database")
            cursor = connection.cursor()
            create_table_query = """
                CREATE TABLE IF NOT EXISTS vessels (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    company_id BIGINT UNSIGNED NOT NULL,
                    manager_company_id BIGINT UNSIGNED NULL,
                    imo BIGINT NOT NULL,
                    image_url VARCHAR(255) NULL,
                    name VARCHAR(255) NULL,
                    owner VARCHAR(255) NULL,
                    manager VARCHAR(255) NULL,
                    flag VARCHAR(10) NULL,
                    type VARCHAR(100) NULL,
                    type_name VARCHAR(255) NULL,
                    built YEAR NULL,
                    builder VARCHAR(255) NULL,
                    class VARCHAR(255) NULL,
                    length DOUBLE(8, 2) NULL,
                    beam DOUBLE(8, 3) NULL,
                    maxdraught DOUBLE(8, 3) NULL,
                    gross_tonnage BIGINT NULL,
                    net_tonnage BIGINT NULL,
                    deadweight_tonnage BIGINT NULL,
                    twentyfoot_equivalent_unit INT NULL,
                    crude INT NULL,
                    gas INT NULL,
                    others_data JSON NULL,
                    created_by BIGINT UNSIGNED NULL,
                    updated_by BIGINT UNSIGNED NULL,
                    deleted_by BIGINT UNSIGNED NULL,
                    created_at TIMESTAMP NULL,
                    updated_at TIMESTAMP NULL,
                    deleted_at TIMESTAMP NULL,
                    call_sign VARCHAR(255) NULL,
                    mmsi VARCHAR(255) NULL,
                    status VARCHAR(255) NULL,
                    a INT NULL,
                    b INT NULL,
                    c INT NULL,
                    d INT NULL,
                    draught DOUBLE(8, 3) NULL,
                    src VARCHAR(255) NULL,
                    zone VARCHAR(255) NULL,
                    company_tags JSON NULL,
                    CONSTRAINT vessels_imo_unique UNIQUE (imo),
                    CONSTRAINT vessels_company_id_foreign
                        FOREIGN KEY (company_id) REFERENCES vessel_companies (id)
                        ON DELETE CASCADE,
                    CONSTRAINT vessels_manager_company_id_foreign
                        FOREIGN KEY (manager_company_id) REFERENCES vessel_companies (id)
                        ON DELETE SET NULL
                ) COLLATE = utf8mb4_unicode_ci
            """
            cursor.execute(create_table_query)
            connection.commit()
            cursor.close()
            connection.close()
            print("Table 'vessels' created/verified successfully")
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return

def upsert_vessel_data(payload):
    """Upsert vessel data into vessels table using IMO as unique key"""
    try:
        connection = create_database_connection()
        if not connection:
            print("Failed to connect to database")
            return False

        cursor = connection.cursor()

        # Create upsert query using ON DUPLICATE KEY UPDATE
        upsert_query = """
            INSERT INTO vessels (
                company_id, imo, mmsi, name, owner, manager, manager_company_id, flag, type_name,
                deadweight_tonnage, image_url, built, length, beam, gross_tonnage,
                status, draught, created_at, updated_at
            ) VALUES (
                %(company_id)s, %(imo)s, %(mmsi)s, %(name)s, %(owner)s, %(manager)s,
                %(manager_company_id)s, %(flag)s, %(type_name)s, %(deadweight_tonnage)s, %(image_url)s,
                %(built)s, %(length)s, %(beam)s, %(gross_tonnage)s, %(status)s,
                %(draught)s, NOW(), NOW()
            )
            ON DUPLICATE KEY UPDATE
                company_id = VALUES(company_id),
                mmsi = VALUES(mmsi),
                name = VALUES(name),
                owner = VALUES(owner),
                manager = VALUES(manager),
                manager_company_id = VALUES(manager_company_id),
                flag = VALUES(flag),
                type_name = VALUES(type_name),
                deadweight_tonnage = VALUES(deadweight_tonnage),
                image_url = VALUES(image_url),
                built = VALUES(built),
                length = VALUES(length),
                beam = VALUES(beam),
                gross_tonnage = VALUES(gross_tonnage),
                status = VALUES(status),
                draught = VALUES(draught),
                updated_at = NOW()
        """

        cursor.execute(upsert_query, payload)
        connection.commit()

        # Check if it was an insert or update
        if cursor.rowcount == 1:
            print(f"✅ Inserted new vessel: IMO {payload['imo']}")
        elif cursor.rowcount == 2:  # MySQL returns 2 for updates
            print(f"🔄 Updated existing vessel: IMO {payload['imo']}")
        else:
            print(f"ℹ️  No changes for vessel: IMO {payload['imo']}")

        cursor.close()
        connection.close()
        return True

    except mysql.connector.Error as e:
        print(f"❌ Error upserting vessel data: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def mark_vessel_as_processed(vessel_id):
    """Mark vessel as processed in company_fleet_vessels table"""
    try:
        connection = create_database_connection()
        if not connection:
            print("Failed to connect to database")
            return False

        cursor = connection.cursor()
        update_query = "UPDATE company_fleet_vessels SET is_processed = TRUE WHERE id = %s"
        cursor.execute(update_query, (vessel_id,))
        connection.commit()

        if cursor.rowcount > 0:
            print(f"✅ Marked vessel ID {vessel_id} as processed")
        else:
            print(f"⚠️ No vessel found with ID {vessel_id}")

        cursor.close()
        connection.close()
        return True

    except mysql.connector.Error as e:
        print(f"❌ Error marking vessel as processed: {e}")
        return False

def main():
    batch_size = 20000
    create_vessels_tables_if_not_exist()
    for i in range(batch_size):
        print(f"Processing batch {i + 1}")
        print(f"start time {datetime.now()}")
        process_vessel()
        print(f"end time {datetime.now()}")
        sleep(3)
if __name__ == "__main__":
    main()