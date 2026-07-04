import sqlite3
import json
import random
from datetime import datetime

def get_db():
    return sqlite3.connect('placement.db')

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Create students table
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        college_id TEXT NOT NULL,
        branch TEXT NOT NULL,
        cgpa REAL,
        skills_text TEXT,
        aptitude_score INTEGER DEFAULT 0,
        ai_match REAL DEFAULT 0.0,
        is_verified INTEGER DEFAULT 0,
        resume_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Create admins table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Create aptitude_questions table
    c.execute('''CREATE TABLE IF NOT EXISTS aptitude_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        options TEXT NOT NULL,  -- JSON string of list
        answer TEXT NOT NULL
    )''')

    # Create aptitude_results table
    c.execute('''CREATE TABLE IF NOT EXISTS aptitude_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        test_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        answers TEXT NOT NULL,  -- JSON string
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )''')

    # Create ai_matches table
    c.execute('''CREATE TABLE IF NOT EXISTS ai_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        role_title TEXT NOT NULL,
        company_name TEXT NOT NULL,
        match_score REAL NOT NULL,
        match_reason TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )''')

    conn.commit()
    conn.close()

def get_random_questions(count=20):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, question, options, answer FROM aptitude_questions ORDER BY RANDOM() LIMIT ?", (count,))
    rows = c.fetchall()
    conn.close()
    # options is JSON string, parse to list
    questions = [(row[0], row[1], json.loads(row[2]), row[3]) for row in rows]
    return questions

def save_aptitude_result(student_id, test_id, score, total, answers):
    conn = get_db()
    c = conn.cursor()
    answers_json = json.dumps(answers)
    c.execute("INSERT INTO aptitude_results (student_id, test_id, score, total, answers) VALUES (?, ?, ?, ?, ?)",
              (student_id, test_id, score, total, answers_json))
    conn.commit()
    conn.close()

def get_aptitude_results(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT score, total FROM aptitude_results WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_ai_matches(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT match_score, match_reason, role_title, company_name FROM ai_matches WHERE student_id = ? ORDER BY match_score DESC", (student_id,))
    rows = c.fetchall()
    conn.close()
    return rows