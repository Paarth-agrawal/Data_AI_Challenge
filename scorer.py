from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any
from config import (
    WEIGHTS, SEMANTIC_HIGH, SEMANTIC_MEDIUM,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM,
    CONFIDENCE_SKILL_STRONG, CONFIDENCE_SKILL_GOOD, CONFIDENCE_SKILL_PARTIAL,
    CONFIDENCE_PROFILE_STRONG, CONFIDENCE_PROFILE_MEDIUM,
    SIGNAL_MAX_SCORE, SIGNAL_MIN_SCORE,
    RESPONSE_RATE_HIGH, RESPONSE_RATE_LOW,
    RECENCY_VERY_ACTIVE_DAYS, RECENCY_ACTIVE_DAYS, RECENCY_RECENT_DAYS,
    NOTICE_IMMEDIATE, NOTICE_SHORT, NOTICE_LONG,
    GITHUB_STRONG, GITHUB_MODERATE,
    RECRUITERS_SAVED_HIGH, RECRUITERS_SAVED_LOW,
    INTERVIEW_RATE_GOOD, INTERVIEW_RATE_POOR,
    OFFER_RATE_GOOD, OFFER_RATE_POOR,
    PROFILE_COMPLETE_STRONG, PROFILE_COMPLETE_WEAK,
    VIEWS_HIGH, VIEWS_MEDIUM, APPS_VERY_ACTIVE, APPS_ACTIVE,
    CONNECTIONS_STRONG, CONNECTIONS_MODERATE,
    ENDORSEMENTS_STRONG, ENDORSEMENTS_MODERATE,
    PLATFORM_TENURE_DAYS, SEARCH_APPEARANCE_HIGH,
    SALARY_WITHIN_RATIO, SALARY_ABOVE_RATIO,
    HONEYPOT_CAREER_TOLERANCE_MONTHS, HONEYPOT_GRAD_YEAR_TOLERANCE,
    HONEYPOT_MIN_ENDORSEMENTS,
    CONSULTING_ALL_PENALTY, CONSULTING_ALL_WEAK_PENALTY,
    CONSULTING_MAJORITY_PENALTY, CONSULTING_MAJORITY_THRESHOLD,
    CONSULTING_AI_EVIDENCE_MIN,
    TFIDF_MAX_WORD_REPEAT,
    MIN_EXPERIENCE_YEARS, MAX_EXPERIENCE_YEARS, MIN_YEARS_TO_QUALIFY,
    SALARY_BUDGET_MAX_LPA,
)

ACRONYMS: Dict[str, str] = {
    "ai": "AI", "ml": "ML", "nlp": "NLP", "llm": "LLM",
    "rag": "RAG", "api": "API", "sql": "SQL", "faiss": "FAISS",
    "mlops": "MLOps", "llmops": "LLMOps", "rlhf": "RLHF",
    "cuda": "CUDA", "bert": "BERT", "gpt": "GPT", "cv": "CV",
    "gpu": "GPU", "cpu": "CPU", "aws": "AWS", "gcp": "GCP",
}

SKILL_ALIASES: Dict[str, List[str]] = {
    "faiss":                ["ann", "approximate nearest neighbour",
                             "vector retrieval", "approximate nearest neighbor",
                             "hnsw", "ivf index"],
    "rag":                  ["retrieval augmented generation", "dense retrieval",
                             "retrieval-augmented", "grounded generation"],
    "llm":                  ["large language model", "gpt", "transformer model",
                             "foundation model", "generative model"],
    "embeddings":           ["vector embeddings", "word embeddings",
                             "dense vectors", "embedding model",
                             "sentence embeddings"],
    "information retrieval":["ir", "document retrieval", "search engine",
                             "semantic search", "neural search"],
    "ranking":              ["learning to rank", "reranking", "re-ranking",
                             "cross encoder", "pointwise ranking",
                             "lambdamart", "listwise ranking"],
    "vector database":      ["vector store", "vector index", "ann index",
                             "embedding store", "chroma", "vespa"],
    "nlp":                  ["natural language processing", "text processing",
                             "language model", "text mining"],
    "fine-tuning":          ["instruction tuning", "sft", "supervised fine",
                             "lora training", "qlora training", "peft"],
    "machine learning":     ["ml pipeline", "model training", "sklearn",
                             "gradient boosting", "xgboost", "lightgbm"],
}


def fix_title_caps(title: str) -> str:
    title_display = title.title()
    for word, replacement in ACRONYMS.items():
        title_display = title_display.replace(word.title(), replacement)
        title_display = title_display.replace(
            f"({word.title()})", f"({replacement})"
        )
    return title_display


def deduplicate_text(text: str) -> str:
    """Prevent TF-IDF exploitation — cap any word at TFIDF_MAX_WORD_REPEAT."""
    words:  List[str]       = text.split()
    counts: Dict[str, int]  = {}
    result: List[str]       = []
    for word in words:
        counts[word] = counts.get(word, 0) + 1
        if counts[word] <= TFIDF_MAX_WORD_REPEAT:
            result.append(word)
    return " ".join(result)


def get_confidence(
    matched_skills: List[str],
    semantic_sim: float,
    signals: Dict[str, Any],
) -> str:
    """
    Compute evidence-based confidence level.
    High requires matched_skills >= CONFIDENCE_SKILL_GOOD AND semantic evidence.
    """
    completeness = signals.get("profile_completeness_score", 0)
    assessments  = signals.get("skill_assessment_scores", {})
    evidence     = 0

    if len(matched_skills) >= CONFIDENCE_SKILL_STRONG:
        evidence += 3
    elif len(matched_skills) >= CONFIDENCE_SKILL_GOOD:
        evidence += 2
    elif len(matched_skills) >= CONFIDENCE_SKILL_PARTIAL:
        evidence += 1

    if semantic_sim >= SEMANTIC_HIGH:
        evidence += 2
    elif semantic_sim >= SEMANTIC_MEDIUM:
        evidence += 1

    if completeness >= CONFIDENCE_PROFILE_STRONG:
        evidence += 2
    elif completeness >= CONFIDENCE_PROFILE_MEDIUM:
        evidence += 1

    if assessments:
        evidence += 1

    if evidence >= CONFIDENCE_HIGH:
        return "High"
    elif evidence >= CONFIDENCE_MEDIUM:
        return "Medium"
    return "Low"


def get_confidence_reasons(
    matched_skills: List[str],
    semantic_sim: float,
    signals: Dict[str, Any],
) -> List[str]:
    """Returns human-readable reasons for the confidence level."""
    reasons: List[str] = []
    completeness = signals.get("profile_completeness_score", 0)
    assessments  = signals.get("skill_assessment_scores", {})

    if len(matched_skills) >= CONFIDENCE_SKILL_GOOD:
        reasons.append(f"✓ {len(matched_skills)} required skills matched")
    elif len(matched_skills) > 0:
        reasons.append(f"⚠ Only {len(matched_skills)} required skills matched")
    else:
        reasons.append("✗ No required skills matched")

    if semantic_sim >= SEMANTIC_HIGH:
        reasons.append("✓ Strong semantic alignment with JD")
    elif semantic_sim >= SEMANTIC_MEDIUM:
        reasons.append("~ Moderate semantic alignment with JD")
    else:
        reasons.append("✗ Low semantic alignment with JD")

    if completeness >= CONFIDENCE_PROFILE_STRONG:
        reasons.append(f"✓ Complete profile ({completeness}%)")
    elif completeness >= CONFIDENCE_PROFILE_MEDIUM:
        reasons.append(f"~ Partial profile ({completeness}%)")
    else:
        reasons.append(f"✗ Incomplete profile ({completeness}%)")

    if assessments:
        best = max(assessments, key=assessments.get)
        reasons.append(f"✓ Verified assessment: {best} ({assessments[best]}/100)")
    else:
        reasons.append("~ No platform assessments taken")

    return reasons


def detect_honeypot(candidate: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Detect impossible/synthetic profiles.
    Conservative thresholds avoid false positives on real senior engineers.
    """
    profile      = candidate.get("profile", {})
    career       = candidate.get("career_history", [])
    education    = candidate.get("education", [])
    signals      = candidate.get("redrob_signals", {})
    current_year = datetime.now().year
    years_exp    = profile.get("years_of_experience", 0)

    grad_year = 0
    if education and isinstance(education, list):
        grad_year = max((edu.get("end_year", 0) or 0) for edu in education)

    if grad_year and grad_year > current_year:
        return True, f"graduation year {grad_year} is in the future"

    if grad_year and grad_year > 0:
        max_possible = current_year - grad_year
        if years_exp > max_possible + HONEYPOT_GRAD_YEAR_TOLERANCE:
            return True, (
                f"{years_exp} yrs experience is impossible given "
                f"graduation year {grad_year}"
            )

    for job in career:
        founded    = job.get("company_founded_year", 0)
        start_year = job.get("start_year", 0)
        if founded and start_year and start_year < founded - 1:
            return True, "worked at company before it was founded"

    if career:
        total_months   = sum(j.get("duration_months", 0) for j in career)
        claimed_months = years_exp * 12
        if total_months > claimed_months + HONEYPOT_CAREER_TOLERANCE_MONTHS:
            return True, (
                f"career history ({total_months}mo) far exceeds "
                f"claimed experience ({claimed_months}mo)"
            )

    skills       = candidate.get("skills", [])
    expert_count = sum(
        1 for s in skills
        if str(s.get("proficiency", "")).lower() in ["expert", "advanced"]
    )
    endorsements      = signals.get("endorsements_received", 999)
    max_plausible_exp = max(10, int(years_exp * 2))

    if expert_count > max_plausible_exp and endorsements < HONEYPOT_MIN_ENDORSEMENTS:
        return True, (
            f"{expert_count} expert skills is implausible for "
            f"{years_exp} years experience with only {endorsements} endorsements"
        )

    return False, ""


def score_skills(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    full_text: str,
    jd_vector: Any = None,
    vectorizer: Any = None,
) -> Tuple[float, List[str], List[str], List[str], float]:
    """Returns (score, reasons, matched, missing, semantic_sim)"""
    skills           = candidate.get("skills", [])
    signals          = candidate.get("redrob_signals", {})
    candidate_skills = [s["name"].lower() for s in skills]
    required_skills  = [s.lower() for s in job.get("required_skills", [])]
    score            = 0.0
    reasons:  List[str] = []

    matched: List[str] = [s for s in required_skills if s in candidate_skills]
    alias_matched: List[str] = []
    for skill in required_skills:
        if skill not in matched:
            aliases = SKILL_ALIASES.get(skill, [])
            if any(alias in full_text for alias in aliases):
                alias_matched.append(skill)

    all_matched = matched + alias_matched
    missing     = [s for s in required_skills if s not in all_matched]

    skill_score = (len(all_matched) / len(required_skills)) * WEIGHTS["skills"]
    score      += skill_score

    if len(all_matched) == 0:
        score -= 15
        reasons.append(
            "no direct skill match found in profile or career history"
        )
    elif len(all_matched) == 1:
        score -= 5
        reasons.append(
            f"limited skill coverage — only {all_matched[0]} verified"
        )
    else:
        top = ", ".join(all_matched[:4])
        if alias_matched:
            reasons.append(
                f"demonstrates production experience in {top}"
                f"; inferred from career: {', '.join(alias_matched[:2])}"
            )
        else:
            reasons.append(
                f"demonstrates production experience in {top}"
            )

    if len(missing) >= 8:
        missing_sample = ", ".join(missing[:3])
        reasons.append(
            f"limited evidence of production experience with "
            f"{missing_sample} and {len(missing)-3} other required skills"
        )

    bonus_skills  = [s.lower() for s in job.get("bonus_skills", [])]
    bonus_matched = [s for s in bonus_skills if s in candidate_skills]
    bonus_score   = min(WEIGHTS["bonus"], len(bonus_matched) * 1.5)
    score        += bonus_score
    if bonus_matched:
        reasons.append(
            f"additional depth in {', '.join(bonus_matched[:3])}"
        )

    assessment_scores = signals.get("skill_assessment_scores", {})
    assessment_map    = [s.lower() for s in job.get("assessment_skill_map", [])]
    relevant_scores   = [
        v for k, v in assessment_scores.items()
        if k.lower() in assessment_map
    ]
    if relevant_scores:
        avg_assessment   = sum(relevant_scores) / len(relevant_scores)
        assessment_bonus = (avg_assessment / 100) * WEIGHTS["assessment"]
        score           += assessment_bonus
        reasons.append(
            f"verified platform assessments average {round(avg_assessment,1)}/100"
        )

    semantic_sim = 0.0
    if jd_vector is not None and vectorizer is not None:
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            clean_text       = deduplicate_text(full_text)
            candidate_vector = vectorizer.transform([clean_text])
            semantic_sim     = float(
                cosine_similarity(jd_vector, candidate_vector)[0][0]
            )
            semantic_score = semantic_sim * WEIGHTS["semantic"]
            score         += semantic_score
            if semantic_sim >= SEMANTIC_HIGH:
                reasons.append(
                    "career history closely aligns with Senior AI Engineer "
                    "requirements at a semantic level"
                )
            elif semantic_sim >= SEMANTIC_MEDIUM:
                reasons.append(
                    "career history shows moderate semantic overlap "
                    "with the role requirements"
                )
        except Exception:
            pass
    else:
        ai_keywords = [
            "embedding", "vector", "retrieval", "ranking",
            "nlp", "transformer", "fine-tun", "rag",
            "faiss", "elasticsearch", "pytorch", "tensorflow",
            "machine learning", "deep learning", "llm"
        ]
        hits       = sum(1 for kw in ai_keywords if kw in full_text)
        score     += min(5, hits * 0.5)
        semantic_sim = hits / len(ai_keywords)
        if hits >= 4:
            reasons.append(
                "career descriptions reference multiple AI/ML concepts "
                "relevant to this role"
            )
        elif hits >= 2:
            reasons.append(
                "career descriptions show some relevant AI/ML work"
            )

    return score, reasons, all_matched, missing, semantic_sim


def score_experience(
    years: float,
    job: Dict[str, Any],
) -> Tuple[float, List[str]]:
    min_exp = job.get("min_experience_years", MIN_EXPERIENCE_YEARS)
    max_exp = job.get("max_experience_years", MAX_EXPERIENCE_YEARS)
    reasons: List[str] = []

    if min_exp <= years <= max_exp:
        exp_score = float(WEIGHTS["experience"])
        reasons.append(
            f"{years} years of experience squarely within "
            f"the {min_exp}–{max_exp} year sweet spot"
        )
    elif years > 12:
        exp_score = 5.0
        reasons.append(
            f"{years} years of experience — may be overqualified "
            f"for this role level"
        )
    elif years > max_exp:
        exp_score = 10.0
        reasons.append(f"{years} years of experience (slightly above ideal range)")
    elif years >= min_exp - 1:
        exp_score = 8.0
        reasons.append(f"{years} years of experience (slightly below ideal range)")
    else:
        exp_score = 3.0
        reasons.append(f"{years} years of experience (below required minimum)")

    return exp_score, reasons


def score_title(
    current_title: str,
    job: Dict[str, Any],
) -> Tuple[float, List[str]]:
    """
    Tiered title scoring.
    Tier 1 (15 pts): Core AI/ML roles — strongest alignment.
    Tier 2 (12 pts): Related data/science roles — good alignment.
    Tier 3 (7 pts):  Generic tech roles — adjacent alignment.
    """
    reasons: List[str] = []
    tiered = job.get("tiered_titles", {})

    for title in tiered.get("tier_1", []):
        if title.lower() in current_title:
            reasons.append(
                f"current role as {fix_title_caps(current_title)} "
                f"directly matches the target function"
            )
            return 15.0, reasons

    for title in tiered.get("tier_2", []):
        if title.lower() in current_title:
            reasons.append(
                f"current role as {fix_title_caps(current_title)} "
                f"is closely adjacent to the target function"
            )
            return 12.0, reasons

    for title in tiered.get("tier_3", []):
        if title.lower() in current_title:
            reasons.append(
                f"current role as {fix_title_caps(current_title)} "
                f"is a technical role but not AI-specific"
            )
            return 7.0, reasons

    reasons.append(
        f"current role as {fix_title_caps(current_title)} "
        f"does not closely match the target function"
    )
    return 0.0, reasons


def score_career(
    career: List[Dict],
    consulting_firms: List[str],
    education: List[Dict],
    full_text: str,
    consulting_ratio: float,
) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    score = 0.0

    product_roles = 0
    for job_entry in career:
        company       = job_entry.get("company", "").lower()
        title         = job_entry.get("title", "").lower()
        industry      = job_entry.get("industry", "").lower()
        is_consulting  = any(firm in company for firm in consulting_firms)
        is_it_services = "it service" in industry or "outsourc" in industry
        is_tech_role   = any(
            t in title for t in
            ["engineer", "scientist", "developer", "researcher", "architect"]
        )
        if not is_consulting and not is_it_services and is_tech_role:
            product_roles += 1

    if product_roles >= 3:
        score += WEIGHTS["career"]
        reasons.append(
            "career demonstrates sustained product-company engineering "
            "experience relevant to a startup AI role"
        )
    elif product_roles >= 1:
        score += 5
        reasons.append(
            "career includes some product-company engineering experience"
        )
    else:
        reasons.append(
            "career history does not show clear product-company "
            "engineering trajectory"
        )

    if education and isinstance(education, list):
        tiers = [edu.get("tier", "") for edu in education]
        if "tier_1" in tiers:
            score += WEIGHTS["education"]
            inst = next(
                (edu.get("institution", "") for edu in education
                 if edu.get("tier") == "tier_1"), ""
            )
            reasons.append(f"Tier-1 institution ({inst})")

    return score, reasons


def score_location(
    country: str,
    location: str,
) -> Tuple[float, List[str]]:
    preferred_cities = [
        "pune", "noida", "delhi", "hyderabad", "mumbai",
        "bangalore", "bengaluru", "chennai", "gurugram", "gurgaon"
    ]
    if country == "india" or any(
        city in location for city in preferred_cities
    ):
        return float(WEIGHTS["location"]), [
            "location aligns with the hiring preference for Pune/Noida area"
        ]
    return 0.0, []


def score_signals(
    signals: Dict[str, Any],
    job: Dict[str, Any],
) -> Tuple[float, List[str]]:
    signal_score = 0.0
    reasons: List[str] = []

    completeness = signals.get("profile_completeness_score", 0)
    if completeness >= PROFILE_COMPLETE_STRONG:
        signal_score += 2
        reasons.append(f"complete platform profile ({completeness}%)")
    elif completeness < PROFILE_COMPLETE_WEAK:
        signal_score -= 1

    signup = signals.get("signup_date", "")
    if signup:
        try:
            signup_date = datetime.fromisoformat(signup.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - signup_date).days > PLATFORM_TENURE_DAYS:
                signal_score += 0.5
        except Exception:
            pass

    last_active = signals.get("last_active_date", "")
    if last_active:
        try:
            last_date     = datetime.fromisoformat(
                last_active.replace("Z", "+00:00")
            )
            days_inactive = (datetime.now(timezone.utc) - last_date).days
            if days_inactive <= RECENCY_VERY_ACTIVE_DAYS:
                signal_score += 4
                reasons.append("active on platform within the last week")
            elif days_inactive <= RECENCY_ACTIVE_DAYS:
                signal_score += 3
                reasons.append("active on platform within the last month")
            elif days_inactive <= RECENCY_RECENT_DAYS:
                signal_score += 1
                reasons.append("active on platform within the last 3 months")
            else:
                signal_score -= 3
                reasons.append(
                    f"platform inactivity of {days_inactive} days "
                    f"suggests reduced availability"
                )
        except Exception:
            pass

    if signals.get("open_to_work_flag", False):
        signal_score += 3
        reasons.append("actively marked open to new opportunities")
    else:
        signal_score -= 2
        reasons.append("not currently marked as open to work")

    views = signals.get("profile_views_received_30d", 0)
    if views >= VIEWS_HIGH:
        signal_score += 1
    elif views >= VIEWS_MEDIUM:
        signal_score += 0.5

    apps = signals.get("applications_submitted_30d", 0)
    if apps >= APPS_VERY_ACTIVE:
        signal_score += 1.5
        reasons.append("very actively applying to roles")
    elif apps >= APPS_ACTIVE:
        signal_score += 0.5
        reasons.append("actively applying to roles")

    rr = signals.get("recruiter_response_rate", 0)
    signal_score += round(rr * 3, 1)
    if rr >= RESPONSE_RATE_HIGH:
        reasons.append(
            f"strong recruiter engagement history ({int(rr*100)}% response rate)"
        )
    elif rr < RESPONSE_RATE_LOW:
        reasons.append(
            f"low recruiter response rate ({int(rr*100)}%) is a concern"
        )
    else:
        reasons.append(f"moderate recruiter response rate ({int(rr*100)}%)")

    avg_rt = signals.get("avg_response_time_hours", 999)
    if avg_rt <= 24:
        signal_score += 1
        reasons.append("responds to recruiter outreach within 24 hours")
    elif avg_rt >= 120:
        signal_score -= 1

    conn = signals.get("connection_count", 0)
    if conn >= CONNECTIONS_STRONG:
        signal_score += 1
    elif conn >= CONNECTIONS_MODERATE:
        signal_score += 0.5

    end = signals.get("endorsements_received", 0)
    if end >= ENDORSEMENTS_STRONG:
        signal_score += 1
        reasons.append(
            f"well-regarded on platform with {end} endorsements"
        )
    elif end >= ENDORSEMENTS_MODERATE:
        signal_score += 0.5

    notice = signals.get("notice_period_days", 90)
    if notice == NOTICE_IMMEDIATE:
        signal_score += 2
        reasons.append("immediately available to join")
    elif notice <= NOTICE_SHORT:
        signal_score += 1.5
        reasons.append(f"available within {notice} days")
    elif notice > NOTICE_LONG:
        signal_score -= 1.5
        reasons.append(
            f"notice period of {notice} days may delay onboarding"
        )

    salary_range = signals.get("expected_salary_range_inr_lpa", {})
    salary_max   = salary_range.get("max", 0)
    budget_max   = job.get("salary_budget_max_lpa", SALARY_BUDGET_MAX_LPA)
    if salary_max > 0:
        if salary_max <= budget_max * SALARY_WITHIN_RATIO:
            signal_score += 1
            reasons.append("salary expectation is well within budget")
        elif salary_max > budget_max * SALARY_ABOVE_RATIO:
            signal_score -= 1
            reasons.append(
                f"salary expectation ({salary_max} LPA max) "
                f"exceeds the role budget"
            )

    if signals.get("preferred_work_mode", "") in [
        "onsite", "hybrid", "flexible"
    ]:
        signal_score += 0.5

    if signals.get("willing_to_relocate", False):
        signal_score += 1
        reasons.append("willing to relocate for the role")

    github = signals.get("github_activity_score", -1)
    if github >= GITHUB_STRONG:
        signal_score += 2
        reasons.append(
            f"active open-source contributor (GitHub score: {github})"
        )
    elif github >= GITHUB_MODERATE:
        signal_score += 1
        reasons.append(f"moderate GitHub activity (score: {github})")
    elif github == -1:
        signal_score -= 0.5

    if signals.get("search_appearance_30d", 0) >= SEARCH_APPEARANCE_HIGH:
        signal_score += 0.5

    saved = signals.get("saved_by_recruiters_30d", 0)
    if saved >= RECRUITERS_SAVED_HIGH:
        signal_score += 1.5
        reasons.append(
            f"saved by {saved} other recruiters in the last 30 days — "
            f"strong market demand signal"
        )
    elif saved >= RECRUITERS_SAVED_LOW:
        signal_score += 0.5

    ir = signals.get("interview_completion_rate", 1)
    if ir >= INTERVIEW_RATE_GOOD:
        signal_score += 1
    elif ir < INTERVIEW_RATE_POOR:
        signal_score -= 2
        reasons.append(
            f"low interview completion rate ({int(ir*100)}%) "
            f"suggests unreliable availability"
        )

    offer_rate = signals.get("offer_acceptance_rate", -1)
    if offer_rate >= OFFER_RATE_GOOD:
        signal_score += 1
        reasons.append("strong offer acceptance history")
    elif 0 <= offer_rate < OFFER_RATE_POOR:
        signal_score -= 1
        reasons.append("historically declines a high proportion of offers")

    if signals.get("verified_email", False):
        signal_score += 0.5
    if signals.get("verified_phone", False):
        signal_score += 0.5
    if signals.get("linkedin_connected", False):
        signal_score += 0.5

    return max(SIGNAL_MIN_SCORE, min(SIGNAL_MAX_SCORE, signal_score)), reasons


def get_score_breakdown(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    jd_vector: Any = None,
    vectorizer: Any = None,
) -> Dict[str, float]:
    """Single source of truth for score breakdown. Used by main.py and app.py."""
    profile          = candidate.get("profile", {})
    signals          = candidate.get("redrob_signals", {})
    career           = candidate.get("career_history", [])
    education        = candidate.get("education", [])
    current_title    = profile.get("current_title", "").lower()
    years_experience = profile.get("years_of_experience", 0)
    consulting_firms = job.get("consulting_firms", [])
    location         = profile.get("location", "").lower()
    country          = profile.get("country", "").lower()

    full_text = deduplicate_text(
        profile.get("summary", "").lower() + " " +
        profile.get("headline", "").lower() + " " +
        " ".join(j.get("description", "").lower() for j in career)
    )

    s_score, _, _, _, _ = score_skills(
        candidate, job, full_text, jd_vector, vectorizer
    )
    e_score, _  = score_experience(years_experience, job)
    t_score, _  = score_title(current_title, job)

    all_companies   = [j.get("company", "").lower() for j in career]
    consulting_jobs = sum(
        1 for c in all_companies
        if any(firm in c for firm in consulting_firms)
    )
    total_jobs       = len(all_companies) if all_companies else 1
    consulting_ratio = consulting_jobs / total_jobs

    c_score, _   = score_career(
        career, consulting_firms, education, full_text, consulting_ratio
    )
    l_score, _   = score_location(country, location)
    sig_score, _ = score_signals(signals, job)

    return {
        "Skills":     round(s_score, 1),
        "Experience": round(e_score, 1),
        "Title":      round(t_score, 1),
        "Career":     round(c_score, 1),
        "Location":   round(l_score, 1),
        "Signals":    round(sig_score, 1),
    }


def compare_candidates(
    a: Dict[str, Any],
    b: Dict[str, Any],
    job: Dict[str, Any],
    score_a: float,
    score_b: float,
    jd_vector: Any = None,
    vectorizer: Any = None,
) -> str:
    """Explains why candidate A outranked candidate B."""
    bd_a = get_score_breakdown(a, job, jd_vector, vectorizer)
    bd_b = get_score_breakdown(b, job, jd_vector, vectorizer)

    advantages:     List[str] = []
    disadvantages:  List[str] = []

    for section in bd_a:
        diff = bd_a[section] - bd_b[section]
        if diff >= 2:
            advantages.append(f"{section} (+{round(diff,1)} pts)")
        elif diff <= -2:
            disadvantages.append(f"{section} ({round(diff,1)} pts)")

    margin = round(score_a - score_b, 2)

    if advantages:
        msg = f"Rank #1 leads on: {'; '.join(advantages[:3])}."
        if disadvantages:
            msg += f" Lags on: {'; '.join(disadvantages[:2])}."
        msg += f" Total margin: {margin} pts."
        return msg

    return (
        f"Scores are very close (margin: {margin} pts). "
        f"Tie-broken by candidate ID."
    )


def score_candidate(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    jd_tfidf_vector: Any = None,
    tfidf_vectorizer: Any = None,
) -> Tuple[float, str]:
    """Main scoring function. Returns (raw_score, reason_string)."""
    score:   float      = 0.0
    reasons: List[str]  = []

    profile          = candidate.get("profile", {})
    signals          = candidate.get("redrob_signals", {})
    career           = candidate.get("career_history", [])
    education        = candidate.get("education", [])
    current_title    = profile.get("current_title", "").lower()
    years_experience = profile.get("years_of_experience", 0)
    consulting_firms = job.get("consulting_firms", [])
    location         = profile.get("location", "").lower()
    country          = profile.get("country", "").lower()

    full_text = deduplicate_text(
        profile.get("summary", "").lower() + " " +
        profile.get("headline", "").lower() + " " +
        " ".join(j.get("description", "").lower() for j in career)
    )

    is_honeypot, reason = detect_honeypot(candidate)
    if is_honeypot:
        return 0.0, f"Disqualified: synthetic profile detected — {reason}"

    for bad in job.get("avoid_titles", []):
        if bad.lower() in current_title:
            return 0.0, (
                f"Disqualified: {fix_title_caps(current_title)} is an "
                f"unrelated job function for this role"
            )

    if years_experience < MIN_YEARS_TO_QUALIFY:
        return 0.0, (
            f"Disqualified: {years_experience} years of experience is "
            f"insufficient for a Senior AI Engineer role"
        )

    for flag in job.get("junior_title_flags", []):
        if flag in current_title:
            return 0.0, (
                f"Disqualified: {fix_title_caps(current_title)} is a "
                f"junior-level role — this position requires senior experience"
            )

    all_companies   = [j.get("company", "").lower() for j in career]
    consulting_jobs = sum(
        1 for c in all_companies
        if any(firm in c for firm in consulting_firms)
    )
    total_jobs       = len(all_companies) if all_companies else 1
    consulting_ratio = consulting_jobs / total_jobs

    ai_core     = job.get("ai_core_terms", [])
    ai_evidence = sum(1 for kw in ai_core if kw in full_text)

    if consulting_ratio == 1.0 and ai_evidence < CONSULTING_AI_EVIDENCE_MIN:
        score -= CONSULTING_ALL_PENALTY
        reasons.append(
            "entire career at IT consulting firms with limited AI/ML "
            "work evidence — suggests managed services rather than "
            "product engineering background"
        )
    elif consulting_ratio == 1.0:
        score -= CONSULTING_ALL_WEAK_PENALTY
        reasons.append(
            "entire career at consulting firms, though AI work evidence exists"
        )
    elif consulting_ratio >= CONSULTING_MAJORITY_THRESHOLD:
        score -= CONSULTING_MAJORITY_PENALTY
        reasons.append("career is predominantly consulting-firm based")

    s_score, s_reasons, matched, missing, _ = score_skills(
        candidate, job, full_text, jd_tfidf_vector, tfidf_vectorizer
    )
    score += s_score
    reasons.extend(s_reasons)

    e_score, e_reasons = score_experience(years_experience, job)
    score += e_score
    reasons.extend(e_reasons)

    t_score, t_reasons = score_title(current_title, job)
    score += t_score
    reasons.extend(t_reasons)

    c_score, c_reasons = score_career(
        career, consulting_firms, education, full_text, consulting_ratio
    )
    score += c_score
    reasons.extend(c_reasons)

    l_score, l_reasons = score_location(country, location)
    score += l_score
    reasons.extend(l_reasons)

    sig_score, sig_reasons = score_signals(signals, job)
    score += sig_score
    reasons.extend(sig_reasons)

    return round(max(score, 0), 2), " | ".join(reasons)