from datetime import datetime, timezone

def detect_honeypot(candidate):
    """
    Only flag genuinely impossible profiles.
    Be conservative — better to miss a honeypot than disqualify a real candidate.
    """
    profile = candidate.get("profile", {})
    career  = candidate.get("career_history", [])
    skills  = candidate.get("skills", [])

    current_year  = datetime.now().year
    years_exp     = profile.get("years_of_experience", 0)
    grad_year     = profile.get("graduation_year", 0)

    # Check 1: Graduation year in the future
    if grad_year and grad_year > current_year:
        return True, f"Honeypot: graduation year {grad_year} is in the future"

    # Check 2: Experience impossible given graduation year
    # e.g. graduated 2022 but claims 15 years experience
    if grad_year and grad_year > 0:
        max_possible = current_year - grad_year
        if years_exp > max_possible + 2:
            return True, f"Honeypot: {years_exp} yrs exp but graduated {grad_year}"

    # Check 3: Worked at a company BEFORE it was founded
    for job in career:
        founded    = job.get("company_founded_year", 0)
        start_year = job.get("start_year", 0)
        if founded and start_year and start_year < founded - 1:
            return True, "Honeypot: worked at company before it was founded"

    # Check 4: Career history duration wildly exceeds claimed experience
    # Only flag if career months are MORE than 3 years beyond claimed
    if career:
        total_months  = sum(j.get("duration_months", 0) for j in career)
        claimed_months = years_exp * 12
        if total_months > claimed_months + 36:
            return True, f"Honeypot: career history ({total_months}mo) far exceeds claimed exp ({claimed_months}mo)"

    # Check 5: Expert in 20+ skills — truly impossible
    # (removed the 10+ check — 10 expert skills is realistic for senior engineers)
    expert_skills = [
        s for s in skills
        if str(s.get("proficiency", "")).lower() in ["expert", "advanced"]
    ]
    if len(expert_skills) >= 20:
        return True, "Honeypot: expert in 20+ skills simultaneously"

    return False, ""


def score_candidate(candidate, job):
    score   = 0
    reasons = []

    # ── SETUP ─────────────────────────────────────────────────────────
    profile          = candidate.get("profile", {})
    signals          = candidate.get("redrob_signals", {})
    career           = candidate.get("career_history", [])
    skills           = candidate.get("skills", [])
    current_title    = profile.get("current_title", "").lower()
    years_experience = profile.get("years_of_experience", 0)
    consulting_firms = job.get("consulting_firms", [])
    candidate_skills = [s["name"].lower() for s in skills]

    # ── HONEYPOT CHECK ────────────────────────────────────────────────
    is_honeypot, honeypot_reason = detect_honeypot(candidate)
    if is_honeypot:
        return 0.0, f"Disqualified: {honeypot_reason}"

    # ── INSTANT DISQUALIFIERS ─────────────────────────────────────────

    # 1. Completely unrelated job function
    for bad in job.get("avoid_titles", []):
        if bad.lower() in current_title:
            return 0.0, f"Disqualified: unrelated role ({current_title})"

    # 2. Entire career at consulting firms only
    all_companies = [j.get("company", "").lower() for j in career]
    if all_companies and all(
        any(firm in company for firm in consulting_firms)
        for company in all_companies
    ):
        return 0.0, "Disqualified: entire career at consulting firms"

    # 3. Less than 2 years experience
    if years_experience < 2:
        return 0.0, f"Disqualified: too junior ({years_experience} yrs)"

    # 4. Junior title
    for junior_flag in job.get("junior_title_flags", []):
        if junior_flag in current_title:
            return 0.0, f"Disqualified: junior level role ({current_title})"

    # ── 1. SKILL MATCH (50 points max) ───────────────────────────────
    required_skills = [s.lower() for s in job.get("required_skills", [])]
    matched         = [s for s in required_skills if s in candidate_skills]
    skill_score     = (len(matched) / len(required_skills)) * 50
    score          += skill_score

    if len(matched) == 0:
        score -= 15
        reasons.append("No required skills matched")
    elif len(matched) == 1:
        score -= 8
        reasons.append(f"Only 1 skill matched: {matched[0]}")
    else:
        reasons.append(f"Skills: {', '.join(matched[:5])}")

    # Bonus skills (5 points max)
    bonus_skills  = [s.lower() for s in job.get("bonus_skills", [])]
    bonus_matched = [s for s in bonus_skills if s in candidate_skills]
    bonus_score   = min(5, len(bonus_matched) * 1.5)
    score        += bonus_score
    if bonus_matched:
        reasons.append(f"Bonus: {', '.join(bonus_matched[:3])}")

    # ── 2. EXPERIENCE (15 points max) ────────────────────────────────
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
    if exp_score == 15:
        reasons.append(f"{years_experience} yrs experience")
    elif "Overqualified" not in " ".join(reasons):
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
        reasons.append(f"Title: {current_title}")

    # ── 4. CAREER QUALITY (10 points max) ────────────────────────────
    product_roles = 0
    for job_entry in career:
        company       = job_entry.get("company", "").lower()
        title         = job_entry.get("title", "").lower()
        is_consulting = any(firm in company for firm in consulting_firms)
        is_tech_role  = any(t in title for t in ["engineer", "scientist",
                                                   "developer", "researcher"])
        if not is_consulting and is_tech_role:
            product_roles += 1

    if product_roles >= 3:
        score += 10
        reasons.append("Strong product history")
    elif product_roles >= 1:
        score += 5
        reasons.append("Some product history")

    # ── 5. BEHAVIORAL SIGNALS (15 points max) ────────────────────────
    if signals.get("open_to_work_flag", False):
        score += 4
        reasons.append("Open to work")
    else:
        score -= 3

    last_active = signals.get("last_active_date", "")
    if last_active:
        try:
            last_date     = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
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

    response_rate = signals.get("recruiter_response_rate", 0)
    score        += round(response_rate * 4, 1)
    reasons.append(f"Response rate: {int(response_rate * 100)}%")

    notice = signals.get("notice_period_days", 90)
    if notice <= 30:
        score += 3
        reasons.append(f"Notice: {notice}d")
    elif notice > 60:
        score -= 2

    github = signals.get("github_activity_score", -1)
    if github >= 60:
        score += 3
        reasons.append(f"GitHub: {github}")
    elif github >= 30:
        score += 1

    if signals.get("willing_to_relocate", False):
        score += 2
        reasons.append("Will relocate")

    interview_rate = signals.get("interview_completion_rate", 1)
    if interview_rate < 0.4:
        score -= 3
        reasons.append("Low interview completion")

    return round(max(score, 0), 2), " | ".join(reasons)