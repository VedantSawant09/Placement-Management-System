#!/usr/bin/env python3
"""
Admin Portal for Placement Management System
Console-based admin interface for managing students and tests
"""

import getpass
import bcrypt
import json
from datetime import datetime
from aimatcher import compute_match
from database import get_roles
from db import get_db_connection

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def admin_login():
    """Admin login"""
    print("=" * 50)
    print("ADMIN PORTAL LOGIN")
    print("=" * 50)

    email = input("Admin Email: ").strip().lower()
    password = input("Password: ")

    # Check against database
    conn = sqlite3.connect('placement.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,))
    admin = c.fetchone()
    conn.close()

    if not admin or not check_password(password, admin[3]):  # admin[3] is password_hash
        print("❌ Invalid admin credentials!")
        return False

    print("✅ Admin login successful!")
    return True

def view_all_submissions():
    """View all student submissions"""
    print("\n" + "=" * 80)
    print("ALL STUDENT SUBMISSIONS")
    print("=" * 80)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, name, email, skills_text, cgpa, resume, is_verified, created_at
        FROM users WHERE role = 'student'
        ORDER BY created_at DESC
    """)
    students = c.fetchall()
    conn.close()

    if not students:
        print("No student submissions found.")
        return []

    print(f"Total submissions: {len(students)}")
    print("-" * 120)

    # Print header
    print(f"{'ID':<5} {'Name':<20} {'Email':<30} {'CGPA':<5} {'Skills':<25} {'Resume':<10} {'Status':<10} {'Submitted':<15}")
    print("-" * 120)

    for student in students:
        student_id, name, email, skills, cgpa, resume, is_verified, created_at = student
        status = "APPROVED" if is_verified else "PENDING"
        resume_status = "YES" if resume else "NO"
        cgpa_display = str(cgpa) if cgpa else "N/A"
        skills_display = skills[:20] + "..." if skills and len(skills) > 20 else (skills or "N/A")
        submitted_date = created_at.split('T')[0] if created_at else "N/A"

        print(f"{student_id:<5} {name[:19]:<20} {email[:29]:<30} {cgpa_display:<5} {skills_display:<25} {resume_status:<10} {status:<10} {submitted_date:<15}")

    return students

def run_ai_skill_match(student_id):
    """Run AI skill matching for a specific student"""
    print(f"\n🔍 Running AI Skill Match for Student ID: {student_id}")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, email, skills_text, resume, cgpa FROM users WHERE id = ? AND role = 'student'", (student_id,))
    student = c.fetchone()
    conn.close()

    if not student:
        print("❌ Student not found!")
        return

    print(f"Student: {student[0]} ({student[1]})")
    print(f"CGPA: {student[4] or 'N/A'}")

    # Get roles for matching
    roles_data = []
    roles = get_roles()
    for role in roles:
        title, skills, company = role
        roles_data.append((title, skills, company))

    # Run matching
    resume_text = student[3] or student[2] or ""  # resume or skills
    matches = compute_match(resume_text, roles_data, student[4])

    print("\n🎯 AI MATCHING RESULTS:")
    print("-" * 50)

    for i, match in enumerate(matches[:5], 1):  # Top 5 matches
        title, score, company, eligible = match
        percentage = score * 100
        status = "✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"

        print(f"{i}. {title} at {company}")
        print(".1f")
        print(f"   CGPA Eligibility: {status}")
        print()

def assign_aptitude_test(student_id, test_name):
    """Assign an aptitude test to a student (auto-generate score)"""
    print(f"\n📝 Assigning aptitude test '{test_name}' to Student ID: {student_id}")

    # Load test data
    try:
        with open(f"tests/{test_name}.json", 'r') as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Test file '{test_name}.json' not found!")
        return

    # Simulate taking the test (auto-generate answers)
    import random
    questions = test_data.get("questions", [])
    score = 0
    answers = {}

    print(f"Simulating test with {len(questions)} questions...")

    for i, q in enumerate(questions):
        # Randomly select an answer (simulate student taking test)
        user_answer = random.choice(q["options"])

        # Check if correct
        if user_answer.lower().strip() == q["answer"].lower().strip():
            score += 1

        answers[f"q{i}"] = user_answer

    # Store result in database
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO results (user_id, test_name, score, total, answers, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, test_name, score, len(questions), json.dumps(answers), datetime.now().isoformat()))

    conn.commit()
    conn.close()

    percentage = (score / len(questions)) * 100
    print(".1f")

def show_dashboard():
    """Show admin dashboard with scores and statistics"""
    print("\n" + "=" * 80)
    print("ADMIN DASHBOARD - SCORES & STATISTICS")
    print("=" * 80)

    conn = sqlite3.connect('placement.db')
    c = conn.cursor()

    # Get all test results with student info
    c.execute("""
        SELECT r.test_name, r.score, r.total, r.timestamp, u.name, u.email
        FROM results r
        JOIN users u ON r.user_id = u.id
        WHERE u.role = 'student'
        ORDER BY r.timestamp DESC
        LIMIT 20
    """)
    results = c.fetchall()

    # Get statistics
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'student' AND is_verified = 1")
    verified_students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM results")
    total_tests = c.fetchone()[0]

    c.execute("SELECT AVG(score * 1.0 / total) FROM results")
    avg_score = c.fetchone()[0]

    conn.close()

    print("📊 OVERVIEW:")
    print(f"   Verified Students: {verified_students}")
    print(f"   Total Tests Taken: {total_tests}")
    print(".1f")
    print()
    print("📈 RECENT TEST RESULTS:")
    print("-" * 80)

    if not results:
        print("No test results found.")
    else:
        for result in results:
            test_name, score, total, timestamp, name, email = result
            percentage = (score / total) * 100
            print(f"Test: {test_name}")
            print(f"Student: {name} ({email})")
            print(".1f")
            print(f"Date: {timestamp}")
            print("-" * 80)

def admin_menu():
    """Main admin menu"""
    while True:
        print("\n" + "=" * 50)
        print("ADMIN PORTAL MENU")
        print("=" * 50)
        print("1. View All Student Submissions")
        print("2. Run AI Skill Match for Student")
        print("3. Assign Aptitude Test to Student")
        print("4. View Dashboard & Statistics")
        print("5. Exit")
        print("=" * 50)

        choice = input("Enter choice (1-5): ").strip()

        if choice == "1":
            view_all_submissions()

        elif choice == "2":
            students = view_all_submissions()
            if students:
                try:
                    student_id = int(input("Enter Student ID for AI matching: ").strip())
                    run_ai_skill_match(student_id)
                except ValueError:
                    print("❌ Invalid student ID!")

        elif choice == "3":
            students = view_all_submissions()
            if students:
                try:
                    student_id = int(input("Enter Student ID: ").strip())
                    print("Available tests: techcorp_aptitude, techcorp_technical, datasolutions_aptitude, webmasters_technical")
                    test_name = input("Enter test name: ").strip()
                    assign_aptitude_test(student_id, test_name)
                except ValueError:
                    print("❌ Invalid student ID!")

        elif choice == "4":
            show_dashboard()

        elif choice == "5":
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    if admin_login():
        admin_menu()
    else:
        print("Login failed. Exiting...")