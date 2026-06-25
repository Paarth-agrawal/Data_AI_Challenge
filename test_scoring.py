"""
Unit tests for AI Candidate Ranking System.
Run: python tests/test_scoring.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import (
    detect_honeypot, score_candidate, score_experience,
    score_title, score_signals, score_location, get_confidence
)
from job_description import JOB


def make_candidate(
    title="ML Engineer", years=6.0,
    skills=None, signals=None, career=None, grad_year=2015
):
    base_signals = {
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
    if signals:
        base_signals.update(signals)
    return {
        "candidate_id": "CAND_TEST_001",
        "profile": {
            "anonymized_name": "Test Candidate",
            "current_title": title,
            "years_of_experience": years,
            "headline": "", "summary": "",
            "location": "Pune", "country": "India",
        },
        "skills": skills or [
            {"name": "Python", "proficiency": "Expert"},
            {"name": "Machine Learning", "proficiency": "Expert"},
            {"name": "NLP", "proficiency": "Advanced"},
        ],
        "career_history": career or [{
            "company": "TechCorp", "title": "ML Engineer",
            "duration_months": 36, "industry": "SaaS",
            "description": "built recommendation systems using embeddings"
        }],
        "education": [
            {"tier": "tier_2", "institution": "NIT", "end_year": grad_year}
        ],
        "certifications": [],
        "redrob_signals": base_signals,
    }


# ── HONEYPOT TESTS ─────────────────────────────────────────────────────

def test_honeypot_future_graduation():
    c = make_candidate(grad_year=2030)
    result, reason = detect_honeypot(c)
    assert result is True, "Should detect future graduation"
    assert "future" in reason.lower()
    print("  ✅ test_honeypot_future_graduation")


def test_honeypot_impossible_experience():
    c = make_candidate(years=15.0, grad_year=2020)
    result, reason = detect_honeypot(c)
    assert result is True, "15 yrs since 2020 is impossible"
    print("  ✅ test_honeypot_impossible_experience")


def test_honeypot_normal_candidate():
    c = make_candidate(years=6.0, grad_year=2015)
    result, _ = detect_honeypot(c)
    assert result is False, "Normal candidate should not be flagged"
    print("  ✅ test_honeypot_normal_candidate")


def test_honeypot_career_duration():
    career = [{"company": "X", "title": "Eng",
               "duration_months": 200, "industry": "SaaS",
               "description": "ml systems"}]
    c = make_candidate(years=5.0, career=career)
    result, _ = detect_honeypot(c)
    assert result is True, "200 months vs 60 claimed should trigger"
    print("  ✅ test_honeypot_career_duration")


# ── DISQUALIFIER TESTS ─────────────────────────────────────────────────

def test_disqualified_unrelated_role():
    c = make_candidate(title="Marketing Manager")
    score, reason = score_candidate(c, JOB)
    assert score == 0.0
    assert "Disqualified" in reason
    print("  ✅ test_disqualified_unrelated_role")


def test_disqualified_too_junior():
    c = make_candidate(years=1.0)
    score, reason = score_candidate(c, JOB)
    assert score == 0.0
    assert "junior" in reason.lower()
    print("  ✅ test_disqualified_too_junior")


def test_disqualified_junior_title():
    c = make_candidate(title="Junior ML Engineer")
    score, reason = score_candidate(c, JOB)
    assert score == 0.0
    print("  ✅ test_disqualified_junior_title")


# ── SCORING TESTS ──────────────────────────────────────────────────────

def test_strong_candidate_scores_well():
    skills = [
        {"name": s, "proficiency": "Expert"} for s in [
            "Python", "Machine Learning", "Deep Learning",
            "NLP", "PyTorch", "Embeddings", "FAISS",
        ]
    ]
    c = make_candidate(title="Senior AI Engineer", years=6.5, skills=skills)
    score, _ = score_candidate(c, JOB)
    assert score >= 60, f"Strong candidate should score ≥60, got {score}"
    print(f"  ✅ test_strong_candidate_scores_well (score={score})")


def test_experience_sweet_spot():
    sweet, _ = score_experience(7.0, JOB)
    over, _  = score_experience(13.0, JOB)
    under, _ = score_experience(2.0, JOB)
    assert sweet > over
    assert sweet > under
    print("  ✅ test_experience_sweet_spot")


def test_tier1_title_beats_tier3():
    tier1, _ = score_title("senior ai engineer", JOB)
    tier3, _ = score_title("backend engineer", JOB)
    assert tier1 > tier3
    print(f"  ✅ test_tier1_title_beats_tier3 ({tier1} > {tier3})")


def test_tier3_title_still_scores():
    tier3, _ = score_title("software engineer", JOB)
    assert tier3 > 0
    print(f"  ✅ test_tier3_title_still_scores (score={tier3})")


def test_score_non_negative():
    c = make_candidate(title="Accountant", years=10.0)
    score, _ = score_candidate(c, JOB)
    assert score >= 0.0
    print("  ✅ test_score_non_negative")


def test_consulting_penalty():
    career = [
        {"company": "TCS", "title": "Engineer",
         "duration_months": 60, "industry": "IT Services",
         "description": "java development projects"}
    ]
    c = make_candidate(career=career)
    score, reason = score_candidate(c, JOB)
    assert score < 80, "Consulting-only should be penalised"
    print(f"  ✅ test_consulting_penalty (score={score})")


def test_location_india_bonus():
    score, reasons = score_location("india", "pune")
    assert score > 0
    assert len(reasons) > 0
    print("  ✅ test_location_india_bonus")


def test_location_no_penalty_outside_india():
    score, _ = score_location("usa", "san francisco")
    assert score >= 0, "Outside India should never give negative score"
    print("  ✅ test_location_no_penalty_outside_india")


def test_salary_within_budget():
    signals = {"expected_salary_range_inr_lpa": {"min": 15, "max": 30}}
    c = make_candidate(signals=signals)
    score, _ = score_candidate(c, JOB)
    # Just check it runs without error
    assert score >= 0
    print("  ✅ test_salary_within_budget")


def test_salary_above_budget():
    signals = {"expected_salary_range_inr_lpa": {"min": 50, "max": 90}}
    c_high = make_candidate(signals=signals)
    signals2 = {"expected_salary_range_inr_lpa": {"min": 15, "max": 30}}
    c_normal = make_candidate(signals=signals2)
    score_high, _   = score_candidate(c_high, JOB)
    score_normal, _ = score_candidate(c_normal, JOB)
    assert score_normal >= score_high, "Above-budget should not score higher"
    print("  ✅ test_salary_above_budget")


def test_confidence_high():
    matched = ["python", "nlp", "pytorch", "embeddings", "faiss"]
    signals = {"profile_completeness_score": 85,
               "skill_assessment_scores": {"NLP": 80}}
    conf = get_confidence(matched, 0.2, signals)
    assert conf == "High", f"Expected High, got {conf}"
    print("  ✅ test_confidence_high")


def test_confidence_low():
    conf = get_confidence([], 0.0, {})
    assert conf == "Low", f"Expected Low, got {conf}"
    print("  ✅ test_confidence_low")


if __name__ == "__main__":
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
        test_tier1_title_beats_tier3,
        test_tier3_title_still_scores,
        test_score_non_negative,
        test_consulting_penalty,
        test_location_india_bonus,
        test_location_no_penalty_outside_india,
        test_salary_within_budget,
        test_salary_above_budget,
        test_confidence_high,
        test_confidence_low,
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed}/{passed+failed} passed")
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ {failed} test(s) failed")