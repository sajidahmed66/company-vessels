#!/usr/bin/env python3
"""
Check if port status was updated after processing
"""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'database': 'magic_port_updated',
    'user': 'root',
    'password': 'rootpassword'
}

def check_port_status():
    """Check port status in port_dicts table"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check specific port ID 1
        cursor.execute("SELECT id, url, is_active FROM port_dicts WHERE id = 1")
        record = cursor.fetchone()

        if record:
            port_id, url, is_active = record
            print(f"📊 Port ID: {port_id}")
            print(f"📡 URL: {url}")
            print(f"📝 is_active: {is_active}")

            if is_active == 1:
                print("✅ Port status successfully updated to True")
            else:
                print("❌ Port status was not updated")

        # Check overall statistics
        cursor.execute("SELECT COUNT(*) FROM port_dicts WHERE is_active = true")
        active_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM port_dicts WHERE is_active = false")
        inactive_count = cursor.fetchone()[0]

        print(f"\n📊 Port Status Summary:")
        print(f"✅ Active (processed): {active_count}")
        print(f"⏳ Inactive (to process): {inactive_count}")
        print(f"📊 Total: {active_count + inactive_count}")

        cursor.close()
        connection.close()

    except Error as e:
        print(f"❌ Error checking port status: {e}")

if __name__ == "__main__":
    check_port_status()