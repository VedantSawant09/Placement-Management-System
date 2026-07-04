# Simple text matching without scikit-learn to avoid compilation issues
import re

def compute_match(resume_text, roles, user_cgpa=None):
    if not resume_text:
        return []
    matches = []
    resume_lower = resume_text.lower()

    for title, skills, company in roles:
        if not skills:
            continue

        # Simple keyword matching instead of TF-IDF
        resume_words = set(re.findall(r'\b\w+\b', resume_lower))
        skill_words = set(re.findall(r'\b\w+\b', skills.lower()))
        common_words = resume_words.intersection(skill_words)

        # Calculate match score based on common keywords
        skill_score = len(common_words) / len(skill_words) if skill_words else 0.0

        # Get company min CGPA
        from database import get_companies
        companies = get_companies()
        min_cgpa = 0.0
        for comp in companies:
            if comp[1] == company:
                min_cgpa = comp[4] if len(comp) > 4 else 0.0
                break

        # CGPA eligibility
        eligible = user_cgpa >= min_cgpa if user_cgpa else False

        # Combine scores (skill match + CGPA factor)
        cgpa_factor = 1.0 if eligible else 0.5
        final_score = skill_score * cgpa_factor

        matches.append((title, final_score, company, eligible))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:5]  # Top 5 matches
