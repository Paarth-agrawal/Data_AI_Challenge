from datetime import datetime, timezone

# ── ACRONYM DICTIONARY ────────────────────────────────────────────────
ACRONYMS = {
    "ai": "AI", "ml": "ML", "nlp": "NLP", "llm": "LLM",
    "rag": "RAG", "api": "API", "sql": "SQL", "faiss": "FAISS",
    "mlops": "MLOps", "llmops": "LLMOps", "rlhf": "RLHF",
    "cuda": "CUDA", "bert": "BERT", "gpt": "GPT", "cv": "CV",
    "gpu": "GPU", "cpu": "CPU", "aws": "AWS", "gcp": "GCP",
}


def fix_title_caps(title):
    title_display = title.title()
    for word, replacement in ACRONYMS.items():
        title_display = title_display.replace(word.title(), replacement)
        title_display = title_display.replace(
            f"({word.title()})", f"({replacement})"
        )
    return title_display


# ── SKILL ALIAS MAP ───────────────────────────────────────────────────
# Catches semantic equivalents missed by exact matching
SKILL_ALIASES = {
    "faiss": ["ann", "approximate nearest neighbour",
               "vector retrieval", "approximate nearest neighbor"],
    "rag":   ["retrieval augmented generation", "dense retrieval",
               "retrieval-augmented"],
    "llm":   ["large language model", "gpt", "transformer model"],
    "embeddings": ["vector embeddings", "word embeddings",
                    "dense vectors", "embedding model"],
    "information retrieval": ["ir", "document retrieval",
                               "search engine", "semantic search"],
    "ranking": ["learning to rank", "reranking", "re-ranking",
                 "cross encoder", "pointwise ranking"],
    "vector database": ["vector store", "vector index",
                         "ann index", "embedding store"],
    "nlp":   ["natural language processing", "text processing",
               "language model", "text mining"],
}


def detect_honeypot(candidate):
    profile      = candidate.get("profile", {})
    career       = candidate.get("career_history", [])
    education    = candidate.get("education", [])
    current_year = datetime.now().year
    years_exp    = profile.get("years_of_experience", 0)

    # Fix: use max graduation year not first entry
    grad_year = 0
    if education and isinstance(education, list):
        grad_year = max(
            (edu.get("end_year", 0) or 0) for edu in education
        )

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

    # Fix: 48 month tolerance for freelancing/parallel work
    if career:
        total_months   = sum(j.get("duration_months", 0) for j in career)
        claimed_months = years_exp * 12
        if total_months > claimed_months + 48:
            return True, (
                f"Honeypot: career history ({total_months}mo) "
                f"far exceeds claimed exp ({claimed_months}mo)"
            )

    # Fix: only flag 20+ experts if under 8 years experience
    skills = candidate.get("skills", [])
    expert_count = sum(
        1 for s in skills
        if str(s.get("proficiency", "")).lower() in ["expert", "advanced"]
    )
    if expert_count >= 20 and years_exp < 8:
        return True, (
            "Honeypot: expert in 20+ skills with under 8 years experience"
        )

    return False, ""


def score_candidate(candidate, job, jd_tfidf_vector=None,
                    tfidf_vectorizer=None):
    score   = 0
    reasons = []

    # ── SETUP ─────────────────────────────────────────────────────────
    profile          = candidate.get("profile", {})
    signals          = candidate.get("redrob_signals", {})
    career           = candidate.get("career_history", [])
    skills           = candidate.get("skills", [])
    education        = candidate.get("education", [])
    current_title    = profile.get("current_title", "").lower()
    years_experience = profile.get("years_of_experience", 0)
    consulting_firms = job.get("consulting_firms", [])
    candidate_skills = [s["name"].lower() for s in skills]
    summary          = profile.get("summary", "").lower()
    headline         = profile.get("headline", "").lower()
    location         = profile.get("location", "").lower()
    country          = profile.get("country", "").lower()

    full_text = (
        summary + " " + headline + " " +
        " ".join(j.get("description", "").lower() for j in career)
    )

    # ── HONEYPOT CHECK ────────────────────────────────────────────────
    is_honeypot, honeypot_reason = detect_honeypot(candidate)
    if is_honeypot:
        return 0.0, f"Disqualified: {honeypot_reason}"

    # ── INSTANT DISQUALIFIERS ─────────────────────────────────────────
    for bad in job.get("avoid_titles", []):
        if bad.lower() in current_title:
            return 0.0, f"Disqualified: unrelated role ({current_title})"

    if years_experience < 2:
        return 0.0, f"Disqualified: too junior ({years_experience} yrs)"

    for flag in job.get("junior_title_flags", []):
        if flag in current_title:
            return 0.0, f"Disqualified: junior role ({current_title})"

    # ── CONSULTING PENALTY (not disqualification) ─────────────────────
    all_companies = [j.get("company", "").lower() for j in career]
    consulting_jobs = sum(
        1 for company in all_companies
        if any(firm in company for firm in consulting_firms)
    )
    total_jobs = len(all_companies) if all_companies else 1
    consulting_ratio = consulting_jobs / total_jobs

    # Only penalise if consulting AND weak AI evidence
    ai_evidence_count = sum(1 for kw in [
        "embedding", "retrieval", "ranking", "nlp", "transformer",
        "machine learning", "deep learning", "llm", "vector"
    ] if kw in full_text)

    if consulting_ratio == 1.0 and ai_evidence_count < 3:
        score -= 15
        reasons.append("Entire career at consulting firms — limited AI evidence")
    elif consulting_ratio == 1.0:
        score -= 7
        reasons.append("Entire career at consulting firms")
    elif consulting_ratio >= 0.5:
        score -= 4
        reasons.append("Primarily consulting background")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 1 — SKILL MATCH WITH ALIASES (35 points max)
    # ══════════════════════════════════════════════════════════════════

    required_skills = [s.lower() for s in job.get("required_skills", [])]
    matched = []
    alias_matched = []

    for skill in required_skills:
        if skill in candidate_skills:
            matched.append(skill)
        else:
            # Check aliases in full text
            aliases = SKILL_ALIASES.get(skill, [])
            if any(alias in full_text for alias in aliases):
                alias_matched.append(skill)

    all_matched = matched + alias_matched
    missing     = [s for s in required_skills if s not in all_matched]

    skill_score = (len(all_matched) / len(required_skills)) * 35
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
                f"{'; inferred: ' + ', '.join(alias_matched[:2]) if alias_matched else ''}"
            )
        else:
            reasons.append(f"Skills: {', '.join(matched[:5])}")

    if len(missing) >= 8:
        reasons.append(f"Missing {len(missing)} required JD skills")

    # Bonus skills (5 points max)
    bonus_skills  = [s.lower() for s in job.get("bonus_skills", [])]
    bonus_matched = [s for s in bonus_skills if s in candidate_skills]
    bonus_score   = min(5, len(bonus_matched) * 1.5)
    score        += bonus_score
    if bonus_matched:
        reasons.append(f"Bonus: {', '.join(bonus_matched[:3])}")

    # Skill assessment scores (5 points max)
    assessment_scores = signals.get("skill_assessment_scores", {})
    assessment_map    = [s.lower() for s in job.get("assessment_skill_map", [])]
    relevant_scores   = []
    for skill_name, score_val in assessment_scores.items():
        if skill_name.lower() in assessment_map:
            relevant_scores.append(score_val)
    if relevant_scores:
        avg_assessment   = sum(relevant_scores) / len(relevant_scores)
        assessment_bonus = (avg_assessment / 100) * 5
        score           += assessment_bonus
        reasons.append(f"Assessment avg: {round(avg_assessment, 1)}/100")

    # ── SEMANTIC SIMILARITY via TF-IDF (10 points max) ────────────────
    # Catches candidates whose descriptions show AI work
    # even without exact skill keywords
    if jd_tfidf_vector is not None and tfidf_vectorizer is not None:
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            candidate_vector = tfidf_vectorizer.transform([full_text])
            similarity = cosine_similarity(
                jd_tfidf_vector, candidate_vector
            )[0][0]
            semantic_score = similarity * 10
            score += semantic_score
            if similarity >= 0.15:
                reasons.append(
                    f"Strong semantic JD alignment ({round(similarity, 2)})"
                )
            elif similarity >= 0.08:
                reasons.append(
                    f"Moderate semantic JD alignment ({round(similarity, 2)})"
                )
        except Exception:
            pass
    else:
        # Fallback: keyword count in descriptions
        ai_keywords = [
            "embedding", "vector", "retrieval", "ranking", "recommendation",
            "nlp", "transformer", "fine-tun", "rag", "semantic search",
            "faiss", "elasticsearch", "pytorch", "tensorflow",
            "machine learning", "deep learning", "llm", "information retrieval"
        ]
        keyword_hits = sum(1 for kw in ai_keywords if kw in full_text)
        desc_bonus = min(5, keyword_hits * 0.5)
        score += desc_bonus
        if keyword_hits >= 4:
            reasons.append("Strong AI work in career descriptions")
        elif keyword_hits >= 2:
            reasons.append("Some AI work in career descriptions")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2 — EXPERIENCE (15 points max)
    # ══════════════════════════════════════════════════════════════════

    min_exp = job.get("min_experience_years", 5)
    max_exp = job.get("max_experience_years", 9)

    if min_exp <= years_experience <= max_exp:
        exp_score = 15
    elif years_experience > 12:
        exp_score = 5
        reasons.append(f"Overqualified: {years_experience} yrs")
    elif years_experience > max_exp:
        exp_score = 10
    elif years_experience >= min_exp - 1:
        exp_score = 8
    else:
        exp_score = 3
    score += exp_score

    if "Overqualified" not in " ".join(reasons):
        reasons.append(f"{years_experience} yrs experience")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3 — JOB TITLE (15 points max)
    # ══════════════════════════════════════════════════════════════════

    title_matched = False
    for good in job.get("preferred_titles", []):
        if good.lower() in current_title:
            score += 15
            reasons.append(f"Strong title: {current_title}")
            title_matched = True
            break

    if not title_matched:
        reasons.append(f"Title: {current_title}")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 4 — CAREER QUALITY (10 points max)
    # ══════════════════════════════════════════════════════════════════

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
        score += 10
        reasons.append("Strong product company history")
    elif product_roles >= 1:
        score += 5
        reasons.append("Some product company experience")

    # Education tier bonus (3 points max)
    if education and isinstance(education, list):
        tiers = [edu.get("tier", "") for edu in education]
        if "tier_1" in tiers:
            score += 3
            inst = next(
                (edu.get("institution", "") for edu in education
                 if edu.get("tier") == "tier_1"), ""
            )
            reasons.append(f"Tier-1 institution ({inst})")
        elif "tier_2" in tiers:
            score += 1

    # ══════════════════════════════════════════════════════════════════
    # SECTION 5 — LOCATION (bonus only, never penalty)
    # ══════════════════════════════════════════════════════════════════

    preferred_cities = [
        "pune", "noida", "delhi", "hyderabad", "mumbai",
        "bangalore", "bengaluru", "chennai", "gurugram", "gurgaon"
    ]
    if country == "india" or any(city in location for city in preferred_cities):
        score += 2
        reasons.append("India-based")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 6 — ALL 23 BEHAVIORAL SIGNALS (20 points max)
    # ══════════════════════════════════════════════════════════════════

    signal_score = 0

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
            days_on    = (datetime.now(timezone.utc) - signup_date).days
            if days_on > 180:
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

    applications = signals.get("applications_submitted_30d", 0)
    if applications >= 5:
        signal_score += 1.5
        reasons.append("Very actively applying")
    elif applications >= 1:
        signal_score += 0.5

    response_rate = signals.get("recruiter_response_rate", 0)
    signal_score += round(response_rate * 3, 1)
    if response_rate >= 0.7:
        reasons.append(f"High response rate ({int(response_rate*100)}%)")
    elif response_rate < 0.3:
        reasons.append(f"Low response rate ({int(response_rate*100)}%)")
    else:
        reasons.append(f"Response rate: {int(response_rate*100)}%")

    avg_response = signals.get("avg_response_time_hours", 999)
    if avg_response <= 24:
        signal_score += 1
        reasons.append("Fast responder")
    elif avg_response >= 120:
        signal_score -= 1

    connections = signals.get("connection_count", 0)
    if connections >= 500:
        signal_score += 1
    elif connections >= 300:
        signal_score += 0.5

    endorsements = signals.get("endorsements_received", 0)
    if endorsements >= 30:
        signal_score += 1
        reasons.append(f"Well endorsed ({endorsements})")
    elif endorsements >= 15:
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

    salary_info = signals.get("expected_salary_range_inr_lpa", {})
    salary_min  = salary_info.get("min", 0)
    budget_max  = job.get("salary_budget_max_lpa", 40)
    if salary_min > budget_max:
        signal_score -= 2
        reasons.append(f"Above budget (expects {salary_min}+ LPA)")

    work_mode = signals.get("preferred_work_mode", "")
    if work_mode in ["onsite", "hybrid", "flexible"]:
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

    interview_rate = signals.get("interview_completion_rate", 1)
    if interview_rate >= 0.8:
        signal_score += 1
    elif interview_rate < 0.4:
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

    signal_score = max(-5, min(20, signal_score))
    score       += signal_score

    return round(max(score, 0), 2), " | ".join(reasons)