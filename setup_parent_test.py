import MySQLdb
from MySQLdb.cursors import DictCursor
from werkzeug.security import generate_password_hash

# Database connection
connection = MySQLdb.connect(
    host='localhost',
    user='root',
    password='@Rupali231985',
    database='attendance_system',
    cursorclass=DictCursor
)
cursor = connection.cursor()

# Create a test student for parent portal
try:
    test_roll_no = "TEST-2024-001"
    test_parent_password = "ParentPass123"
    
    # Hash the parent password
    hashed_parent_password = generate_password_hash(test_parent_password)
    
    # Check if test student already exists
    cursor.execute("SELECT id FROM students WHERE roll_number = %s", (test_roll_no,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing test student
        cursor.execute("""
            UPDATE students 
            SET parent_password = %s
            WHERE roll_number = %s
        """, (hashed_parent_password, test_roll_no))
        print(f"✓ Updated test student: {test_roll_no}")
        print(f"  Parent Password: {test_parent_password}")
    else:
        # Create new test student
        cursor.execute("""
            INSERT INTO students (username, password, full_name, email, phone, roll_number, parent_password, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "teststudent",
            generate_password_hash("TestStudent123"),
            "Test Student",
            "test@example.com",
            "9876543210",
            test_roll_no,
            hashed_parent_password,
            1
        ))
        print(f"✓ Created test student account:")
        print(f"  Roll Number: {test_roll_no}")
        print(f"  Parent Password: {test_parent_password}")
    
    connection.commit()
    print("\n✓ Parent Portal Database Setup Complete!")
    print("\nYou can now test parent login with:")
    print(f"  Roll Number: {test_roll_no}")
    print(f"  Parent Password: {test_parent_password}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    connection.rollback()
finally:
    cursor.close()
    connection.close()
