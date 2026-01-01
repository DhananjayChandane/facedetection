import MySQLdb
from MySQLdb.cursors import DictCursor

# Database connection
connection = MySQLdb.connect(
    host='localhost',
    user='root',
    password='@Rupali231985',
    database='attendance_system',
    cursorclass=DictCursor
)
cursor = connection.cursor()

# Check if parent_password column exists
cursor.execute("""
    SELECT COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME='students' AND COLUMN_NAME='parent_password'
""")

result = cursor.fetchone()

if result:
    print("✓ parent_password column already exists in students table")
else:
    print("✗ parent_password column NOT found. Creating it...")
    cursor.execute("""
        ALTER TABLE students 
        ADD COLUMN parent_password VARCHAR(255) DEFAULT NULL
    """)
    connection.commit()
    print("✓ parent_password column created successfully!")

# Verify the table structure
cursor.execute("DESC students")
columns = cursor.fetchall()
print("\nStudents table columns:")
for col in columns:
    print(f"  - {col['Field']}: {col['Type']}")

cursor.close()
connection.close()
