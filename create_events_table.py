"""
Script to create classroom_events table in the database
Run this script once to set up the events table
"""
import MySQLdb
import sys

# Database configuration - Update these if needed
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '@Rupali231985',
    'database': 'attendance_system'
}

def create_events_table():
    """Create the classroom_events table"""
    try:
        # Connect to database
        conn = MySQLdb.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Creating classroom_events table...")
        
        # Create table SQL
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS classroom_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            classroom_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            description LONGTEXT,
            event_date DATE NOT NULL,
            event_time TIME,
            event_type ENUM('assignment', 'exam', 'lecture', 'project', 'quiz', 'other') DEFAULT 'other',
            created_by INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES teachers(id) ON DELETE CASCADE,
            INDEX idx_classroom_date (classroom_id, event_date),
            INDEX idx_event_date (event_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        print("[SUCCESS] Table 'classroom_events' created successfully!")
        
        # Verify table exists
        cursor.execute("SHOW TABLES LIKE 'classroom_events'")
        if cursor.fetchone():
            print("[SUCCESS] Table verification successful!")
        else:
            print("[WARNING] Table creation may have failed")
        
        cursor.close()
        conn.close()
        
        return True
        
    except MySQLdb.Error as e:
        print(f"[ERROR] Error creating table: {e}")
        print(f"Error code: {e.args[0]}")
        print(f"Error message: {e.args[1]}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("Classroom Events Table Creation Script")
    print("=" * 50)
    print()
    
    success = create_events_table()
    
    print()
    if success:
        print("=" * 50)
        print("Setup completed successfully!")
        print("You can now use the events feature.")
        print("=" * 50)
        sys.exit(0)
    else:
        print("=" * 50)
        print("Setup failed. Please check the error messages above.")
        print("=" * 50)
        sys.exit(1)

