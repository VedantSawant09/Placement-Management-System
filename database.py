import sqlite3
import bcrypt
import json
from datetime import datetime, timedelta

DB_NAME = "placement.db"

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Students table (renamed for clarity)
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        college_id TEXT UNIQUE NOT NULL,
        branch TEXT NOT NULL,
        cgpa REAL NOT NULL,
        skills_text TEXT,
        resume_path TEXT,
        aptitude_score INTEGER DEFAULT 0,
        ai_match REAL DEFAULT 0.0,
        is_verified BOOLEAN DEFAULT FALSE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Admins table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Aptitude_Questions table
    c.execute('''CREATE TABLE IF NOT EXISTS aptitude_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        options JSON NOT NULL,
        answer TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        difficulty TEXT DEFAULT 'medium',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Companies table
    c.execute('''CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        required_skills TEXT,
        min_cgpa REAL DEFAULT 0.0
    )''')

    # Roles table
    c.execute('''CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        required_skills TEXT,
        company_id INTEGER,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )''')

    # Aptitude_Results table
    c.execute('''CREATE TABLE IF NOT EXISTS aptitude_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        test_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        answers JSON,
        completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )''')

    # AI_Matches table
    c.execute('''CREATE TABLE IF NOT EXISTS ai_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        role_id INTEGER NOT NULL,
        match_score REAL NOT NULL,
        match_reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(role_id) REFERENCES roles(id)
    )''')

    # Verification tokens table
    c.execute('''CREATE TABLE IF NOT EXISTS verification_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_type TEXT NOT NULL,  -- 'student' or 'admin'
        token TEXT NOT NULL,
        token_type TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # JWT sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS jwt_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_type TEXT NOT NULL,  -- 'student' or 'admin'
        token_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

def seed_companies_and_roles():
    conn = get_db()
    c = conn.cursor()

    # Seed companies (using existing schema)
    companies = [
        ("TechCorp", "Leading technology company", "Python, Java, SQL, AWS", 7.0),
        ("DataSolutions", "Data analytics firm", "Python, SQL, Excel, Machine Learning", 6.5),
        ("WebMasters", "Web development agency", "HTML, CSS, JavaScript, React", 6.0),
        ("CloudOps", "Cloud infrastructure specialists", "AWS, Docker, Linux, Kubernetes", 7.5),
        ("InnovatePM", "Product management consultancy", "Agile, Communication, Strategy, Scrum", 7.0)
    ]
    c.executemany("INSERT OR IGNORE INTO companies (name, description, required_skills, min_cgpa) VALUES (?, ?, ?, ?)", companies)

    # Seed roles (using existing schema)
    roles = [
        ("Software Engineer", "Develop software applications", "Python, Java, SQL", 1),
        ("Data Analyst", "Analyze data and generate insights", "Python, SQL, Excel", 2),
        ("Web Developer", "Build websites and web applications", "HTML, CSS, JavaScript", 3),
        ("DevOps Engineer", "Manage infrastructure and deployments", "AWS, Docker, Linux", 4),
        ("Product Manager", "Oversee product development", "Agile, Communication, Strategy", 5)
    ]
    c.executemany("INSERT OR IGNORE INTO roles (title, description, required_skills, company_id) VALUES (?, ?, ?, ?)", roles)

    # Seed default admin user
    hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    c.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
              ("Admin", "admin@placement.com", hashed, "admin"))

    conn.commit()
    conn.close()

def migrate_existing_data():
    """Migrate data from existing tables to new schema if needed"""
    conn = get_db()
    c = conn.cursor()

    # Check if old users table exists and migrate students
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if c.fetchone():
        c.execute("SELECT COUNT(*) FROM students")
        if c.fetchone()[0] == 0:
            try:
                c.execute("SELECT name, email, password, NULL, NULL, cgpa, skills, NULL, approved FROM users WHERE role = 'student'")
                old_students = c.fetchall()
                for student in old_students:
                    c.execute("""INSERT INTO students (name, email, password_hash, college_id, branch, cgpa, skills_text, resume_path, is_verified)
                               VALUES (?, ?, ?, 'TEMP_' || ?, 'TEMP', ?, ?, NULL, ?)""",
                             (student[0], student[1], student[2], student[0].replace(' ', '_'), student[5], student[6], student[7]))
            except sqlite3.OperationalError as e:
                print(f"Student migration skipped: {e}")

    conn.commit()
    conn.close()

# User management functions
def create_user(name, email, password, cgpa=None, phone=None, role='student'):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO users (name, email, password, cgpa, phone, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (name, email.lower(), hashed, cgpa, phone, role, datetime.now().isoformat()))
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id

def find_user(email):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    user = c.fetchone()
    conn.close()
    return user

def update_user_skills(user_id, skills=None, resume=None, cgpa=None, phone=None, approved=None):
    conn = get_db()
    c = conn.cursor()
    updates = []
    values = []
    if skills is not None:
        updates.append("skills = ?")
        values.append(skills)
    if resume is not None:
        updates.append("resume = ?")
        values.append(resume)
    if cgpa is not None:
        updates.append("cgpa = ?")
        values.append(cgpa)
    if phone is not None:
        updates.append("phone = ?")
        values.append(phone)
    if approved is not None:
        updates.append("approved = ?")
        values.append(approved)
    if updates:
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        values.append(user_id)
        c.execute(query, values)
        # Users table (combined for students and admins)
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            cgpa REAL,
            phone TEXT,
            role TEXT DEFAULT 'student',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            skills TEXT,
            resume TEXT,
            approved INTEGER DEFAULT 0
        )''')
    
        # Slots table for scheduling
        c.execute('''CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            slot_time TEXT NOT NULL,
            created_by INTEGER,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
    
        conn.commit()
        conn.close()

# Verification tokens
def create_verification_token(user_id, token, token_type, expires_hours=24):
    expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO verification_tokens (user_id, token, token_type, expires_at) VALUES (?, ?, ?, ?)",
              (user_id, token, token_type, expires_at))
    token_id = c.lastrowid
    conn.commit()
    conn.close()
    return token_id

def verify_token(token, token_type):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM verification_tokens WHERE token = ? AND token_type = ? AND expires_at > ?",
              (token, token_type, datetime.now().isoformat()))
    result = c.fetchone()
    if result:
        c.execute("DELETE FROM verification_tokens WHERE token = ?", (token,))
        conn.commit()
    conn.close()
    return result[0] if result else None

# JWT sessions
def create_session(user_id, token_hash, expires_hours=24):
    expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO jwt_sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
              (user_id, token_hash, expires_at))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def validate_session(token_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM jwt_sessions WHERE token_hash = ? AND expires_at > ?",
              (token_hash, datetime.now().isoformat()))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def invalidate_session(token_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM jwt_sessions WHERE token_hash = ?", (token_hash,))
    conn.commit()
    conn.close()

# Companies and roles
def get_companies():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, description, required_skills, min_cgpa FROM companies")
    companies = c.fetchall()
    conn.close()
    return companies

def get_roles():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT r.title, r.required_skills, c.name FROM roles r JOIN companies c ON r.company_id = c.id")
    roles = c.fetchall()
    conn.close()
    return roles

# Aptitude questions
def get_random_questions(count=20, category="general"):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, question, options, answer FROM aptitude_questions WHERE category = ? ORDER BY RANDOM() LIMIT ?",
              (category, count))
    questions = c.fetchall()
    conn.close()
    return questions

def add_aptitude_question(question, options, answer, category="general", difficulty="medium"):
    conn = get_db()
    c = conn.cursor()
    options_json = json.dumps(options)
    c.execute("INSERT INTO aptitude_questions (question, options, answer, category, difficulty) VALUES (?, ?, ?, ?, ?)",
              (question, options_json, answer, category, difficulty))
    question_id = c.lastrowid
    conn.commit()
    conn.close()
    return question_id

# Aptitude results
def save_aptitude_result(student_id, test_id, score, total_questions, answers):
    conn = get_db()
    c = conn.cursor()
    answers_json = json.dumps(answers)
    c.execute("INSERT INTO aptitude_results (student_id, test_id, score, total_questions, answers) VALUES (?, ?, ?, ?, ?)",
              (student_id, test_id, score, total_questions, answers_json))
    result_id = c.lastrowid
    conn.commit()
    conn.close()
    return result_id

def get_aptitude_results(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT score, total_questions, completed_at FROM aptitude_results WHERE student_id = ? ORDER BY completed_at DESC",
              (student_id,))
    results = c.fetchall()
    conn.close()
    return results

# AI matches
def save_ai_match(student_id, role_id, match_score, match_reason):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO ai_matches (student_id, role_id, match_score, match_reason) VALUES (?, ?, ?, ?)",
              (student_id, role_id, match_score, match_reason))
    match_id = c.lastrowid
    conn.commit()
    conn.close()
    return match_id

def get_ai_matches(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT am.match_score, am.match_reason, r.title, c.name
        FROM ai_matches am
        JOIN roles r ON am.role_id = r.id
        JOIN companies c ON r.company_id = c.id
        WHERE am.student_id = ?
        ORDER BY am.match_score DESC
    """, (student_id,))
    matches = c.fetchall()
    conn.close()
    return matches

# Slots
def schedule_slot(user_id, slot_time, created_by=None, notes=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO slots (user_id, slot_time, created_by, notes) VALUES (?, ?, ?, ?)",
              (user_id, slot_time, created_by, notes))
    conn.commit()
    conn.close()

def get_slots(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT slot_time, notes FROM slots WHERE user_id = ?", (user_id,))
    slots = c.fetchall()
    conn.close()
    return slots

def get_all_slots():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.user_id, s.slot_time, s.notes, u.name, u.email
        FROM slots s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.slot_time
    """)
    slots = c.fetchall()
    conn.close()
    return slots

def cancel_slot(slot_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    conn.commit()
    conn.close()

# Admin functions
def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role != 'admin' ORDER BY approved DESC, name")
    users = c.fetchall()
    conn.close()
    return users

def get_user_details(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def approve_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET approved = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# Initialize database
if __name__ == "__main__":
    init_db()
    seed_companies_and_roles()
    migrate_existing_data()
    print("Database initialized and migrated successfully.")
