#!/usr/bin/env python3
"""
Student Registration Form
Simple console-based form for student registration
"""

import sqlite3
import bcrypt
import getpass

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def register_student():
    """Student registration form"""
    print("=" * 50)
    print("STUDENT REGISTRATION FORM")
    print("=" * 50)

    # Collect student information
    name = input("Full Name: ").strip()
    email = input("Email: ").strip().lower()
    password = input("Password: ")
    confirm_password = input("Confirm Password: ")

    if password != confirm_password:
        print("❌ Passwords do not match!")
        return False

    cgpa = input("CGPA (optional): ").strip()
    cgpa = float(cgpa) if cgpa else None

    skills = input("Skills (comma separated): ").strip()
    resume_text = input("Resume text (paste your resume): ").strip()

    print("\n" + "=" * 50)

    # Confirm details
    print("Please confirm your details:")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"CGPA: {cgpa or 'Not provided'}")
    print(f"Skills: {skills}")
    print(f"Resume: {'Provided' if resume_text else 'Not provided'}")

    confirm = input("\nSubmit registration? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Registration cancelled.")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect('placement.db')
        c = conn.cursor()

        # Check if email already exists
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        if c.fetchone():
            print("❌ Email already registered!")
            return False

        # Hash password and insert user
        pwd_hash = hash_password(password)
        c.execute("""
            INSERT INTO users (name, email, password_hash, skills_text, resume, cgpa, role, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, pwd_hash, skills, resume_text, cgpa, "student", 0))

        conn.commit()
        conn.close()

        print("\n✅ Registration successful!")
        print("Your account is pending approval from an administrator.")
        print("You will be able to login once approved.")
        return True

    except Exception as e:
        print(f"❌ Registration failed: {str(e)}")
        return False

if __name__ == "__main__":
    register_student()