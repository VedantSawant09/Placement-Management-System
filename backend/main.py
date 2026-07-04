from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import os
import sys
from pathlib import Path
import shutil
import bcrypt
import jwt
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import *
from database import *
from ..auth import *
from ai_match import get_student_matches

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Placement Management System API",
    description="Backend API for student placement management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(data: dict):
    payload = {
        'user_id': data['sub'],
        'user_type': data['user_type'],
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.now()
    }
    token = jwt.encode(payload, os.getenv('JWT_SECRET', 'your_jwt_secret_key'), algorithm='HS256')
    return token

def verify_token(token):
    try:
        payload = jwt.decode(token, os.getenv('JWT_SECRET', 'your_jwt_secret_key'), algorithms=['HS256'])
        return payload
    except:
        return None

# Upload folder setup
UPLOAD_DIR = Path("uploads/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user"""
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data

# Student Routes
@app.post("/students/register", response_model=MessageResponse)
async def register_student(student: StudentCreate):
    """Register a new student"""
    # Check if email or college_id already exists
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM students WHERE email = ? OR college_id = ?",
              (student.email, student.college_id))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email or College ID already registered")

    # Hash password
    hashed_password = hash_password(student.password)

    # Insert student
    c.execute("""INSERT INTO students (name, email, password_hash, college_id, branch, cgpa, skills_text)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (student.name, student.email, hashed_password, student.college_id,
               student.branch, student.cgpa, student.skills))

    student_id = c.lastrowid
    conn.commit()
    conn.close()

    return {"message": "Student registered successfully. Please wait for admin approval."}

@app.post("/students/login", response_model=Token)
async def login_student(login_data: LoginRequest):
    """Student login"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, password_hash, is_verified FROM students WHERE email = ?",
              (login_data.email,))
    student = c.fetchone()
    conn.close()

    if not student or not verify_password(login_data.password, student[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not student[2]:  # Not verified
        raise HTTPException(status_code=403, detail="Account pending admin approval")

    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(student[0]), "user_type": "student"}
    )

    return {"access_token": access_token, "token_type": "bearer", "user_type": "student"}

@app.get("/students/me", response_model=StudentResponse)
async def get_student_profile(current_user: dict = Depends(get_current_user)):
    """Get current student profile"""
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id = ?", (int(current_user["user_id"]),))
    student = c.fetchone()
    conn.close()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return StudentResponse(
        id=student[0],
        name=student[1],
        email=student[2],
        college_id=student[4],
        branch=student[5],
        cgpa=student[6],
        skills=student[7],
        aptitude_score=student[8],
        ai_match=student[9],
        is_verified=student[10],
        resume_path=student[11],
        created_at=datetime.fromisoformat(student[12])
    )

@app.put("/students/me", response_model=MessageResponse)
async def update_student_profile(
    name: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    cgpa: Optional[float] = Form(None),
    skills: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Update student profile"""
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    student_id = int(current_user["user_id"])
    updates = {}
    values = []

    if name:
        updates["name"] = "?"
        values.append(name)
    if branch:
        updates["branch"] = "?"
        values.append(branch)
    if cgpa:
        updates["cgpa"] = "?"
        values.append(cgpa)
    if skills:
        updates["skills_text"] = "?"
        values.append(skills)

    # Handle resume upload
    if resume:
        # Save file
        file_path = UPLOAD_DIR / f"student_{student_id}_{resume.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(resume.file, buffer)

        updates["resume_path"] = "?"
        values.append(str(file_path))

    if updates:
        query = f"UPDATE students SET {', '.join([f'{k} = {v}' for k, v in updates.items()])} WHERE id = ?"
        values.append(student_id)

        conn = get_db()
        c = conn.cursor()
        c.execute(query, values)
        conn.commit()
        conn.close()

    return {"message": "Profile updated successfully"}

@app.post("/students/test/start", response_model=TestStartResponse)
async def start_aptitude_test(current_user: dict = Depends(get_current_user)):
    """Start aptitude test"""
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get random questions
    questions = get_random_questions(20)

    # For now, create a simple test session
    test_id = 1  # In a real app, you'd track test sessions

    return TestStartResponse(
        test_id=test_id,
        questions=[QuestionResponse(id=q[0], question=q[1], options=q[2]) for q in questions],
        time_limit=1200  # 20 minutes
    )

@app.post("/students/test/submit", response_model=TestResult)
async def submit_aptitude_test(
    test_id: int,
    answers: TestSubmission,
    current_user: dict = Depends(get_current_user)
):
    """Submit aptitude test answers"""
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    student_id = int(current_user["user_id"])

    # Get questions and correct answers
    conn = get_db()
    c = conn.cursor()
    question_ids = list(answers.answers.keys())
    placeholders = ','.join('?' * len(question_ids))
    c.execute(f"SELECT id, answer FROM aptitude_questions WHERE id IN ({placeholders})",
              question_ids)
    correct_answers = {str(row[0]): row[1] for row in c.fetchall()}
    conn.close()

    # Calculate score
    score = 0
    for q_id, answer in answers.answers.items():
        if answer == correct_answers.get(q_id):
            score += 1

    total = len(answers.answers)
    percentage = (score / total) * 100

    # Save result
    save_aptitude_result(student_id, test_id, score, total, answers.answers.dict())

    return TestResult(
        score=score,
        total=total,
        percentage=round(percentage, 2),
        answers=answers.answers
    )

@app.get("/students/dashboard", response_model=StudentDashboard)
async def get_student_dashboard(current_user: dict = Depends(get_current_user)):
    """Get student dashboard data"""
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    student_id = int(current_user["user_id"])

    # Get profile
    profile = await get_student_profile(current_user)

    # Get aptitude results
    aptitude_results = get_aptitude_results(student_id)
    results_data = [TestResult(score=r[0], total=r[1], percentage=(r[0]/r[1])*100 if r[1] > 0 else 0, answers={})
                   for r in aptitude_results]

    # Get AI matches
    matches = get_ai_matches(student_id)
    ai_matches = [MatchResponse(role_title=m[2], company_name=m[3],
                               match_score=m[0], match_reason=m[1]) for m in matches]

    return StudentDashboard(
        profile=profile,
        aptitude_results=results_data,
        ai_matches=ai_matches
    )

# Admin Routes
@app.post("/admins/register", response_model=MessageResponse)
async def register_admin(admin: AdminCreate):
    """Register a new admin"""
    # Check if email already exists
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM admins WHERE email = ?", (admin.email,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = hash_password(admin.password)

    # Insert admin
    c.execute("""INSERT INTO admins (name, phone, email, password_hash)
               VALUES (?, ?, ?, ?)""",
              (admin.name, admin.phone, admin.email, hashed_password))

    conn.commit()
    conn.close()

    return {"message": "Admin registered successfully"}

@app.post("/admins/login", response_model=Token)
async def login_admin(login_data: LoginRequest):
    """Admin login"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM admins WHERE email = ?", (login_data.email,))
    admin = c.fetchone()
    conn.close()

    if not admin or not verify_password(login_data.password, admin[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(admin[0]), "user_type": "admin"}
    )

    return {"access_token": access_token, "token_type": "bearer", "user_type": "admin"}

@app.get("/admins/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(current_user: dict = Depends(get_current_user)):
    """Get admin dashboard"""
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    conn = get_db()
    c = conn.cursor()

    # Get stats
    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM students WHERE is_verified = 1")
    verified_students = c.fetchone()[0]

    c.execute("SELECT AVG(cgpa) FROM students WHERE cgpa IS NOT NULL")
    avg_cgpa = c.fetchone()[0] or 0

    c.execute("SELECT AVG(aptitude_score) FROM students")
    avg_aptitude = c.fetchone()[0] or 0

    c.execute("SELECT AVG(ai_match) FROM students")
    avg_ai_match = c.fetchone()[0] or 0

    # Get recent students
    c.execute("SELECT * FROM students ORDER BY created_at DESC LIMIT 10")
    recent_students_data = c.fetchall()
    conn.close()

    recent_students = []
    for s in recent_students_data:
        recent_students.append(StudentResponse(
            id=s[0], name=s[1], email=s[2], college_id=s[4], branch=s[5],
            cgpa=s[6], skills=s[7], aptitude_score=s[8], ai_match=s[9],
            is_verified=s[10], resume_path=s[11], created_at=datetime.fromisoformat(s[12])
        ))

    stats = AdminStats(
        total_students=total_students,
        verified_students=verified_students,
        pending_approvals=total_students - verified_students,
        avg_cgpa=round(avg_cgpa, 2),
        avg_aptitude_score=round(avg_aptitude, 2),
        avg_ai_match=round(avg_ai_match, 2)
    )

    return AdminDashboard(stats=stats, recent_students=recent_students)

@app.post("/admins/students/{student_id}/approve", response_model=MessageResponse)
async def approve_student(student_id: int, current_user: dict = Depends(get_current_user)):
    """Approve student registration"""
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE students SET is_verified = 1 WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

    return {"message": "Student approved successfully"}

@app.delete("/admins/students/{student_id}", response_model=MessageResponse)
async def reject_student(student_id: int, current_user: dict = Depends(get_current_user)):
    """Reject student registration"""
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

    return {"message": "Student rejected and removed"}

@app.get("/admins/students", response_model=PaginatedResponse)
async def get_students_list(
    page: int = 1,
    per_page: int = 25,
    search: str = "",
    status: str = "all",
    current_user: dict = Depends(get_current_user)
):
    """Get paginated list of students"""
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    conn = get_db()
    c = conn.cursor()

    # Build query
    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR skills_text LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])

    if status == "approved":
        query += " AND is_verified = 1"
    elif status == "pending":
        query += " AND is_verified = 0"

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    c.execute(query, params)
    students_data = c.fetchall()

    # Get total count
    count_query = "SELECT COUNT(*) FROM students WHERE 1=1"
    count_params = params[:-2]  # Remove LIMIT and OFFSET
    c.execute(count_query, count_params)
    total = c.fetchone()[0]

    conn.close()

    students = []
    for s in students_data:
        students.append(StudentResponse(
            id=s[0], name=s[1], email=s[2], college_id=s[4], branch=s[5],
            cgpa=s[6], skills=s[7], aptitude_score=s[8], ai_match=s[9],
            is_verified=s[10], resume_path=s[11], created_at=datetime.fromisoformat(s[12])
        ))

    return PaginatedResponse(
        students=students,
        pagination={
            "page": page,
            "per_page": per_page,
            "total_students": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)