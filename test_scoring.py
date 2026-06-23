"""
Unit tests for the AI Candidate Ranking System.
Run with: python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import (
    detect_honeypot, score_candidate, score_skills,
    score_experience, score_title, score_signals
)
from job_description import JOB


# ── TEST DATA ─────────────────────────────────────────────────────────

def make_candidate(
    title="ML Engineer",
    years=6.0,
    skills=None,
    signals=None,
    career=None,
    grad_year=2015
):
    return {
        "candidate_id": "CAND_TEST_001",
        "profile": {
            "anonymized_name": "Test Candidate",
            "current_title": title,
            "years_of_experience": years,
            "headline": "",
            "summary": "",
            "location": "Pune",
            "country": "India",
        },
        "skills": skills or [
            {"name": "Python", "proficiency": "Expert"},
            {"name": "Machine Learning", "proficiency": "Expert"},
            {"name": "NLP", "proficiency": "Advanced"},
        ],
        "career_history": career or [
            {
                "company": "TechCorp",
                "title": "ML Engineer",
                "duration_months": 36,
                "industry": "SaaS",
                "description": "Built recommendation systems using embeddings and FAISS"
            }
        ],
        "education": [
            {"tier": "tier_2", "institution": "NIT", "end_year": grad_year}
        ],
        "certifications": [],
        "redrob_signals": signals or {
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.7,
            "last_active_date": "2026-06-01",
            "notice_period_days": 30,
            "github_activity_score": 65,
            "profile_completeness_score": 80,
            "verified_email": True,
            "verified_phone": True,
            "skill_assessment_scores": {},
            "saved_by_recruiters_30d": 3,
            "interview_completion_rate": 0.8,
            "offer_acceptance_rate": 0.6,
            "linkedin_connected": True,
            "applications_submitted_30d": 2,
            "profile_views_received_30d": 15,
            "connection_count": 350,
            "endorsements_received": 20,
            "avg_response_time_hours": 12,
            "willing_to_relocate": True,
            "preferred_work_mode": "hybrid",
            "expected_salary_range_inr_lpa": {"min": 20, "max": 35},
            "search_appearance_30d": 150,
            "signup_date": "2024-01-01",
        }
    }


# ── HONEYPOT TESTS ────────────────────────────────────────────────────

def test_honeypot_future_graduation():
    candidate = make_candidate(grad_year=2030)
    result, reason = detect_honeypot(candidate)
    assert result is True
    assert "future" in reason.lower()


def test_honeypot_impossible_experience():
    # Graduated 2020, claims 15 years
    candidate = make_candidate(years=15.0, grad_year=2020)
    result, reason = detect_honeypot(candidate)
    assert result is True
    assert "graduated" in reason.lower()


def test_honeypot_normal_candidate():
    candidate = make_candidate(years=6.0, grad_year=2015)
    result, reason = detect_honeypot(candidate)
    assert result is False


def test_honeypot_career_duration():
    # 200 months career but claims 5 years (60 months)
    career = [
        {"company": "X", "title": "Engineer",
         "duration_months": 200, "industry": "SaaS",
         "description": "built ML systems"}
    ]
    candidate = make_candidate(years=5.0, career=career)
    result, _ = detect_honeypot(candidate)
    assert result is True


# ── SCORING TESTS ─────────────────────────────────────────────────────

def test_disqualified_unrelated_role():
    candidate = make_candidate(title="Marketing Manager")
    score, reason = score_candidate(candidate, JOB)
    assert score == 0.0
    assert "Disqualified" in reason


def test_disqualified_too_junior():
    candidate = make_candidate(years=1.0)
    score, reason = score_candidate(candidate, JOB)
    assert score == 0.0
    assert "junior" in reason.lower()


def test_disqualified_junior_title():
    candidate = make_candidate(title="Junior ML Engineer")
    score, reason = score_candidate(candidate, JOB)
    assert score == 0.0
    assert "junior" in reason.lower()


def test_strong_candidate_scores_well():
    skills = [
        {"name": "Python", "proficiency": "Expert"},
        {"name": "Machine Learning", "proficiency": "Expert"},
        {"name": "Deep Learning", "proficiency": "Expert"},
        {"name": "NLP", "proficiency": "Expert"},
        {"name": "PyTorch", "proficiency": "Expert"},
        {"name": "Embeddings", "proficiency": "Expert"},
        {"name": "FAISS", "proficiency": "Advanced"},
    ]
    candidate = make_candidate(
        title="Senior AI Engineer",
        years=6.5,
        skills=skills
    )
    score, _ = score_candidate(candidate, JOB)
    assert score >= 60, f"Strong candidate should score ≥60, got {score}"


def test_experience_sweet_spot():
    score_sweet, _ = score_experience(7.0, JOB)
    score_over, _  = score_experience(13.0, JOB)
    score_under, _ = score_experience(2.0, JOB)
    assert score_sweet > score_over
    assert score_sweet > score_under


def test_strong_title_scores_higher():
    score_good, _ = score_title("senior ai engineer", JOB)
    score_weak, _ = score_title("cloud engineer", JOB)
    assert score_good > score_weak


def test_score_is_non_negative():
    candidate = make_candidate(
        title="Accountant",
        years=10.0
    )
    score, _ = score_candidate(candidate, JOB)
    assert score >= 0.0


def test_score_does_not_exceed_max():
    skills = [
        {"name": s, "proficiency": "Expert"} for s in [
            "Python", "Machine Learning", "Deep Learning", "NLP",
            "PyTorch", "TensorFlow", "Embeddings", "FAISS",
            "Elasticsearch", "Information Retrieval", "Ranking",
            "Sentence-Transformers", "Vector Database", "LLM"
        ]
    ]
    candidate = make_candidate(
        title="Senior AI Engineer",
        years=7.0,
        skills=skills
    )
    score, _ = score_candidate(candidate, JOB)
    # Max possible is around 120 + signals
    assert score <= 150, f"Score should not exceed max, got {score}"


if __name__ == "__main__":
    # Run manually without pytest
    tests = [
        test_honeypot_future_graduation,
        test_honeypot_impossible_experience,
        test_honeypot_normal_candidate,
        test_honeypot_career_duration,
        test_disqualified_unrelated_role,
        test_disqualified_too_junior,
        test_disqualified_junior_title,
        test_strong_candidate_scores_well,
        test_experience_sweet_spot,
        test_strong_title_scores_higher,
        test_score_is_non_negative,
        test_score_does_not_exceed_max,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed+failed} tests passed")