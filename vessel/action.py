from contextlib import nullcontext
from operator import truediv

import mysql.connector
from vessel_scrap import VesselScraper
import json


def create_database_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='magic_port',
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
        sql_query = "SELECT * FROM company_fleet_vessels LIMIT 1"
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
    """Create vessel payload for vessels table from fleet data and scraped data"""

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
     last_position_update, created_at, updated_at) = vessel_record
    # Create payload mapping fleet + scraped data to vessels table
    payload = {
        # From fleet data
        'company_id': company_id,
        'imo': vessel_imo,
        'mmsi': str(vessel_mmsi) if vessel_mmsi else None,
        'name': vessel_name,
        'owner': registered_owner,
        'manager': commercial_manager or ism_manager,  # Prefer commercial, fallback to ism
        'flag': flag,
        'type_name': vessel_type,
        'deadweight_tonnage': int(dwt) if dwt else None,

        # From scraped data (flattened) - using actual VesselFinder field names
        'image_url': flattened_data.get('vessel_image_url'),
        'built': flattened_data.get('Year of Build'),
        'length': parse_numeric(flattened_data.get('Length Overall (m)')),  # ✅ Available
        'beam': parse_numeric(flattened_data.get('Beam (m)')),  # ✅ Available
        'maxdraught': None,  # ❌ Not available in this vessel's data
        'gross_tonnage': parse_numeric(flattened_data.get('Gross Tonnage')),
        'status': flattened_data.get('Status'),
        'draught': parse_numeric(flattened_data.get('Draught')),
    }

    return payload

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
    """Process single vessel"""
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
     last_position_update, created_at, updated_at) = vessel_record

    print("\n" + "="*50)
    print(f"\nProcessing vessel: {vessel_name} (IMO: {vessel_imo})")

    # Scrape vessel data
    scraper = VesselScraper()
    url = f"https://www.vesselfinder.com/vessels/details/{vessel_imo}"
    scraped_data = scraper.scrape_vessel_data(url)
    flattened_data = scraper.flatten_json(scraped_data)
    payload = create_vessel_payload(vessel_record, flattened_data)
    result = upsert_vessel_data(payload)
    # print("\n" + "="*50)
    print("SCRAPED DATA (JSON OUTPUT):")
    # print("="*50)
    # print(json.dumps(flattened_data.get("vessel_image_url"), indent=2, ensure_ascii=False))

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
                company_id, imo, mmsi, name, owner, manager, flag, type_name,
                deadweight_tonnage, image_url, built, length, beam, gross_tonnage,
                status, draught, created_at, updated_at
            ) VALUES (
                %(company_id)s, %(imo)s, %(mmsi)s, %(name)s, %(owner)s, %(manager)s,
                %(flag)s, %(type_name)s, %(deadweight_tonnage)s, %(image_url)s,
                %(built)s, %(length)s, %(beam)s, %(gross_tonnage)s, %(status)s,
                %(draught)s, NOW(), NOW()
            )
            ON DUPLICATE KEY UPDATE
                company_id = VALUES(company_id),
                mmsi = VALUES(mmsi),
                name = VALUES(name),
                owner = VALUES(owner),
                manager = VALUES(manager),
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

def upsert_vessel_table(payload):
    """Upsert vessel data into database"""


def main():
    batched_size = 100
    process_vessel()
    create_vessels_tables_if_not_exist()
if __name__ == "__main__":
    main()