import json
import csv
import subprocess
import jsonlines
from job_description import JOB
from scorer import score_candidate

def build_reasoning(title, years, matched_skills, signals, score):
    """
    Build a human-readable 1-2 sentence reasoning string.
    Uses data directly passed in — no recomputation.
    """
    # Fix title capitalisation properly
    title_display = title.title()
    title_display = title_display.replace(" Ai", " AI").replace("Ai ", "AI ")
    title_display = title_display.replace(" Ml", " ML").replace("Ml ", "ML ")
    title_display = title_display.replace("Nlp", "NLP").replace("Llm", "LLM")
    title_display = title_display.replace("(Ml)", "(ML)").replace("(Ai)", "(AI)")

    open_to_work  = signals.get("open_to_work_flag", False)
    notice        = signals.get("notice_period_days", 90)
    response_rate = signals.get("recruiter_response_rate", 0)
    github        = signals.get("github_activity_score", -1)

    parts = []

    # Skills sentence
    if matched_skills:
        top_skills = ", ".join(matched_skills[:3])
        parts.append(f"strong {top_skills} background directly matches JD requirements")

    # Availability
    if open_to_work and notice <= 30:
        parts.append(f"actively looking with {notice}-day notice period")
    elif open_to_work:
        parts.append("actively open to opportunities")
    else:
        parts.append("not currently marked as open to work — may need outreach")

    # Positive signals
    if response_rate >= 0.7:
        parts.append(f"high recruiter response rate ({int(response_rate*100)}%)")
    elif response_rate < 0.3:
        parts.append(f"low response rate ({int(response_rate*100)}%) is a concern")

    if github >= 60:
        parts.append(f"active GitHub presence (score: {github})")

    # Build final string
    opening   = f"{title_display} with {years} years of experience"
    body      = "; ".join(parts[:3])
    reasoning = f"{opening}; {body}."

    # Honest concerns
    if years > 12:
        reasoning += f" Note: {years} years experience may be overqualified for this role."
    elif score < 50:
        reasoning += " Profile is adjacent to requirements but below ideal fit threshold."

    return reasoning


# ── LOAD AND SCORE ────────────────────────────────────────────────────
print("Loading and scoring all candidates...")
print("This will take 2-4 minutes. Please wait...\n")

results               = []
disqualified          = 0
total                 = 0
required_skills_lower = [s.lower() for s in JOB.get("required_skills", [])]

with jsonlines.open("candidates.jsonl") as reader:
    for candidate in reader:
        total += 1

        score, raw_reasoning = score_candidate(candidate, JOB)

        profile  = candidate.get("profile", {})
        signals  = candidate.get("redrob_signals", {})
        skills   = candidate.get("skills", [])
        title    = profile.get("current_title", "")
        years    = profile.get("years_of_experience", 0)

        # Compute matched skills once — used in reasoning
        candidate_skills_lower = [s["name"].lower() for s in skills]
        matched_skills = [
            s for s in required_skills_lower
            if s in candidate_skills_lower
        ]

        if score == 0:
            disqualified += 1

        reasoning = build_reasoning(title, years, matched_skills, signals, score)

        results.append({
            "candidate_id": candidate["candidate_id"],
            "name":         profile.get("anonymized_name", ""),
            "title":        title,
            "years":        years,
            "score":        score,
            "reasoning":    reasoning
        })

        if total % 10000 == 0:
            print(f"  Processed {total:,} candidates...")

# ── SORT ──────────────────────────────────────────────────────────────
print("\nSorting results...")
results.sort(key=lambda x: x["score"], reverse=True)

qualified = total - disqualified
print(f"\nTotal candidates : {total:,}")
print(f"Disqualified     : {disqualified:,}")
print(f"Qualified        : {qualified:,}")

# ── PRINT TOP 10 ──────────────────────────────────────────────────────
print("\n========== TOP 10 CANDIDATES ==========\n")
for i, r in enumerate(results[:10], 1):
    print(f"#{i}  {r['name']}")
    print(f"     Title    : {r['title']}")
    print(f"     Score    : {r['score']}")
    print(f"     Reasoning: {r['reasoning']}")
    print()

# ── SAVE CSV ──────────────────────────────────────────────────────────
print("Saving submission.csv...")
with open("submission.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["candidate_id", "rank", "score", "reasoning"])
    for rank, r in enumerate(results[:100], 1):
        writer.writerow([
            r["candidate_id"],
            rank,
            r["score"],
            r["reasoning"]
        ])

print("submission.csv saved!")

# ── AUTO VALIDATE ─────────────────────────────────────────────────────
print("\nValidating format...")
result = subprocess.run(
    ["python", "validate_submission.py", "submission.csv"],
    capture_output=True, text=True
)
print(result.stdout if result.stdout else result.stderr)
print("\n===== DONE =====")