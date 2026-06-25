from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

ACRONYMS = {
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

WEIGHTS: Dict[str, int] = {
    "skills":     35,
    "assessment":  5,
    "bonus":       5,
    "semantic":   10,
    "experience": 15,
    "title":      15,
    "career":     10,
    "signals":    20,
    "location":    2,
    "education":   1,
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
    """Prevent TF-IDF exploitation — cap any word at 3 occurrences."""
    words  = text.split()
    counts: Dict[str, int] = {}
    result = []
    for word in words:
        counts[word] = counts.get(word, 0) + 1
        if counts[word] <= 3:
            result.append(word)
    return " ".join(result)


def detect_honeypot(candidate: Dict) -> Tuple[bool, str]:
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
        return True, f"Honeypot: graduation year {grad_year} is in the future"

    if grad_year and grad_year > 0:
        max_possible = current_year - grad_year
        if years_exp > max_possible + 2:
            return True, (
                f"Honeypot: {years_exp} yrs exp but graduated {grad_year}"
            )

    for job in career:
        founded    = job.get("company_founded_year", 0)
        start_year = job.get("start_year", 0)
        if founded and start_year and start_year < founded - 1:
            return True, "Honeypot: worked at company before it was founded"

    if career:
        total_months   = sum(j.get("duration_months", 0) for j in career)
        claimed_months = years_exp * 12
        if total_months > claimed_months + 48:
            return True, (
                f"Honeypot: career history ({total_months}mo) "
                f"far exceeds claimed exp ({claimed_months}mo)"
            )

    skills       = candidate.get("skills", [])
    expert_count = sum(
        1 for s in skills
        if str(s.get("proficiency", "")).lower() in ["expert", "advanced"]
    )
    endorsements      = signals.get("endorsements_received", 999)
    max_plausible_exp = max(10, int(years_exp * 2))

    if expert_count > max_plausible_exp and endorsements < 5:
        return True, (
            f"Honeypot: {expert_count} expert skills implausible "
            f"for {years_exp} yrs with {endorsements} endorsements"
        )

    return False, ""


def score_skills(
    candidate: Dict,
    job: Dict,
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
    reasons: List[str] = []

    matched = [s for s in required_skills if s in candidate_skills]
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
        reasons.append("No required skills matched")
    elif len(all_matched) == 1:
        score -= 5
        reasons.append(f"Only 1 skill matched: {all_matched[0]}")
    else:
        if alias_matched:
            reasons.append(
                f"Skills: {', '.join(matched[:4])}"
                f"; inferred: {', '.join(alias_matched[:2])}"
            )
        else:
            reasons.append(f"Skills: {', '.join(matched[:5])}")

    if len(missing) >= 8:
        reasons.append(f"Missing {len(missing)} required JD skills")

    bonus_skills  = [s.lower() for s in job.get("bonus_skills", [])]
    bonus_matched = [s for s in bonus_skills if s in candidate_skills]
    bonus_score   = min(WEIGHTS["bonus"], len(bonus_matched) * 1.5)
    score        += bonus_score
    if bonus_matched:
        reasons.append(f"Bonus: {', '.join(bonus_matched[:3])}")

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
        reasons.append(f"Assessment avg: {round(avg_assessment, 1)}/100")

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
            if semantic_sim >= 0.15:
                reasons.append(
                    f"Strong semantic JD alignment ({round(semantic_sim, 2)})"
                )
            elif semantic_sim >= 0.08:
                reasons.append(
                    f"Moderate semantic alignment ({round(semantic_sim, 2)})"
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
        hits         = sum(1 for kw in ai_keywords if kw in full_text)
        desc_bonus   = min(5, hits * 0.5)
        score       += desc_bonus
        semantic_sim = hits / len(ai_keywords)
        if hits >= 4:
            reasons.append("Strong AI work in career descriptions")
        elif hits >= 2:
            reasons.append("Some AI work in career descriptions")

    return score, reasons, all_matched, missing, semantic_sim


def score_experience(years: float, job: Dict) -> Tuple[float, List[str]]:
    min_exp = job.get("min_experience_years", 5)
    max_exp = job.get("max_experience_years", 9)
    reasons: List[str] = []

    if min_exp <= years <= max_exp:
        exp_score = float(WEIGHTS["experience"])
    elif years > 12:
        exp_score = 5.0
        reasons.append(f"Overqualified: {years} yrs")
    elif years > max_exp:
        exp_score = 10.0
    elif years >= min_exp - 1:
        exp_score = 8.0
    else:
        exp_score = 3.0

    if "Overqualified" not in " ".join(reasons):
        reasons.append(f"{years} yrs experience")

    return exp_score, reasons


def score_title(current_title: str, job: Dict) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    tiered = job.get("tiered_titles", {})

    for title in tiered.get("tier_1", []):
        if title.lower() in current_title:
            reasons.append(f"Strong AI title: {current_title}")
            return 15.0, reasons

    for title in tiered.get("tier_2", []):
        if title.lower() in current_title:
            reasons.append(f"Relevant title: {current_title}")
            return 12.0, reasons

    for title in tiered.get("tier_3", []):
        if title.lower() in current_title:
            reasons.append(f"Tech-adjacent title: {current_title}")
            return 7.0, reasons

    reasons.append(f"Title: {current_title}")
    return 0.0, reasons


def score_career(
    career: List,
    consulting_firms: List,
    education: List,
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
        reasons.append("Strong product company history")
    elif product_roles >= 1:
        score += 5
        reasons.append("Some product company experience")

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


def score_location(country: str, location: str) -> Tuple[float, List[str]]:
    preferred_cities = [
        "pune", "noida", "delhi", "hyderabad", "mumbai",
        "bangalore", "bengaluru", "chennai", "gurugram", "gurgaon"
    ]
    if country == "india" or any(city in location for city in preferred_cities):
        return float(WEIGHTS["location"]), ["Location aligns with hiring preference"]
    return 0.0, []


def score_signals(signals: Dict, job: Dict) -> Tuple[float, List[str]]:
    signal_score = 0.0
    reasons: List[str] = []

    completeness = signals.get("profile_completeness_score", 0)
    if completeness >= 80:
        signal_score += 2
        reasons.append(f"Complete profile ({completeness}%)")
    elif completeness < 50:
        signal_score -= 1

    signup = signals.get("signup_date", "")
    if signup:
        try:
            signup_date = datetime.fromisoformat(signup.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - signup_date).days > 180:
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
            if days_inactive <= 7:
                signal_score += 4
                reasons.append("Active this week")
            elif days_inactive <= 30:
                signal_score += 3
                reasons.append("Active this month")
            elif days_inactive <= 90:
                signal_score += 1
                reasons.append("Active last 3 months")
            else:
                signal_score -= 3
                reasons.append(f"Inactive {days_inactive} days")
        except Exception:
            pass

    if signals.get("open_to_work_flag", False):
        signal_score += 3
        reasons.append("Open to work")
    else:
        signal_score -= 2

    views = signals.get("profile_views_received_30d", 0)
    if views >= 20:
        signal_score += 1
    elif views >= 10:
        signal_score += 0.5

    apps = signals.get("applications_submitted_30d", 0)
    if apps >= 5:
        signal_score += 1.5
        reasons.append("Very actively applying")
    elif apps >= 1:
        signal_score += 0.5
        reasons.append("Actively applying")

    rr = signals.get("recruiter_response_rate", 0)
    signal_score += round(rr * 3, 1)
    if rr >= 0.7:
        reasons.append(f"High response rate ({int(rr*100)}%)")
    elif rr < 0.3:
        reasons.append(f"Low response rate ({int(rr*100)}%)")
    else:
        reasons.append(f"Response rate: {int(rr*100)}%")

    avg_rt = signals.get("avg_response_time_hours", 999)
    if avg_rt <= 24:
        signal_score += 1
        reasons.append("Fast responder")
    elif avg_rt >= 120:
        signal_score -= 1

    conn = signals.get("connection_count", 0)
    signal_score += 1 if conn >= 500 else (0.5 if conn >= 300 else 0)

    end = signals.get("endorsements_received", 0)
    if end >= 30:
        signal_score += 1
        reasons.append(f"Well endorsed ({end})")
    elif end >= 15:
        signal_score += 0.5

    notice = signals.get("notice_period_days", 90)
    if notice == 0:
        signal_score += 2
        reasons.append("Immediate joiner")
    elif notice <= 30:
        signal_score += 1.5
        reasons.append(f"Notice: {notice}d")
    elif notice > 90:
        signal_score -= 1.5
        reasons.append(f"Long notice: {notice}d")

    # Salary fit — small but realistic signal
    salary_range = signals.get("expected_salary_range_inr_lpa", {})
    salary_max   = salary_range.get("max", 0)
    budget_max   = job.get("salary_budget_max_lpa", 40)
    if salary_max > 0:
        if salary_max <= budget_max:
            signal_score += 1
            reasons.append("Salary within budget")
        elif salary_max <= budget_max * 1.2:
            pass  # Slightly above — neutral
        else:
            signal_score -= 1
            reasons.append(f"Salary above budget (max {salary_max} LPA)")

    if signals.get("preferred_work_mode", "") in ["onsite", "hybrid", "flexible"]:
        signal_score += 0.5

    if signals.get("willing_to_relocate", False):
        signal_score += 1
        reasons.append("Will relocate")

    github = signals.get("github_activity_score", -1)
    if github >= 70:
        signal_score += 2
        reasons.append(f"Active GitHub ({github})")
    elif github >= 40:
        signal_score += 1
        reasons.append(f"GitHub score: {github}")
    elif github == -1:
        signal_score -= 0.5

    if signals.get("search_appearance_30d", 0) >= 200:
        signal_score += 0.5

    saved = signals.get("saved_by_recruiters_30d", 0)
    if saved >= 5:
        signal_score += 1.5
        reasons.append(f"Saved by {saved} recruiters")
    elif saved >= 2:
        signal_score += 0.5

    ir = signals.get("interview_completion_rate", 1)
    if ir >= 0.8:
        signal_score += 1
    elif ir < 0.4:
        signal_score -= 2
        reasons.append("Low interview completion")

    offer_rate = signals.get("offer_acceptance_rate", -1)
    if offer_rate >= 0.7:
        signal_score += 1
        reasons.append("High offer acceptance")
    elif 0 <= offer_rate < 0.3:
        signal_score -= 1

    if signals.get("verified_email", False):
        signal_score += 0.5
    if signals.get("verified_phone", False):
        signal_score += 0.5
    if signals.get("linkedin_connected", False):
        signal_score += 0.5

    return max(-5, min(20, signal_score)), reasons


def get_score_breakdown(
    candidate: Dict,
    job: Dict,
    jd_vector: Any = None,
    vectorizer: Any = None,
) -> Dict[str, float]:
    """
    Returns detailed score breakdown per section.
    Used by both main.py and app.py — single source of truth.
    """
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

    c_score, _  = score_career(
        career, consulting_firms, education, full_text, consulting_ratio
    )
    l_score, _  = score_location(country, location)
    sig_score, _ = score_signals(signals, job)

    return {
        "Skills":    round(s_score, 1),
        "Experience": round(e_score, 1),
        "Title":     round(t_score, 1),
        "Career":    round(c_score, 1),
        "Location":  round(l_score, 1),
        "Signals":   round(sig_score, 1),
    }


def compare_candidates(
    a: Dict, b: Dict, job: Dict,
    score_a: float, score_b: float,
    jd_vector: Any = None,
    vectorizer: Any = None,
) -> str:
    """
    Explains why candidate A outranked candidate B.
    Used in Streamlit comparison mode.
    """
    bd_a = get_score_breakdown(a, job, jd_vector, vectorizer)
    bd_b = get_score_breakdown(b, job, jd_vector, vectorizer)

    differences = []
    for section in bd_a:
        diff = bd_a[section] - bd_b[section]
        if diff >= 2:
            differences.append(
                f"{section}: +{round(diff, 1)} pts advantage"
            )
        elif diff <= -2:
            differences.append(
                f"{section}: -{round(abs(diff), 1)} pts disadvantage"
            )

    if differences:
        return (
            f"Rank #1 leads because: {'; '.join(differences[:3])}. "
            f"Total margin: {round(score_a - score_b, 2)} pts."
        )
    return (
        f"Scores are very close ({round(score_a - score_b, 2)} pts margin). "
        f"Tie-broken by candidate ID."
    )

def get_confidence(
    matched_skills: List[str],
    semantic_sim: float,
    signals: Dict,
) -> str:
    """High confidence requires matched_skills >= 4 AND semantic evidence."""
    completeness = signals.get("profile_completeness_score", 0)
    assessments  = signals.get("skill_assessment_scores", {})
    evidence     = 0

    if len(matched_skills) >= 6:
        evidence += 3
    elif len(matched_skills) >= 4:
        evidence += 2
    elif len(matched_skills) >= 2:
        evidence += 1

    if semantic_sim >= 0.15:
        evidence += 2
    elif semantic_sim >= 0.08:
        evidence += 1

    if completeness >= 75:
        evidence += 2
    elif completeness >= 50:
        evidence += 1

    if assessments:
        evidence += 1

    if evidence >= 7:
        return "High"
    elif evidence >= 4:
        return "Medium"
    return "Low"

def score_candidate(
    candidate: Dict,
    job: Dict,
    jd_tfidf_vector: Any = None,
    tfidf_vectorizer: Any = None,
) -> Tuple[float, str]:

    score: float     = 0.0
    reasons: List[str] = []

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
        return 0.0, f"Disqualified: {reason}"

    for bad in job.get("avoid_titles", []):
        if bad.lower() in current_title:
            return 0.0, f"Disqualified: unrelated role ({current_title})"

    if years_experience < 2:
        return 0.0, f"Disqualified: too junior ({years_experience} yrs)"

    for flag in job.get("junior_title_flags", []):
        if flag in current_title:
            return 0.0, f"Disqualified: junior role ({current_title})"

    all_companies   = [j.get("company", "").lower() for j in career]
    consulting_jobs = sum(
        1 for c in all_companies
        if any(firm in c for firm in consulting_firms)
    )
    total_jobs       = len(all_companies) if all_companies else 1
    consulting_ratio = consulting_jobs / total_jobs

    ai_core     = job.get("ai_core_terms", [])
    ai_evidence = sum(1 for kw in ai_core if kw in full_text)

    if consulting_ratio == 1.0 and ai_evidence < 3:
        score -= 15
        reasons.append("Entire career consulting — limited AI evidence")
    elif consulting_ratio == 1.0:
        score -= 7
        reasons.append("Entire career at consulting firms")
    elif consulting_ratio >= 0.5:
        score -= 4
        reasons.append("Primarily consulting background")

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