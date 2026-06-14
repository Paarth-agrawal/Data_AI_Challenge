from datetime import datetime, timezone

def score_candidate(candidate, job):
    score = 0
    reasons = []

    # ── SETUP: define everything first ────────────────────────────────
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    career  = candidate.get("career_history", [])
    skills  = candidate.get("skills", [])

    current_title    = profile.get("current_title", "").lower()
    years_experience = profile.get("years_of_experience", 0)
    consulting_firms = job.get("consulting_firms", [])
    candidate_skills = [s["name"].lower() for s in skills]

    # ── INSTANT DISQUALIFIERS (score = 0, stop immediately) ───────────

    # 1. Wrong job function — Accountant, HR, Marketing etc.
    for bad in job.get("avoid_titles", []):
        if bad.lower() in current_title:
            return 0.0, f"Disqualified: unrelated role ({current_title})"

    # 2. Entire career only at consulting firms
    all_companies = [j.get("company", "").lower() for j in career]
    if all_companies and all(
        any(firm in company for firm in consulting_firms)
        for company in all_companies
    ):
        return 0.0, "Disqualified: entire career at consulting firms"

    # 3. Less than 2 years experience — too junior
    if years_experience < 2:
        return 0.0, f"Disqualified: too junior ({years_experience} yrs)"

    # ── 1. SKILL MATCH (35 points max) ───────────────────────────────
    required_skills = [s.lower() for s in job.get("required_skills", [])]
    matched = [s for s in required_skills if s in candidate_skills]
    skill_score = (len(matched) / len(required_skills)) * 35
    score += skill_score

    if matched:
        reasons.append(f"Skills: {', '.join(matched[:5])}")
    else:
        reasons.append("No required skills matched")

    # Bonus skills (5 points max)
    bonus_skills = [s.lower() for s in job.get("bonus_skills", [])]
    bonus_matched = [s for s in bonus_skills if s in candidate_skills]
    bonus_score = min(5, len(bonus_matched) * 1.5)
    score += bonus_score
    if bonus_matched:
        reasons.append(f"Bonus: {', '.join(bonus_matched[:3])}")

    # ── 2. EXPERIENCE (20 points max) ────────────────────────────────
    min_exp = job.get("min_experience_years", 5)
    max_exp = job.get("max_experience_years", 9)

    if min_exp <= years_experience <= max_exp:
        exp_score = 20          # Sweet spot
    elif years_experience > max_exp:
        exp_score = 15          # Overqualified but still good
    elif years_experience >= min_exp - 1:
        exp_score = 12          # Slightly under but acceptable
    else:
        exp_score = 5           # Too junior
    score += exp_score
    reasons.append(f"{years_experience} yrs experience")

    # ── 3. JOB TITLE (15 points max) ─────────────────────────────────
    title_matched = False
    for good in job.get("preferred_titles", []):
        if good.lower() in current_title:
            score += 15
            reasons.append(f"Strong title: {current_title}")
            title_matched = True
            break

    if not title_matched:
        # Partial credit for generic engineering titles
        if any(t in current_title for t in ["engineer", "developer", "scientist"]):
            score += 5
            reasons.append(f"Tech title: {current_title}")

    # ── 4. CAREER QUALITY (10 points max) ────────────────────────────
    product_roles = 0
    for job_entry in career:
        company = job_entry.get("company", "").lower()
        title   = job_entry.get("title", "").lower()
        is_consulting = any(firm in company for firm in consulting_firms)
        is_tech_role  = any(t in title for t in ["engineer", "scientist", "developer", "researcher"])
        if not is_consulting and is_tech_role:
            product_roles += 1

    if product_roles >= 3:
        score += 10
        reasons.append("Strong product company history")
    elif product_roles >= 1:
        score += 5
        reasons.append("Some product company experience")

    # ── 5. BEHAVIORAL SIGNALS (15 points max) ────────────────────────

    # Open to work (most important signal)
    if signals.get("open_to_work_flag", False):
        score += 5
        reasons.append("Open to work")
    else:
        score -= 3

    # Recency — how recently active?
    last_active = signals.get("last_active_date", "")
    if last_active:
        try:
            last_date    = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            days_inactive = (datetime.now(timezone.utc) - last_date).days
            if days_inactive <= 14:
                score += 5
                reasons.append("Active this week")
            elif days_inactive <= 30:
                score += 4
                reasons.append("Active this month")
            elif days_inactive <= 90:
                score += 2
                reasons.append("Active last 3 months")
            else:
                score -= 4
                reasons.append(f"Inactive {days_inactive} days")
        except Exception:
            pass

    # Response rate
    response_rate = signals.get("recruiter_response_rate", 0)
    score += round(response_rate * 5, 1)
    reasons.append(f"Response rate: {int(response_rate * 100)}%")

    # Notice period (JD wants sub-30 days)
    notice = signals.get("notice_period_days", 90)
    if notice <= 30:
        score += 3
        reasons.append(f"Notice: {notice}d")
    elif notice > 60:
        score -= 2

    # GitHub activity
    github = signals.get("github_activity_score", -1)
    if github >= 60:
        score += 3
        reasons.append(f"GitHub: {github}")
    elif github >= 30:
        score += 1

    # Willing to relocate to Pune/Noida
    if signals.get("willing_to_relocate", False):
        score += 2
        reasons.append("Willing to relocate")

    # Interview completion — low rate is a red flag
    interview_rate = signals.get("interview_completion_rate", 1)
    if interview_rate < 0.4:
        score -= 3
        reasons.append("Low interview completion")

    return round(max(score, 0), 2), " | ".join(reasons)