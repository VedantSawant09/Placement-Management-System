import re
from typing import List
import io
from pypdf import PdfReader

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text content from PDF file"""
    try:
        pdf_reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def extract_skills_from_text(text: str) -> List[str]:
    """Extract technical skills from resume text using regex patterns"""
    if not text:
        return []

    # Convert to lowercase for matching
    text_lower = text.lower()

    # Common technical skills patterns
    skill_patterns = [
        # Programming languages
        r'\b(python|java|javascript|c\+\+|c#|php|ruby|swift|kotlin|typescript|go|golang|rust|scala|r|matlab)\b',
        # Web technologies
        r'\b(html|css|react|angular|vue|node\.js|express|django|flask|spring|laravel)\b',
        # Databases
        r'\b(sql|mysql|postgresql|mongodb|oracle|sqlite|redis|cassandra)\b',
        # Cloud platforms
        r'\b(aws|azure|gcp|google cloud|heroku|docker|kubernetes|jenkins)\b',
        # Data Science/AI
        r'\b(machine learning|deep learning|artificial intelligence|neural networks|tensorflow|pytorch|pandas|numpy|scikit-learn|nlp|computer vision)\b',
        # Tools
        r'\b(git|github|linux|windows|macos|android|ios)\b',
        # Soft skills and domains
        r'\b(communication|leadership|teamwork|problem solving|analytical|project management|agile|scrum)\b'
    ]

    found_skills = set()

    for pattern in skill_patterns:
        matches = re.findall(pattern, text_lower)
        found_skills.update(matches)

    # Clean up duplicates and format
    skills_list = list(found_skills)
    skills_list.sort()

    return skills_list

def preprocess_text(text: str) -> str:
    """Preprocess text by removing extra spaces, converting to lowercase, etc."""
    if not text:
        return ""
    # Remove extra whitespace and convert to lowercase
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return text
