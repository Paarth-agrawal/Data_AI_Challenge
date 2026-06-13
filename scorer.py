def score_candidate(candidate, job):
    score = 0
    reasons = []

    # 1. SKILL MATCH (40 points max)
    candidate_skills = [s["name"].lower() for s in candidate.get("skills", [])]
    matched_skills = []
    for required in job["required_skills"]:
        if required.lower() in candidate_skills:
            matched_skills.append(required)
    
    skill_score = (len(matched_skills) / len(job["required_skills"])) * 40
    score += skill_score
    if matched_skills:
        reasons.append(f"Matched skills: {', '.join(matched_skills)}")

    # 2. EXPERIENCE (30 points max)
    years = candidate["profile"].get("years_of_experience", 0)
    if years >= job["min_experience_years"]:
        exp_score = min(30, years * 2)
        score += exp_score
    reasons.append(f"{years} years of experience")

    # 3. JOB TITLE MATCH (20 points max)
    current_title = candidate["profile"].get("current_title", "").lower()
    for preferred in job["preferred_titles"]:
        if preferred.lower() in current_title:
            score += 20
            reasons.append(f"Relevant title: {current_title}")
            break
    
    # Penalty for wrong job functions
    for bad_title in job["avoid_titles"]:
        if bad_title.lower() in current_title:
            score -= 15
            reasons.append(f"Warning: unrelated title ({current_title})")

    # 4. BEHAVIORAL SIGNALS (10 points max)
    signals = candidate.get("redrob_signals", {})
    response_rate = signals.get("recruiter_response_rate", 0)
    signal_score = round(response_rate * 10, 2)
    score += signal_score
    reasons.append(f"Response rate: {response_rate}")

    # Return final score and reasoning
    return round(score, 2), " | ".join(reasons)