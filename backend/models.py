from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

# Student Models
class StudentBase(BaseModel):
    name: str
    email: EmailStr
    college_id: str
    branch: str
    cgpa: float
    skills: str

class StudentCreate(StudentBase):
    password: str

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    cgpa: Optional[float] = None
    skills: Optional[str] = None

class StudentResponse(StudentBase):
    id: int
    aptitude_score: int
    ai_match: float
    is_verified: bool
    resume_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Admin Models
class AdminBase(BaseModel):
    name: str
    phone: str
    email: EmailStr

class AdminCreate(AdminBase):
    password: str

class AdminResponse(AdminBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Authentication Models
class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    user_type: Optional[str] = None

# Aptitude Test Models
class QuestionResponse(BaseModel):
    id: int
    question: str
    options: List[str]

class TestStartResponse(BaseModel):
    test_id: int
    questions: List[QuestionResponse]
    time_limit: int  # seconds

class TestSubmission(BaseModel):
    answers: Dict[str, str]  # question_id -> selected_option

class TestResult(BaseModel):
    score: int
    total: int
    percentage: float
    answers: Dict[str, str]

# AI Matching Models
class MatchResponse(BaseModel):
    role_title: str
    company_name: str
    match_score: float
    match_reason: str

# Dashboard Models
class StudentDashboard(BaseModel):
    profile: StudentResponse
    aptitude_results: List[TestResult]
    ai_matches: List[MatchResponse]

class AdminStats(BaseModel):
    total_students: int
    verified_students: int
    pending_approvals: int
    avg_cgpa: float
    avg_aptitude_score: float
    avg_ai_match: float

class AdminDashboard(BaseModel):
    stats: AdminStats
    recent_students: List[StudentResponse]

# Generic Response Models
class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    students: List[StudentResponse]
    pagination: Dict[str, int]