# -*- coding: utf-8 -*-
import asyncio
import time
import json
import re
import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from single_port import SinglePortScrapper

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'magic_port_updated',
    'user': 'root',
    'password': 'rootpassword'
}

# Configuration
BATCH_SIZE = 5000  # Number of ports to process in each batch
MAX_RETRIES = 3  # Maximum retry attempts per port

class DatabaseManager:
    """Database manag0er for port data operations"""

    def __init__(self, db_config):
        self.db_config = db_config
        self.connection = None

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                print("✅ Connected to database")
                # Auto-create tables if they don't exist
                self.create_tables_if_not_exist()
                return True
        except Error as e:
            print(f"❌ Database connection error: {e}")
            return False

    def create_tables_if_not_exist(self):
        """Create database tables if they don't exist"""
        try:
            cursor = self.connection.cursor()

            # Create port_data table
            port_data_sql = """
            CREATE TABLE IF NOT EXISTS port_data (
                id INT NOT NULL AUTO_INCREMENT,
                name VARCHAR(255) DEFAULT NULL,
                country VARCHAR(100) DEFAULT NULL,
                unlocode VARCHAR(10) DEFAULT NULL,
                latitude DECIMAL(10,8) DEFAULT NULL,
                longitude DECIMAL(11,8) DEFAULT NULL,
                navigation JSON DEFAULT NULL,
                depths JSON DEFAULT NULL,
                port_characteristics JSON DEFAULT NULL,
                restrictions JSON DEFAULT NULL,
                port_equipment JSON DEFAULT NULL,
                communication JSON DEFAULT NULL,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                source_url VARCHAR(500) DEFAULT NULL,
                PRIMARY KEY (id),
                UNIQUE KEY unlocode (unlocode),
                KEY country (country),
                KEY scraped_at (scraped_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            cursor.execute(port_data_sql)
            print("✅ port_data table created/verified")

            cursor.close()
            return True

        except Error as e:
            print(f"❌ Error creating tables: {e}")
            return False

    def get_port_urls(self, limit=None):
        """Get port URLs from port_dicts table (legacy method)"""
        try:
            cursor = self.connection.cursor(dictionary=True)

            # Build query based on limit
            if limit:
                sql = "SELECT id, url FROM port_dicts WHERE url IS NOT NULL AND url != '' LIMIT %s"
                cursor.execute(sql, (limit,))
            else:
                sql = "SELECT id, url FROM port_dicts WHERE url IS NOT NULL AND url != ''"
                cursor.execute(sql)

            records = cursor.fetchall()
            cursor.close()

            return records
        except Error as e:
            print(f"❌ Error getting port URLs from database: {e}")
            return []

    def insert_port_data(self, port_data):
        """Insert port data into port_data table"""
        try:
            cursor = self.connection.cursor()

            # Parse coordinates
            lat, lng = parse_coordinates(port_data.get('coordinates'))

            # Insert or update using ON DUPLICATE KEY UPDATE
            sql = """
            INSERT INTO port_data (
                name, country, unlocode, latitude, longitude,
                navigation, depths, port_characteristics, restrictions,
                port_equipment, communication, scraped_at, source_url
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                country = VALUES(country),
                latitude = VALUES(latitude),
                longitude = VALUES(longitude),
                navigation = VALUES(navigation),
                depths = VALUES(depths),
                port_characteristics = VALUES(port_characteristics),
                restrictions = VALUES(restrictions),
                port_equipment = VALUES(port_equipment),
                communication = VALUES(communication),
                scraped_at = VALUES(scraped_at),
                source_url = VALUES(source_url)
            """

            values = (
                port_data.get('port_name'),
                port_data.get('country'),
                port_data.get('unlocode'),
                lat,
                lng,
                json.dumps(port_data.get('navigation', {})),
                json.dumps(port_data.get('depths', {})),
                json.dumps(port_data.get('port_characteristics', {})),
                json.dumps(port_data.get('restrictions', {})),
                json.dumps(port_data.get('port_equipment', {})),
                json.dumps(port_data.get('communication', {})),
                port_data.get('scraped_at'),
                port_data.get('source_url')
            )

            cursor.execute(sql, values)
            self.connection.commit()

            cursor.close()

            print(f"✅ Successfully saved to database: {port_data.get('port_name')} ({port_data.get('unlocode')})")
            return True

        except Error as e:
            print(f"❌ Error inserting port data: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔌 Database connection closed")

def create_database_connection():
    """Create MySQL database connection (legacy function)"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_single_port():
    """Get single port data from database where is_active = false"""
    try:
        connection = create_database_connection()
        cursor = connection.cursor()
        sql_select_query = "SELECT id, url FROM port_dicts WHERE is_active = false LIMIT 1"
        cursor.execute(sql_select_query)
        records = cursor.fetchall()
        if connection:
            cursor.close()
            connection.close()
        return records
    except Error as e:
        print(f"❌ Error getting port data: {e}")
        return None

def update_port_status(port_id, status=True):
    """Update port status after processing"""
    try:
        connection = create_database_connection()
        cursor = connection.cursor()
        sql_update = "UPDATE port_dicts SET is_active = %s WHERE id = %s"
        cursor.execute(sql_update, (status, port_id))
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"❌ Error updating port status: {e}")
        return False

def parse_coordinates(coord_string):
    """Parse coordinate string '41.81º, 19.59º' to separate lat/lng"""
    if not coord_string:
        return None, None

    try:
        # Remove the º symbol and split by comma
        coords = coord_string.replace('º', '').split(',')
        if len(coords) == 2:
            lat = float(coords[0].strip())
            lng = float(coords[1].strip())
            return lat, lng
    except (ValueError, IndexError) as e:
        print(f"Error parsing coordinates '{coord_string}': {e}")

    return None, None


async def scrape_single_port(url, port_id=None, db_manager=None):
    """Scrape a single port with time logging, file saving and database insertion"""
    # Start time logging
    start_time = datetime.now()
    print(f"🚀 Starting scrape for: {url}")
    print(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Create scraper instance
    scraper = SinglePortScrapper(port_url=url, headless=True)

    # Run scraping process
    result = await scraper.scrape()

    if result:
        # End time logging
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n✅ Scraping completed successfully!")
        print(f"⏱️  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total duration: {duration.total_seconds():.2f} seconds")

        # Print JSON output
        scraper.print_json_output()

        # Save to file with format country_port_name_unlocode.json
        if result.get("country") and result.get("port_name") and result.get("unlocode"):
            # Clean up the strings for filename
            country = re.sub(r'[^\w\s-]', '', result["country"]).strip().replace(' ', '_')
            port_name = re.sub(r'[^\w\s-]', '', result["port_name"]).strip().replace(' ', '_')
            unlocode = re.sub(r'[^\w\s-]', '', result["unlocode"]).strip()

            filename = f"ports_data/{country}_{port_name}_{unlocode}.json"
        else:
            # Fallback to timestamp if required data is missing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ports_data/port_data_{timestamp}.json"

        try:
            # Ensure the ports_data directory exists
            os.makedirs('ports_data', exist_ok=True)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Data saved to file: {filename}")
        except Exception as e:
            print(f"❌ Error saving to file: {e}")

        # Insert into database if db_manager is provided
        if db_manager:
            db_success = db_manager.insert_port_data(result)
            if db_success:
                print(f"🗄️  Data saved to database successfully")
            else:
                print(f"❌ Failed to save data to database")

        return True
    else:
        # End time logging for failed case
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n❌ Scraping failed!")
        print(f"⏱️  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total duration: {duration.total_seconds():.2f} seconds")
        return False

async def scrape_port_with_retry(url, port_id=None, db_manager=None, max_retries=MAX_RETRIES):
    """Scrape a single port with retry logic"""
    for attempt in range(max_retries):
        try:
            success = await scrape_single_port(url, port_id, db_manager)
            if success:
                return True
            else:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⏳ Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"❌ Error scraping {url} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)

    print(f"💀 All attempts failed for: {url}")
    return False

async def main():
    """Main function to scrape ports from database following company scraper pattern"""
    print("🚀 Starting MagicPort Database Scraper")
    print(f"📊 Batch size: {BATCH_SIZE} ports")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    start_time = time.time()
    total_processed = 0
    success_count = 0

    # Initialize database manager for port_data table operations
    db_manager = DatabaseManager(DB_CONFIG)

    try:
        # Connect to database
        if not db_manager.connect():
            print("❌ Failed to connect to database")
            return

        print("✅ Database connection established")

        # Process ports one by one, following company scraper pattern
        for i in range(BATCH_SIZE):
            print(f"\n🔄 Processing batch {i+1}/{BATCH_SIZE}")
            try:
                # Get single port data
                port_data = get_single_port()
                if not port_data:
                    print("No more ports to process")
                    break

                port_id = port_data[0][0]
                url = port_data[0][1]

                print(f"📍 Processing port ID: {port_id}, URL: {url}")
                print(f"⏰ Start time: {datetime.now()}")

                # Scrape the port
                success = await scrape_port_with_retry(url, port_id, db_manager)

                # Update port status
                if success:
                    print("✅ Successfully saved port")
                    update_port_status(port_id, True)
                    print(f"✅ Successfully processed port ID: {port_id}")
                    success_count += 1
                    print(f"⏰ End time: {datetime.now()}")
                else:
                    print(f"❌ Failed to process port ID: {port_id}")

                total_processed += 1

            except KeyboardInterrupt:
                print(f"\n🛑 Script interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error processing port: {e}")
                continue

    except Exception as e:
        print(f"❌ Error in main processing: {e}")

    finally:
        # Close database connection
        db_manager.close()

    # Summary
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / total_processed if total_processed > 0 else 0

    print("\n" + "="*60)
    print("📊 BATCH SCRAPING SUMMARY")
    print("="*60)
    print(f"✅ Successfully scraped: {success_count}/{total_processed} ports")
    print(f"❌ Failed: {total_processed - success_count} ports")
    print(f"⏱️  Total time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print(f"⚡ Average time per port: {avg_time:.2f} seconds")
    print(f"🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n📁 Files saved in ports_data/ directory")
    print(f"🗄️  Data saved to port_data table")
    print(f"📝 Port status updated in port_dicts table")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())