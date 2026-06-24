import csv
import sys
import time
import subprocess
import jsonlines
from typing import Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from job_description import JOB
from scorer import (
    score_candidate, fix_title_caps, WEIGHTS,
    deduplicate_text
)

JD_TEXT = """
senior ai engineer embeddings vector database faiss elasticsearch
nlp information retrieval ranking sentence transformers pytorch tensorflow
machine learning deep learning llm fine-tuning rag semantic search
retrieval augmented generation dense retrieval hybrid search reranking
recommendation systems ann approximate nearest neighbour pinecone weaviate
qdrant milvus opensearch production deployment evaluation ndcg map
python code quality product company startup cross encoder learning to rank
xgboost neural ranking lora qlora peft bm25 hybrid retrieval
dense sparse fusion transformer architecture
"""


def get_confidence(
    matched_skills: List,
    semantic_sim: float,
    signals: Dict
) -> str:
    """
    Confidence requires strong skill evidence AND semantic alignment.
    Fix: High confidence now requires matched_skills >= 4.
    """
    completeness = signals.get("profile_completeness_score", 0)
    assessments  = signals.get("skill_assessment_scores", {})
    career_len   = 0  # will be passed separately if needed

    evidence = 0

    # Skills evidence — requires at least 4 for High
    if len(matched_skills) >= 6:
        evidence += 3
    elif len(matched_skills) >= 4:
        evidence += 2
    elif len(matched_skills) >= 2:
        evidence += 1

    # Semantic evidence
    if semantic_sim >= 0.15:
        evidence += 2
    elif semantic_sim >= 0.08:
        evidence += 1

    # Profile completeness
    if completeness >= 75:
        evidence += 2
    elif completeness >= 50:
        evidence += 1

    # Verified assessments
    if assessments:
        evidence += 1

    if evidence >= 7:
        return "High"
    elif evidence >= 4:
        return "Medium"
    else:
        return "Low"


def build_reasoning(
    candidate: Dict,
    title: str,
    years: float,
    matched_skills: List,
    missing_skills: List,
    signals: Dict,
    score: float,
    semantic_sim: float = 0.0
) -> str:
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

    strengths = []
    concerns  = []

    # Skill strengths
    if len(matched_skills) >= 5:
        top = ", ".join(matched_skills[:4])
        strengths.append(
            f"strong alignment across {len(matched_skills)} required "
            f"skills including {top}"
        )
    elif len(matched_skills) >= 3:
        strengths.append(
            f"{', '.join(matched_skills[:3])} background matches "
            f"core JD requirements"
        )
    elif len(matched_skills) >= 1:
        strengths.append(
            f"matched {len(matched_skills)} required skill(s): "
            f"{', '.join(matched_skills[:2])}"
        )

    if semantic_sim >= 0.15:
        strengths.append("career history shows strong semantic JD alignment")

    # Verified assessment
    rel_assessments = {
        k: v for k, v in assessment.items()
        if k.lower() in [
            s.lower() for s in JOB.get("assessment_skill_map", [])
        ]
    }
    if rel_assessments:
        best = max(rel_assessments, key=rel_assessments.get)
        strengths.append(
            f"verified {best} assessment: {rel_assessments[best]}/100"
        )

    # Availability
    if open_to_work and notice == 0:
        strengths.append("immediately available")
    elif open_to_work and notice <= 30:
        strengths.append(f"actively looking, {notice}-day notice")

    # Engagement — all checked independently
    if response_rate >= 0.75:
        strengths.append(f"highly responsive ({int(response_rate*100)}%)")
    if github >= 70:
        strengths.append(f"strong GitHub activity ({github})")
    if saved >= 5:
        strengths.append(f"saved by {saved} other recruiters")
    if offer_rate >= 0.7:
        strengths.append("strong offer acceptance history")

    # Education
    if education and isinstance(education, list):
        tiers = [edu.get("tier", "") for edu in education]
        if "tier_1" in tiers:
            inst = next(
                (edu.get("institution", "") for edu in education
                 if edu.get("tier") == "tier_1"), ""
            )
            strengths.append(f"Tier-1 education ({inst})")

    # Location
    if country and country.lower() == "india":
        strengths.append("location aligns with hiring preference")

    # Concerns
    if len(missing_skills) >= 8:
        concerns.append(f"missing {len(missing_skills)} of 14 required JD skills")
    elif len(matched_skills) == 0:
        concerns.append("no direct AI skill evidence found")

    if not open_to_work:
        concerns.append("not marked open to work")
    elif notice > 90:
        concerns.append(f"long notice period ({notice} days)")

    if response_rate < 0.25:
        concerns.append(f"low response rate ({int(response_rate*100)}%)")
    if interview_rate < 0.4:
        concerns.append("low interview completion rate")
    if 0 <= offer_rate < 0.3:
        concerns.append("historically declines offers")
    if years > 12:
        concerns.append(f"may be overqualified ({years} yrs)")
    if country and country.lower() != "india":
        concerns.append(
            f"based outside India ({location}) — relocation required"
        )

    # Build balanced output
    opening = f"{title_display} with {years} years of experience"
    if strengths and concerns:
        body = (
            f"Strengths: {'; '.join(strengths[:3])}. "
            f"Concerns: {'; '.join(concerns[:2])}."
        )
    elif strengths:
        body = f"{'; '.join(strengths[:4])}."
    else:
        body = f"Profile below threshold — concerns: {'; '.join(concerns[:3])}."

    return f"{opening}. {body}"


def run_ranking(candidates_path: str, output_path: str) -> None:
    start_time = time.time()
    print(f"Loading candidates from {candidates_path}...")
    print("Please wait — approximately 4 minutes on CPU...\n")

    all_candidates      = []
    all_candidate_texts = []

    with jsonlines.open(candidates_path) as reader:
        for candidate in reader:
            profile  = candidate.get("profile", {})
            career   = candidate.get("career_history", [])
            raw_text = (
                profile.get("summary", "").lower() + " " +
                profile.get("headline", "").lower() + " " +
                " ".join(s["name"].lower()
                          for s in candidate.get("skills", [])) + " " +
                " ".join(j.get("description", "").lower() for j in career)
            )
            all_candidate_texts.append(deduplicate_text(raw_text))
            all_candidates.append(candidate)

    total = len(all_candidates)
    print(f"Loaded {total:,} candidates.")

    print("Building TF-IDF semantic model...")
    vectorizer   = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    all_texts    = [deduplicate_text(JD_TEXT)] + all_candidate_texts
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    jd_vector    = tfidf_matrix[0]
    cand_vectors = tfidf_matrix[1:]
    semantic_scores = cosine_similarity(jd_vector, cand_vectors)[0]
    print("Semantic model ready.\n")

    print("Scoring candidates...")
    results               = []
    disqualified          = 0
    required_skills_lower = [s.lower() for s in JOB.get("required_skills", [])]

    for i, candidate in enumerate(all_candidates):
        score, raw_reasoning = score_candidate(
            candidate, JOB,
            jd_tfidf_vector=jd_vector,
            tfidf_vectorizer=vectorizer
        )

        profile  = candidate.get("profile", {})
        signals  = candidate.get("redrob_signals", {})
        skills   = candidate.get("skills", [])
        title    = profile.get("current_title", "")
        years    = profile.get("years_of_experience", 0)

        candidate_skills_lower = [s["name"].lower() for s in skills]
        matched_skills = [
            s for s in required_skills_lower if s in candidate_skills_lower
        ]
        missing_skills = [
            s for s in required_skills_lower if s not in candidate_skills_lower
        ]

        if score == 0:
            disqualified += 1

        sem_sim    = float(semantic_scores[i])
        confidence = get_confidence(matched_skills, sem_sim, signals)
        reasoning  = build_reasoning(
            candidate, title, years,
            matched_skills, missing_skills,
            signals, score, sem_sim
        )

        results.append({
            "candidate_id": candidate["candidate_id"],
            "name":         profile.get("anonymized_name", ""),
            "title":        title,
            "years":        years,
            "score":        score,
            "confidence":   confidence,
            "reasoning":    reasoning
        })

        if (i + 1) % 10000 == 0:
            print(f"  Processed {i+1:,} candidates...")

    print("\nSorting results...")
    results.sort(key=lambda x: (-x["score"], x["candidate_id"]))

    max_score   = results[0]["score"]  if results else 1
    min_score   = results[-1]["score"] if results else 0
    score_range = max_score - min_score if max_score != min_score else 1

    for r in results:
        r["normalized_score"] = round(
            (r["score"] - min_score) / score_range, 4
        )

    elapsed   = time.time() - start_time
    qualified = total - disqualified

    print(f"\nTotal        : {total:,}")
    print(f"Qualified    : {qualified:,}")
    print(f"Disqualified : {disqualified:,}")
    print(f"Runtime      : {elapsed:.1f}s ({elapsed/60:.1f} min)")

    print("\n========== TOP 10 CANDIDATES ==========\n")
    for i, r in enumerate(results[:10], 1):
        print(f"#{i}  {r['name']} [{r['confidence']} confidence]")
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
    print(f"\nTotal runtime: {elapsed:.1f}s")
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