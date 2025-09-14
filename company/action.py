import json
import re
import time
import sys
import asyncio
import argparse
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import mysql.connector  # Change to psycopg2 for PostgreSQL
from mysql.connector import Error
from singel_company import EnhancedMagicPortScraper
import asyncio


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


def get_company():
    """Get company data from database"""
    try:
        connection = create_database_connection()
        cursor = connection.cursor()
        sql_select_Query = "SELECT id, company_name, magicport_url FROM companies_directory WHERE is_active = FALSE ORDER BY id ASC LIMIT 1"
        cursor.execute(sql_select_Query)
        records = cursor.fetchall()
        if connection:
            cursor.close()
            connection.close()
        return records
    except mysql.connector.Error as e:
        print(f"Error getting company data: {e}")
        return None

def update_company_status(company_id, status=True):
    """Update company status after processing"""
    try:
        connection = create_database_connection()
        cursor = connection.cursor()
        sql_update = "UPDATE companies_directory SET is_active = %s WHERE id = %s"
        cursor.execute(sql_update, (status, company_id))
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except mysql.connector.Error as e:
        print(f"Error updating company status: {e}")
        return False

async def main():
    batch_size =1
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'magic_port',
        'user': 'root',
        'password': 'rootpassword'
    }

    for _ in range(batch_size):
        try:
            company_data = get_company()
            if not company_data:
                print("No more companies to process")
                break
            print(f"Processing company: {company_data[0]}")
            print(f"start time {datetime.now()}")
            scraper = EnhancedMagicPortScraper(
                company_id=company_data[0][0],
                company_name=company_data[0][1],
                company_url=company_data[0][2],
                db_config=db_config,
                headless=True,
            )
            # Run the full scraping process
            success = await scraper.scrape_and_save_to_database()

            # Update company status
            if success:
                update_company_status(company_data[0][0], True)
                print(f"Successfully processed company ID: {company_data[0]}")
                print(f"end time {datetime.now()}")

            else:
                print(f"Failed to process company ID: {company_data[0]}")
        except KeyboardInterrupt:
            print(f"\nScript interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"Error processing company: {e}")
            continue



if __name__ == "__main__":
    asyncio.run(main())
