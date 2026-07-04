import sqlite3
import bcrypt

def init_db():
    conn = sqlite3.connect('placement.db')
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        skills_text TEXT,
        resume TEXT,
        cgpa REAL,
        role TEXT DEFAULT 'student',
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Create roles table
    c.execute('''CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        skill_text TEXT NOT NULL
    )''')

    # Create companies table
    c.execute('''CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        required_skills TEXT,
        min_cgpa REAL,
        role_id INTEGER,
        FOREIGN KEY(role_id) REFERENCES roles(id)
    )''')

    # Create results table
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        test_name TEXT,
        score INTEGER,
        total INTEGER,
        answers TEXT,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Create slots table
    c.execute('''CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        slot_time TEXT,
        created_by INTEGER,
        is_admin_slot BOOLEAN DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(created_by) REFERENCES users(id)
    )''')

    # Create aptitude_results table
    c.execute('''CREATE TABLE IF NOT EXISTS aptitude_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        test_name TEXT,
        score INTEGER,
        total INTEGER,
        answers TEXT,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Create ai_matches table
    c.execute('''CREATE TABLE IF NOT EXISTS ai_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role_id INTEGER,
        match_score REAL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(role_id) REFERENCES roles(id)
    )''')

    # Create tokens table
    c.execute('''CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        token TEXT UNIQUE,
        token_type TEXT,
        expires_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Create sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        token_hash TEXT UNIQUE,
        expires_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    conn.commit()
    conn.close()

def create_admin_user():
    """Create a default admin user if none exists"""
    conn = sqlite3.connect('placement.db')
    c = conn.cursor()

    # Check if admin exists
    c.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    if not c.fetchone():
        # Create admin user
        password = "admin123"  # Default password
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        c.execute("""
            INSERT INTO users (name, email, password_hash, branch, role, is_verified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("Administrator", "admin@placement.com", hashed.decode(), None, "admin", 1))

        print("Default admin user created:")
        print("Email: admin@placement.com")
        print("Password: admin123")
        print("Please change the password after first login!")

    conn.commit()
    conn.close()

def seed_demo_data():
    """Add some demo data for testing"""
    conn = sqlite3.connect('placement.db')
    c = conn.cursor()

    # Seed roles
    roles = [
        ("Backend Engineer", "python flask sql api django rest postgresql sqlite aws docker api development"),
        ("Data Scientist", "python pandas numpy scikit-learn statistics machine learning data analysis ml model"),
        ("Frontend Engineer", "javascript react html css typescript responsive design web ux"),
        ("DevOps Engineer", "docker kubernetes aws ci/cd linux monitoring infra terraform"),
    ]

    for title, skill_text in roles:
        c.execute("INSERT OR IGNORE INTO roles (title, skill_text) VALUES (?, ?)", (title, skill_text))

    print("Roles seeded successfully!")

    # Seed companies
    companies = [
        ("TCS", "python flask sql api django", 7.0, 1),
        ("Wipro", "java sql spring boot", 7.5, 1),
        ("Infosys", "javascript react html css", 7.2, 1),
        ("Google", "python machine learning data analysis", 8.0, 2),
        ("Microsoft", "javascript react typescript azure", 8.5, 3),
        ("Amazon", "docker kubernetes aws terraform", 8.2, 4),
    ]

    for name, skills, min_cgpa, role_id in companies:
        c.execute("INSERT OR IGNORE INTO companies (name, required_skills, min_cgpa, role_id) VALUES (?, ?, ?, ?)",
                 (name, skills, min_cgpa, role_id))

    # Create some demo students (unverified)
    demo_students = [
        ("John Doe", "john@example.com", "john123", "python javascript html css", "Experienced developer with 2 years of experience", 8.5),
        ("Jane Smith", "jane@example.com", "jane123", "java sql spring boot", "Software engineering student with database experience", 8.2),
        ("Bob Johnson", "bob@example.com", "bob123", "javascript react node.js", "Frontend developer passionate about UI/UX", 7.8),
    ]

    for name, email, password, skills, resume, cgpa in demo_students:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        c.execute("""
            INSERT OR IGNORE INTO users (name, email, password_hash, skills_text, resume, cgpa, branch, role, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, hashed.decode(), skills, resume, cgpa, "Computer Science", "student", 0))

    conn.commit()
    conn.close()
    print("Demo data seeded successfully!")

if __name__ == "__main__":
    init_db()
    create_admin_user()
    seed_demo_data()
    print("Database initialized successfully!")