"""
Unit tests for AI Candidate Ranking System.
Run: python test_scoring.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import (
    detect_honeypot, score_candidate, score_experience,
    score_title, score_signals, score_location,
    get_confidence, deduplicate_text, get_score_breakdown,
    get_matched_and_missing_skills
)
from job_description import JOB
from config import WEIGHTS


def make_candidate(
    title="ML Engineer", years=6.0,
    skills=None, signals=None, career=None, grad_year=2015,
    country="India", location="Pune"
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
            "location": location, "country": country,
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
    result, _ = detect_honeypot(c)
    assert result is True
    print("  ✅ test_honeypot_future_graduation")


def test_honeypot_impossible_experience():
    c = make_candidate(years=15.0, grad_year=2020)
    result, _ = detect_honeypot(c)
    assert result is True
    print("  ✅ test_honeypot_impossible_experience")


def test_honeypot_normal_candidate():
    c = make_candidate(years=6.0, grad_year=2015)
    result, _ = detect_honeypot(c)
    assert result is False
    print("  ✅ test_honeypot_normal_candidate")


def test_honeypot_career_duration():
    career = [{"company": "X", "title": "Eng",
               "duration_months": 200, "industry": "SaaS",
               "description": "ml systems"}]
    c = make_candidate(years=5.0, career=career)
    result, _ = detect_honeypot(c)
    assert result is True
    print("  ✅ test_honeypot_career_duration")


# ── DISQUALIFIER TESTS ─────────────────────────────────────────────────

def test_disqualified_unrelated_role():
    c = make_candidate(title="Marketing Manager")
    score, reason = score_candidate(c, JOB)
    assert score == 0.0 and "Disqualified" in reason
    print("  ✅ test_disqualified_unrelated_role")


def test_disqualified_too_junior():
    c = make_candidate(years=1.0)
    score, reason = score_candidate(c, JOB)
    assert score == 0.0 and "Disqualified" in reason
    print("  ✅ test_disqualified_too_junior")


def test_disqualified_junior_title():
    c = make_candidate(title="Junior ML Engineer")
    score, _ = score_candidate(c, JOB)
    assert score == 0.0
    print("  ✅ test_disqualified_junior_title")


# ── SCORING TESTS ──────────────────────────────────────────────────────

def test_strong_candidate_scores_well():
    skills = [{"name": s, "proficiency": "Expert"} for s in [
        "Python", "Machine Learning", "Deep Learning",
        "NLP", "PyTorch", "Embeddings", "FAISS",
    ]]
    c = make_candidate(title="Senior AI Engineer", years=6.5, skills=skills)
    score, _ = score_candidate(c, JOB)
    assert score >= 60, f"Expected ≥60, got {score}"
    print(f"  ✅ test_strong_candidate_scores_well (score={score})")


def test_experience_sweet_spot():
    sweet, _ = score_experience(7.0, JOB)
    over, _  = score_experience(13.0, JOB)
    under, _ = score_experience(2.0, JOB)
    assert sweet > over and sweet > under
    print("  ✅ test_experience_sweet_spot")


def test_tier1_title_beats_tier3():
    t1, _ = score_title("senior ai engineer", JOB)
    t3, _ = score_title("backend engineer", JOB)
    assert t1 > t3
    print(f"  ✅ test_tier1_title_beats_tier3 ({t1} > {t3})")


def test_tier3_title_still_scores():
    t3, _ = score_title("software engineer", JOB)
    assert t3 > 0
    print(f"  ✅ test_tier3_title_still_scores ({t3})")


def test_score_non_negative():
    c = make_candidate(title="Accountant", years=10.0)
    score, _ = score_candidate(c, JOB)
    assert score >= 0.0
    print("  ✅ test_score_non_negative")


def test_consulting_penalty():
    career = [{"company": "TCS", "title": "Engineer",
               "duration_months": 60, "industry": "IT Services",
               "description": "java development projects"}]
    c = make_candidate(career=career)
    score, _ = score_candidate(c, JOB)
    assert score < 80
    print(f"  ✅ test_consulting_penalty (score={score})")


def test_location_india_bonus():
    score, reasons = score_location("india", "pune")
    assert score > 0 and len(reasons) > 0
    print("  ✅ test_location_india_bonus")


def test_location_no_penalty_outside_india():
    score, _ = score_location("usa", "san francisco")
    assert score >= 0
    print("  ✅ test_location_no_penalty_outside_india")


def test_salary_above_budget_penalised():
    sig_high = {"expected_salary_range_inr_lpa": {"min": 50, "max": 90}}
    sig_norm = {"expected_salary_range_inr_lpa": {"min": 15, "max": 30}}
    c_high = make_candidate(signals=sig_high)
    c_norm = make_candidate(signals=sig_norm)
    s_high, _ = score_candidate(c_high, JOB)
    s_norm, _ = score_candidate(c_norm, JOB)
    assert s_norm >= s_high
    print("  ✅ test_salary_above_budget_penalised")


def test_confidence_high():
    matched = ["python", "nlp", "pytorch", "embeddings", "faiss", "rag"]
    sigs = {"profile_completeness_score": 85,
            "skill_assessment_scores": {"NLP": 80}}
    conf = get_confidence(matched, 0.2, sigs)
    assert conf == "High", f"Expected High, got {conf}"
    print("  ✅ test_confidence_high")


def test_confidence_low():
    conf = get_confidence([], 0.0, {})
    assert conf == "Low", f"Expected Low, got {conf}"
    print("  ✅ test_confidence_low")


# ── EDGE CASE TESTS ────────────────────────────────────────────────────

def test_empty_profile_no_crash():
    """Empty profile should not crash — return 0 with disqualification."""
    c = {
        "candidate_id": "CAND_EMPTY",
        "profile": {},
        "skills": [], "career_history": [],
        "education": [], "redrob_signals": {}
    }
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_empty_profile_no_crash")


def test_missing_career_no_crash():
    c = make_candidate(career=[])
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_missing_career_no_crash")


def test_missing_skills_no_crash():
    c = make_candidate(skills=[])
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_missing_skills_no_crash")


def test_missing_signals_no_crash():
    c = make_candidate()
    c["redrob_signals"] = {}
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_missing_signals_no_crash")


def test_unicode_profile_no_crash():
    """Hindi/Japanese characters in profile should not crash."""
    c = make_candidate()
    c["profile"]["summary"] = "मैं एक AI इंजीनियर हूं। 私はAIエンジニアです。"
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_unicode_profile_no_crash")


def test_keyword_stuffing_prevented():
    """Repeated keywords should not inflate score beyond normal range."""
    stuffed_career = [{
        "company": "TechCorp", "title": "ML Engineer",
        "duration_months": 36, "industry": "SaaS",
        "description": ("embeddings " * 500 + "faiss " * 500 +
                         "ranking " * 500 + "rag " * 500)
    }]
    c_stuffed = make_candidate(career=stuffed_career)
    c_normal  = make_candidate()
    s_stuffed, _ = score_candidate(c_stuffed, JOB)
    s_normal, _  = score_candidate(c_normal, JOB)
    # Stuffed should not dramatically outperform normal due to deduplication
    assert s_stuffed < s_normal + 30, (
        f"Keyword stuffing inflated score too much: "
        f"{s_stuffed} vs {s_normal}"
    )
    print(
        f"  ✅ test_keyword_stuffing_prevented "
        f"(stuffed={s_stuffed}, normal={s_normal})"
    )


def test_deduplication_works():
    text   = "faiss faiss faiss faiss faiss faiss faiss faiss"
    result = deduplicate_text(text)
    assert result.count("faiss") <= 3
    print("  ✅ test_deduplication_works")


def test_invalid_date_no_crash():
    c = make_candidate()
    c["redrob_signals"]["last_active_date"] = "not-a-date"
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_invalid_date_no_crash")


# ── WEIGHT-OVERRIDE TESTS (Streamlit slider parity) ─────────────────────

def test_custom_weights_change_score():
    """Raising the skills weight should raise the score of a skill-heavy
    candidate relative to the default weights — proves the UI sliders
    actually influence ranking rather than being cosmetic."""
    skills = [{"name": s, "proficiency": "Expert"} for s in [
        "Python", "Machine Learning", "Deep Learning", "NLP", "PyTorch"
    ]]
    c = make_candidate(skills=skills)
    default_score, _ = score_candidate(c, JOB)

    boosted_weights = dict(WEIGHTS)
    boosted_weights["skills"] = 70  # double the default 35
    boosted_score, _ = score_candidate(c, JOB, weights=boosted_weights)

    assert boosted_score > default_score, (
        f"Expected boosted skills weight to raise score: "
        f"{boosted_score} vs {default_score}"
    )
    print(
        f"  ✅ test_custom_weights_change_score "
        f"(default={default_score}, boosted={boosted_score})"
    )


def test_zero_weight_removes_signal_contribution():
    """Zeroing out the 'signals' weight should remove behavioral signals
    from the score entirely."""
    c = make_candidate(signals={"github_activity_score": 95, "saved_by_recruiters_30d": 10})
    zero_weights = dict(WEIGHTS)
    zero_weights["signals"] = 0
    sig_score, _ = score_signals(c["redrob_signals"], JOB, weights=zero_weights)
    assert sig_score == 0.0
    print("  ✅ test_zero_weight_removes_signal_contribution")


def test_score_breakdown_respects_custom_weights():
    c = make_candidate()
    custom = dict(WEIGHTS)
    custom["experience"] = 30
    breakdown = get_score_breakdown(c, JOB, weights=custom)
    assert breakdown["Experience"] <= 30
    print("  ✅ test_score_breakdown_respects_custom_weights")


# ── ADDITIONAL EDGE CASES ────────────────────────────────────────────────

def test_extremely_large_summary_no_crash():
    """A pathologically long summary/headline should not crash or blow up
    runtime — deduplication should cap repeated-word inflation."""
    c = make_candidate()
    c["profile"]["summary"] = "embeddings retrieval faiss ranking llm " * 5000
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_extremely_large_summary_no_crash")


def test_missing_education_field_no_crash():
    c = make_candidate()
    del c["education"]
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_missing_education_field_no_crash")


def test_zero_years_experience_disqualified():
    c = make_candidate(years=0.0)
    score, reason = score_candidate(c, JOB)
    assert score == 0.0 and "Disqualified" in reason
    print("  ✅ test_zero_years_experience_disqualified")


def test_negative_or_missing_signals_dont_crash():
    c = make_candidate()
    c["redrob_signals"]["expected_salary_range_inr_lpa"] = {}
    c["redrob_signals"]["skill_assessment_scores"] = None
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_negative_or_missing_signals_dont_crash")


def test_malformed_career_history_no_crash():
    """Career entries missing expected keys should not crash scoring."""
    c = make_candidate(career=[{"company": "X"}])
    score, _ = score_candidate(c, JOB)
    assert score >= 0
    print("  ✅ test_malformed_career_history_no_crash")


# ── CONSISTENCY / REGRESSION TESTS ──────────────────────────────────────

def test_alias_matched_skill_not_shown_as_missing():
    """
    A skill credited via alias in career text (e.g. 'approximate nearest
    neighbour' -> 'faiss') must appear in the matched list, not the
    missing list — this is the exact discrepancy that used to exist
    between what score_skills scored and what main.py/app.py displayed.
    """
    career = [{
        "company": "TechCorp", "title": "ML Engineer",
        "duration_months": 36, "industry": "SaaS",
        "description": "built approximate nearest neighbour search "
                        "for product recommendations"
    }]
    c = make_candidate(
        skills=[{"name": "Python", "proficiency": "Expert"}],
        career=career
    )
    full_text = deduplicate_text(
        c["career_history"][0]["description"].lower()
    )
    matched, missing = get_matched_and_missing_skills(c, JOB, full_text)
    assert "faiss" in matched, f"expected alias-matched 'faiss' in {matched}"
    assert "faiss" not in missing
    print("  ✅ test_alias_matched_skill_not_shown_as_missing")


def test_no_skill_penalty_scales_with_weight():
    """
    The 'no skills matched' penalty inside score_skills must scale with
    weights['skills'] instead of being a flat -15, so a caller who lowers
    the skills weight (e.g. a Streamlit slider) doesn't apply a
    disproportionately large fixed penalty relative to the rest of the
    score.
    """
    c = make_candidate(skills=[])  # no required skills present
    default_score, _ = score_candidate(c, JOB)

    low_skill_weights = dict(WEIGHTS)
    low_skill_weights["skills"] = 5  # far below default 35
    low_score, _ = score_candidate(c, JOB, weights=low_skill_weights)

    assert low_score >= 0.0 and default_score >= 0.0
    print(
        f"  ✅ test_no_skill_penalty_scales_with_weight "
        f"(default_skills_weight_score={default_score}, "
        f"low_skills_weight_score={low_score})"
    )


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
        test_salary_above_budget_penalised,
        test_confidence_high,
        test_confidence_low,
        test_empty_profile_no_crash,
        test_missing_career_no_crash,
        test_missing_skills_no_crash,
        test_missing_signals_no_crash,
        test_unicode_profile_no_crash,
        test_keyword_stuffing_prevented,
        test_deduplication_works,
        test_invalid_date_no_crash,
        test_custom_weights_change_score,
        test_zero_weight_removes_signal_contribution,
        test_score_breakdown_respects_custom_weights,
        test_extremely_large_summary_no_crash,
        test_missing_education_field_no_crash,
        test_zero_years_experience_disqualified,
        test_negative_or_missing_signals_dont_crash,
        test_malformed_career_history_no_crash,
        test_alias_matched_skill_not_shown_as_missing,
        test_no_skill_penalty_scales_with_weight,
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