from datetime import datetime, timezone

def score_candidate(candidate, job):
    score = 0
    reasons = []

    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})

    # ── INSTANT DISQUALIFIERS ──────────────────────────────────────────
    # Consulting-only career (TCS, Infosys etc.) = disqualify
    consulting_firms = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini"]
    career = candidate.get("career_history", [])
    all_companies = [job.get("company", "").lower() for job in career]
    if all(any(firm in company for firm in consulting_firms) for company in all_companies) and len(all_companies) > 0:
        return 0.0, "Disqualified: entire career at consulting firms only"

    # Wrong job function (Marketing, HR, Sales etc.) = disqualify
    current_title = profile.get("current_title", "").lower()
    bad_functions = ["marketing", "hr ", "human resource", "sales", "graphic design", "content writer"]
    for bad in bad_functions:
        if bad in current_title:
            return 0.0, f"Disqualified: unrelated job function ({current_title})"

    # ── 1. SKILL MATCH (30 points) ────────────────────────────────────
    candidate_skills = [s["name"].lower() for s in candidate.get("skills", [])]
    
    # Core must-have skills from JD
    core_skills = ["python", "embeddings", "vector database", "faiss", "elasticsearch",
                   "nlp", "information retrieval", "ranking", "sentence-transformers",
                   "pytorch", "tensorflow", "machine learning", "deep learning"]
    
    matched = [s for s in core_skills if s in candidate_skills]
    skill_score = (len(matched) / len(core_skills)) * 30
    score += skill_score
    if matched:
        reasons.append(f"Core skills: {', '.join(matched[:4])}")
    else:
        reasons.append("No core skills matched")

    # Bonus for nice-to-have skills
    bonus_skills = ["lora", "qlora", "fine-tuning", "xgboost", "qdrant", "pinecone",
                    "weaviate", "milvus", "open-source", "llm"]
    bonus_matched = [s for s in bonus_skills if s in candidate_skills]
    bonus = min(5, len(bonus_matched) * 1.5)
    score += bonus
    if bonus_matched:
        reasons.append(f"Bonus skills: {', '.join(bonus_matched[:3])}")

    # ── 2. EXPERIENCE & CAREER QUALITY (25 points) ────────────────────
    years = profile.get("years_of_experience", 0)
    
    # Sweet spot is 5-9 years per JD
    if 5 <= years <= 9:
        exp_score = 25
    elif years >= 4:
        exp_score = 18
    elif years >= 3:
        exp_score = 10
    else:
        exp_score = 0
    score += exp_score
    reasons.append(f"{years} yrs experience")

    # Product company bonus (not consulting)
    product_titles = ["engineer", "scientist", "researcher", "developer", "architect"]
    product_experience = sum(
        1 for job in career
        if any(t in job.get("title", "").lower() for t in product_titles)
        and not any(firm in job.get("company", "").lower() for firm in consulting_firms)
    )
    if product_experience >= 2:
        score += 10
        reasons.append("Product company experience")

    # ── 3. JOB TITLE RELEVANCE (15 points) ───────────────────────────
    good_titles = ["ai engineer", "ml engineer", "machine learning", "data scientist",
                   "nlp engineer", "research engineer", "applied scientist"]
    for good in good_titles:
        if good in current_title:
            score += 15
            reasons.append(f"Strong title: {current_title}")
            break

    # ── 4. BEHAVIORAL SIGNALS (25 points) ────────────────────────────
    
    # open_to_work is critical
    if signals.get("open_to_work_flag", False):
        score += 8
        reasons.append("Actively looking")
    else:
        score -= 5
        reasons.append("Not marked open to work")

    # Recency — how recently were they active?
    last_active = signals.get("last_active_date", "")
    if last_active:
        try:
            last_date = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            days_inactive = (datetime.now(timezone.utc) - last_date).days
            if days_inactive <= 30:
                score += 8
                reasons.append("Active in last 30 days")
            elif days_inactive <= 90:
                score += 4
                reasons.append("Active in last 90 days")
            else:
                score -= 5
                reasons.append(f"Inactive for {days_inactive} days")
        except:
            pass

    # Response rate
    response_rate = signals.get("recruiter_response_rate", 0)
    score += round(response_rate * 5, 1)
    reasons.append(f"Response rate: {int(response_rate*100)}%")

    # Notice period (JD wants sub-30 days)
    notice = signals.get("notice_period_days", 90)
    if notice <= 30:
        score += 4
        reasons.append(f"Notice: {notice} days")
    elif notice > 60:
        score -= 3

    # GitHub activity (real engineers have it)
    github = signals.get("github_activity_score", -1)
    if github >= 50:
        score += 5
        reasons.append(f"GitHub active (score: {github})")
    elif github >= 20:
        score += 2

    # Willing to relocate to Pune/Noida
    if signals.get("willing_to_relocate", False):
        score += 2
        reasons.append("Willing to relocate")

    # Interview completion rate
    interview_rate = signals.get("interview_completion_rate", 0)
    if interview_rate < 0.5:
        score -= 3
        reasons.append("Low interview completion")

    return round(max(score, 0), 2), " | ".join(reasons)