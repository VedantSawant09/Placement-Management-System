import streamlit as st
from db import init_db, create_user, find_user_by_email, update_user_skills, get_user_by_id, get_all_companies, save_result, get_user_results, schedule_slot, get_slots, get_unapproved_students, approve_student, reject_student, get_all_users, get_all_students
from ai_match import compute_matches, is_eligible
from utils import extract_text_from_pdf, extract_skills_from_text
from pathlib import Path
import json
import bcrypt
import plotly.express as px
import pandas as pd
from datetime import datetime
import re
import io
from PyPDF2 import PdfReader

# Init DB & basic settings
init_db()
st.set_page_config(
    page_title="Placement Management System",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional UI with dark background
st.markdown("""
<style>
    /* Global Styles */
    * {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Main Background */
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: #ffffff;
    }

    /* Headers */
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        color: #00d4ff;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }

    .sidebar-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #ff6b6b;
        margin-bottom: 1.5rem;
        border-bottom: 2px solid #ff6b6b;
        padding-bottom: 0.5rem;
    }

    /* Message Styles */
    .success-msg {
        background: linear-gradient(135deg, #2d5016 0%, #4a7c59 100%);
        color: #c8e6c9;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 15px 0;
        border-left: 4px solid #4caf50;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    .error-msg {
        background: linear-gradient(135deg, #5d1a1a 0%, #8b2635 100%);
        color: #ffcdd2;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 15px 0;
        border-left: 4px solid #f44336;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    .info-msg {
        background: linear-gradient(135deg, #1a3d5c 0%, #2c5aa0 100%);
        color: #bbdefb;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 15px 0;
        border-left: 4px solid #2196f3;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    /* Button Styles */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.4);
    }

    /* Card Styles */
    .card {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
        margin: 15px 0;
        border: 1px solid #455a64;
        transition: transform 0.2s ease;
        color: #ecf0f1;
    }

    .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    }

    /* Form Styles */
    .stTextInput>div>div>input,
    .stTextArea>div>textarea,
    .stNumberInput>div>div>input {
        border-radius: 8px;
        border: 2px solid #546e7a;
        padding: 12px;
        font-size: 16px;
        transition: border-color 0.3s ease;
        background-color: #37474f;
        color: #ffffff;
    }

    .stTextInput>div>div>input:focus,
    .stTextArea>div>textarea:focus,
    .stNumberInput>div>div>input:focus {
        border-color: #00d4ff;
        box-shadow: 0 0 0 3px rgba(0,212,255,0.2);
        background-color: #455a64;
    }

    /* Table Styles */
    .stTable {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        background-color: #2c3e50;
    }

    .stTable th {
        background-color: #34495e;
        color: #00d4ff;
        font-weight: 600;
    }

    .stTable td {
        background-color: #2c3e50;
        color: #ecf0f1;
        border-bottom: 1px solid #455a64;
    }

    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4caf50 0%, #81c784 100%);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
        color: #ecf0f1;
    }

    /* Metric Cards */
    .css-1r6slb0 {
        background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        color: #ecf0f1;
    }

    /* File Uploader */
    .stFileUploader {
        border-radius: 8px;
        border: 2px dashed #00d4ff;
        padding: 20px;
        background-color: #37474f;
        color: #ecf0f1;
    }

    /* Radio Buttons */
    .stRadio > div {
        background-color: #37474f;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #546e7a;
        color: #ecf0f1;
    }

    /* Streamlit Default Overrides */
    .stMarkdown, .stText {
        color: #ecf0f1;
    }

    .stSelectbox > div > div {
        background-color: #37474f;
        color: #ecf0f1;
        border: 2px solid #546e7a;
    }

    .stSelectbox > div > div:focus {
        border-color: #00d4ff;
        box-shadow: 0 0 0 3px rgba(0,212,255,0.2);
    }
</style>
""", unsafe_allow_html=True)

# helpers - removed duplicate functions, using imports from utils.py

def login_flow():
    st.markdown('<h2 class="sidebar-header">🔐 Login</h2>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        email = st.text_input("📧 Email", key="login_email")
        password = st.text_input("🔒 Password", type="password", key="login_pw")
        if st.button("🚀 Login", use_container_width=True):
            print(f"DEBUG: Login attempt for email: {email}")  # Log login attempt
            try:
                user = find_user_by_email(email)
                print(f"DEBUG: find_user_by_email returned: {user is not None}")
                if not user:
                    print("DEBUG: User not found in database")  # Log user not found
                    st.markdown('<div class="error-msg">❌ Invalid credentials</div>', unsafe_allow_html=True)
                    return
            except Exception as e:
                print(f"DEBUG: Error finding user: {e}")
                st.markdown('<div class="error-msg">❌ Database error during login</div>', unsafe_allow_html=True)
                return
            stored = user[3]
            print(f"DEBUG: Retrieved stored hash: {stored[:20]}...")  # Log partial hash for debugging
            print(f"DEBUG: Password to check: {password[:5]}...")  # Log partial password
            print(f"DEBUG: User ID: {user[0]}, Name: {user[1]}")
            # stored is string (decoded)
            try:
                is_valid = bcrypt.checkpw(password.encode(), stored.encode())
                print(f"DEBUG: bcrypt.checkpw result: {is_valid}")  # Log check result
                if is_valid:
                    st.session_state["user_id"] = user[0]
                    st.session_state["user_name"] = user[1]
                    st.session_state["user_role"] = user[4]  # Store user role
                    print(f"DEBUG: Login successful for user {user[1]} (ID: {user[0]}, Role: {user[4]})")  # Log success
                    st.markdown('<div class="success-msg">✅ Successfully logged in!</div>', unsafe_allow_html=True)
                    st.rerun()
                else:
                    print("DEBUG: Password check failed")  # Log failed check
                    st.markdown('<div class="error-msg">❌ Invalid credentials</div>', unsafe_allow_html=True)
            except Exception as e:
                print(f"DEBUG: Exception during login: {e}")  # Log exception
                st.markdown('<div class="error-msg">❌ Login failed (hash check)</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def register_flow():
    st.markdown('<h2 class="sidebar-header">📝 Register</h2>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("👤 Full Name", key="reg_name")

        email = st.text_input("📧 Email", key="reg_email")

        password = st.text_input("🔒 Password", key="reg_pw", type="password")

        role = st.selectbox("👥 Role", ["student", "admin", "hr"], key="reg_role")

        if role == "admin":
            phone = st.text_input("📞 Phone Number", key="reg_phone")
        else:
            cgpa = st.number_input("🎓 CGPA (0.0 - 10.0)", min_value=0.0, max_value=10.0, value=7.0, step=0.01)

        if st.button("📋 Register", use_container_width=True):
            if not (name and email and password):
                st.markdown('<div class="error-msg">❌ Name, email, and password are required</div>', unsafe_allow_html=True)
                return
            if find_user_by_email(email):
                st.markdown('<div class="error-msg">❌ Email already registered</div>', unsafe_allow_html=True)
                return
            cgpa_val = cgpa if role == "student" else None
            phone_val = phone if role == "admin" else None
            uid = create_user(name, email, password, cgpa=cgpa_val, phone=phone_val, role=role)
            st.markdown('<div class="success-msg">✅ Successfully registered! Please login.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def logout():
    for k in ["user_id","user_name"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

# UI pages
menu = ["Home","Register","Login"]
if "user_id" in st.session_state:
    user_role = st.session_state.get("user_role")
    if user_role == "admin":
        # Admin menu - only dashboard and admin functions
        menu = ["Admin Dashboard", "Logout"]
    elif user_role == "hr":
        # HR menu - similar to admin but with HR-specific functions
        menu = ["HR Dashboard", "Logout"]
    else:
        # Student menu - full functionality
        menu = ["Dashboard","Profile","Aptitude Test","Download Papers","Logout"]

choice = st.sidebar.selectbox("Menu", menu)

if choice == "Home":
    st.markdown('<h1 class="main-header">🎓 Placement Management System</h1>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        <div class="card">
        <h3 style="color: #1f77b4; margin-bottom: 1rem;">🚀 Welcome to Your Career Journey!</h3>
        <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 1.5rem;">This comprehensive placement portal helps you prepare for your dream job with cutting-edge technology and personalized guidance.</p>
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 6px 12px rgba(0,0,0,0.3);">
            <h4 style="color: #ffffff; margin-bottom: 1.5rem; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">🎯 What You Can Do:</h4>
            <ul style="list-style: none; padding: 0;">
                <li style="margin-bottom: 1rem; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                    <span style="color: #00ff88; font-size: 1.2rem;">📝</span>
                    <strong style="color: #00ff88; margin-left: 10px;">Register & Profile Management:</strong>
                    <span style="color: #e0e0e0;">Create your professional profile with CGPA and skills</span>
                </li>
                <li style="margin-bottom: 1rem; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                    <span style="color: #00d4ff; font-size: 1.2rem;">📄</span>
                    <strong style="color: #00d4ff; margin-left: 10px;">Resume Analysis:</strong>
                    <span style="color: #e0e0e0;">Upload PDF resumes for automatic skill extraction</span>
                </li>
                <li style="margin-bottom: 1rem; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                    <span style="color: #ff6b6b; font-size: 1.2rem;">🤖</span>
                    <strong style="color: #ff6b6b; margin-left: 10px;">AI Skill Matching:</strong>
                    <span style="color: #e0e0e0;">Get matched with companies based on your skills and CGPA</span>
                </li>
                <li style="margin-bottom: 1rem; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                    <span style="color: #ffd93d; font-size: 1.2rem;">📊</span>
                    <strong style="color: #ffd93d; margin-left: 10px;">Aptitude Testing:</strong>
                    <span style="color: #e0e0e0;">Take comprehensive tests and track your performance</span>
                </li>
                <li style="margin-bottom: 1rem; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                    <span style="color: #a855f7; font-size: 1.2rem;">📥</span>
                    <strong style="color: #a855f7; margin-left: 10px;">Question Papers:</strong>
                    <span style="color: #e0e0e0;">Download company-specific practice papers</span>
                </li>
                <li style="margin-bottom: 1rem; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                    <span style="color: #06d6a0; font-size: 1.2rem;">📅</span>
                    <strong style="color: #06d6a0; margin-left: 10px;">Slot Scheduling:</strong>
                    <span style="color: #e0e0e0;">Book placement interview slots</span>
                </li>
            </ul>
        </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <img src="https://img.icons8.com/fluency/240/000000/resume.png" style="width: 200px; height: 200px; border-radius: 50%; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <h4 style="color: #1f77b4; text-align: center; margin-bottom: 1.5rem;">📈 Quick Stats</h4>
        """, unsafe_allow_html=True)

        companies = get_all_companies()
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("🏢 Companies", len(companies), help="Available companies for placement")
        with col_b:
            st.metric("📄 Test Papers", "3", help="Practice question papers available")

        st.markdown("""
        <div style="text-align: center; margin-top: 1rem; padding: 10px; background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; border-radius: 8px;">
            <strong>Ready to Start Your Journey? Register Now!</strong>
        </div>
        </div>
        """, unsafe_allow_html=True)
elif choice == "Register":
    register_flow()
elif choice == "Login":
    login_flow()
elif choice == "Logout":
    logout()
elif choice == "Profile":
    uid = st.session_state["user_id"]
    user = get_user_by_id(uid)
    st.markdown('<h1 class="main-header">👤 Profile Management</h1>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <img src="https://img.icons8.com/fluency/120/000000/user-male-circle.png" style="width: 120px; height: 120px; border-radius: 50%; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 3px solid #007bff;">
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: #1f77b4; text-align: center; margin-bottom: 1.5rem;">👤 Profile Information</h4>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 1rem;">
            <strong style="color: #495057;">👤 Full Name:</strong><br>
            <span style="font-size: 1.1rem; color: #212529;">{user[1]}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 1rem;">
            <strong style="color: #495057;">📧 Email Address:</strong><br>
            <span style="font-size: 1.1rem; color: #212529;">{user[2]}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 1rem;">
            <strong style="color: #495057;">🎓 CGPA:</strong><br>
            <span style="font-size: 1.1rem; color: #212529; font-weight: bold;">{user[7]}/10</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">🛠 Skills Management</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color: #6c757d; margin-bottom: 1rem;">Update your skills manually or let AI extract them from your resume</p>', unsafe_allow_html=True)

        skills = st.text_area(
            "💡 Skills (comma separated)",
            value=user[5] or "",
            height=100,
            placeholder="e.g., python, java, sql, communication, problem solving",
            help="Enter your technical and soft skills separated by commas"
        )

        if st.button("💾 Save Skills", use_container_width=True):
            update_user_skills(uid, skills_text=skills)
            st.markdown('<div class="success-msg">✅ Skills saved successfully!</div>', unsafe_allow_html=True)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">📄 Resume Upload & AI Analysis</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color: #6c757d; margin-bottom: 1rem;">Upload your PDF resume for automatic skill extraction using advanced AI</p>', unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "📎 Upload PDF resume",
            type=["pdf"],
            help="Supported formats: PDF. Maximum size: 10MB"
        )

        if uploaded:
            with st.spinner("🔍 Analyzing your resume..."):
                b = uploaded.read()
                text = extract_text_from_pdf(b)

            if text.strip():
                # Extract skills from the resume text
                extracted_skills = extract_skills_from_text(text)
                # extract_skills_from_text returns a list, so we can join it directly
                skills_str = ", ".join(extracted_skills) if extracted_skills else "No skills detected"

                st.markdown(f"""
                <div class="success-msg">
                ✅ <strong>Resume Analysis Complete!</strong><br>
                <strong>Extracted Skills:</strong> {skills_str}<br>
                <em>Your skills have been automatically added to your profile.</em>
                </div>
                """, unsafe_allow_html=True)

                # Update both resume text and skills
                update_user_skills(uid, resume_text=text, skills_text=skills_str)
                st.rerun()
            else:
                st.markdown("""
                <div class="error-msg">
                ❌ <strong>Analysis Failed</strong><br>
                Could not extract text from the PDF. Please ensure the file is not password-protected and contains readable text.
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">📅 Interview Slot Scheduling</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color: #6c757d; margin-bottom: 1rem;">Book your placement interview slots</p>', unsafe_allow_html=True)

        if st.button("📋 Book Interview Slot", use_container_width=True):
            schedule_slot(uid, datetime.now().isoformat(), notes="Booked via profile")
            st.markdown('<div class="success-msg">✅ Interview slot booked successfully! Check your dashboard for details.</div>', unsafe_allow_html=True)

        slots = get_slots(uid)
        if slots:
            st.markdown('<h5 style="color: #495057;">📅 Your Booked Slots:</h5>', unsafe_allow_html=True)
            for s in slots:
                st.markdown(f"""
                <div style="background: #e9ecef; padding: 10px; border-radius: 6px; margin-bottom: 0.5rem;">
                🕒 <strong>{s[0]}</strong>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; color: #6c757d; font-style: italic;">
            No interview slots booked yet<br>
            <small>Book a slot to schedule your placement interviews</small>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif choice == "HR Dashboard":
    uid = st.session_state["user_id"]
    st.markdown('<h1 class="main-header">👥 HR Dashboard</h1>', unsafe_allow_html=True)

    # HR-specific functionality can be added here
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">👥 HR Functions</h4>', unsafe_allow_html=True)
    st.markdown('<p style="color: #6c757d; margin-bottom: 1.5rem;">Welcome to the HR Dashboard. Additional HR functions can be implemented here.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif choice == "Admin Dashboard":
    uid = st.session_state["user_id"]
    st.markdown('<h1 class="main-header">🏛 Admin Dashboard</h1>', unsafe_allow_html=True)

    # Student approval section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">👥 Student Registrations</h4>', unsafe_allow_html=True)
    st.markdown('<p style="color: #6c757d; margin-bottom: 1.5rem;">Review and approve student applications</p>', unsafe_allow_html=True)

    # Get unapproved students
    unapproved_students = get_unapproved_students()

    if unapproved_students:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); color: #856404; padding: 15px; border-radius: 8px; margin-bottom: 1rem;">
            ⚠️ <strong>{len(unapproved_students)}</strong> student(s) pending approval
        </div>
        """, unsafe_allow_html=True)

        for student in unapproved_students:
            with st.expander(f"📋 {student[1]} - {student[2]}", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                    **👤 Name:** {student[1]}
                    **📧 Email:** {student[2]}
                    **🎓 CGPA:** {student[3] or 'Not provided'}
                    **💡 Skills:** {student[4] or 'Not provided'}
                    **📄 Resume:** {len(student[5] or '')} characters
                    **📅 Applied:** {student[6]}
                    """)

                with col2:
                    if st.button(f"✅ Approve {student[0]}", key=f"approve_{student[0]}"):
                        approve_student(student[0])
                        st.success(f"✅ {student[1]} has been approved!")
                        st.rerun()

                    if st.button(f"❌ Reject {student[0]}", key=f"reject_{student[0]}"):
                        reject_student(student[0])
                        st.error(f"❌ {student[1]}'s application has been rejected.")
                        st.rerun()
    else:
        st.markdown("""
        <div style="text-align: center; color: #6c757d; padding: 2rem;">
        ✅ No pending student registrations
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # All registered students section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">📋 All Registered Students</h4>', unsafe_allow_html=True)
    st.markdown('<p style="color: #6c757d; margin-bottom: 1.5rem;">View and manage all student profiles</p>', unsafe_allow_html=True)

    all_students = get_all_students()
    if all_students:
        # Add search/filter functionality
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("🔍 Search by name or email", key="search_students")
        with col2:
            filter_status = st.selectbox("Filter by status", ["All", "Approved", "Pending"], key="filter_status")

        # Filter students
        filtered_students = []
        for student in all_students:
            status = "Approved" if student[6] == 1 else "Pending"
            if filter_status != "All" and status != filter_status:
                continue
            if search_term and search_term.lower() not in (student[1] + student[2]).lower():
                continue
            filtered_students.append(student)

        if filtered_students:
            st.markdown(f"**Showing {len(filtered_students)} student(s)**")

            for student in filtered_students:
                status = "✅ Approved" if student[6] == 1 else "⏳ Pending"
                status_color = "#28a745" if student[6] == 1 else "#ffc107"

                with st.expander(f"👤 {student[1]} - {student[2]} ({status})", expanded=False):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown("### 📊 Student Profile")
                        st.markdown(f"""
                        **👤 Full Name:** {student[1]}
                        **📧 Email:** {student[2]}
                        **🎓 CGPA:** {student[3] or 'Not provided'}/10
                        **💡 Skills:** {student[4] or 'Not provided'}
                        **📄 Resume Text:** {len(student[5] or '')} characters
                        **📅 Registered:** {student[7]}
                        **Status:** <span style="color: {status_color}; font-weight: bold;">{status}</span>
                        """, unsafe_allow_html=True)

                        # Show AI matching results for this student
                        candidate_text = student[5] or student[4] or ""
                        if candidate_text.strip():
                            companies = get_all_companies()
                            matches = compute_matches(candidate_text, companies, top_k=5)
                            if matches:
                                st.markdown("### 🤖 AI Company Matches")
                                match_rows = []
                                for m in matches:
                                    eligible = is_eligible(student[3], m["min_cgpa"]) if student[3] else False
                                    match_rows.append({
                                        "🏢 Company": m["name"],
                                        "📊 Match %": f"{round(m['score']*100,1)}%",
                                        "🎓 Min CGPA": f"{m['min_cgpa']}",
                                        "✅ Eligible": "✅ Yes" if eligible else "❌ No"
                                    })
                                st.table(match_rows)

                    with col2:
                        st.markdown("### ⚙️ Actions")
                        if student[6] == 0:  # If pending
                            if st.button(f"✅ Approve Student", key=f"admin_approve_{student[0]}"):
                                approve_student(student[0])
                                st.success(f"✅ {student[1]} has been approved!")
                                st.rerun()
                        else:  # If approved
                            st.markdown("**Status:** Approved ✅")

                        if st.button(f"❌ Remove Student", key=f"admin_remove_{student[0]}"):
                            reject_student(student[0])
                            st.error(f"❌ {student[1]} has been removed from the system.")
                            st.rerun()
        else:
            st.markdown("No students match the current search/filter criteria.")
    else:
        st.markdown("No students registered yet.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Statistics section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">📊 System Statistics</h4>', unsafe_allow_html=True)

    all_users = get_all_users()
    total_students = len([u for u in all_users if u[2] == 'student'])
    approved_students = len([u for u in all_users if u[2] == 'student' and u[3] == 1])
    total_admins = len([u for u in all_users if u[2] == 'admin'])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👨‍🎓 Total Students", total_students)
    with col2:
        st.metric("✅ Approved Students", approved_students)
    with col3:
        st.metric("⏳ Pending Approval", total_students - approved_students)
    with col4:
        st.metric("👑 Admins", total_admins)
    st.markdown('</div>', unsafe_allow_html=True)

elif choice == "Dashboard":
    uid = st.session_state["user_id"]
    st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)
    user = get_user_by_id(uid)

    # Quick profile card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: #1f77b4; text-align: center; margin-bottom: 1.5rem;">👤 Profile Overview</h4>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👤 Full Name", user[1])
    with col2:
        st.metric("📧 Email", user[2])
    with col3:
        st.metric("🎓 CGPA", f"{user[7]}/10")

    # Skills display
    current_skills = user[5] or "No skills added yet"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 15px; border-radius: 8px; margin-top: 1rem;">
        <strong style="color: #495057;">💡 Current Skills:</strong><br>
        <span style="color: #007bff; font-weight: 500;">{current_skills}</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # AI matching only for students
    if st.session_state.get("user_role") == "student":
        candidate_text = user[6] or (user[5] or "")
        if not candidate_text.strip():
            st.markdown('<div class="info-msg">💡 Add skills in Profile or upload resume to enable AI matching.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<h4 style="color: #1f77b4; margin-bottom: 1rem;">🤖 AI Skill Matching Results</h4>', unsafe_allow_html=True)
            st.markdown('<p style="color: #6c757d; margin-bottom: 1.5rem;">Companies matched based on your skills and CGPA using advanced TF-IDF algorithm</p>', unsafe_allow_html=True)

            companies = get_all_companies()
            matches = compute_matches(candidate_text, companies, top_k=10)
            rows = []
            for m in matches:
                eligible = is_eligible(user[7], m["min_cgpa"])
                rows.append({
                    "🏢 Company": m["name"],
                    "📊 Match %": f"{round(m['score']*100,1)}%",
                    "🎓 Min CGPA": f"{m['min_cgpa']}",
                    "✅ Eligible": "✅ Yes" if eligible else "❌ No"
                })

            if rows:
                st.markdown('<div style="overflow-x: auto;">', unsafe_allow_html=True)
                st.table(rows[:10])
                st.markdown('</div>', unsafe_allow_html=True)

                # Enhanced bar chart
                df = pd.DataFrame(rows)
                df["📊 Match %"] = df["📊 Match %"].str.rstrip('%').astype(float)
                fig = px.bar(df, x="🏢 Company", y="📊 Match %", color="✅ Eligible",
                            title="🎯 Top Company Matches by Skill Compatibility",
                            color_discrete_map={"✅ Yes": "#28a745", "❌ No": "#dc3545"},
                            labels={"📊 Match %": "Skill Match Percentage"})
                fig.update_layout(
                    plot_bgcolor='rgba(44,62,80,1)',
                    paper_bgcolor='rgba(44,62,80,1)',
                    font=dict(color='#ecf0f1', size=12),
                    title_font=dict(color='#00d4ff')
                )
                fig.update_xaxes(gridcolor='#455a64', color='#ecf0f1')
                fig.update_yaxes(gridcolor='#455a64', color='#ecf0f1')
                st.plotly_chart(fig, width='stretch')

                # Summary stats
                eligible_count = sum(1 for row in rows if "✅ Yes" in row["✅ Eligible"])
                avg_match = sum(float(row["📊 Match %"].rstrip('%')) for row in rows) / len(rows)

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%); padding: 20px; border-radius: 8px; margin-top: 1rem;">
                    <h5 style="color: #1f77b4; margin-bottom: 1rem;">📈 Matching Summary</h5>
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div>
                            <div style="font-size: 2rem; font-weight: bold; color: #28a745;">{eligible_count}</div>
                            <div style="color: #6c757d;">Eligible Companies</div>
                        </div>
                        <div>
                            <div style="font-size: 2rem; font-weight: bold; color: #007bff;">{avg_match:.1f}%</div>
                            <div style="color: #6c757d;">Average Match</div>
                        </div>
                        <div>
                            <div style="font-size: 2rem; font-weight: bold; color: #17a2b8;">{len(rows)}</div>
                            <div style="color: #6c757d;">Total Matches</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="text-align: center; color: #6c757d; padding: 2rem;">
                <h5>No company data available</h5>
                <p>Please run <code>python init_data.py</code> to load company information.</p>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: #00d4ff; margin-bottom: 1rem;">📈 Test Performance Analytics</h4>', unsafe_allow_html=True)

    results = get_user_results(uid)
    if results:
        st.markdown('<p style="color: #b0b0b0; margin-bottom: 1.5rem;">Your aptitude test results and performance tracking</p>', unsafe_allow_html=True)

        # Create data for visualization
        test_names = []
        scores = []
        percentages = []
        dates = []

        for r in results:
            percentage = round((r[1]/r[2])*100, 1) if r[2] > 0 else 0
            test_names.append(r[0])
            scores.append(f"{r[1]}/{r[2]}")
            percentages.append(percentage)
            dates.append(r[4])  # Fixed: r[4] is timestamp, not r[3] which is answers

        # Performance Graph
        df = pd.DataFrame({
            'Test': test_names,
            'Score (%)': percentages,
            'Date': dates
        })

        st.markdown('<h5 style="color: #00d4ff; margin-bottom: 1rem;">📊 Performance Trends</h5>', unsafe_allow_html=True)

        # Line chart for performance over time
        fig_line = px.line(df, x='Date', y='Score (%)', markers=True,
                          title='Test Performance Over Time',
                          color_discrete_sequence=['#00d4ff'])
        fig_line.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ecf0f1'),
            title_font=dict(color='#00d4ff')
        )
        fig_line.update_xaxes(gridcolor='#455a64', color='#ecf0f1')
        fig_line.update_yaxes(gridcolor='#455a64', color='#ecf0f1')
        st.plotly_chart(fig_line, width='stretch')

        # Bar chart for individual test scores
        fig_bar = px.bar(df, x='Test', y='Score (%)',
                        title='Individual Test Scores',
                        color='Score (%)',
                        color_continuous_scale=['#ff6b6b', '#ffd93d', '#00ff88'])
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ecf0f1'),
            title_font=dict(color='#00d4ff')
        )
        fig_bar.update_xaxes(gridcolor='#455a64', color='#ecf0f1')
        fig_bar.update_yaxes(gridcolor='#455a64', color='#ecf0f1')
        st.plotly_chart(fig_bar, use_container_width=True)

        # Detailed results table
        st.markdown('<h5 style="color: #00d4ff; margin-bottom: 1rem;">📋 Detailed Results</h5>', unsafe_allow_html=True)

        for i, (name, score, percentage, date) in enumerate(zip(test_names, scores, percentages, dates)):
            # Color coding based on performance
            if percentage >= 80:
                color = "#00ff88"  # Green
                status = "🏆 Excellent"
                bg_color = "rgba(0,255,136,0.1)"
            elif percentage >= 60:
                color = "#ffd93d"  # Yellow
                status = "👍 Good"
                bg_color = "rgba(255,217,61,0.1)"
            else:
                color = "#ff6b6b"  # Red
                status = "📚 Needs Improvement"
                bg_color = "rgba(255,107,107,0.1)"

            st.markdown(f"""
            <div style="background: {bg_color}; padding: 15px; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid {color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <strong style="color: #ecf0f1; font-size: 1.1rem;">{name}</strong>
                    <span style="color: {color}; font-weight: bold;">{status}</span>
                </div>
                <div style="margin-bottom: 0.5rem;">
                    <strong style="color: #b0b0b0;">Score:</strong> <span style="color: #00d4ff; font-weight: bold;">{score} ({percentage}%)</span>
                </div>
                <div style="color: #b0b0b0; font-size: 0.9rem;">
                    📅 Completed on {date}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Overall statistics with pie chart
        total_tests = len(results)
        avg_score = sum(percentages) / total_tests if total_tests > 0 else 0
        best_score = max(percentages) if total_tests > 0 else 0

        # Performance distribution for pie chart
        excellent = sum(1 for p in percentages if p >= 80)
        good = sum(1 for p in percentages if 60 <= p < 80)
        needs_improvement = sum(1 for p in percentages if p < 60)

        if total_tests > 0:
            st.markdown('<h5 style="color: #00d4ff; margin-bottom: 1rem;">📊 Performance Distribution</h5>', unsafe_allow_html=True)

            # Pie chart
            pie_data = pd.DataFrame({
                'Category': ['Excellent (80%+)', 'Good (60-79%)', 'Needs Improvement (<60%)'],
                'Count': [excellent, good, needs_improvement],
                'Color': ['#00ff88', '#ffd93d', '#ff6b6b']
            })

            fig_pie = px.pie(pie_data, values='Count', names='Category',
                           title='Test Performance Distribution',
                           color='Category',
                           color_discrete_map={'Excellent (80%+)': '#00ff88',
                                             'Good (60-79%)': '#ffd93d',
                                             'Needs Improvement (<60%)': '#ff6b6b'})
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ecf0f1'),
                title_font=dict(color='#00d4ff')
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-top: 1.5rem;">
            <h5 style="margin-bottom: 1rem; color: white;">📊 Performance Summary</h5>
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold;">{total_tests}</div>
                    <div style="font-size: 0.9rem;">Total Tests</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold;">{avg_score:.1f}%</div>
                    <div style="font-size: 0.9rem;">Average Score</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold;">{best_score:.1f}%</div>
                    <div style="font-size: 0.9rem;">Best Score</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="text-align: center; color: #b0b0b0; padding: 2rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">📝</div>
        <h5 style="color: #ecf0f1;">No test results yet</h5>
        <p>Take an aptitude test to see your performance analytics and track your progress!</p>
        <div style="margin-top: 1rem;">
            <em style="color: #00d4ff;">Navigate to "Aptitude Test" in the sidebar to get started</em>
        </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif choice == "Aptitude Test":
    uid = st.session_state["user_id"]
    # Only allow students to take aptitude tests
    if st.session_state.get("user_role") == "student":
        st.markdown('<h1 class="main-header">🧠 Aptitude Test</h1>', unsafe_allow_html=True)

        path = Path("tests/aptitude.json")
        if not path.exists():
            st.markdown('<div class="error-msg">❌ No aptitude test found. Run <code>python init_data.py</code> to create sample test.</div>', unsafe_allow_html=True)
        else:
            test = json.loads(path.read_text())
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"### 📝 {test.get('title','Aptitude Test')}")
            st.markdown("*Answer all questions and submit to see your score!*")

            with st.form("apt_form"):
                answers = {}
                for i, q in enumerate(test["questions"]):
                    st.markdown(f"*Question {i+1}:* {q['q']}")
                    ans = st.radio("Select your answer:", q["options"], key=f"q{i}", label_visibility="collapsed")
                    answers[f"q{i}"] = ans
                    st.markdown("---")

                submitted = st.form_submit_button("🚀 Submit Test", use_container_width=True)
                if submitted:
                    score = 0
                    for i, q in enumerate(test["questions"]):
                        if answers.get(f"q{i}", "").strip().lower() == q["answer"].strip().lower():
                            score += 1
                    save_result(uid, "aptitude", score, len(test["questions"]), answers)
                    percentage = round((score / len(test["questions"])) * 100, 1)
                    st.markdown(f'<div class="success-msg">✅ Test submitted! Score: <strong>{score}/{len(test["questions"])} ({percentage}%)</strong></div>', unsafe_allow_html=True)
                    st.progress(percentage/100)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<h1 class="main-header">👑 Admin Access</h1>', unsafe_allow_html=True)
        st.markdown('<div class="info-msg">🛡️ Aptitude tests are only available for students. Admins can manage student results through the Admin Dashboard.</div>', unsafe_allow_html=True)

elif choice == "Download Papers":
    st.markdown('<h1 class="main-header">📥 Download Question Papers</h1>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📚 Company-Specific Question Papers")
    st.markdown("Download sample question papers from top companies to prepare for placements:")

    papers_dir = Path("papers")
    papers_dir.mkdir(exist_ok=True)

    expected = [
        ("🏢 TCS", "paper1_tcs.pdf", "Tata Consultancy Services"),
        ("🏢 Wipro", "paper2_wipro.pdf", "Wipro Technologies"),
        ("🏢 Infosys", "paper3_infosys.pdf", "Infosys Limited")
    ]

    cols = st.columns(3)
    for i, (icon_name, filename, company) in enumerate(expected):
        with cols[i]:
            fp = papers_dir / filename
            if fp.exists():
                st.markdown(f"{icon_name} {company}")
                st.download_button(
                    f"📥 Download {company} Paper",
                    fp.read_bytes(),
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.markdown(f"{icon_name} {company}")
                st.markdown('<div class="error-msg">❌ Paper not available</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)