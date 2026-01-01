"""
Face Attendance System - Project Report Generator
Generates a comprehensive PDF report of the project
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.colors import HexColor
from datetime import datetime
import os

def create_project_report():
    """Generate comprehensive PDF report of Face Attendance System"""
    
    # Create PDF file
    filename = f"Face_Attendance_System_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CustomJustify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='CustomCenter', alignment=TA_CENTER, fontSize=14, textColor=colors.HexColor('#1a1a1a')))
    styles.add(ParagraphStyle(name='CustomTitle', fontSize=24, textColor=colors.HexColor('#2c3e50'), 
                             spaceAfter=30, alignment=TA_CENTER, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CustomHeading1', fontSize=18, textColor=colors.HexColor('#34495e'), 
                             spaceAfter=12, spaceBefore=12, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CustomHeading2', fontSize=14, textColor=colors.HexColor('#34495e'), 
                             spaceAfter=10, spaceBefore=10, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CustomBody', fontSize=11, alignment=TA_JUSTIFY, spaceAfter=12))
    styles.add(ParagraphStyle(name='CustomCode', fontSize=9, fontName='Courier', 
                             textColor=colors.HexColor('#c7254e'), 
                             backColor=colors.HexColor('#f9f2f4')))
    
    # Title Page
    elements.append(Spacer(1, 2*inch))
    title = Paragraph("Face Attendance System", styles['CustomTitle'])
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    subtitle = Paragraph("Comprehensive Project Documentation", styles['CustomCenter'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.5*inch))
    
    date_text = Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['CustomCenter'])
    elements.append(date_text)
    elements.append(PageBreak())
    
    # Table of Contents
    elements.append(Paragraph("Table of Contents", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.2*inch))
    
    toc_items = [
        "1. Executive Summary",
        "2. Project Overview",
        "3. Technology Stack",
        "4. System Architecture",
        "5. Key Features",
        "6. Database Schema",
        "7. File Structure",
        "8. Core Modules",
        "9. API Endpoints",
        "10. Security Features",
        "11. Installation Guide",
        "12. Usage Instructions",
        "13. Future Enhancements"
    ]
    
    for item in toc_items:
        elements.append(Paragraph(item, styles['CustomBody']))
    
    elements.append(PageBreak())
    
    # 1. Executive Summary
    elements.append(Paragraph("1. Executive Summary", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    summary = """
    The Face Attendance System is a modern, web-based attendance management solution that leverages 
    facial recognition technology to automate and streamline the attendance tracking process. Built 
    with Flask and Python, this system provides a secure, efficient, and user-friendly platform for 
    educational institutions to manage student attendance through biometric verification.
    """
    elements.append(Paragraph(summary, styles['CustomBody']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Key Highlights
    elements.append(Paragraph("<b>Key Highlights:</b>", styles['CustomHeading2']))
    highlights = [
        "• Real-time facial recognition for attendance marking",
        "• Separate portals for teachers and students",
        "• Automated attendance report generation in Excel format",
        "• Geolocation-based attendance verification",
        "• QR code-based classroom joining",
        "• Leave management system",
        "• Responsive design for mobile and desktop",
        "• MySQL database for secure data storage"
    ]
    for highlight in highlights:
        elements.append(Paragraph(highlight, styles['CustomBody']))
    
    elements.append(PageBreak())
    
    # 2. Project Overview
    elements.append(Paragraph("2. Project Overview", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    overview = """
    This attendance system eliminates traditional paper-based or manual attendance methods by 
    implementing cutting-edge face recognition technology. The system authenticates students in 
    real-time using their facial features, ensuring accurate attendance records while preventing 
    proxy attendance.
    """
    elements.append(Paragraph(overview, styles['CustomBody']))
    
    elements.append(Paragraph("<b>Project Goals:</b>", styles['CustomHeading2']))
    goals = [
        "• Automate attendance marking process",
        "• Reduce time spent on manual attendance",
        "• Ensure accuracy and prevent proxy attendance",
        "• Provide real-time attendance analytics",
        "• Generate comprehensive attendance reports",
        "• Enable remote attendance monitoring for teachers"
    ]
    for goal in goals:
        elements.append(Paragraph(goal, styles['CustomBody']))
    
    elements.append(PageBreak())
    
    # 3. Technology Stack
    elements.append(Paragraph("3. Technology Stack", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Create technology table
    tech_data = [
        ['Category', 'Technology', 'Version/Purpose'],
        ['Backend Framework', 'Flask', 'Python web framework'],
        ['Face Recognition', 'face_recognition', 'Facial detection & encoding'],
        ['Computer Vision', 'OpenCV', '4.8.1.78'],
        ['Database', 'MySQL', 'Data persistence'],
        ['Data Processing', 'NumPy', '1.26.4'],
        ['Report Generation', 'Pandas & openpyxl', 'Excel reports'],
        ['Frontend', 'HTML/CSS/JavaScript', 'Responsive UI'],
        ['Authentication', 'Flask Sessions', 'User authentication'],
        ['Security', 'Werkzeug', 'Password hashing'],
    ]
    
    tech_table = Table(tech_data, colWidths=[1.8*inch, 1.8*inch, 2.4*inch])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(tech_table)
    
    elements.append(PageBreak())
    
    # 4. System Architecture
    elements.append(Paragraph("4. System Architecture", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    arch = """
    The system follows a three-tier architecture pattern:
    """
    elements.append(Paragraph(arch, styles['CustomBody']))
    
    elements.append(Paragraph("<b>Presentation Layer:</b>", styles['CustomHeading2']))
    elements.append(Paragraph("HTML templates with responsive CSS and JavaScript for user interaction, " +
                             "real-time webcam capture, and dynamic content updates.", styles['CustomBody']))
    
    elements.append(Paragraph("<b>Application Layer:</b>", styles['CustomHeading2']))
    elements.append(Paragraph("Flask application (app.py) handling routing, business logic, authentication, " +
                             "and facial recognition processing. Custom modules include face_recognition_utils.py " +
                             "for biometric operations and excel_generator.py for report generation.", styles['CustomBody']))
    
    elements.append(Paragraph("<b>Data Layer:</b>", styles['CustomHeading2']))
    elements.append(Paragraph("MySQL database storing user credentials, classroom information, attendance records, " +
                             "face encodings, and leave applications.", styles['CustomBody']))
    
    elements.append(PageBreak())
    
    # 5. Key Features
    elements.append(Paragraph("5. Key Features", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    features = [
        ("<b>Facial Recognition:</b>", "Real-time face detection and matching using dlib's face encoding models. " +
         "Supports registration of face data and verification during attendance marking."),
        
        ("<b>User Management:</b>", "Separate authentication for teachers and students with role-based access " +
         "control. Profile management with photo upload capability."),
        
        ("<b>Classroom Management:</b>", "Teachers can create classrooms with custom codes, schedule times, " +
         "venues, and geofencing parameters. Students join using class codes or QR codes."),
        
        ("<b>Attendance Marking:</b>", "Students mark attendance via facial verification within designated time " +
         "windows. Geolocation validation ensures students are within classroom boundaries."),
        
        ("<b>Attendance Reports:</b>", "Automated Excel report generation with student-wise attendance statistics. " +
         "Teachers can download comprehensive attendance records."),
        
        ("<b>Leave Management:</b>", "Students can apply for leaves with reasons. Teachers review and approve/reject " +
         "leave applications."),
        
        ("<b>Dashboard Analytics:</b>", "Visual attendance statistics, recent activity logs, and performance metrics " +
         "for both teachers and students."),
        
        ("<b>Security Features:</b>", "Password hashing with Werkzeug, session-based authentication, face encoding " +
         "encryption, and role-based route protection."),
    ]
    
    for title, desc in features:
        elements.append(Paragraph(title, styles['CustomHeading2']))
        elements.append(Paragraph(desc, styles['CustomBody']))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(PageBreak())
    
    # 6. Database Schema
    elements.append(Paragraph("6. Database Schema", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("The system uses MySQL database 'attendance_system' with the following key tables:", 
                             styles['CustomBody']))
    elements.append(Spacer(1, 0.1*inch))
    
    schema_data = [
        ['Table', 'Key Fields', 'Purpose'],
        ['teachers', 'id, username, password, email, full_name, face_encoding', 'Teacher authentication & profiles'],
        ['students', 'id, username, password, email, full_name, roll_number, face_encoding', 'Student authentication & profiles'],
        ['classrooms', 'id, teacher_id, class_name, class_code, start_time, end_time, venue', 'Classroom configuration'],
        ['classroom_students', 'student_id, classroom_id', 'Student enrollment mapping'],
        ['attendance', 'student_id, classroom_id, date, status, marked_at, latitude, longitude', 'Attendance records'],
        ['leaves', 'student_id, classroom_id, date, reason, status', 'Leave applications'],
    ]
    
    schema_table = Table(schema_data, colWidths=[1.5*inch, 2.5*inch, 2*inch])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(schema_table)
    
    elements.append(PageBreak())
    
    # 7. File Structure
    elements.append(Paragraph("7. File Structure", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    file_structure = """
    <b>Root Directory:</b><br/>
    ├── face_attendence/<br/>
    │   ├── app.py (Main Flask application)<br/>
    │   ├── face_recognition_utils.py (Face processing module)<br/>
    │   ├── excel_generator.py (Report generation)<br/>
    │   ├── db_config.py (Database configuration)<br/>
    │   ├── static/ (CSS, JavaScript, uploads)<br/>
    │   │   ├── css/<br/>
    │   │   │   ├── style.css<br/>
    │   │   │   └── mobile.css<br/>
    │   │   ├── js/<br/>
    │   │   │   ├── main.js<br/>
    │   │   │   ├── webcam.js<br/>
    │   │   │   └── face_capture.js<br/>
    │   │   └── uploads/<br/>
    │   ├── templates/ (HTML templates)<br/>
    │   │   ├── layout.html<br/>
    │   │   ├── login.html<br/>
    │   │   ├── dashboard.html<br/>
    │   │   ├── teacher_dashboard.html<br/>
    │   │   ├── capture_face.html<br/>
    │   │   ├── mark_attendance.html<br/>
    │   │   └── [other templates]<br/>
    │   ├── face_encodings/ (Stored face data)<br/>
    │   ├── reports/ (Generated Excel reports)<br/>
    │   └── dlib models (Face detection models)<br/>
    └── requirements.txt
    """
    elements.append(Paragraph(file_structure, styles['CustomCode']))
    
    elements.append(PageBreak())
    
    # 8. Core Modules
    elements.append(Paragraph("8. Core Modules", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    modules = [
        ("<b>app.py (Main Application):</b>", 
         "Contains 50+ routes handling authentication, classroom management, attendance operations, " +
         "profile management, and API endpoints. Implements decorators for authentication and role-based access control."),
        
        ("<b>face_recognition_utils.py (FaceUtils Class):</b>", 
         "Core facial recognition module with methods: extract_face_encoding() - Detects and extracts 128-d " +
         "face encodings; compare_faces() - Compares encodings with configurable threshold; " +
         "recognize_face() - Identifies users from stored encodings; detect_faces_in_frame() - " +
         "Real-time face detection."),
        
        ("<b>excel_generator.py (ExcelGenerator Class):</b>", 
         "Generates formatted Excel reports using openpyxl with attendance statistics, student-wise summary, " +
         "and date-wise records with conditional formatting."),
        
        ("<b>db_config.py:</b>", 
         "Database connection configuration using Flask-MySQLdb with connection pooling and cursor management."),
    ]
    
    for title, desc in modules:
        elements.append(Paragraph(title, styles['CustomHeading2']))
        elements.append(Paragraph(desc, styles['CustomBody']))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(PageBreak())
    
    # 9. API Endpoints
    elements.append(Paragraph("9. API Endpoints", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    api_data = [
        ['Method', 'Endpoint', 'Description'],
        ['GET/POST', '/login', 'User authentication'],
        ['GET/POST', '/signup', 'New user registration'],
        ['GET', '/dashboard', 'Student dashboard'],
        ['GET', '/teacher_dashboard', 'Teacher dashboard'],
        ['GET/POST', '/capture_face', 'Face registration'],
        ['GET/POST', '/mark_attendance/<id>', 'Attendance marking'],
        ['GET/POST', '/create_classroom', 'Create new classroom'],
        ['POST', '/join_classroom', 'Join classroom by code'],
        ['GET', '/export_report/<id>', 'Download attendance Excel'],
        ['GET/POST', '/manage_attendance/<id>', 'Manual attendance edit'],
        ['GET', '/api/attendance_stats', 'Attendance statistics JSON'],
        ['POST', '/verify_face_api', 'Face verification API'],
        ['GET', '/leaves/manage', 'Leave management'],
        ['GET', '/logout', 'User logout'],
    ]
    
    api_table = Table(api_data, colWidths=[1*inch, 2.5*inch, 2.5*inch])
    api_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(api_table)
    
    elements.append(PageBreak())
    
    # 10. Security Features
    elements.append(Paragraph("10. Security Features", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    security = [
        "<b>Password Security:</b> All passwords are hashed using Werkzeug's generate_password_hash with PBKDF2-SHA256 algorithm.",
        "<b>Session Management:</b> Flask sessions with secure secret keys for maintaining user authentication state.",
        "<b>Role-Based Access Control:</b> Custom decorators (@teacher_required, @student_required) protect routes from unauthorized access.",
        "<b>SQL Injection Prevention:</b> Parameterized queries using MySQLdb prevent SQL injection attacks.",
        "<b>Face Encoding Security:</b> Face encodings stored as binary data in database, preventing unauthorized access to biometric data.",
        "<b>File Upload Validation:</b> Strict file type validation (PNG, JPG, JPEG, GIF only) with secure filename handling.",
        "<b>Geolocation Verification:</b> Optional geofencing ensures students are physically present in classroom location.",
        "<b>Time-Window Enforcement:</b> Attendance can only be marked within configured time windows (±15 minutes buffer).",
        "<b>CSRF Protection:</b> Session-based verification prevents cross-site request forgery attacks.",
        "<b>Error Handling:</b> Custom error pages (404, 500) prevent information leakage."
    ]
    
    for item in security:
        elements.append(Paragraph(item, styles['CustomBody']))
        elements.append(Spacer(1, 0.05*inch))
    
    elements.append(PageBreak())
    
    # 11. Installation Guide
    elements.append(Paragraph("11. Installation Guide", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    installation_steps = [
        ("<b>Step 1: Prerequisites</b>", 
         "Install Python 3.8+, MySQL Server, and Visual Studio Build Tools (for dlib compilation on Windows)."),
        
        ("<b>Step 2: Clone/Extract Project</b>", 
         "Extract the face_attendence folder to your desired location."),
        
        ("<b>Step 3: Install Dependencies</b>", 
         "Run: pip install -r requirements.txt<br/>" +
         "Additional packages: flask, flask-mysqldb, face-recognition, opencv-python, werkzeug, openpyxl"),
        
        ("<b>Step 4: Database Setup</b>", 
         "Create MySQL database 'attendance_system'. Update credentials in db_config.py. " +
         "Run database migration scripts to create tables."),
        
        ("<b>Step 5: Configure Application</b>", 
         "Set SECRET_KEY environment variable. Configure UPLOAD_FOLDER and MYSQL settings in app.py."),
        
        ("<b>Step 6: Run Application</b>", 
         "Execute: python app.py<br/>Access at: http://localhost:5000"),
    ]
    
    for title, desc in installation_steps:
        elements.append(Paragraph(title, styles['CustomHeading2']))
        elements.append(Paragraph(desc, styles['CustomBody']))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(PageBreak())
    
    # 12. Usage Instructions
    elements.append(Paragraph("12. Usage Instructions", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("<b>For Teachers:</b>", styles['CustomHeading2']))
    teacher_steps = [
        "1. Register account selecting 'Teacher' role",
        "2. Login and register face biometrics via Profile → Capture Face",
        "3. Create classroom with name, code, schedule, and venue (optional geofencing)",
        "4. Share classroom code or QR code with students",
        "5. Monitor attendance via Teacher Dashboard",
        "6. Download Excel reports for analysis",
        "7. Manually edit attendance if needed",
        "8. Review and approve leave applications"
    ]
    for step in teacher_steps:
        elements.append(Paragraph(step, styles['CustomBody']))
    
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("<b>For Students:</b>", styles['CustomHeading2']))
    student_steps = [
        "1. Register account selecting 'Student' role",
        "2. Login and register face biometrics (required for attendance)",
        "3. Join classroom using class code or QR scan",
        "4. Mark attendance within scheduled time using face verification",
        "5. View attendance statistics on dashboard",
        "6. Apply for leaves when needed",
        "7. Track attendance percentage for each class"
    ]
    for step in student_steps:
        elements.append(Paragraph(step, styles['CustomBody']))
    
    elements.append(PageBreak())
    
    # 13. Future Enhancements
    elements.append(Paragraph("13. Future Enhancements", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    enhancements = [
        "<b>Mobile Application:</b> Native Android/iOS apps for easier access and better camera integration.",
        "<b>Multi-Face Detection:</b> Bulk attendance marking by detecting multiple faces simultaneously.",
        "<b>Live Dashboard:</b> Real-time WebSocket updates for instant attendance notifications.",
        "<b>Email Notifications:</b> Automated email alerts for low attendance, leave approvals, etc.",
        "<b>Advanced Analytics:</b> ML-based insights, attendance patterns, and predictive analytics.",
        "<b>Biometric Backup:</b> Additional authentication methods (fingerprint, OTP) as fallback.",
        "<b>Cloud Deployment:</b> Deploy on AWS/Azure with scalable architecture for multiple institutions.",
        "<b>API Integration:</b> RESTful APIs for integration with existing student information systems.",
        "<b>Parent Portal:</b> Allow parents to monitor their child's attendance in real-time.",
        "<b>Attendance Reminders:</b> Push notifications reminding students to mark attendance.",
    ]
    
    for item in enhancements:
        elements.append(Paragraph(item, styles['CustomBody']))
        elements.append(Spacer(1, 0.05*inch))
    
    elements.append(PageBreak())
    
    # Project Statistics
    elements.append(Paragraph("Project Statistics", styles['CustomHeading1']))
    elements.append(Spacer(1, 0.1*inch))
    
    stats_data = [
        ['Metric', 'Count'],
        ['Total Python Files', '5+'],
        ['Total Routes/Endpoints', '50+'],
        ['HTML Templates', '15+'],
        ['JavaScript Files', '3'],
        ['CSS Files', '2'],
        ['Database Tables', '6'],
        ['Lines of Code (Approx)', '2000+'],
        ['External Dependencies', '15+'],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 3*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(stats_table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Conclusion
    elements.append(Paragraph("Conclusion", styles['CustomHeading1']))
    conclusion = """
    The Face Attendance System represents a modern solution to traditional attendance management challenges. 
    By leveraging facial recognition technology, it provides a secure, efficient, and accurate method for 
    tracking student attendance. The system's comprehensive feature set, including classroom management, 
    leave handling, and detailed reporting, makes it a complete solution for educational institutions 
    looking to modernize their attendance processes.
    """
    elements.append(Paragraph(conclusion, styles['CustomBody']))
    
    elements.append(Spacer(1, 0.3*inch))
    footer = Paragraph("<i>Report generated automatically by Face Attendance System</i>", styles['CustomCenter'])
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    print(f"\n✓ PDF Report generated successfully: {filename}")
    return filename

if __name__ == "__main__":
    try:
        print("Generating Face Attendance System Project Report...")
        print("-" * 60)
        report_file = create_project_report()
        print("-" * 60)
        print(f"Report saved to: {os.path.abspath(report_file)}")
        print("\nReport includes:")
        print("  • Executive Summary")
        print("  • Complete Technology Stack")
        print("  • System Architecture")
        print("  • Key Features & Capabilities")
        print("  • Database Schema")
        print("  • API Documentation")
        print("  • Security Features")
        print("  • Installation & Usage Guide")
        print("  • Future Enhancement Roadmap")
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
