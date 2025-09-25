import json
import re
import time
import sys
import asyncio
import argparse
from datetime import datetime
from operator import truediv
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
    """from lower half got japan and china"""
    try:
        connection = create_database_connection()
        cursor = connection.cursor()
        sql_select_Query = "SELECT id, company_name, magicport_url FROM companies_directory WHERE id < 12362 ORDER BY id ASC LIMIT 1"
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


def find_company_by_name(name):
    """Find existing company by name"""
    try:
        connection = create_database_connection()
        cursor = connection.cursor()
        sql_select_Query = "SELECT id FROM vessel_companies WHERE name = %s"
        cursor.execute(sql_select_Query, (name,))
        result = cursor.fetchone()
        cursor.close()
        return True if result else False
    except Error as e:
        print(f"Error finding company by name: {e}")
        return None


async def main():
    batch_size = 1
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'magic_port',
        'user': 'root',
        'password': 'rootpassword'
    }
    for i in range(batch_size):
        print(f"Processing batch {i + 1}")
        try:
            company_data = get_company()
            if not company_data:
                print("No more companies to process")

            print(f"Processing company: {company_data[0]}")
            print(f"start time {datetime.now()}")

            is_company_exist = find_company_by_name(company_data[0][1])
            print(f" company exist: {is_company_exist}")
            if not is_company_exist:
                update_company_status(company_data[0][0], False)

        except KeyboardInterrupt:
            print(f"\nScript interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"Error processing company: {e}")
            continue



if __name__ == "__main__":
    asyncio.run(main())
