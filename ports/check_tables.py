#!/usr/bin/env python3
"""
Check available tables in the database
"""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'database': 'magic_port_updated',
    'user': 'root',
    'password': 'rootpassword'
}

def check_tables():
    """Check all tables in the database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        print(f"📊 Found {len(tables)} tables in magic_port_updated database:")
        for table in tables:
            table_name = table[0]

            # Check if table has 'url' column
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = 'magic_port_updated'
                AND table_name = '{table_name}'
                AND column_name = 'url'
            """)
            has_url = cursor.fetchone()[0] > 0

            # Get record count
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]

            url_indicator = " 📡" if has_url else ""
            print(f"  - {table_name}{url_indicator} ({count} records)")

        print("\n📡 Tables with URL column")

        cursor.close()
        connection.close()

    except Error as e:
        print(f"❌ Error checking tables: {e}")

if __name__ == "__main__":
    check_tables()