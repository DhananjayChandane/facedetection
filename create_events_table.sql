-- Create classroom_events table
CREATE TABLE IF NOT EXISTS `classroom_events` (
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
);

-- Add some sample events (optional)
-- INSERT INTO classroom_events (classroom_id, title, description, event_date, event_time, event_type, created_by)
-- VALUES 
-- (1, 'Midterm Exam', 'Midterm examination for CS101', '2024-12-30', '10:00:00', 'exam', 1),
-- (1, 'Assignment 1 Due', 'Submit your first assignment', '2024-12-28', '23:59:00', 'assignment', 1);
