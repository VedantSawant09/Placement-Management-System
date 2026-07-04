from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def prepare_corpus(company_skill_texts, candidate_text):
    # company_skill_texts: list[str]
    # candidate_text: str
    return company_skill_texts + [candidate_text]

def compute_matches(candidate_text, companies, top_k=10):
    """
    companies: list of tuples (id, name, required_skills_csv, min_cgpa)
    returns: list of dicts {id, name, score (0..1), min_cgpa}
    """
    if not candidate_text or not companies:
        return []
    skill_texts = [c[2] for c in companies]
    titles = [c[1] for c in companies]
    corpus = prepare_corpus(skill_texts, candidate_text)
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(corpus)
    company_vecs = tfidf[:-1]
    candidate_vec = tfidf[-1]
    sims = cosine_similarity(candidate_vec, company_vecs)[0]  # shape (n_companies,)
    result = []
    for i, s in enumerate(sims):
        result.append({
            "id": companies[i][0],
            "name": titles[i],
            "score": float(s),
            "min_cgpa": float(companies[i][4])
        })
    result.sort(key=lambda x: x["score"], reverse=True)
    return result[:top_k]

def is_eligible(user_cgpa, company_min_cgpa):
    return float(user_cgpa) >= float(company_min_cgpa)