import csv
import sys
import subprocess
import jsonlines
from job_description import JOB
from scorer import score_candidate, fix_title_caps


def build_reasoning(candidate, title, years, matched_skills,
                    missing_skills, signals, score):
    """
    Build specific honest reasoning with 5 points.
    Fix issue 8: all engagement signals shown independently.
    Fix issue 9: missing skills explicitly mentioned.
    Fix issue 10: acronym dictionary used for titles.
    """
    profile   = candidate.get("profile", {})
    career    = candidate.get("career_history", [])
    education = candidate.get("education", [])
    summary   = profile.get("summary", "")
    location  = profile.get("location", "")
    country   = profile.get("country", "")

    title_display  = fix_title_caps(title)
    open_to_work   = signals.get("open_to_work_flag", False)
    notice         = signals.get("notice_period_days", 90)
    response_rate  = signals.get("recruiter_response_rate", 0)
    github         = signals.get("github_activity_score", -1)
    saved          = signals.get("saved_by_recruiters_30d", 0)
    offer_rate     = signals.get("offer_acceptance_rate", -1)
    interview_rate = signals.get("interview_completion_rate", 1)
    assessment     = signals.get("skill_assessment_scores", {})

    parts = []

    # Part 1 — Skills (specific about depth AND gaps)
    if len(matched_skills) >= 5:
        top = ", ".join(matched_skills[:4])
        parts.append(
            f"strong alignment across {len(matched_skills)} required skills "
            f"including {top}"
        )
    elif len(matched_skills) >= 3:
        top = ", ".join(matched_skills[:3])
        parts.append(f"{top} background matches core JD requirements")
    elif len(matched_skills) >= 1:
        parts.append(
            f"partial skill match ({', '.join(matched_skills[:2])}); "
            f"missing {len(missing_skills)} required skills"
        )
    else:
        full_text = summary.lower()
        for j in career:
            full_text += j.get("description", "").lower()
        ai_terms = [
            "embedding", "retrieval", "ranking", "recommendation",
            "nlp", "vector", "transformer", "rag", "semantic"
        ]
        found_terms = [t for t in ai_terms if t in full_text]
        if found_terms:
            parts.append(
                f"no listed AI skills but career work references "
                f"{found_terms[0]} and related systems"
            )
        else:
            parts.append(
                f"no direct AI skill match; missing all "
                f"{len(missing_skills)} required JD skills"
            )

    # Part 2 — Verified assessment
    rel_assessments = {
        k: v for k, v in assessment.items()
        if k.lower() in [s.lower() for s in JOB.get("assessment_skill_map", [])]
    }
    if rel_assessments:
        best_skill = max(rel_assessments, key=rel_assessments.get)
        best_score = rel_assessments[best_skill]
        parts.append(f"verified {best_skill} assessment: {best_score}/100")

    # Part 3 — Availability
    if open_to_work and notice == 0:
        parts.append("immediately available")
    elif open_to_work and notice <= 30:
        parts.append(f"actively looking, {notice}-day notice")
    elif open_to_work:
        parts.append(f"open to work but {notice}-day notice period")
    else:
        parts.append("not marked open to work — outreach needed")

    # Part 4 — Fix issue 8: ALL engagement signals independently checked
    engagement_parts = []
    if response_rate >= 0.75:
        engagement_parts.append(
            f"highly responsive ({int(response_rate*100)}%)"
        )
    elif response_rate < 0.25:
        engagement_parts.append(
            f"low response rate ({int(response_rate*100)}%)"
        )
    if github >= 70:
        engagement_parts.append(f"strong GitHub activity ({github})")
    elif github >= 40:
        engagement_parts.append(f"moderate GitHub presence ({github})")
    if saved >= 5:
        engagement_parts.append(f"saved by {saved} other recruiters")
    if offer_rate >= 0.7:
        engagement_parts.append("strong offer acceptance history")
    elif 0 <= offer_rate < 0.3:
        engagement_parts.append("historically declines offers")

    if engagement_parts:
        parts.append("; ".join(engagement_parts[:2]))

    # Part 5 — Location and education
    if country and country.lower() != "india":
        parts.append(
            f"based outside India ({location}) — "
            f"relocation required for Pune/Noida role"
        )
    elif education and isinstance(education, list):
        tiers = [edu.get("tier", "") for edu in education]
        if "tier_1" in tiers:
            inst = next(
                (edu.get("institution", "") for edu in education
                 if edu.get("tier") == "tier_1"), ""
            )
            parts.append(f"Tier-1 education ({inst})")
        elif notice > 60:
            parts.append(
                f"notice period of {notice} days may delay joining"
            )
    elif notice > 60:
        parts.append(f"notice period of {notice} days may delay joining")

    # Build final reasoning with 5 parts
    opening   = f"{title_display} with {years} years of experience"
    body      = "; ".join(parts[:5])
    reasoning = f"{opening}; {body}."

    # Honest closing concerns
    if years > 12:
        reasoning += f" Seniority ({years} yrs) may be above role level."
    elif score < 30:
        reasoning += " Profile is below ideal fit threshold."
    elif interview_rate < 0.4:
        reasoning += " Low interview completion rate is a hiring risk."

    return reasoning


def run_ranking(candidates_path, output_path):
    print(f"Loading and scoring candidates from {candidates_path}...")
    print("Please wait — this takes 2-4 minutes...\n")

    results               = []
    disqualified          = 0
    total                 = 0
    required_skills_lower = [s.lower() for s in JOB.get("required_skills", [])]

    with jsonlines.open(candidates_path) as reader:
        for candidate in reader:
            total += 1
            score, raw_reasoning = score_candidate(candidate, JOB)

            profile  = candidate.get("profile", {})
            signals  = candidate.get("redrob_signals", {})
            skills   = candidate.get("skills", [])
            title    = profile.get("current_title", "")
            years    = profile.get("years_of_experience", 0)

            candidate_skills_lower = [s["name"].lower() for s in skills]
            matched_skills = [
                s for s in required_skills_lower
                if s in candidate_skills_lower
            ]
            missing_skills = [
                s for s in required_skills_lower
                if s not in candidate_skills_lower
            ]

            if score == 0:
                disqualified += 1

            reasoning = build_reasoning(
                candidate, title, years,
                matched_skills, missing_skills, signals, score
            )

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

    print("\nSorting results...")
    results.sort(key=lambda x: (-x["score"], x["candidate_id"]))

    max_score   = results[0]["score"]  if results else 1
    min_score   = results[-1]["score"] if results else 0
    score_range = max_score - min_score if max_score != min_score else 1

    for r in results:
        r["normalized_score"] = round(
            (r["score"] - min_score) / score_range, 4
        )

    qualified = total - disqualified
    print(f"\nTotal        : {total:,}")
    print(f"Qualified    : {qualified:,}")
    print(f"Disqualified : {disqualified:,}")
    print(
        f"Top score    : {results[0]['score']} "
        f"→ normalized: {results[0]['normalized_score']}"
    )

    print("\n========== TOP 10 CANDIDATES ==========\n")
    for i, r in enumerate(results[:10], 1):
        print(f"#{i}  {r['name']}")
        print(f"     Title    : {r['title']}")
        print(f"     Score    : {r['normalized_score']}")
        print(f"     Reasoning: {r['reasoning']}")
        print()

    print(f"Saving {output_path}...")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, r in enumerate(results[:100], 1):
            writer.writerow([
                r["candidate_id"],
                rank,
                r["normalized_score"],
                r["reasoning"]
            ])
    print(f"{output_path} saved!")

    print("\nValidating format...")
    result = subprocess.run(
        ["python", "validate_submission.py", output_path],
        capture_output=True, text=True
    )
    print(result.stdout if result.stdout else result.stderr)
    print("\n===== DONE =====")


if __name__ == "__main__":
    candidates_path = "candidates.jsonl"
    output_path     = "submission.csv"

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--candidates" and i + 1 < len(args):
            candidates_path = args[i + 1]
        if arg == "--out" and i + 1 < len(args):
            output_path = args[i + 1]

    run_ranking(candidates_path, output_path)