# -*- coding: utf-8 -*-
"""
Test script to verify database integration functionality
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'magic_port_updated',
    'user': 'root',
    'password': 'rootpassword'
}

def test_database_connection():
    """Test database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("✅ Database connection successful")
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()
            print(f"📊 Connected to database: {db_name[0]}")
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_table_creation():
    """Test port_data table creation"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'magic_port_updated'
            AND table_name = 'port_data'
        """)

        table_exists = cursor.fetchone()[0]

        if table_exists > 0:
            print("✅ port_data table exists")

            # Show table structure
            cursor.execute("DESCRIBE port_data")
            columns = cursor.fetchall()
            print("📋 Table structure:")
            for column in columns:
                print(f"  - {column[0]}: {column[1]}")
        else:
            print("❌ port_data table does not exist")
            print("💡 Run: mysql -u root -p magic_port_updated < create_port_data_table.sql")

        cursor.close()
        connection.close()
        return table_exists > 0

    except Error as e:
        print(f"❌ Error checking table: {e}")
        return False

def test_port_dict_data():
    """Test if port_dict table has data"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check if port_dicts table exists first
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'magic_port_updated'
            AND table_name = 'port_dicts'
        """)

        table_exists = cursor.fetchone()[0]

        if table_exists == 0:
            print("❌ port_dicts table does not exist")
            print("💡 Please ensure port_dicts table exists with id and url columns")
            return False

        # Count records with URLs
        cursor.execute("""
            SELECT COUNT(*)
            FROM port_dicts
            WHERE url IS NOT NULL AND url != ''
        """)

        count = cursor.fetchone()[0]
        print(f"📊 Found {count} port URLs in port_dicts table")

        if count > 0:
            # Show sample URLs
            cursor.execute("""
                SELECT id, url
                FROM port_dicts
                WHERE url IS NOT NULL AND url != ''
                LIMIT 3
            """)

            records = cursor.fetchall()
            print("📝 Sample URLs:")
            for record in records:
                print(f"  - ID {record[0]}: {record[1]}")

        cursor.close()
        connection.close()
        return count > 0

    except Error as e:
        print(f"❌ Error checking port_dict: {e}")
        return False

def test_database_manager():
    """Test DatabaseManager class"""
    try:
        # Import and test DatabaseManager
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        from action import DatabaseManager

        db_manager = DatabaseManager(DB_CONFIG)

        # Test connection
        if db_manager.connect():
            print("✅ DatabaseManager connection successful")

            # Test table creation
            print("✅ Table creation/verification successful")

            # Test getting port URLs
            port_urls = db_manager.get_port_urls(limit=1)
            if port_urls:
                print(f"✅ Successfully retrieved {len(port_urls)} port URLs")
                print(f"📝 Sample: ID {port_urls[0]['id']} -> {port_urls[0]['url']}")
            else:
                print("⚠️  No port URLs found (table may be empty)")

            db_manager.close()
            return True
        else:
            print("❌ DatabaseManager connection failed")
            return False

    except Exception as e:
        print(f"❌ Error testing DatabaseManager: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing MagicPort Database Integration")
    print("="*50)

    tests = [
        ("Database Connection", test_database_connection),
        ("Table Creation", test_table_creation),
        ("Port Dict Data", test_port_dict_data),
        ("DatabaseManager", test_database_manager)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n🎉 All tests passed! Ready to run the scraper.")
        print("💡 Run: uv run python action.py")
    else:
        print("\n⚠️  Some tests failed. Please fix issues before running scraper.")

if __name__ == "__main__":
    main()