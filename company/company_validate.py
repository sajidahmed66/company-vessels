import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    'host': 'localhost',
    'database': 'magic_port_final',
    'user': 'root',
    'password': 'rootpassword'
}

# Logging structure
validation_log = {
    'corrections': [],
    'missing_companies': [],
    'errors': [],
    'summary': {
        'total_processed': 0,
        'company_id_corrections': 0,
        'manager_company_id_corrections': 0,
        'needs_manual_review': 0,
        'errors': 0
    }
}


def create_database_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def get_unprocessed_vessels(batch_size=10):
    """Get vessels that haven't been validated yet"""
    try:
        connection = create_database_connection()
        if not connection:
            return None

        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT v.*
            FROM vessels v
            LEFT JOIN vessel_validation_tracking vvt ON v.id = vvt.vessel_id
            WHERE vvt.vessel_id IS NULL
            ORDER BY v.id ASC
            LIMIT %s
        """
        cursor.execute(query, (batch_size,))
        vessels = cursor.fetchall()
        cursor.close()
        connection.close()
        return vessels
    except Error as e:
        print(f"Error getting unprocessed vessels: {e}")
        return None


def find_company_by_name(name):
    """Find company by exact name match"""
    if not name:
        return None

    try:
        connection = create_database_connection()
        if not connection:
            return None

        cursor = connection.cursor(dictionary=True)
        query = "SELECT id, name FROM vessel_companies WHERE name = %s LIMIT 1"
        cursor.execute(query, (name,))
        company = cursor.fetchone()
        cursor.close()
        connection.close()
        return company
    except Error as e:
        print(f"Error finding company by name: {e}")
        return None


def create_company(name):
    """Create a new company with name only"""
    if not name:
        return None

    try:
        connection = create_database_connection()
        if not connection:
            return None

        cursor = connection.cursor()
        query = """
            INSERT INTO vessel_companies (name, address, created_at, updated_at)
            VALUES (%s, '', NOW(), NOW())
        """
        cursor.execute(query, (name,))
        connection.commit()
        company_id = cursor.lastrowid
        cursor.close()
        connection.close()

        return {'id': company_id, 'name': name}
    except Error as e:
        print(f"Error creating company: {e}")
        return None


def update_vessel_company_id(vessel_id, company_id=None, manager_company_id=None):
    """Update vessel's company_id or manager_company_id"""
    try:
        connection = create_database_connection()
        if not connection:
            return False

        cursor = connection.cursor()

        if company_id is not None:
            query = "UPDATE vessels SET company_id = %s WHERE id = %s"
            cursor.execute(query, (company_id, vessel_id))

        if manager_company_id is not None:
            query = "UPDATE vessels SET manager_company_id = %s WHERE id = %s"
            cursor.execute(query, (manager_company_id, vessel_id))

        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"Error updating vessel company IDs: {e}")
        return False


def insert_tracking_record(vessel_id, status, company_id_corrected=False,
                          manager_company_id_corrected=False, notes=None):
    """Insert validation tracking record"""
    try:
        connection = create_database_connection()
        if not connection:
            return False

        cursor = connection.cursor()
        query = """
            INSERT INTO vessel_validation_tracking
            (vessel_id, status, company_id_corrected, manager_company_id_corrected, notes)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (vessel_id, status, company_id_corrected,
                              manager_company_id_corrected, notes))
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"Error inserting tracking record: {e}")
        return False


def validate_vessel(vessel):
    """Validate and correct vessel's company FKs"""
    vessel_id = vessel['id']
    imo = vessel['imo']
    owner_name = vessel['owner']
    manager_name = vessel['manager']
    current_company_id = vessel['company_id']
    current_manager_company_id = vessel['manager_company_id']

    company_id_corrected = False
    manager_company_id_corrected = False
    needs_review = False
    notes = []

    # Validate company_id (owner)
    if owner_name:
        owner_company = find_company_by_name(owner_name)
        if not owner_company:
            # Create new company if not found
            owner_company = create_company(owner_name)
            if owner_company:
                notes.append(f"Created new company '{owner_name}' with ID {owner_company['id']}")
                validation_log['summary']['companies_created'] = validation_log['summary'].get('companies_created', 0) + 1

        if owner_company:
            correct_company_id = owner_company['id']
            if current_company_id != correct_company_id:
                # Update the FK
                if update_vessel_company_id(vessel_id, company_id=correct_company_id):
                    company_id_corrected = True
                    validation_log['corrections'].append({
                        'vessel_id': vessel_id,
                        'imo': imo,
                        'field': 'company_id',
                        'old_value': current_company_id,
                        'new_value': correct_company_id,
                        'company_name': owner_name
                    })
                    validation_log['summary']['company_id_corrections'] += 1
                    notes.append(f"Updated company_id from {current_company_id} to {correct_company_id}")
        else:
            # Failed to create company
            needs_review = True
            validation_log['missing_companies'].append({
                'vessel_id': vessel_id,
                'imo': imo,
                'field': 'owner/company_id',
                'company_name': owner_name
            })
            notes.append(f"Failed to create company '{owner_name}'")

    # Validate manager_company_id
    if manager_name:
        manager_company = find_company_by_name(manager_name)
        if not manager_company:
            # Create new company if not found
            manager_company = create_company(manager_name)
            if manager_company:
                notes.append(f"Created new company '{manager_name}' with ID {manager_company['id']}")
                validation_log['summary']['companies_created'] = validation_log['summary'].get('companies_created', 0) + 1

        if manager_company:
            correct_manager_id = manager_company['id']
            if current_manager_company_id != correct_manager_id:
                # Update the FK
                if update_vessel_company_id(vessel_id, manager_company_id=correct_manager_id):
                    manager_company_id_corrected = True
                    validation_log['corrections'].append({
                        'vessel_id': vessel_id,
                        'imo': imo,
                        'field': 'manager_company_id',
                        'old_value': current_manager_company_id,
                        'new_value': correct_manager_id,
                        'company_name': manager_name
                    })
                    validation_log['summary']['manager_company_id_corrections'] += 1
                    notes.append(f"Updated manager_company_id from {current_manager_company_id} to {correct_manager_id}")
        else:
            # Failed to create company
            needs_review = True
            validation_log['missing_companies'].append({
                'vessel_id': vessel_id,
                'imo': imo,
                'field': 'manager/manager_company_id',
                'company_name': manager_name
            })
            notes.append(f"Failed to create company '{manager_name}'")

    # Determine status
    if needs_review:
        status = 'needs_review'
        validation_log['summary']['needs_manual_review'] += 1
    else:
        status = 'success'

    # Insert tracking record
    notes_str = '; '.join(notes) if notes else None
    insert_tracking_record(vessel_id, status, company_id_corrected,
                          manager_company_id_corrected, notes_str)

    validation_log['summary']['total_processed'] += 1

    return {
        'vessel_id': vessel_id,
        'imo': imo,
        'status': status,
        'company_id_corrected': company_id_corrected,
        'manager_company_id_corrected': manager_company_id_corrected
    }


def save_log_file():
    """Save validation log to file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f'vessel_validation_{timestamp}.json'

    with open(log_file, 'w') as f:
        json.dump(validation_log, f, indent=2, default=str)

    print(f"\nLog saved to: {log_file}")


def print_summary():
    """Print validation summary"""
    summary = validation_log['summary']
    print("\n" + "="*60)
    print("VESSEL VALIDATION SUMMARY")
    print("="*60)
    print(f"Total vessels processed: {summary['total_processed']}")
    print(f"Company ID corrections: {summary['company_id_corrections']}")
    print(f"Manager Company ID corrections: {summary['manager_company_id_corrections']}")
    print(f"Companies created: {summary.get('companies_created', 0)}")
    print(f"Vessels needing manual review: {summary['needs_manual_review']}")
    print(f"Errors: {summary['errors']}")
    print("="*60)


async def main():
    batch_size = 10
    size = 6762
    total_batches_processed = 0

    print("Starting vessel validation process...")
    print(f"Batch size: {batch_size}\n")

    for i in range(size):
        try:
            vessels = get_unprocessed_vessels(batch_size)

            if not vessels or len(vessels) == 0:
                print("\nNo more vessels to process!")
                break

            total_batches_processed += 1
            print(f"\nProcessing batch #{total_batches_processed} ({len(vessels)} vessels)...")

            for idx, vessel in enumerate(vessels, 1):
                try:
                    result = validate_vessel(vessel)
                    status_icon = "✓" if result['status'] == 'success' else "⚠"
                    print(f"  {status_icon} Vessel {idx}/{len(vessels)}: ID={result['vessel_id']}, IMO={result['imo']}, Status={result['status']}")

                except Exception as e:
                    print(f"  ✗ Error processing vessel ID {vessel['id']}: {e}")
                    validation_log['errors'].append({
                        'vessel_id': vessel['id'],
                        'imo': vessel.get('imo'),
                        'error': str(e)
                    })
                    validation_log['summary']['errors'] += 1

                    # Still insert tracking record for error case
                    insert_tracking_record(vessel['id'], 'error', notes=str(e))

            print(f"Batch #{total_batches_processed} completed.")

        except KeyboardInterrupt:
            print(f"\n\nScript interrupted by user")
            break
        except Exception as e:
            print(f"Error processing batch: {e}")
            break

    # Print summary and save log
    print_summary()
    save_log_file()


if __name__ == "__main__":
    asyncio.run(main())
