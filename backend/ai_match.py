from sentence_transformers import SentenceTransformer, util
import numpy as np
from typing import List, Tuple, Dict
from database import get_db, get_roles, save_ai_match
import re
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Initialize the model
model = SentenceTransformer('all-MiniLM-L6-v2')

def preprocess_text(text: str) -> str:
    """Preprocess text by removing extra spaces, converting to lowercase, etc."""
    if not text:
        return ""
    # Remove extra whitespace and convert to lowercase
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return text

def compute_skill_match(student_skills: str, job_skills: str) -> float:
    """Compute similarity between student skills and job requirements"""
    try:
        student_skills = preprocess_text(student_skills)
        job_skills = preprocess_text(job_skills)

        if not student_skills or not job_skills:
            return 0.0

        # Encode both texts
        emb1 = model.encode(student_skills, convert_to_tensor=True)
        emb2 = model.encode(job_skills, convert_to_tensor=True)

        # Compute cosine similarity
        similarity = util.cos_sim(emb1, emb2)
        score = similarity.item() * 100  # Convert to percentage

        return round(score, 2)
    except Exception as e:
        print(f"Error computing skill match: {e}")
        return 0.0

def get_student_matches(student_id: int, student_skills: str, student_cgpa: float) -> List[Dict]:
    conn = get_db()
    c = conn.cursor()

    # Get student skills
    c.execute("SELECT skills_text FROM students WHERE id = ?", (student_id,))
    student_row = c.fetchone()
    if not student_row or not student_row[0]:
        conn.close()
        return []

    student_skills = student_row[0]

    # Get all job postings (assuming a jobs table exists, but for now, use mock data)
    # For demonstration, we'll use mock job data since we don't have a jobs table yet
    jobs = [
        {"role": "Software Engineer", "company": "TechCorp", "required_skills": "Python, Java, SQL, AWS"},
        {"role": "Data Analyst", "company": "DataSolutions", "required_skills": "Python, SQL, Excel, Machine Learning"},
        {"role": "Web Developer", "company": "WebMasters", "required_skills": "HTML, CSS, JavaScript, React"},
        {"role": "DevOps Engineer", "company": "CloudOps", "required_skills": "AWS, Docker, Linux, Kubernetes"},
        {"role": "Product Manager", "company": "InnovatePM", "required_skills": "Agile, Communication, Strategy, Scrum"}
    ]

    # Vectorize skills
    skills_list = [student_skills] + [job["required_skills"] for job in jobs]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(skills_list)

    # Calculate similarities
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

    # Sort by similarity and take top 5
    sorted_indices = similarities.argsort()[::-1][:5]

    matches = []
    for idx in sorted_indices:
        match_score = round(float(similarities[idx]), 2)
        if match_score > 0.1:  # Only include matches above threshold
            job = jobs[idx]
            matches.append((match_score,
                          f"Skills match: {student_skills} vs {job['required_skills']}",
                          job["role"], job["company"]))

    # Save matches to database
    c.execute("DELETE FROM ai_matches WHERE student_id = ?", (student_id,))
    for match in matches:
        c.execute("INSERT INTO ai_matches (student_id, role_title, company_name, match_score, match_reason) VALUES (?, ?, ?, ?, ?)",
                 (student_id, match[2], match[3], match[0], match[1]))

    conn.commit()
    conn.close()

    return matches

def update_matches(student_id: int):
    """Update AI matches for a student (called after profile updates)"""
    # This would typically be called when student updates their profile
    # For now, we'll implement it as a placeholder
    pass