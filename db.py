import sqlite3
import bcrypt
import json
from datetime import datetime
import time
import random
import os

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

def try_steal_lock(pid, lock_file):
    """Attempt to steal the lock if the owning process is dead."""
    if PSUTIL_AVAILABLE:
        try:
            process = psutil.Process(pid)
            if process.is_running():
                return False  # Process is still running, don't steal
            else:
                # Process is dead, remove lock and steal
                try:
                    os.remove(lock_file)
                    with open(lock_file, 'w') as f:
                        f.write(str(os.getpid()))
                    return True
                except:
                    return False
        except psutil.NoSuchProcess:
            # Process doesn't exist, safe to steal
            try:
                os.remove(lock_file)
                with open(lock_file, 'w') as f:
                    f.write(str(os.getpid()))
                return True
            except:
                return False
    else:
        # Without psutil, we can't reliably check, so assume it's dead and try to steal
        try:
            os.remove(lock_file)
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except:
            return False

def get_db_connection(retries=5, timeout=0.1):
    """Get database connection with retry logic for concurrent access."""
    for attempt in range(retries):
        try:
            conn = sqlite3.connect('placement.db', timeout=timeout)
            print(f"DEBUG: Database connection established on attempt {attempt + 1}")
            return conn
        except sqlite3.OperationalError as e:
            print(f"DEBUG: Connection attempt {attempt + 1} failed: {e}")
            if "database is locked" in str(e) and attempt < retries - 1:
                # Exponential backoff with jitter
                delay = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)
                print(f"DEBUG: Database locked, retrying in {delay:.2f} seconds")
                time.sleep(delay)
                continue
            else:
                print(f"DEBUG: Giving up after {attempt + 1} attempts")
                raise e

def init_db():
    print("DEBUG: Starting database initialization")
    # Use file-based locking to prevent concurrent initialization
    lock_file = 'placement.db.lock'
    lock_acquired = False

    try:
        print("DEBUG: Checking for lock file")
        # Try to create lock file atomically
        try:
            with open(lock_file, 'x') as f:
                f.write(str(os.getpid()))
            lock_acquired = True
            print("DEBUG: Lock acquired successfully")
        except FileExistsError:
            print("DEBUG: Lock file exists, waiting...")
            # Lock file exists, wait for other process to complete
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if not os.path.exists(lock_file):
                    print("DEBUG: Lock file removed, proceeding")
                    break
                if i % 5 == 0:
                    print(f"DEBUG: Still waiting for lock, {i} seconds elapsed")
            else:
                print("DEBUG: Timeout waiting for lock, attempting to steal")
                # Timeout - try to steal the lock if process is dead
                try:
                    with open(lock_file, 'r') as f:
                        pid = int(f.read().strip())
                    print(f"DEBUG: Attempting to steal lock from PID {pid}")
                    # Check if process is still running (cross-platform)
                    success = try_steal_lock(pid, lock_file)
                    if success:
                        lock_acquired = True
                        print("DEBUG: Lock stolen successfully")
                    else:
                        print("DEBUG: Failed to steal lock, giving up")
                        return  # Give up
                except (ValueError, FileNotFoundError) as e:
                    print(f"DEBUG: Invalid lock file: {e}, removing")
                    # Invalid lock file, remove it
                    try:
                        os.remove(lock_file)
                        with open(lock_file, 'w') as f:
                            f.write(str(os.getpid()))
                        lock_acquired = True
                        print("DEBUG: Invalid lock removed, new lock acquired")
                    except Exception as e:
                        print(f"DEBUG: Failed to create new lock: {e}")
                        pass

        if not lock_acquired:
            print("DEBUG: Lock not acquired, skipping initialization")
            return  # Another process is initializing

        print("DEBUG: Proceeding with database initialization")
        # Now initialize the database
        conn = get_db_connection()
        c = conn.cursor()
        print("DEBUG: Got database connection for initialization")

        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            skills TEXT,
            resume TEXT,
            cgpa REAL,
            phone TEXT,
            approved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        print("DEBUG: Ensured users table exists")

        # Companies table
        c.execute('''CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            required_skills TEXT,
            min_cgpa REAL DEFAULT 0.0
        )''')

        # Results table
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

        # Slots table
        c.execute('''CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            slot_time TEXT,
            notes TEXT
        )''')

        # Seed some data
        companies = [
            ("TechCorp", "Leading technology company", "Python, Java, SQL, AWS", 7.0),
            ("DataSolutions", "Data analytics firm", "Python, SQL, Excel, Machine Learning", 6.5),
            ("WebMasters", "Web development agency", "HTML, CSS, JavaScript, React", 6.0),
            ("CloudOps", "Cloud infrastructure specialists", "AWS, Docker, Linux, Kubernetes", 7.5),
            ("InnovatePM", "Product management consultancy", "Agile, Communication, Strategy, Scrum", 7.0)
        ]
        c.executemany("INSERT OR IGNORE INTO companies (name, description, required_skills, min_cgpa) VALUES (?, ?, ?, ?)", companies)

        # Seed default admin user
        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ("Admin", "admin@placement.com", hashed, "admin"))

        conn.commit()
        conn.close()
        print("DEBUG: Database initialization completed successfully")
    except Exception as e:
        print(f"DEBUG: Error during database initialization: {e}")
        # Clean up lock file on any error
        if lock_acquired:
            try:
                os.remove(lock_file)
            except Exception:
                pass
        raise e
    finally:
        # Always try to clean up lock file when done
        if lock_acquired:
            try:
                os.remove(lock_file)
                print("DEBUG: Lock file cleaned up")
            except Exception:
                pass

def create_user(name, email, password, cgpa=None, phone=None, role="student"):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (name, email, password, cgpa, phone, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (name, email.lower(), hashed, cgpa, phone, role, datetime.now().isoformat()))
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id

def find_user_by_email(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    user = c.fetchone()
    conn.close()
    return user

def update_user_skills(uid, skills_text=None, resume_text=None, approved=None, cgpa=None):
    conn = get_db_connection()
    c = conn.cursor()
    if skills_text is not None:
        c.execute("UPDATE users SET skills = ? WHERE id = ?", (skills_text, uid))
    if resume_text is not None:
        c.execute("UPDATE users SET resume = ? WHERE id = ?", (resume_text, uid))
    if approved is not None:
        c.execute("UPDATE users SET approved = ? WHERE id = ?", (approved, uid))
    if cgpa is not None:
        c.execute("UPDATE users SET cgpa = ? WHERE id = ?", (cgpa, uid))
    conn.commit()
    conn.close()

def get_user_by_id(uid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (uid,))
    user = c.fetchone()
    conn.close()
    return user

def get_all_companies():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, description, required_skills, min_cgpa FROM companies")
    companies = c.fetchall()
    conn.close()
    return companies

def save_result(uid, test_name, score, total, answers):
    conn = get_db_connection()
    c = conn.cursor()
    answers_json = json.dumps(answers)
    c.execute("INSERT INTO results (user_id, test_name, score, total, answers, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
              (uid, test_name, score, total, answers_json, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_results(uid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT test_name, score, total, answers, timestamp FROM results WHERE user_id = ?", (uid,))
    results = c.fetchall()
    conn.close()
    return results

def schedule_slot(uid, slot_time, notes=""):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO slots (user_id, slot_time, notes) VALUES (?, ?, ?)", (uid, slot_time, notes))
    conn.commit()
    conn.close()

def get_slots(uid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT slot_time, notes FROM slots WHERE user_id = ?", (uid,))
    slots = c.fetchall()
    conn.close()
    return slots

def get_all_students():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, email, cgpa, skills, resume, approved, created_at FROM users WHERE role = 'student'")
    students = c.fetchall()
    conn.close()
    return students

def get_all_slots():
    conn = get_db_connection()
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
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    conn.commit()
    conn.close()

def update_slot(slot_id, new_time, new_notes):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE slots SET slot_time = ?, notes = ? WHERE id = ?", (new_time, new_notes, slot_id))
    conn.commit()
    conn.close()

def get_unapproved_students():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, email, cgpa, skills, resume, created_at FROM users WHERE role = 'student' AND approved = 0")
    students = c.fetchall()
    conn.close()
    return students

def approve_student(student_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET approved = 1 WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

def reject_student(student_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, email, role, approved FROM users")
    users = c.fetchall()
    conn.close()
    return users