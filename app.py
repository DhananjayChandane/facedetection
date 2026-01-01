import os
import cv2
import numpy as np
import pandas as pd
import face_recognition
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, make_response, g, current_app
# from flask_mysqldb import MySQL
import MySQLdb
import MySQLdb.cursors
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import io
import json
from functools import wraps
import base64
import threading
import time

# Import custom modules
from face_recognition_utils import FaceUtils
from excel_generator import ExcelGenerator

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '@Rupali231985'
app.config['MYSQL_DB'] = 'attendance_system'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Custom MySQL class to handle connection management
class MySQL:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        app.teardown_appcontext(self.teardown)

    @property
    def connection(self):
        if 'db' not in g:
            g.db = MySQLdb.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                passwd=current_app.config['MYSQL_PASSWORD'],
                db=current_app.config['MYSQL_DB']
            )
        return g.db

    def teardown(self, exception):
        db = g.pop('db', None)
        if db is not None:
            db.close()

# Initialize MySQL
mysql = MySQL(app)

face_utils = FaceUtils()

# Configure reports directory with absolute path
reports_dir = os.path.join(app.root_path, 'reports')
os.makedirs(reports_dir, exist_ok=True)
excel_gen = ExcelGenerator(reports_dir=reports_dir)

# Jinja2 filter to format time (handles both time and timedelta objects)
@app.template_filter('format_time')
def format_time_filter(value):
    """Format time or timedelta object to string"""
    if value is None:
        return ''
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f'{hours:02d}:{minutes:02d}'
    elif hasattr(value, 'strftime'):
        return value.strftime('%I:%M %p')
    return str(value)

# Create other directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('face_encodings', exist_ok=True)
os.makedirs('temp', exist_ok=True)

# ==================== BACKGROUND TASKS ====================

def cleanup_expired_events():
    """Background task to automatically delete expired classroom events"""
    while True:
        try:
            # Sleep for 1 hour before checking again
            time.sleep(3600)
            
            # Connect to database
            conn = MySQLdb.connect(
                host=app.config['MYSQL_HOST'],
                user=app.config['MYSQL_USER'],
                passwd=app.config['MYSQL_PASSWORD'],
                db=app.config['MYSQL_DB']
            )
            cursor = conn.cursor()
            
            # Delete events that are more than 7 days old
            deletion_date = (datetime.now() - timedelta(days=7)).date()
            cursor.execute('''
                DELETE FROM classroom_events 
                WHERE event_date < %s
            ''', (deletion_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                print(f"[Cleanup Task] Deleted {deleted_count} expired classroom events")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[Cleanup Task Error] {str(e)}")
            try:
                cursor.close()
                conn.close()
            except:
                pass

# Start background cleanup task in a separate thread
cleanup_thread = threading.Thread(target=cleanup_expired_events, daemon=True)
cleanup_thread.start()

# ==================== DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'teacher':
            flash('Teacher access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'student':
            flash('Student access required', 'danger')
            return redirect(url_for('teacher_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== UTILITY FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_db_connection():
    return mysql.connection

# ==================== ROUTES ====================

@app.route('/')
def index():
    if 'user_id' in session:
        if session['user_type'] == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_method = request.form.get('login_method', 'password')
        
        # Password-based login
        if login_method == 'password':
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            user_type = request.form.get('user_type', 'student')
            
            if not username or not password:
                flash('Username and password are required', 'danger')
                return render_template('login.html')
            
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            
            try:
                if user_type == 'teacher':
                    cursor.execute('SELECT * FROM teachers WHERE username = %s', (username,))
                else:
                    cursor.execute('SELECT * FROM students WHERE username = %s', (username,))
                
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['user_type'] = user_type
                    session['full_name'] = user.get('full_name', user['username'])
                    
                    # Check if face is registered
                    if user.get('face_encoding') is not None:
                        session['face_registered'] = True
                    else:
                        session['face_registered'] = False
                    
                    flash('Login successful!', 'success')
                    
                    if user_type == 'teacher':
                        return redirect(url_for('teacher_dashboard'))
                    else:
                        return redirect(url_for('dashboard'))
                else:
                    flash('Invalid username or password', 'danger')
            except Exception as e:
                flash(f'Login error: {str(e)}', 'danger')
                print(f"Login error: {e}")
            finally:
                cursor.close()
        
        # Face-based login
        elif login_method == 'face':
            if 'face_image' not in request.files:
                return jsonify({'success': False, 'message': 'No image provided'})
            
            file = request.files['face_image']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No image selected'})
            
            try:
                # Read image
                img_bytes = file.read()
                nparr = np.frombuffer(img_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is None:
                    return jsonify({'success': False, 'message': 'Invalid image format'})
                
                # Extract face encoding
                unknown_encoding = face_utils.extract_face_encoding(image)
                
                if unknown_encoding is None:
                    return jsonify({'success': False, 'message': 'No face detected in image'})
                
                # Get all users with registered faces (both students and teachers)
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                
                # Check students
                cursor.execute('''
                    SELECT id, full_name, face_encoding, 'student' as user_type
                    FROM students
                    WHERE face_encoding IS NOT NULL
                ''')
                students = cursor.fetchall()
                
                # Check teachers
                cursor.execute('''
                    SELECT id, full_name, face_encoding, 'teacher' as user_type
                    FROM teachers
                    WHERE face_encoding IS NOT NULL
                ''')
                teachers = cursor.fetchall()
                
                all_users = students + teachers
                
                if not all_users:
                    cursor.close()
                    return jsonify({'success': False, 'message': 'No registered users found'})
                
                # Compare with all known encodings
                known_encodings = []
                user_ids = []
                user_names = []
                user_types = []
                
                for user in all_users:
                    if user['face_encoding']:
                        encoding = np.frombuffer(user['face_encoding'], dtype=np.float64)
                        known_encodings.append(encoding)
                        user_ids.append(user['id'])
                        user_names.append(user['full_name'])
                        user_types.append(user['user_type'])
                
                # Recognize face
                face_index, distance = face_utils.recognize_face_from_list(unknown_encoding, known_encodings)
                
                if face_index is not None:
                    user_id = user_ids[face_index]
                    user_name = user_names[face_index]
                    user_type = user_types[face_index]
                    
                    # Set session
                    session['user_id'] = user_id
                    session['username'] = user_name
                    session['user_type'] = user_type
                    session['full_name'] = user_name
                    session['face_registered'] = True
                    
                    cursor.close()
                    
                    return jsonify({
                        'success': True,
                        'message': f'Welcome {user_name}!',
                        'redirect': url_for('teacher_dashboard') if user_type == 'teacher' else url_for('dashboard')
                    })
                else:
                    cursor.close()
                    return jsonify({'success': False, 'message': 'Face not recognized. Please use password login.'})
                    
            except Exception as e:
                print(f"Face login error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        full_name = request.form.get('full_name', '')
        user_type = request.form.get('user_type', 'student')
        
        # Check if username exists
        cursor = mysql.connection.cursor()
        if user_type == 'teacher':
            cursor.execute('SELECT id FROM teachers WHERE username = %s', (username,))
        else:
            cursor.execute('SELECT id FROM students WHERE username = %s', (username,))
        
        if cursor.fetchone():
            flash('Username already exists', 'danger')
            cursor.close()
            return redirect(url_for('signup'))
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        # Insert user
        if user_type == 'teacher':
            cursor.execute('''
                INSERT INTO teachers (username, password, email, full_name) 
                VALUES (%s, %s, %s, %s)
            ''', (username, hashed_password, email, full_name))
        else:
            cursor.execute('''
                INSERT INTO students (username, password, email, full_name) 
                VALUES (%s, %s, %s, %s)
            ''', (username, hashed_password, email, full_name))
        
        mysql.connection.commit()
        cursor.close()
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
@student_required
def dashboard():
    student_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if face is registered and roll_number is filled
    cursor.execute('SELECT face_encoding, roll_number FROM students WHERE id = %s', (student_id,))
    user_data = cursor.fetchone()
    face_registered = user_data and user_data['face_encoding'] is not None
    
    # Show alert if roll_number is missing
    if user_data and not user_data.get('roll_number'):
        flash('⚠️ Important: Please update your profile with your Roll Number. This is required for attendance tracking.', 'warning')

    # Get enrolled classrooms
    cursor.execute('''
        SELECT c.id, c.class_name, c.class_code, c.schedule_time, c.venue, t.full_name as teacher_name
        FROM classrooms c
        JOIN classroom_students cs ON c.id = cs.classroom_id
        JOIN teachers t ON c.teacher_id = t.id
        WHERE cs.student_id = %s
    ''', (student_id,))
    classrooms = cursor.fetchall()
    
    # Get attendance summary
    attendance_summary = []
    total_present_all = 0
    total_absent_all = 0
    total_days_all = 0
    
    for classroom in classrooms:
        cursor.execute('''
            SELECT 
                COUNT(*) as total_days,
                SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present_days,
                SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as absent_days
            FROM attendance
            WHERE student_id = %s AND classroom_id = %s
        ''', (student_id, classroom['id']))
        
        summary = cursor.fetchone()
        present = summary['present_days'] or 0
        absent = summary['absent_days'] or 0
        total = summary['total_days'] or 0
        
        if total > 0:
            percentage = (present / total) * 100
        else:
            percentage = 0
        
        total_present_all += present
        total_absent_all += absent
        total_days_all += total
        
        attendance_summary.append({
            'class_id': classroom['id'],
            'class_name': classroom['class_name'],
            'schedule_time': classroom.get('schedule_time'),
            'venue': classroom.get('venue'),
            'present': present,
            'total': total,
            'percentage': round(percentage, 2)
        })
    
    # Calculate overall statistics
    if total_days_all > 0:
        overall_attendance = round((total_present_all / total_days_all) * 100, 1)
    else:
        overall_attendance = 0
    
    # Get today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT a.id, a.classroom_id, c.class_name
        FROM attendance a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE a.student_id = %s AND a.date = %s AND a.status = 'P'
    ''', (student_id, today))
    today_attendance = cursor.fetchall()
    
    # Get monthly data for chart
    cursor.execute('''
        SELECT 
            DATE_FORMAT(MIN(a.date), '%%b') as month_name,
            MONTH(a.date) as month_num,
            ROUND(SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as percentage
        FROM attendance a
        WHERE a.student_id = %s AND YEAR(a.date) = YEAR(CURDATE())
        GROUP BY MONTH(a.date), YEAR(a.date)
        ORDER BY MONTH(a.date) ASC
    ''', (student_id,))
    monthly_data = cursor.fetchall()
    
    # Get upcoming events for each classroom (next 7 days)
    today_date = datetime.now().date()
    next_week = today_date + timedelta(days=7)
    
    classroom_events = {}
    for classroom in classrooms:
        cursor.execute('''
            SELECT id, title, description, event_date, event_time, event_type
            FROM classroom_events
            WHERE classroom_id = %s AND event_date BETWEEN %s AND %s
            ORDER BY event_date ASC, event_time ASC
            LIMIT 5
        ''', (classroom['id'], today_date, next_week))
        
        events_raw = cursor.fetchall()
        # Convert timedelta to time for event_time fields
        events = []
        for event in events_raw:
            event_dict = dict(event)
            if event_dict.get('event_time') and isinstance(event_dict['event_time'], timedelta):
                # Convert timedelta to time object
                total_seconds = int(event_dict['event_time'].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                event_dict['event_time'] = datetime.strptime(f'{hours:02d}:{minutes:02d}', '%H:%M').time()
            events.append(event_dict)
        classroom_events[classroom['id']] = events
    
    cursor.close()
    
    return render_template('dashboard.html', 
                         classrooms=classrooms, 
                         attendance_summary=attendance_summary,
                         face_registered=face_registered,
                         total_classrooms=len(classrooms),
                         overall_attendance=overall_attendance,
                         total_present=total_present_all,
                         total_absent=total_absent_all,
                         today_attendance=today_attendance,
                         monthly_data=monthly_data,
                         classroom_events=classroom_events)

@app.route('/api/attendance_stats')
@login_required
def dashboard_stats():
    """API endpoint for dashboard stats"""
    student_id = session['user_id']
    if session['user_type'] != 'student':
        return jsonify({'error': 'Not authorized'}), 403
        
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get overall stats
    cursor.execute('''
        SELECT 
            COUNT(*) as total_days,
            SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present_days
        FROM attendance
        WHERE student_id = %s
    ''', (student_id,))
    
    stats = cursor.fetchone()
    cursor.close()
    
    return jsonify({
        'total_days': stats['total_days'] or 0,
        'present_days': stats['present_days'] or 0,
        'attendance_percentage': round((stats['present_days'] / stats['total_days'] * 100) if stats['total_days'] else 0, 1)
    })


@app.route('/teacher_dashboard')
@login_required
@teacher_required
def teacher_dashboard():
    teacher_id = session['user_id']
    active_tab = request.args.get('tab', 'overview')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if face is registered
    cursor.execute('SELECT face_encoding FROM teachers WHERE id = %s', (teacher_id,))
    user_data = cursor.fetchone()
    face_registered = user_data and user_data['face_encoding'] is not None

    # Get teacher's classrooms
    cursor.execute('''
        SELECT c.*, 
               COUNT(DISTINCT cs.student_id) as student_count
        FROM classrooms c
        LEFT JOIN classroom_students cs ON c.id = cs.classroom_id
        WHERE c.teacher_id = %s
        GROUP BY c.id
    ''', (teacher_id,))
    classrooms = cursor.fetchall()
    
    # Get recent attendance
    cursor.execute('''
        SELECT a.*, s.full_name as student_name, c.class_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE c.teacher_id = %s
        ORDER BY a.date DESC, a.marked_at DESC
        LIMIT 20
    ''', (teacher_id,))
    recent_attendance = cursor.fetchall()
    
    # Get today's attendance stats
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as absent_count,
            COUNT(*) as total_count
        FROM attendance a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE c.teacher_id = %s AND a.date = %s
    ''', (teacher_id, today))
    
    today_stats = cursor.fetchone()
    present_count = today_stats['present_count'] or 0
    absent_count = today_stats['absent_count'] or 0
    total_count = today_stats['total_count'] or 0
    
    # Calculate overall attendance percentage
    cursor.execute('''
        SELECT 
            COUNT(*) as total_records,
            SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present_records
        FROM attendance a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE c.teacher_id = %s
    ''', (teacher_id,))
    
    overall_stats = cursor.fetchone()
    overall_total = overall_stats['total_records'] or 0
    overall_present = overall_stats['present_records'] or 0
    attendance_percentage = round((overall_present / overall_total * 100), 1) if overall_total > 0 else 0
    
    # Get yesterday's stats for comparison
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present_count
        FROM attendance a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE c.teacher_id = %s AND a.date = %s
    ''', (teacher_id, yesterday))
    
    yesterday_stats = cursor.fetchone()
    yesterday_present = yesterday_stats['present_count'] or 0
    
    # Calculate percentage change
    present_change = present_count - yesterday_present if yesterday_present > 0 else 0
    present_percentage_change = round((present_change / yesterday_present * 100), 1) if yesterday_present > 0 else 0
    
    cursor.close()
    
    return render_template('teacher_dashboard.html', 
                         classrooms=classrooms, 
                         recent_attendance=recent_attendance,
                         face_registered=face_registered,
                         active_tab=active_tab,
                         today=today,
                         present_count=present_count,
                         absent_count=absent_count,
                         total_count=total_count,
                         attendance_percentage=attendance_percentage,
                         present_change=present_change,
                         present_percentage_change=present_percentage_change)

@app.route('/qr_code/<int:classroom_id>')
@login_required
@teacher_required
def qr_code(classroom_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM classrooms WHERE id = %s AND teacher_id = %s', (classroom_id, session['user_id']))
    classroom = cursor.fetchone()
    cursor.close()
    if not classroom:
        flash('Classroom not found', 'danger')
        return redirect(url_for('teacher_dashboard'))
    join_url = url_for('join_classroom_qr', class_code=classroom['class_code'], _external=True)
    attendance_url = url_for('mark_attendance', classroom_id=classroom_id, _external=True)
    return render_template('join_qr.html', classroom=classroom, join_url=join_url, attendance_url=attendance_url)

@app.route('/manage_attendance/<int:classroom_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def manage_attendance(classroom_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Verify ownership
    cursor.execute('SELECT * FROM classrooms WHERE id = %s AND teacher_id = %s', 
                  (classroom_id, session['user_id']))
    classroom = cursor.fetchone()
    
    if not classroom:
        cursor.close()
        flash('Classroom not found or access denied', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Handle manual attendance update
    if request.method == 'POST':
        action = request.form.get('action', 'update')
        
        if action == 'add_missing':
            # Add attendance for student who missed marking
            student_id = request.form.get('student_id')
            status = request.form.get('status', 'P')
            date_str = request.form.get('date')
            
            try:
                # Check if record exists
                cursor.execute('''
                    SELECT id FROM attendance 
                    WHERE student_id = %s AND classroom_id = %s AND date = %s
                ''', (student_id, classroom_id, date_str))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute('''
                        UPDATE attendance 
                        SET status = %s, marked_at = NOW()
                        WHERE id = %s
                    ''', (status, existing['id']))
                    msg = 'Attendance updated successfully'
                else:
                    # Create new record for missed attendance
                    cursor.execute('''
                        INSERT INTO attendance (student_id, classroom_id, date, marked_at, status)
                        VALUES (%s, %s, %s, NOW(), %s)
                    ''', (student_id, classroom_id, date_str, status))
                    msg = 'Attendance added successfully for missing student'
                
                mysql.connection.commit()
                flash(msg, 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash(f'Error updating attendance: {e}', 'danger')
        else:
            # Regular update
            student_id = request.form.get('student_id')
            status = request.form.get('status')
            date_str = request.form.get('date')
            
            try:
                # Check if record exists
                cursor.execute('''
                    SELECT id FROM attendance 
                    WHERE student_id = %s AND classroom_id = %s AND date = %s
                ''', (student_id, classroom_id, date_str))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute('''
                        UPDATE attendance SET status = %s, marked_at = NOW()
                        WHERE id = %s
                    ''', (status, existing['id']))
                else:
                    cursor.execute('''
                        INSERT INTO attendance (student_id, classroom_id, date, marked_at, status)
                        VALUES (%s, %s, %s, NOW(), %s)
                    ''', (student_id, classroom_id, date_str, status))
                
                mysql.connection.commit()
                flash('Attendance updated successfully', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash(f'Error updating attendance: {e}', 'danger')
            
        return redirect(url_for('manage_attendance', classroom_id=classroom_id, date=date_str))

    # GET: Show list
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get all enrolled students
    cursor.execute('''
        SELECT s.id, s.full_name, s.roll_number, s.profile_image
        FROM students s
        JOIN classroom_students cs ON s.id = cs.student_id
        WHERE cs.classroom_id = %s
        ORDER BY s.roll_number
    ''', (classroom_id,))
    students = cursor.fetchall()
    
    # Get attendance for date
    cursor.execute('''
        SELECT student_id, status, marked_at
        FROM attendance
        WHERE classroom_id = %s AND date = %s
    ''', (classroom_id, date_str))
    attendance_records = {row['student_id']: row for row in cursor.fetchall()}
    
    # Separate students into marked and missing
    student_list = []
    missing_students = []
    
    for student in students:
        record = attendance_records.get(student['id'])
        if record:
            # Student marked attendance
            student['status'] = record['status']
            student['time'] = record['marked_at'].strftime('%H:%M') if record['marked_at'] else '-'
            student_list.append(student)
        else:
            # Student missed marking attendance
            student['status'] = 'Not Marked'
            student['time'] = '-'
            missing_students.append(student)
        
    cursor.close()
    return render_template('manage_attendance.html', 
                         classroom=classroom, 
                         students=student_list, 
                         missing_students=missing_students,
                         date=date_str, 
                         datetime=datetime.now())

@app.route('/export_report/<int:classroom_id>')
@login_required
@teacher_required
def export_report(classroom_id):
    # Verify ownership
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM classrooms WHERE id = %s AND teacher_id = %s', 
                  (classroom_id, session['user_id']))
    if not cursor.fetchone():
        cursor.close()
        flash('Access denied', 'danger')
        return redirect(url_for('teacher_dashboard'))
    cursor.close()
    
    # Generate report
    filepath = excel_gen.generate_attendance_report(classroom_id, mysql.connection)
    
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    else:
        flash('Error generating report or no data available', 'danger')
        return redirect(url_for('teacher_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/parent_login', methods=['GET', 'POST'])
def parent_login():
    """Parent login using student roll_no and parent password"""
    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip()
        parent_password = request.form.get('parent_password', '')
        
        if not roll_no or not parent_password:
            flash('Roll Number and Password are required', 'danger')
            return render_template('parent_login.html')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        try:
            # Find student by roll_number
            cursor.execute('SELECT id, full_name, roll_number, parent_password FROM students WHERE roll_number = %s', (roll_no,))
            student = cursor.fetchone()
            
            if student and student['parent_password'] and check_password_hash(student['parent_password'], parent_password):
                # Parent login successful
                session['parent_user_id'] = student['id']
                session['student_name'] = student['full_name']
                session['student_roll_no'] = student['roll_number']
                session['user_type'] = 'parent'
                flash(f"Welcome! You are viewing {student['full_name']}'s information", 'success')
                cursor.close()
                return redirect(url_for('parent_dashboard'))
            else:
                flash('Invalid Roll Number or Password', 'danger')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
            print(f"Parent login error: {e}")
        finally:
            cursor.close()
    
    return render_template('parent_login.html')

@app.route('/parent_dashboard')
def parent_dashboard():
    """Parent dashboard showing student information"""
    if session.get('user_type') != 'parent' or not session.get('parent_user_id'):
        flash('Parent access required', 'danger')
        return redirect(url_for('parent_login'))
    
    student_id = session['parent_user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Get student information
        cursor.execute('SELECT * FROM students WHERE id = %s', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            flash('Student not found', 'danger')
            cursor.close()
            return redirect(url_for('parent_login'))
        
        # Get all enrolled classrooms
        cursor.execute('''
            SELECT c.id, c.class_name, c.class_code, c.schedule_time, c.venue, t.full_name as teacher_name
            FROM classrooms c
            JOIN classroom_students cs ON c.id = cs.classroom_id
            JOIN teachers t ON c.teacher_id = t.id
            WHERE cs.student_id = %s
            ORDER BY c.class_name
        ''', (student_id,))
        classrooms = cursor.fetchall()
        
        # Get attendance summary for each classroom
        attendance_data = {}
        for classroom in classrooms:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_days,
                    SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present_days,
                    SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as absent_days,
                    SUM(CASE WHEN status = 'L' THEN 1 ELSE 0 END) as leave_days
                FROM attendance
                WHERE student_id = %s AND classroom_id = %s
            ''', (student_id, classroom['id']))
            
            summary = cursor.fetchone()
            present = summary['present_days'] or 0
            total = summary['total_days'] or 0
            absent = summary['absent_days'] or 0
            leaves = summary['leave_days'] or 0
            
            percentage = round((present / total) * 100, 1) if total > 0 else 0
            
            attendance_data[classroom['id']] = {
                'present': present,
                'absent': absent,
                'leaves': leaves,
                'total': total,
                'percentage': percentage,
                'status': 'Good' if percentage >= 75 else 'Warning' if percentage >= 60 else 'Critical'
            }
        
        # Get recent attendance records
        cursor.execute('''
            SELECT a.*, c.class_name
            FROM attendance a
            JOIN classrooms c ON a.classroom_id = c.id
            WHERE a.student_id = %s
            ORDER BY a.date DESC
            LIMIT 20
        ''', (student_id,))
        recent_attendance = cursor.fetchall()
        
        # Get overall statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as total_present,
                SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as total_absent,
                SUM(CASE WHEN status = 'L' THEN 1 ELSE 0 END) as total_leaves
            FROM attendance
            WHERE student_id = %s
        ''', (student_id,))
        
        overall = cursor.fetchone()
        total_records = overall['total_records'] or 0 if overall else 0
        total_present = overall['total_present'] or 0 if overall else 0
        total_absent = overall['total_absent'] or 0 if overall else 0
        total_leaves = overall['total_leaves'] or 0 if overall else 0
        overall_percentage = round((total_present / total_records) * 100, 1) if total_records > 0 else 0
        
        cursor.close()
        
        # Prepare overall stats dictionary for template
        overall_stats = {
            'total_records': total_records,
            'total_present': total_present,
            'total_absent': total_absent,
            'total_leaves': total_leaves
        }
        
        return render_template('parent_dashboard.html',
                             student=student,
                             classrooms=classrooms,
                             attendance_data=attendance_data,
                             recent_attendance=recent_attendance,
                             overall_percentage=overall_percentage,
                             overall=overall_stats,
                             total_classrooms=len(classrooms))
    
    except Exception as e:
        print(f"Parent dashboard error: {e}")
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        cursor.close()
        return redirect(url_for('parent_login'))

@app.route('/parent_logout')
def parent_logout():
    """Parent logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('parent_login'))

@app.route('/create_classroom', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_classroom():
    if request.method == 'POST':
        class_name = request.form['class_name']
        class_code = request.form['class_code']
        description = request.form.get('description', '')
        teacher_id = session['user_id']
        
        # New fields
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        schedule_days = request.form.get('schedule_days', '')
        venue = request.form.get('venue', '')
        
        # Format schedule_time for display
        schedule_time = f"{schedule_days} {start_time} - {end_time}" if schedule_days and start_time else ""
        
        cursor = mysql.connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO classrooms (teacher_id, class_name, class_code, description, start_time, end_time, schedule_time, venue)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (teacher_id, class_name, class_code, description, start_time, end_time, schedule_time, venue))
            classroom_id = cursor.lastrowid
            mysql.connection.commit()
            flash('Classroom created successfully!', 'success')
            # Redirect to QR code page to show the generated QR code
            return redirect(url_for('qr_code', classroom_id=classroom_id))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error creating classroom: {str(e)}', 'danger')
        finally:
            cursor.close()
    
    return render_template('create_classroom.html')

@app.route('/join_classroom', methods=['POST'])
@login_required
@student_required
def join_classroom():
    class_code = request.form['class_code']
    student_id = session['user_id']
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Find classroom
    cursor.execute('SELECT id FROM classrooms WHERE class_code = %s', (class_code,))
    classroom = cursor.fetchone()
    
    if not classroom:
        flash('Invalid class code', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if already joined
    cursor.execute('''
        SELECT * FROM classroom_students 
        WHERE student_id = %s AND classroom_id = %s
    ''', (student_id, classroom['id']))
    
    if cursor.fetchone():
        flash('Already joined this classroom', 'info')
    else:
        try:
            cursor.execute('''
                INSERT INTO classroom_students (student_id, classroom_id) 
                VALUES (%s, %s)
            ''', (student_id, classroom['id']))
            mysql.connection.commit()
            flash('Successfully joined classroom!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error joining classroom: {str(e)}', 'danger')
    
    cursor.close()
    return redirect(url_for('dashboard'))

@app.route('/join/<class_code>', methods=['GET'])
@login_required
@student_required
def join_classroom_qr(class_code):
    student_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Find classroom
    cursor.execute('SELECT * FROM classrooms WHERE class_code = %s', (class_code,))
    classroom = cursor.fetchone()
    
    if not classroom:
        cursor.close()
        flash('Invalid class code', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if already joined
    cursor.execute('''
        SELECT * FROM classroom_students 
        WHERE student_id = %s AND classroom_id = %s
    ''', (student_id, classroom['id']))
    
    already_joined = cursor.fetchone() is not None
    
    if not already_joined:
        # Auto-join the classroom
        try:
            cursor.execute('''
                INSERT INTO classroom_students (student_id, classroom_id) 
                VALUES (%s, %s)
            ''', (student_id, classroom['id']))
            mysql.connection.commit()
            flash('Successfully joined classroom!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error joining classroom: {str(e)}', 'danger')
    else:
        flash('You are already enrolled in this classroom', 'info')
    
    cursor.close()
    return redirect(url_for('dashboard'))

@app.route('/capture_face', methods=['GET', 'POST'])
@login_required
def capture_face():
    # Get redirect URL from query param
    next_page = request.args.get('next')
    
    if request.method == 'POST':
        if 'face_image' not in request.files:
            flash('No image uploaded', 'danger')
            return redirect(request.url)
        
        file = request.files['face_image']
        if file.filename == '':
            flash('No image selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                user_id = session['user_id']
                print(f"Processing face registration for user {user_id}")
                # Read image
                img_bytes = file.read()
                nparr = np.frombuffer(img_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is None:
                    print("Error: Image decode failed")
                    flash('Invalid image format', 'danger')
                    return redirect(request.url)

                # Extract face encoding
                print("Extracting face encoding...")
                encoding = face_utils.extract_face_encoding(image)
                
                if encoding is None:
                    print("Error: No face detected in image")
                    flash('No face detected. Please try again with better lighting and ensure your face is clearly visible.', 'danger')
                    return redirect(request.url)
                
                print(f"Face detected. Encoding shape: {encoding.shape}")
                
                # Save encoding
                user_id = session['user_id']
                user_type = session['user_type']
                
                table = 'teachers' if user_type == 'teacher' else 'students'
                cursor = mysql.connection.cursor()
                
                # Convert encoding to bytes
                encoding_bytes = encoding.tobytes()
                
                print(f"Updating database for {table} id {user_id}")
                cursor.execute(f'''
                    UPDATE {table} 
                    SET face_encoding = %s, face_registered_at = NOW()
                    WHERE id = %s
                ''', (encoding_bytes, user_id))
                
                mysql.connection.commit()
                print("Database updated successfully")
                cursor.close()
                
                # Also save to file for backup
                try:
                    np.save(f'face_encodings/{user_id}_{user_type}.npy', encoding)
                except Exception as e:
                    print(f"Error saving backup encoding: {e}")
                
                flash('Face registered successfully!', 'success')
                
                # Update session to reflect face registration
                session['face_registered'] = True
                
                # Redirect to next page if provided, else dashboard
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                print(f"Error in capture_face: {e}")
                flash(f'An error occurred: {str(e)}', 'danger')
                return redirect(request.url)
    
    return render_template('capture_face.html')

@app.route('/mark_attendance/<int:classroom_id>', methods=['GET', 'POST'])
@login_required
@student_required
def mark_attendance(classroom_id):
    # GET request: Render the page
    if request.method == 'GET':
        student_id = session['user_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Check enrollment
        cursor.execute('''
            SELECT * FROM classroom_students 
            WHERE student_id = %s AND classroom_id = %s
        ''', (student_id, classroom_id))
        
        if not cursor.fetchone():
            flash('You are not enrolled in this classroom', 'danger')
            cursor.close()
            return redirect(url_for('dashboard'))
            
        # Get classroom info
        cursor.execute('SELECT * FROM classrooms WHERE id = %s', (classroom_id,))
        classroom = cursor.fetchone()
        cursor.close()
        
        # Check time window if start_time/end_time are set
        if classroom.get('start_time') and classroom.get('end_time'):
            # Convert timedelta to datetime.time if necessary, or parse string
            # MySQLdb returns TIME columns as timedelta objects usually
            current_time = datetime.now().time()
            
            # Helper to convert timedelta/string to time
            def to_time(t):
                if isinstance(t, str):
                    return datetime.strptime(t, '%H:%M:%S').time()
                if isinstance(t, timedelta):
                    return (datetime.min + t).time()
                return t

            start_time = to_time(classroom['start_time'])
            end_time = to_time(classroom['end_time'])
            
            # Create datetime objects for comparison (using today's date)
            now = datetime.now()
            start_dt = datetime.combine(now.date(), start_time)
            end_dt = datetime.combine(now.date(), end_time)
            
            # Add buffers
            start_window = start_dt - timedelta(minutes=15)
            end_window = end_dt + timedelta(minutes=15)
            
            if not (start_window <= now <= end_window):
                flash(f'Attendance can only be marked between {start_window.strftime("%I:%M %p")} and {end_window.strftime("%I:%M %p")}', 'warning')
                return redirect(url_for('dashboard'))

        return render_template('mark_attendance.html', classroom=classroom)

    # POST request: Process attendance
    print(f"Marking attendance for classroom {classroom_id}")
    if 'face_image' not in request.files:
        print("Error: No face_image in request")
        return jsonify({'success': False, 'message': 'No image received'})
    
    file = request.files['face_image']
    if file.filename == '':
        print("Error: Empty filename")
        return jsonify({'success': False, 'message': 'No image selected'})
        
    # Get Geolocation if available
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    
    # Optional geofencing check
    def parse_geofence_from_venue(venue_text):
        try:
            if not venue_text:
                return None, None, None
            import re
            latlng_match = re.search(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', venue_text)
            radius_match = re.search(r'(\d+)\s*m', venue_text.lower())
            if latlng_match:
                lat = float(latlng_match.group(1))
                lng = float(latlng_match.group(2))
                radius = float(radius_match.group(1)) if radius_match else 150.0
                return lat, lng, radius
        except Exception:
            pass
        return None, None, None
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM classrooms WHERE id = %s', (classroom_id,))
        classroom_info = cursor.fetchone()
        cursor.close()
    except Exception:
        classroom_info = None
    
    # Compute geofence if classroom has coordinates available (either explicit columns or in venue text)
    center_lat = None
    center_lng = None
    radius_m = None
    if classroom_info:
        center_lat = classroom_info.get('venue_lat')
        center_lng = classroom_info.get('venue_lng')
        radius_m = classroom_info.get('geofence_radius_m')
        if center_lat is None or center_lng is None:
            pl_lat, pl_lng, pl_radius = parse_geofence_from_venue(classroom_info.get('venue'))
            center_lat = center_lat or pl_lat
            center_lng = center_lng or pl_lng
            radius_m = radius_m or pl_radius
    
    # Enforce geofence only if we have center coordinates and a radius, and client provided location
    if center_lat is not None and center_lng is not None and radius_m:
        if latitude and longitude:
            try:
                import math
                lat1 = float(latitude)
                lon1 = float(longitude)
                lat2 = float(center_lat)
                lon2 = float(center_lng)
                R = 6371000.0
                phi1 = math.radians(lat1)
                phi2 = math.radians(lat2)
                dphi = math.radians(lat2 - lat1)
                dlambda = math.radians(lon2 - lon1)
                a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                distance = R * c
                if distance > float(radius_m):
                    return jsonify({'success': False, 'message': 'You are outside the classroom geofence'})
            except Exception:
                pass
        else:
            # If geofence is configured but no location provided, gently require location
            return jsonify({'success': False, 'message': 'Location required to mark attendance for this classroom'})
        
    try:
        # Read image
        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            print("Error: Image decode failed")
            return jsonify({'success': False, 'message': 'Invalid image'})

        # Get known encodings
        print("Fetching known encodings...")
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            SELECT s.id, s.full_name, s.face_encoding 
            FROM students s
            JOIN classroom_students cs ON s.id = cs.student_id
            WHERE cs.classroom_id = %s AND s.face_encoding IS NOT NULL
        ''', (classroom_id,))
        
        students = cursor.fetchall()
        print(f"Found {len(students)} students with registered faces")
        
        if not students:
            print("No students registered for this class")
            cursor.close()
            return jsonify({'success': False, 'message': 'No students registered for this class'})
            
        known_encodings = []
        student_ids = []
        student_names = []
        
        for student in students:
            if student['face_encoding']:
                encoding = np.frombuffer(student['face_encoding'], dtype=np.float64)
                known_encodings.append(encoding)
                student_ids.append(student['id'])
                student_names.append(student['full_name'])
        
        # Recognize face
        print("Recognizing face...")
        
        # Extract encoding from current image
        unknown_encoding = face_utils.extract_face_encoding(image)
        
        if unknown_encoding is None:
             print("Error: No face detected in uploaded image")
             return jsonify({'success': False, 'message': 'No face detected in image'})
        
             
        face_index, distance = face_utils.recognize_face_from_list(unknown_encoding, known_encodings)
        print(f"Recognition result: {face_index}, Distance: {distance}")
        
        if face_index is not None:
            student_id = student_ids[face_index]
            student_name = student_names[face_index]
            print(f"Face matched: {student_name} (ID: {student_id})")
            
            # Security check: Ensure logged-in user matches detected face
            current_user_id = session.get('user_id')
            if session.get('user_type') == 'student' and current_user_id != student_id:
                 print(f"Face mismatch: Logged in user {current_user_id} != Detected user {student_id}")
                 # We can either block or just warn. Let's block for security.
                 cursor.close()
                 return jsonify({'success': False, 'message': 'Detected face does not match logged-in user'})
            
            # Check if already marked today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT id FROM attendance 
                WHERE student_id = %s AND classroom_id = %s AND date = %s
            ''', (student_id, classroom_id, today))
            
            if cursor.fetchone():
                print("Attendance already marked today")
                cursor.close()
                return jsonify({'success': False, 'message': f'Attendance already marked for {student_name}'})
            
            # Mark attendance
            print("Inserting attendance record...")
            cursor.execute('''
                INSERT INTO attendance (student_id, classroom_id, date, status, marked_at, verification_method, latitude, longitude)
                VALUES (%s, %s, %s, 'P', NOW(), 'face', %s, %s)
            ''', (student_id, classroom_id, today, latitude, longitude))
            
            mysql.connection.commit()
            cursor.close()
            print("Attendance marked successfully")
            
            return jsonify({
                'success': True, 
                'message': f'Attendance marked for {student_name}',
                'student_name': student_name,
                'time': datetime.now().strftime('%H:%M:%S')
            })
        else:
            print("Face not recognized")
            cursor.close()
            
            # Check if current user has face registered
            if session.get('user_type') == 'student':
                current_user_id = session.get('user_id')
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('SELECT face_encoding FROM students WHERE id = %s', (current_user_id,))
                result = cursor.fetchone()
                cursor.close()
                
                if not result or not result['face_encoding']:
                    print("Current user has no face registered")
                    return jsonify({'success': False, 'message': 'Face not recognized', 'needs_registration': True})
            
            return jsonify({'success': False, 'message': 'Face not recognized. Please try again.'})
            
    except Exception as e:
        print(f"Exception in mark_attendance: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/view_attendance/<int:classroom_id>')
@login_required
def view_attendance(classroom_id):
    user_type = session['user_type']
    user_id = session['user_id']
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if user_type == 'teacher':
        # Verify teacher owns this classroom
        cursor.execute('''
            SELECT * FROM classrooms 
            WHERE id = %s AND teacher_id = %s
        ''', (classroom_id, user_id))
        
        if not cursor.fetchone():
            flash('Unauthorized access', 'danger')
            return redirect(url_for('teacher_dashboard'))
        
        # Get all attendance for this classroom
        cursor.execute('''
            SELECT a.*, s.full_name as student_name, s.username,
                   DATE_FORMAT(a.date, '%%Y-%%m-%%d') as formatted_date
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.classroom_id = %s
            ORDER BY a.date DESC, s.full_name
        ''', (classroom_id,))
    else:
        # Student can only see their own attendance
        cursor.execute('''
            SELECT a.*, c.class_name,
                   DATE_FORMAT(a.date, '%%Y-%%m-%%d') as formatted_date
            FROM attendance a
            JOIN classrooms c ON a.classroom_id = c.id
            WHERE a.student_id = %s AND a.classroom_id = %s
            ORDER BY a.date DESC
        ''', (user_id, classroom_id))
    
    attendance_records = cursor.fetchall()
    
    # Get classroom info
    cursor.execute('SELECT * FROM classrooms WHERE id = %s', (classroom_id,))
    classroom = cursor.fetchone()
    
    cursor.close()
    
    return render_template('attendance.html', 
                         attendance_records=attendance_records,
                         classroom=classroom,
                         user_type=user_type)

@app.route('/download_attendance/<int:classroom_id>')
@login_required
@teacher_required
def download_attendance(classroom_id):
    teacher_id = session['user_id']
    
    # Verify ownership
    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT * FROM classrooms 
        WHERE id = %s AND teacher_id = %s
    ''', (classroom_id, teacher_id))
    
    if not cursor.fetchone():
        flash('Unauthorized access', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Generate Excel report
    excel_file = excel_gen.generate_attendance_report(classroom_id, mysql.connection)
    
    if excel_file:
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'attendance_class_{classroom_id}.xlsx'
        )
    else:
        flash('Error generating report', 'danger')
        return redirect(url_for('view_attendance', classroom_id=classroom_id))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    user_type = session['user_type']
    
    table = 'teachers' if user_type == 'teacher' else 'students'
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        roll_number = request.form.get('roll_number', '') if user_type == 'student' else None
        parent_password = request.form.get('parent_password', '') if user_type == 'student' else None
        parent_password_confirm = request.form.get('parent_password_confirm', '') if user_type == 'student' else None
        
        # Validate parent password match
        if user_type == 'student' and parent_password:
            if parent_password != parent_password_confirm:
                flash('Parent passwords do not match', 'danger')
                cursor.close()
                return redirect(url_for('profile'))
            if len(parent_password) < 6:
                flash('Parent password must be at least 6 characters', 'danger')
                cursor.close()
                return redirect(url_for('profile'))
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{user_id}_{int(datetime.now().timestamp())}_{file.filename}")
                file_path = os.path.join(app.root_path, 'static', 'uploads', 'profiles', filename)
                file.save(file_path)
                
                # Update database with profile image
                try:
                    cursor.execute(f'''
                        UPDATE {table} 
                        SET profile_image = %s
                        WHERE id = %s
                    ''', (f'uploads/profiles/{filename}', user_id))
                    mysql.connection.commit()
                    
                    # Update session
                    session['profile_image'] = f'uploads/profiles/{filename}'
                except Exception as e:
                    print(f"Error updating profile image: {e}")
        
        try:
            # Update with roll_number and parent_password for students
            if user_type == 'student':
                # Hash parent password if provided
                hashed_parent_password = None
                if parent_password:
                    hashed_parent_password = generate_password_hash(parent_password)
                
                if hashed_parent_password:
                    cursor.execute(f'''
                        UPDATE {table} 
                        SET full_name = %s, email = %s, phone = %s, roll_number = %s, parent_password = %s
                        WHERE id = %s
                    ''', (full_name, email, phone, roll_number, hashed_parent_password, user_id))
                    flash('Profile updated successfully! Parent password has been set.', 'success')
                else:
                    cursor.execute(f'''
                        UPDATE {table} 
                        SET full_name = %s, email = %s, phone = %s, roll_number = %s
                        WHERE id = %s
                    ''', (full_name, email, phone, roll_number, user_id))
                    flash('Profile updated successfully!', 'success')
            else:
                # Teachers don't have roll_number or parent_password
                cursor.execute(f'''
                    UPDATE {table} 
                    SET full_name = %s, email = %s, phone = %s
                    WHERE id = %s
                ''', (full_name, email, phone, user_id))
        except MySQLdb.OperationalError as e:
            # If phone column doesn't exist (Error 1054), try without it
            if e.args[0] == 1054:
                if user_type == 'student':
                    cursor.execute(f'''
                        UPDATE {table} 
                        SET full_name = %s, email = %s, roll_number = %s
                        WHERE id = %s
                    ''', (full_name, email, roll_number, user_id))
                else:
                    cursor.execute(f'''
                        UPDATE {table} 
                        SET full_name = %s, email = %s
                        WHERE id = %s
                    ''', (full_name, email, user_id))
                flash('Profile updated (Phone number not saved - field missing)', 'warning')
            else:
                raise e
        
        mysql.connection.commit()
        session['full_name'] = full_name
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    # Get user data
    cursor.execute(f'SELECT * FROM {table} WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    face_registered = False
    if user and user.get('face_encoding'):
        face_registered = True
        # Ensure session is synced
        session['face_registered'] = True
    
    return render_template('profile.html', user=user, user_type=user_type, face_registered=face_registered)

@app.route('/verify_face_api', methods=['POST'])
@login_required
def verify_face_api():
    """API endpoint for face verification"""
    if 'face_image' not in request.files:
        return jsonify({'success': False, 'message': 'No image'})
    
    file = request.files['face_image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Empty file'})
    
    # Read image
    img_bytes = file.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Extract encoding
    current_encoding = face_utils.extract_face_encoding(image)
    
    if current_encoding is None:
        return jsonify({'success': False, 'message': 'No face detected'})
    
    # Get stored encoding
    user_id = session['user_id']
    user_type = session['user_type']
    table = 'teachers' if user_type == 'teacher' else 'students'
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(f'SELECT face_encoding FROM {table} WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    if not user or not user['face_encoding']:
        return jsonify({'success': False, 'message': 'Face not registered'})
    
    # Compare
    stored_encoding = np.frombuffer(user['face_encoding'], dtype=np.float64)
    match = face_utils.compare_faces(stored_encoding, current_encoding)
    
    return jsonify({
        'success': match,
        'message': 'Face verified' if match else 'Face mismatch'
    })

@app.route('/leaves', methods=['GET'])
@login_required
@student_required
def my_leaves():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    student_id = session['user_id']
    
    cursor.execute('''
        SELECT l.*, c.class_name, c.class_code
        FROM leaves l
        JOIN classrooms c ON l.classroom_id = c.id
        WHERE l.student_id = %s
        ORDER BY l.created_at DESC
    ''', (student_id,))
    leaves = cursor.fetchall()
    
    cursor.close()
    return render_template('student_leaves.html', leaves=leaves)

@app.route('/leaves/apply', methods=['GET', 'POST'])
@login_required
@student_required
def apply_leave():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    student_id = session['user_id']
    
    if request.method == 'POST':
        classroom_id = request.form.get('classroom_id')
        date = request.form.get('date')
        reason = request.form.get('reason')
        
        try:
            cursor.execute('''
                INSERT INTO leaves (student_id, classroom_id, date, reason)
                VALUES (%s, %s, %s, %s)
            ''', (student_id, classroom_id, date, reason))
            mysql.connection.commit()
            flash('Leave application submitted successfully', 'success')
            return redirect(url_for('my_leaves'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error submitting leave: {e}', 'danger')
    
    # Get enrolled classrooms for dropdown
    cursor.execute('''
        SELECT c.id, c.class_name 
        FROM classrooms c
        JOIN classroom_students cs ON c.id = cs.classroom_id
        WHERE cs.student_id = %s
    ''', (student_id,))
    classrooms = cursor.fetchall()
    cursor.close()
    
    return render_template('apply_leave.html', classrooms=classrooms)

@app.route('/leaves/manage', methods=['GET', 'POST'])
@login_required
@teacher_required
def manage_leaves():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    teacher_id = session['user_id']
    
    if request.method == 'POST':
        leave_id = request.form.get('leave_id')
        status = request.form.get('status')
        
        try:
            # Verify ownership of the classroom associated with the leave
            cursor.execute('''
                SELECT l.id 
                FROM leaves l
                JOIN classrooms c ON l.classroom_id = c.id
                WHERE l.id = %s AND c.teacher_id = %s
            ''', (leave_id, teacher_id))
            
            if cursor.fetchone():
                cursor.execute('UPDATE leaves SET status = %s WHERE id = %s', (status, leave_id))
                
                # If approved, also mark attendance as 'L' (Leave) or just keep it separate?
                # User asked for "leave management", implying it might override attendance or be a valid excuse.
                # For now, I'll just update leave status. Optionally, I could insert an attendance record 'L'.
                if status == 'Approved':
                    # Fetch details to update attendance
                    cursor.execute('SELECT * FROM leaves WHERE id = %s', (leave_id,))
                    leave = cursor.fetchone()
                    
                    # Check if attendance exists
                    cursor.execute('''
                        SELECT id FROM attendance 
                        WHERE student_id = %s AND classroom_id = %s AND date = %s
                    ''', (leave['student_id'], leave['classroom_id'], leave['date']))
                    
                    if cursor.fetchone():
                        cursor.execute('''
                            UPDATE attendance SET status = 'L', verification_method = 'manual'
                            WHERE student_id = %s AND classroom_id = %s AND date = %s
                        ''', (leave['student_id'], leave['classroom_id'], leave['date']))
                    else:
                         cursor.execute('''
                            INSERT INTO attendance (student_id, classroom_id, date, status, marked_at, verification_method)
                            VALUES (%s, %s, %s, 'L', NOW(), 'manual')
                        ''', (leave['student_id'], leave['classroom_id'], leave['date']))
                
                mysql.connection.commit()
                flash(f'Leave application {status.lower()}', 'success')
            else:
                flash('Access denied or leave not found', 'danger')
                
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating leave: {e}', 'danger')
            
        return redirect(url_for('manage_leaves'))
    
    # Get pending leaves for teacher's classrooms
    cursor.execute('''
        SELECT l.*, s.full_name as student_name, s.roll_number, c.class_name
        FROM leaves l
        JOIN classrooms c ON l.classroom_id = c.id
        JOIN students s ON l.student_id = s.id
        WHERE c.teacher_id = %s
        ORDER BY l.status = 'Pending' DESC, l.date DESC
    ''', (teacher_id,))
    leaves = cursor.fetchall()
    
    cursor.close()
    return render_template('manage_leaves.html', leaves=leaves)



# ==================== API ROUTES ====================

@app.route('/api/attendance_stats/<int:classroom_id>')
@login_required
def attendance_stats(classroom_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT 
            DATE_FORMAT(date, '%%Y-%%m-%%d') as date,
            SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as absent,
            COUNT(*) as total
        FROM attendance
        WHERE classroom_id = %s
        GROUP BY date
        ORDER BY date DESC
        LIMIT 30
    ''', (classroom_id,))
    
    stats = cursor.fetchall()
    cursor.close()
    
    return jsonify(stats)

@app.route('/api/classroom_students/<int:classroom_id>')
@login_required
@teacher_required
def classroom_students(classroom_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT s.id, s.username, s.full_name, s.email,
               (SELECT COUNT(*) FROM attendance 
                WHERE student_id = s.id AND classroom_id = %s AND status = 'P') as present_days,
               (SELECT COUNT(*) FROM attendance 
                WHERE student_id = s.id AND classroom_id = %s) as total_days
        FROM students s
        JOIN classroom_students cs ON s.id = cs.student_id
        WHERE cs.classroom_id = %s
    ''', (classroom_id, classroom_id, classroom_id))
    
    students = cursor.fetchall()
    cursor.close()
    
    return jsonify(students)

@app.route('/api/teacher_dashboard_data')
@login_required
@teacher_required
def teacher_dashboard_data():
    """API endpoint to fetch real dashboard data"""
    teacher_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get weekly attendance trend (last 7 days)
    cursor.execute('''
        SELECT 
            DATE_FORMAT(a.date, '%%a') as day_name,
            a.date,
            SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN a.status = 'A' THEN 1 ELSE 0 END) as absent
        FROM attendance a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE c.teacher_id = %s AND a.date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY a.date
        ORDER BY a.date ASC
    ''', (teacher_id,))
    
    weekly_data = cursor.fetchall()
    
    # Get class-wise distribution
    cursor.execute('''
        SELECT 
            c.class_name,
            COUNT(DISTINCT cs.student_id) as student_count
        FROM classrooms c
        LEFT JOIN classroom_students cs ON c.id = cs.classroom_id
        WHERE c.teacher_id = %s
        GROUP BY c.id
    ''', (teacher_id,))
    
    class_distribution = cursor.fetchall()
    
    # Get monthly attendance trend
    cursor.execute('''
        SELECT 
            WEEK(a.date) as week_num,
            CONCAT('Week ', WEEK(a.date)) as week_label,
            ROUND(SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as attendance_percentage
        FROM attendance a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE c.teacher_id = %s AND MONTH(a.date) = MONTH(CURDATE()) AND YEAR(a.date) = YEAR(CURDATE())
        GROUP BY WEEK(a.date)
        ORDER BY WEEK(a.date) ASC
    ''', (teacher_id,))
    
    monthly_data = cursor.fetchall()
    
    # Get attendance distribution (Present/Absent/Leave)
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) as absent,
            SUM(CASE WHEN status = 'L' THEN 1 ELSE 0 END) as leave
        FROM attendance a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE c.teacher_id = %s
    ''', (teacher_id,))
    
    distribution = cursor.fetchone()
    
    cursor.close()
    
    return jsonify({
        'weekly': weekly_data,
        'class_distribution': class_distribution,
        'monthly': monthly_data,
        'distribution': distribution
    })

@app.route('/delete_classroom/<int:classroom_id>', methods=['POST'])
@login_required
@teacher_required
def delete_classroom(classroom_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Verify ownership
    cursor.execute('SELECT * FROM classrooms WHERE id = %s AND teacher_id = %s', 
                  (classroom_id, session['user_id']))
    classroom = cursor.fetchone()
    
    if not classroom:
        cursor.close()
        flash('Classroom not found or access denied', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    try:
        # Delete related records first (due to foreign key constraints)
        # Order matters: leaves → attendance → classroom_students → classroom
        
        # Delete leaves for this classroom
        cursor.execute('DELETE FROM leaves WHERE classroom_id = %s', (classroom_id,))
        
        # Delete attendance records
        cursor.execute('DELETE FROM attendance WHERE classroom_id = %s', (classroom_id,))
        
        # Delete classroom_students entries
        cursor.execute('DELETE FROM classroom_students WHERE classroom_id = %s', (classroom_id,))
        
        # Finally delete the classroom
        cursor.execute('DELETE FROM classrooms WHERE id = %s', (classroom_id,))
        
        mysql.connection.commit()
        flash(f'Classroom "{classroom["class_name"]}" has been deleted successfully', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error deleting classroom: {str(e)}', 'danger')
        print(f"Error deleting classroom: {e}")
    
    cursor.close()
    return redirect(url_for('teacher_dashboard'))




#
@app.route('/classroom_events/<int:classroom_id>', methods=['GET', 'POST'])
@login_required
def classroom_events(classroom_id):
    user_type = session['user_type']
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get classroom info
    cursor.execute('SELECT * FROM classrooms WHERE id = %s', (classroom_id,))
    classroom = cursor.fetchone()
    
    if not classroom:
        cursor.close()
        flash('Classroom not found', 'danger')
        return redirect(url_for('dashboard' if user_type == 'student' else 'teacher_dashboard'))
    
    # Check access
    if user_type == 'teacher':
        if classroom['teacher_id'] != user_id:
            cursor.close()
            flash('Access denied', 'danger')
            return redirect(url_for('teacher_dashboard'))
    else:  # student
        cursor.execute('''
            SELECT * FROM classroom_students 
            WHERE student_id = %s AND classroom_id = %s
        ''', (user_id, classroom_id))
        if not cursor.fetchone():
            cursor.close()
            flash('You are not enrolled in this classroom', 'danger')
            return redirect(url_for('dashboard'))
    
    # Handle POST - Create event
    if request.method == 'POST' and user_type == 'teacher':
        title = request.form.get('event_title', '').strip()
        description = request.form.get('event_description', '').strip()
        event_date = request.form.get('event_date')
        event_time = request.form.get('event_time') or None
        event_type = request.form.get('event_type', 'other')
        
        if not title or not event_date:
            flash('Title and date are required', 'danger')
        else:
            try:
                cursor.execute('''
                    INSERT INTO classroom_events (classroom_id, title, description, event_date, event_time, event_type, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (classroom_id, title, description, event_date, event_time, event_type, user_id))
                mysql.connection.commit()
                flash('Event created successfully!', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash(f'Error creating event: {str(e)}', 'danger')
    
    # Get upcoming events (next 30 days)
    today = datetime.now().date()
    future_date = today + timedelta(days=30)
    
    cursor.execute('''
        SELECT * FROM classroom_events
        WHERE classroom_id = %s AND event_date >= %s
        ORDER BY event_date ASC, event_time ASC
    ''', (classroom_id, today))
    upcoming_events_raw = cursor.fetchall()
    
    # Convert timedelta to time for event_time fields
    upcoming_events = []
    for event in upcoming_events_raw:
        event_dict = dict(event)
        if event_dict.get('event_time') and isinstance(event_dict['event_time'], timedelta):
            # Convert timedelta to time object
            total_seconds = int(event_dict['event_time'].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            event_dict['event_time'] = datetime.strptime(f'{hours:02d}:{minutes:02d}', '%H:%M').time()
        upcoming_events.append(event_dict)
    
    # Get past events (last 30 days)
    past_date = today - timedelta(days=30)
    cursor.execute('''
        SELECT * FROM classroom_events
        WHERE classroom_id = %s AND event_date < %s AND event_date >= %s
        ORDER BY event_date DESC, event_time DESC
    ''', (classroom_id, today, past_date))
    past_events_raw = cursor.fetchall()
    
    # Convert timedelta to time for event_time fields
    past_events = []
    for event in past_events_raw:
        event_dict = dict(event)
        if event_dict.get('event_time') and isinstance(event_dict['event_time'], timedelta):
            # Convert timedelta to time object
            total_seconds = int(event_dict['event_time'].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            event_dict['event_time'] = datetime.strptime(f'{hours:02d}:{minutes:02d}', '%H:%M').time()
        past_events.append(event_dict)
    
    cursor.close()
    
    return render_template('classroom_events.html', 
                         classroom=classroom,
                         upcoming_events=upcoming_events,
                         past_events=past_events,
                         is_teacher=(user_type == 'teacher'))

@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
@teacher_required
def delete_event(event_id):
    teacher_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get event and verify ownership
    cursor.execute('''
        SELECT e.*, c.teacher_id 
        FROM classroom_events e
        JOIN classrooms c ON e.classroom_id = c.id
        WHERE e.id = %s AND c.teacher_id = %s
    ''', (event_id, teacher_id))
    
    event = cursor.fetchone()
    if not event:
        cursor.close()
        flash('Event not found or access denied', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    try:
        cursor.execute('DELETE FROM classroom_events WHERE id = %s', (event_id,))
        mysql.connection.commit()
        flash('Event deleted successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error deleting event: {str(e)}', 'danger')
    
    cursor.close()
    return redirect(url_for('classroom_events', classroom_id=event['classroom_id']))

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    mysql.connection.rollback()
    return render_template('500.html'), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
