import MySQLdb
from MySQLdb.cursors import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash

# Database connection
connection = MySQLdb.connect(
    host='localhost',
    user='root',
    password='@Rupali231985',
    database='attendance_system',
    cursorclass=DictCursor
)
cursor = connection.cursor()

print("=" * 60)
print("TESTING PARENT PORTAL SYSTEM")
print("=" * 60)

try:
    # 1. Check if any student with roll_number exists
    print("\n1. Checking existing students with roll numbers...")
    cursor.execute("SELECT id, username, full_name, roll_number, parent_password FROM students WHERE roll_number IS NOT NULL AND roll_number != '' LIMIT 5")
    students_with_roll = cursor.fetchall()
    
    if students_with_roll:
        print(f"   ✓ Found {len(students_with_roll)} students with roll numbers:")
        for student in students_with_roll:
            has_parent_pwd = "Yes" if student['parent_password'] else "No"
            print(f"     - {student['full_name']} (Roll: {student['roll_number']}, Parent Pwd: {has_parent_pwd})")
    else:
        print("   ✗ No students with roll numbers found")
    
    # 2. Check if test student has parent_password set
    print("\n2. Checking TEST-2024-001 account...")
    cursor.execute("SELECT id, username, full_name, roll_number, parent_password FROM students WHERE roll_number = %s", ("TEST-2024-001",))
    test_student = cursor.fetchone()
    
    if test_student:
        print(f"   ✓ Test student found: {test_student['full_name']}")
        print(f"     Roll Number: {test_student['roll_number']}")
        print(f"     Parent Password Hash: {'SET' if test_student['parent_password'] else 'NOT SET'}")
        
        # Test password verification
        if test_student['parent_password']:
            pwd_test = check_password_hash(test_student['parent_password'], 'ParentPass123')
            print(f"     Password 'ParentPass123' verification: {'✓ VALID' if pwd_test else '✗ INVALID'}")
    else:
        print("   ✗ Test student not found")
    
    # 3. Check if test student has any classrooms enrolled
    print("\n3. Checking test student's classroom enrollment...")
    if test_student:
        student_id = test_student['id']
        cursor.execute('''
            SELECT c.id, c.class_name, c.class_code, t.full_name as teacher_name
            FROM classrooms c
            JOIN classroom_students cs ON c.id = cs.classroom_id
            JOIN teachers t ON c.teacher_id = t.id
            WHERE cs.student_id = %s
        ''', (student_id,))
        classrooms = cursor.fetchall()
        
        if classrooms:
            print(f"   ✓ Student enrolled in {len(classrooms)} classroom(s):")
            for classroom in classrooms:
                print(f"     - {classroom['class_name']} (Code: {classroom['class_code']}, Teacher: {classroom['teacher_name']})")
        else:
            print("   ⚠ Student not enrolled in any classrooms")
            print("     You may need to enroll the test student in a classroom for attendance data")
    
    # 4. Check attendance records for test student
    print("\n4. Checking attendance records...")
    if test_student:
        student_id = test_student['id']
        cursor.execute('''
            SELECT COUNT(*) as total FROM attendance WHERE student_id = %s
        ''', (student_id,))
        attendance_count = cursor.fetchone()
        
        if attendance_count['total'] > 0:
            print(f"   ✓ Found {attendance_count['total']} attendance record(s)")
            
            # Get summary
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present,
                    SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as absent,
                    SUM(CASE WHEN status = 'L' THEN 1 ELSE 0 END) as leaves
                FROM attendance WHERE student_id = %s
            ''', (student_id,))
            summary = cursor.fetchone()
            print(f"     Present: {summary['present'] or 0}, Absent: {summary['absent'] or 0}, Leaves: {summary['leaves'] or 0}")
        else:
            print("   ⚠ No attendance records found for test student")

    print("\n" + "=" * 60)
    print("PARENT PORTAL TEST CREDENTIALS")
    print("=" * 60)
    print("\nUse these credentials to test the parent portal:")
    print("  Roll Number: TEST-2024-001")
    print("  Parent Password: ParentPass123")
    print("\nLogin at: /parent_login")
    print("=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    cursor.close()
    connection.close()
