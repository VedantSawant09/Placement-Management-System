import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from database import get_db, get_roles, save_ai_match

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_match(student_skills, job_skills):
    """
    Calculate skill match percentage using sentence-transformer embeddings and cosine similarity.

    Args:
        student_skills (str): Comma-separated string of student skills
        job_skills (str): Comma-separated string of job required skills

    Returns:
        float: Match percentage (0-100)
    """
    try:
        if not student_skills or not job_skills:
            logging.warning("Empty skills provided: student_skills='%s', job_skills='%s'", student_skills, job_skills)
            return 0.0

        # Generate embeddings
        student_embedding = model.encode([student_skills])
        job_embedding = model.encode([job_skills])

        # Calculate cosine similarity
        similarity = cosine_similarity(student_embedding, job_embedding)[0][0]

        # Convert to percentage (cosine similarity ranges from -1 to 1, but for text it's usually positive)
        match_percentage = max(0, (similarity + 1) / 2) * 100

        logging.info("Calculated match: %.2f%% for student_skills='%s' and job_skills='%s'",
                     match_percentage, student_skills, job_skills)

        return round(match_percentage, 2)

    except Exception as e:
        logging.error("Error calculating match: %s", str(e))
        return 0.0

def match_student_to_jobs(user_id):
    """
    Calculate and store matches for a student against all roles.

    Args:
        user_id (int): User ID of the student

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_db()
        c = conn.cursor()

        # Get student skills
        c.execute("SELECT skills FROM users WHERE id = ?", (user_id,))
        result = c.fetchone()
        if not result:
            logging.error("User not found: %d", user_id)
            return False
        student_skills = result[0] or ""

        # Get all roles with IDs
        c.execute("SELECT id, required_skills FROM roles")
        roles = c.fetchall()

        conn.close()

        if not student_skills:
            logging.warning("No skills found for user %d", user_id)
            return False

        # Calculate matches for each role
        for role_id, job_skills in roles:
            if not job_skills:
                continue
            match_score = calculate_match(student_skills, job_skills)
            match_reason = f"Skill match based on embeddings: {match_score}%"

            # Save match (this will insert or update as needed)
            save_ai_match(user_id, role_id, match_score, match_reason)

        logging.info("Successfully matched student %d to %d roles", user_id, len(roles))
        return True

    except Exception as e:
        logging.error("Error matching student to jobs: %s", str(e))
        return False

def get_student_matches(user_id):
    """
    Retrieve stored matches for a student.

    Args:
        user_id (int): User ID of the student

    Returns:
        list: List of tuples (match_score, match_reason, role_title, company_name)
    """
    try:
        from database import get_ai_matches
        matches = get_ai_matches(user_id)
        logging.info("Retrieved %d matches for user %d", len(matches), user_id)
        return matches
    except Exception as e:
        logging.error("Error retrieving student matches: %s", str(e))
        return []

def update_matches(user_id):
    """
    Recalculate all matches for a student by deleting existing matches and computing new ones.

    Args:
        user_id (int): User ID of the student

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_db()
        c = conn.cursor()

        # Delete existing matches
        c.execute("DELETE FROM ai_matches WHERE user_id = ?", (user_id,))
        deleted_count = c.rowcount
        conn.commit()
        conn.close()

        logging.info("Deleted %d existing matches for user %d", deleted_count, user_id)

        # Recalculate matches
        success = match_student_to_jobs(user_id)

        if success:
            logging.info("Successfully updated matches for user %d", user_id)
        else:
            logging.error("Failed to update matches for user %d", user_id)

        return success

    except Exception as e:
        logging.error("Error updating matches: %s", str(e))
        return False

def get_roles_with_ids():
    """
    Get all roles with their IDs and required skills.

    Returns:
        list: List of tuples (role_id, required_skills)
    """
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, required_skills FROM roles")
        roles = c.fetchall()
        conn.close()
        return roles
    except Exception as e:
        logging.error("Error retrieving roles: %s", str(e))
        return []