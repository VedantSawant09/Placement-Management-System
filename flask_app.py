from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_file, send_from_directory, jsonify
import sqlite3
import bcrypt
import json
from pathlib import Path
from datetime import datetime, timezone
import io
import logging
import uuid
import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from functools import wraps
from auth import create_email_verification_token, send_verification_email, verify_email_token, create_jwt_token, verify_jwt_token, invalidate_jwt_token

def jwt_admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        token = token.split(' ')[1]
        payload = verify_jwt_token(token)
        if not payload or payload.get('role') != 'admin':
            return jsonify({'error': 'Invalid token or insufficient permissions'}), 401
        g.user_id = payload['user_id']
        g.user_role = payload['role']
        return f(*args, **kwargs)
    return wrapped
from ai_matcher import get_student_matches, update_matches, match_student_to_jobs
from database import save_aptitude_result, get_aptitude_results, get_ai_matches
# Simple text similarity without scikit-learn for compatibility
def simple_text_similarity(text1, text2):
    """Simple word overlap similarity"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union) if union else 0

APP_SECRET = "replace_this_with_a_random_string_for_demo"
DB_PATH = "placement.db"
TESTS_DIR = Path("tests")
UPLOAD_FOLDER = Path("uploads/resumes")
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.secret_key = APP_SECRET
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------
# DB helpers
# ---------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    return cur.lastrowid

# ---------------------------
# Auth
# ---------------------------

def hash_password(password: str) -> str:
    logger.info(f"Hashing password for user")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    logger.info(f"Password hashed successfully")
    return hashed

def check_password(password: str, hashed: str) -> bool:
    logger.info(f"Verifying password")
    try:
        result = bcrypt.checkpw(password.encode(), hashed.encode())
        logger.info(f"Password verification: {'success' if result else 'failed'}")
        return result
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def interviewer_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = query_db("SELECT role FROM users WHERE id = ?", (session["user_id"],), one=True)
        if not user or user["role"] != "interviewer":
            flash("Access denied. Interviewer privileges required.", "danger")
            return redirect(url_for("dashboard"))
        logger.info(f"Interviewer access granted for user_id: {session['user_id']}")
        return f(*args, **kwargs)
    return wrapped

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = query_db("SELECT role FROM users WHERE id = ?", (session["user_id"],), one=True)
        if not user or user["role"] != "admin":
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for("dashboard"))
        logger.info(f"Admin access granted for user_id: {session['user_id']}")
        return f(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form.get("role", "student")  # Default to student if not specified
        skills = request.form.get("skills","")
        resume = request.form.get("resume","")
        cgpa = request.form.get("cgpa")

        if query_db("SELECT id FROM users WHERE email = ?", (email,), one=True):
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        # Admins are verified immediately, students need approval
        is_verified = 1 if role == "admin" else 0

        # Handle optional name for admin
        if role == "admin" and not name:
            name = "Admin"

        pwd_hash = hash_password(password)
        execute_db("INSERT INTO users (name, email, password_hash, skills_text, resume, cgpa, role, is_verified) VALUES (?,?,?,?,?,?,?,?)",
                    (name, email, pwd_hash, skills, resume, cgpa, role, is_verified))

        if role == "admin":
            flash("Admin registration successful! You can now log in.", "success")
        else:
            flash("Registration submitted successfully! Your account will be reviewed by an administrator before you can log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/student_register", methods=["GET","POST"])
def student_register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        skills = request.form.get("skills","")
        resume = request.form.get("resume","")
        cgpa = request.form.get("cgpa")
        branch = request.form.get("branch","")

        if query_db("SELECT id FROM users WHERE email = ?", (email,), one=True):
            flash("Email already registered.", "danger")
            return redirect(url_for("student_register"))

        pwd_hash = hash_password(password).decode()
        user_id = execute_db("INSERT INTO users (name, email, password_hash, skills_text, resume, cgpa, branch, role, is_verified) VALUES (?,?,?,?,?,?,?,?,?)",
                    (name, email, pwd_hash, skills, resume, cgpa, branch, "student", 0))

        # Create email verification token
        verification_token = create_email_verification_token(user_id)
        send_verification_email(email, verification_token)

        flash("Student registration submitted successfully! Please check your email to verify your account.", "success")
        return redirect(url_for("login"))
    return render_template("student_register.html")

@app.route("/admin_register", methods=["GET","POST"])
def admin_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if query_db("SELECT id FROM users WHERE email = ?", (email,), one=True):
            flash("Email already registered.", "danger")
            return redirect(url_for("admin_register"))

        # Handle optional name for admin
        if not name:
            name = "Admin"

        pwd_hash = hash_password(password)
        execute_db("INSERT INTO users (name, email, password_hash, skills_text, resume, cgpa, branch, role, is_verified) VALUES (?,?,?,?,?,?,?,?,?)",
                    (name, email, pwd_hash, None, None, None, None, "admin", 1))

        flash("Admin registration successful! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("admin_register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if not user:
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))
        if not check_password(password, user["password_hash"]):
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

        # Check if user is verified (for students)
        if user["role"] == "student" and user["is_verified"] == 0:
            flash("Your account is pending approval from an administrator.", "warning")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]

        # Redirect based on role
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin/login", methods=["POST"])
def admin_jwt_login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = query_db("SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,), one=True)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not check_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    # Create JWT token
    token = create_jwt_token(user["id"], "admin")

    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": "admin"
        }
    })

@app.route("/admin/register", methods=["POST"])
def admin_jwt_register():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    if query_db("SELECT id FROM users WHERE email = ?", (email,), one=True):
        return jsonify({"error": "Email already registered"}), 400

    # Handle optional name
    if not name:
        name = "Admin"

    pwd_hash = hash_password(password)
    user_id = execute_db("INSERT INTO users (name, email, password_hash, role, is_verified) VALUES (?,?,?,?,?)",
                        (name, email, pwd_hash, "admin", 1))

    # Create JWT token
    token = create_jwt_token(user_id, "admin")

    return jsonify({
        "message": "Admin registered successfully",
        "token": token,
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "role": "admin"
        }
    })

# ---------------------------
# Tests endpoints
# ---------------------------

def load_test(filename):
    path = TESTS_DIR / filename
    return json.loads(path.read_text(encoding="utf8"))

@app.route("/tests")
@login_required
def tests():
    files = [p.name for p in TESTS_DIR.glob("*.json")]
    return render_template("index.html", tests=files)

@app.route("/take_test/<testfile>", methods=["GET","POST"])
@login_required
def take_test(testfile):
    test = load_test(testfile)
    if request.method == "POST":
        answers = {}
        score = 0
        for i, q in enumerate(test["questions"]):
            ans = request.form.get(f"q{i}", "")
            answers[f"q{i}"] = ans
            if ans.strip().lower() == q["answer"].strip().lower():
                score += 1
        total = len(test["questions"])
        percent = (score/total)*100
        uid = session["user_id"]
        save_aptitude_result(uid, testfile, score, total, answers)
        # Update AI matches after test
        update_matches(uid)
        return redirect(url_for("dashboard"))
    return render_template("take_test.html", test=test, testfile=testfile)

def get_last_result_id(user_id):
    row = query_db("SELECT id FROM results WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,), one=True)
    return row["id"]

@app.route("/result/<int:result_id>")
@login_required
def view_result(result_id):
    r = query_db("SELECT * FROM results WHERE id = ?", (result_id,), one=True)
    return render_template("view_result.html", r=r)

# ---------------------------
# Schedule aptitude slot
# ---------------------------
@app.route("/schedule", methods=["GET","POST"])
@login_required
def schedule_slot():
    if request.method == "POST":
        slot_time = request.form["slot_time"]
        interview_type = request.form.get("interview_type", "Interview")
        uid = session["user_id"]
        # Store both slot_time and interview_type in the slot_time field for simplicity
        slot_info = f"{slot_time} - {interview_type}"
        execute_db("INSERT INTO slots (user_id, slot_time, created_by, is_admin_slot) VALUES (?,?,?,?)", (uid, slot_info, uid, 0))
        flash("Interview slot booked successfully!", "success")
        return redirect(url_for("dashboard"))
    slots = query_db("SELECT * FROM slots WHERE user_id = ?", (session["user_id"],))
    return render_template("schedule_slot.html", slots=slots, datetime=datetime)

# ---------------------------
# Dashboard & Skills-matching
# ---------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    user = query_db("SELECT * FROM users WHERE id = ?", (uid,), one=True)
    results = query_db("SELECT * FROM results WHERE user_id = ? ORDER BY timestamp DESC", (uid,))
    slots = query_db("SELECT * FROM slots WHERE user_id = ?", (uid,))
    roles = query_db("SELECT id, title, skill_text FROM roles")
    role_titles = [r["title"] for r in roles]
    role_texts = [r["skill_text"] for r in roles]
    student_text = user["skills_text"] or ""
    matches = []
    if role_texts and student_text.strip():
        # Use simple text similarity instead of scikit-learn
        similarities = []
        for i, role_text in enumerate(role_texts):
            sim = simple_text_similarity(student_text, role_text)
            similarities.append((roles[i]["title"], sim))
        matches = sorted(similarities, key=lambda x: x[1], reverse=True)[:5]

    # For interviewers, fetch registered users data
    interviewer_data = None
    if user["role"] == "interviewer":
        logger.info("Fetching registered users data for interviewer dashboard section")
        users = query_db("SELECT id, name, email, skills_text, cgpa, resume, created_at FROM users WHERE role != 'interviewer'")
        user_count = len(users)
        interviewer_data = {"users": users, "user_count": user_count}
        logger.info(f"Retrieved {user_count} users for interviewer section")

    return render_template("dashboard.html", user=user, results=results, slots=slots, matches=matches, interviewer_data=interviewer_data)

@app.route("/interviewer_dashboard")
@interviewer_required
def interviewer_dashboard():
    logger.info("Fetching all registered users for interviewer dashboard")
    users = query_db("SELECT id, name, email, skills_text, cgpa, resume, created_at FROM users WHERE role != 'interviewer'")
    user_count = len(users)
    logger.info(f"Retrieved {user_count} users for interviewer dashboard")
    return render_template("interviewer_dashboard.html", users=users, user_count=user_count)

@app.route("/student_registrations")
@admin_required
def student_registrations():
    logger.info("Fetching pending student registrations for approval")
    # Fetch only unverified students
    pending_students = query_db("SELECT id, name, email, skills_text, cgpa, resume, created_at FROM users WHERE role = 'student' AND is_verified = 0")
    logger.info(f"Retrieved {len(pending_students)} pending student registrations")
    return render_template("student_registrations.html", students=pending_students)

@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():
    logger.info("Fetching all registered users for admin dashboard")
    users = query_db("SELECT id, name, email, skills_text, cgpa, resume, role, is_verified, created_at FROM users")
    user_count = len(users)
    student_count = len([u for u in users if u["role"] == "student"])
    interviewer_count = len([u for u in users if u["role"] == "interviewer"])
    admin_count = len([u for u in users if u["role"] == "admin"])
    verified_count = len([u for u in users if u["is_verified"] == 1])
    unverified_count = len([u for u in users if u["is_verified"] == 0])

    # Fetch only admin-created slots
    all_slots = query_db("""
        SELECT s.*, u.name as user_name, creator.name as creator_name
        FROM slots s
        LEFT JOIN users u ON s.user_id = u.id
        LEFT JOIN users creator ON s.created_by = creator.id
        WHERE s.is_admin_slot = 1
        ORDER BY s.id DESC
    """)

    logger.info(f"Retrieved {user_count} users and {len(all_slots)} slots for admin dashboard")
    return render_template("admin_dashboard.html", users=users, user_count=user_count,
                          student_count=student_count, interviewer_count=interviewer_count,
                          admin_count=admin_count, verified_count=verified_count,
                          unverified_count=unverified_count, all_slots=all_slots)

# ---------------------------
# Admin-ish: seed roles (for demo)
# ---------------------------
@app.route("/seed_roles")
def seed_roles():
    exists = query_db("SELECT id FROM roles LIMIT 1", one=True)
    if exists:
        return "Already seeded"
    demo_roles = [
        ("Backend Engineer", "python flask sql api django rest postgresql sqlite aws docker api development"),
        ("Data Scientist", "python pandas numpy scikit-learn statistics machine learning data analysis ml model"),
        ("Frontend Engineer", "javascript react html css typescript responsive design web ux"),
        ("DevOps Engineer", "docker kubernetes aws ci/cd linux monitoring infra terraform"),
    ]
    for title, skill_text in demo_roles:
        execute_db("INSERT INTO roles (title, skill_text) VALUES (?,?)", (title, skill_text))
    return "Seeded"

# ---------------------------
# Download Routes
# ---------------------------
@app.route("/download_test/<testfile>")
@login_required
def download_test(testfile):
    """Allow students to download test question papers"""
    try:
        test_path = TESTS_DIR / testfile
        if test_path.exists():
            return send_from_directory(TESTS_DIR, testfile, as_attachment=True,
                                     download_name=f"{testfile}")
        else:
            flash("Test file not found.", "danger")
            return redirect(url_for("index"))
    except Exception as e:
        flash(f"Error downloading test: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/download_resume/<int:user_id>")
@login_required
def download_resume(user_id):
    """Allow interviewers and admins to download student resumes"""
    # Check if current user is interviewer or admin
    current_user = query_db("SELECT role FROM users WHERE id = ?", (session["user_id"],), one=True)
    if current_user["role"] not in ["interviewer", "admin"]:
        flash("Access denied. Interviewer or admin privileges required.", "danger")
        return redirect(url_for("dashboard"))

    # Get student resume
    student = query_db("SELECT name, resume FROM users WHERE id = ?", (user_id,), one=True)
    if not student or not student["resume"]:
        flash("Resume not found.", "danger")
        return redirect(url_for("interviewer_dashboard"))

    # Create a text file with the resume content
    resume_content = f"Resume for {student['name']}\n\n{student['resume']}"
    resume_io = io.BytesIO()
    resume_io.write(resume_content.encode('utf-8'))
    resume_io.seek(0)

    filename = f"resume_{student['name'].replace(' ', '_')}.txt"
    return send_file(resume_io, as_attachment=True, download_name=filename,
                    mimetype='text/plain')

@app.route("/user_profile/<int:user_id>")
@login_required
def user_profile(user_id):
    logger.info(f"Fetching profile for user_id: {user_id}")
    # Allow access for interviewers and admins
    current_user = query_db("SELECT role FROM users WHERE id = ?", (session["user_id"],), one=True)
    if current_user["role"] not in ["interviewer", "admin"]:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    user = query_db("SELECT id, name, email, skills_text, cgpa, resume, created_at FROM users WHERE id = ? AND role != 'interviewer'", (user_id,), one=True)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("interviewer_dashboard"))
    results = query_db("SELECT * FROM results WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    slots = query_db("SELECT * FROM slots WHERE user_id = ?", (user_id,))
    logger.info(f"Profile data retrieved for user_id: {user_id}")
    return render_template("user_profile.html", user=user, results=results, slots=slots)

# ---------------------------#
# User Verification Management
# ---------------------------#

@app.route("/verify_user/<int:user_id>", methods=["POST"])
@admin_required
def verify_user(user_id):
    try:
        execute_db("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
        return {"success": True, "message": "User verified successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}, 500

@app.route("/reject_user/<int:user_id>", methods=["DELETE"])
@admin_required
def reject_user(user_id):
    try:
        execute_db("DELETE FROM users WHERE id = ?", (user_id,))
        return {"success": True, "message": "User rejected and deleted successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}, 500

# ---------------------------#
# Admin Slot Management
# ---------------------------#

@app.route("/admin_slots", methods=["GET", "POST"])
@admin_required
def admin_slots():
    # Get all users (students) for display
    users = query_db("SELECT id, name, email, skills_text, cgpa, resume, role, is_verified, created_at FROM users WHERE role = 'student' ORDER BY created_at DESC")

    return render_template("admin_slots.html", users=users)

@app.route("/delete_slot/<int:slot_id>", methods=["DELETE"])
@admin_required
def delete_slot(slot_id):
    try:
        # Check if slot exists and is admin-created
        slot = query_db("SELECT * FROM slots WHERE id = ? AND is_admin_slot = 1", (slot_id,), one=True)
        if not slot:
            return {"success": False, "message": "Slot not found or not admin-created"}, 404

        execute_db("DELETE FROM slots WHERE id = ?", (slot_id,))
        return {"success": True, "message": "Slot deleted successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}, 500

# ---------------------------#
# Admin AI Matching
# ---------------------------#

@app.route("/admin_ai_matching")
@admin_required
def admin_ai_matching():
    logger.info("Running AI eligibility matching for all students")
    from aimatcher import compute_match
    from database import get_roles, get_companies, get_all_users

    # Get all roles with companies
    roles_data = []
    roles = get_roles()
    for role in roles:
        title, skills, company = role
        roles_data.append((title, skills, company))

    # Get all verified students
    students = query_db("SELECT id, name, email, skills_text, resume, cgpa FROM users WHERE role = 'student' AND is_verified = 1")

    # Run matching for each student
    student_matches = []
    for student in students:
        logger.info(f"Processing AI matching for student: {student['name']}")
        resume_text = student['resume'] or student['skills_text'] or ""
        matches = compute_match(resume_text, roles_data, student['cgpa'])

        student_matches.append({
            'student': student,
            'matches': matches
        })

    logger.info(f"AI matching completed for {len(students)} students")
    return render_template("admin_ai_matching.html", student_matches=student_matches, len=len)

@app.route("/admin/dashboard/stats", methods=["GET"])
@jwt_admin_required
def admin_dashboard_stats():
    # Get student stats
    total_students = query_db("SELECT COUNT(*) as count FROM users WHERE role = 'student'", one=True)["count"]
    approved_students = query_db("SELECT COUNT(*) as count FROM users WHERE role = 'student' AND is_verified = 1", one=True)["count"]
    pending_approvals = total_students - approved_students

    # Get average CGPA for approved students
    avg_cgpa_result = query_db("SELECT AVG(cgpa) as avg_cgpa FROM users WHERE role = 'student' AND is_verified = 1 AND cgpa IS NOT NULL", one=True)
    avg_cgpa = round(avg_cgpa_result["avg_cgpa"], 2) if avg_cgpa_result["avg_cgpa"] else 0

    # Get average skill match percentage (from ai_matches table)
    avg_match_result = query_db("SELECT AVG(match_score) as avg_match FROM ai_matches", one=True)
    avg_skill_match = round(avg_match_result["avg_match"], 2) if avg_match_result["avg_match"] else 0

    return jsonify({
        "total_students": total_students,
        "approved_students": approved_students,
        "pending_approvals": pending_approvals,
        "avg_cgpa": avg_cgpa,
        "avg_skill_match": avg_skill_match
    })

@app.route("/admin/students/table", methods=["GET"])
@jwt_admin_required
def admin_students_table():
    # Get query parameters for search/filter
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')  # all, approved, pending
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))

    # Build base query
    base_query = """
        SELECT u.id, u.name, u.email, u.cgpa, u.branch, u.skills_text, u.resume,
               u.is_verified, u.created_at, ar.score as aptitude_score,
               ROUND(AVG(am.match_score), 2) as avg_match_score
        FROM users u
        LEFT JOIN aptitude_results ar ON u.id = ar.user_id
        LEFT JOIN ai_matches am ON u.id = am.user_id
        WHERE u.role = 'student'
    """

    # Add filters
    params = []
    if search:
        base_query += " AND (u.name LIKE ? OR u.email LIKE ? OR u.skills_text LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])

    if status_filter == 'approved':
        base_query += " AND u.is_verified = 1"
    elif status_filter == 'pending':
        base_query += " AND u.is_verified = 0"

    # Group by and pagination
    base_query += " GROUP BY u.id ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    students = query_db(base_query, params)

    # Get total count for pagination
    count_query = """
        SELECT COUNT(DISTINCT u.id) as total
        FROM users u
        WHERE u.role = 'student'
    """
    count_params = []
    if search:
        count_query += " AND (u.name LIKE ? OR u.email LIKE ? OR u.skills_text LIKE ?)"
        search_param = f"%{search}%"
        count_params.extend([search_param, search_param, search_param])

    if status_filter == 'approved':
        count_query += " AND u.is_verified = 1"
    elif status_filter == 'pending':
        count_query += " AND u.is_verified = 0"

    total_result = query_db(count_query, count_params, one=True)
    total_students = total_result['total'] if total_result else 0
    total_pages = (total_students + per_page - 1) // per_page

    result = {
        "students": [dict(student) for student in students],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_students": total_students,
            "total_pages": total_pages
        },
        "filters": {
            "search": search,
            "status": status_filter
        }
    }

    return jsonify(result)
# ---------------------------
# Utilities for dev/testing
# ---------------------------
@app.route("/my_results")
@login_required
def my_results():
    uid = session["user_id"]
    results = query_db("SELECT * FROM results WHERE user_id = ?", (uid,))
    return {"results":[dict(r) for r in results]}

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)