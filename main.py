import csv
import sys
import time
import subprocess
import jsonlines
from typing import Dict, List, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from job_description import JOB
from config import (
    TFIDF_MAX_FEATURES, TFIDF_NGRAM_MIN, TFIDF_NGRAM_MAX,
    SEMANTIC_HIGH, SEMANTIC_MEDIUM, TOP_N_CANDIDATES
)
from scorer import (
    score_candidate, fix_title_caps, WEIGHTS,
    deduplicate_text, compare_candidates, get_confidence,
    get_confidence_reasons, get_matched_and_missing_skills
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

# Groups required skills into AI-specific capability buckets so reasoning
# can name *what kind* of gap exists (retrieval infra vs. modeling vs.
# frameworks) instead of a flat, generic skill list.
SKILL_CAPABILITY_GROUPS: Dict[str, List[str]] = {
    "vector & retrieval infrastructure": [
        "faiss", "elasticsearch", "vector database", "information retrieval", "ranking"
    ],
    "modeling & deep learning": [
        "machine learning", "deep learning", "embeddings", "sentence-transformers"
    ],
    "LLM & NLP tooling": [
        "nlp", "llm", "pytorch", "tensorflow"
    ],
}


def group_missing_by_capability(missing_skills: List[str]) -> List[str]:
    """Turn a flat list of missing skill slugs into capability-group phrases,
    e.g. ['no evidence of vector & retrieval infrastructure (FAISS, ranking)']."""
    missing_set = set(missing_skills)
    phrases: List[str] = []
    for group, members in SKILL_CAPABILITY_GROUPS.items():
        hit = [m for m in members if m in missing_set]
        if hit:
            phrases.append(f"{group} ({', '.join(s.title() for s in hit)})")
    return phrases


def build_reasoning(
    candidate: Dict[str, Any],
    title: str,
    years: float,
    matched_skills: List[str],
    missing_skills: List[str],
    signals: Dict[str, Any],
    score: float,
    semantic_sim: float = 0.0,
) -> str:
    """
    Build enterprise-quality reasoning string.
    Format: Strengths + Concerns, specific and factual.
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

    strengths: List[str] = []
    concerns:  List[str] = []

    # Technical strengths
    if len(matched_skills) >= 5:
        top = ", ".join(matched_skills[:4])
        strengths.append(
            f"demonstrates production experience in dense retrieval, "
            f"vector search and modern LLM infrastructure — "
            f"{len(matched_skills)} of 14 required skills verified"
        )
    elif len(matched_skills) >= 3:
        top = ", ".join(matched_skills[:3])
        strengths.append(
            f"technical profile aligns with core JD requirements — "
            f"strong in {top}"
        )
    elif len(matched_skills) >= 1:
        strengths.append(
            f"partial technical alignment — "
            f"{', '.join(matched_skills[:2])} verified"
        )

    if semantic_sim >= SEMANTIC_HIGH:
        strengths.append(
            "career history closely matches the semantic profile "
            "of a Senior AI Engineer"
        )
    elif semantic_sim >= SEMANTIC_MEDIUM and len(matched_skills) < 3:
        strengths.append(
            "career text shows transferable engineering experience "
            "that overlaps with AI/ML work, even where exact skill "
            "tags are missing"
        )

    rel_assessments = {
        k: v for k, v in assessment.items()
        if k.lower() in [
            s.lower() for s in JOB.get("assessment_skill_map", [])
        ]
    }
    if rel_assessments:
        best = max(rel_assessments, key=rel_assessments.get)
        strengths.append(
            f"platform-verified {best} score of "
            f"{rel_assessments[best]}/100"
        )

    # Availability
    if open_to_work and notice == 0:
        strengths.append("immediately available to join")
    elif open_to_work and notice <= 30:
        strengths.append(
            f"actively seeking new opportunities with "
            f"{notice}-day notice period"
        )

    # Engagement signals — all checked independently
    if response_rate >= 0.75:
        strengths.append(
            f"strong recruiter engagement history "
            f"({int(response_rate*100)}% response rate)"
        )
    if github >= 70:
        strengths.append(
            f"active open-source contributor (GitHub score: {github})"
        )
    if saved >= 5:
        strengths.append(
            f"high market demand — saved by {saved} other recruiters "
            f"in the last 30 days"
        )
    if offer_rate >= 0.7:
        strengths.append("strong offer acceptance history")

    if education and isinstance(education, list):
        tiers = [edu.get("tier", "") for edu in education]
        if "tier_1" in tiers:
            inst = next(
                (edu.get("institution", "") for edu in education
                 if edu.get("tier") == "tier_1"), ""
            )
            strengths.append(f"Tier-1 institution background ({inst})")

    if country and country.lower() == "india":
        strengths.append(
            "India-based candidate — aligns with Pune/Noida "
            "hiring preference"
        )

    # Concerns
    if len(missing_skills) >= 8:
        capability_gaps = group_missing_by_capability(missing_skills)
        if capability_gaps:
            concerns.append(
                f"capability gaps in {'; '.join(capability_gaps[:2])} — "
                f"{len(missing_skills)} of 14 required skills unverified overall"
            )
        else:
            missing_sample = ", ".join(missing_skills[:3])
            concerns.append(
                f"limited evidence of production experience with "
                f"{missing_sample} and {len(missing_skills)-3} other "
                f"required skills"
            )
    elif len(matched_skills) == 0:
        concerns.append(
            "no direct AI/ML skill evidence found in profile "
            "or career history"
        )

    if not open_to_work:
        concerns.append(
            "not currently marked as open to work — "
            "recruiter outreach required"
        )
    elif notice > 90:
        concerns.append(
            f"notice period of {notice} days may delay onboarding "
            f"significantly"
        )

    if response_rate < 0.25:
        concerns.append(
            f"historically low recruiter response rate "
            f"({int(response_rate*100)}%) may complicate outreach"
        )
    if interview_rate < 0.4:
        concerns.append(
            f"low interview completion rate ({int(interview_rate*100)}%) "
            f"is a hiring risk"
        )
    if 0 <= offer_rate < 0.3:
        concerns.append(
            "candidate has historically declined a high proportion "
            "of offers — may require additional persuasion"
        )
    if years > 12:
        concerns.append(
            f"seniority level ({years} years) may be above "
            f"the target role grade"
        )
    if country and country.lower() != "india":
        concerns.append(
            f"candidate is based outside India ({location}) — "
            f"relocation required for Pune/Noida role"
        )

    # Build final reasoning
    opening = f"{title_display} with {years} years of experience"

    if strengths and concerns:
        body = (
            f"Strengths: {'; '.join(strengths[:3])}. "
            f"Concerns: {'; '.join(concerns[:2])}."
        )
    elif strengths:
        body = f"{'; '.join(strengths[:4])}."
    else:
        body = (
            f"Profile below threshold — "
            f"concerns: {'; '.join(concerns[:3])}."
        )

    return f"{opening}. {body}"


def run_ranking(candidates_path: str, output_path: str) -> None:
    start_time = time.time()
    print(f"Loading candidates from {candidates_path}...")
    print("Approximately 4 minutes on CPU...\n")

    all_candidates:      List[Dict] = []
    all_candidate_texts: List[str]  = []

    with jsonlines.open(candidates_path) as reader:
        for candidate in reader:
            profile = candidate.get("profile", {})
            career  = candidate.get("career_history", [])
            raw     = (
                profile.get("summary", "").lower() + " " +
                profile.get("headline", "").lower() + " " +
                " ".join(
                    s["name"].lower()
                    for s in candidate.get("skills", [])
                ) + " " +
                " ".join(
                    j.get("description", "").lower() for j in career
                )
            )
            all_candidate_texts.append(deduplicate_text(raw))
            all_candidates.append(candidate)

    total = len(all_candidates)
    print(f"Loaded {total:,} candidates.")

    print("Building TF-IDF semantic model...")
    vectorizer   = TfidfVectorizer(
        max_features=TFIDF_MAX_FEATURES,
        ngram_range=(TFIDF_NGRAM_MIN, TFIDF_NGRAM_MAX)
    )
    all_texts    = [deduplicate_text(JD_TEXT)] + all_candidate_texts
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    jd_vector    = tfidf_matrix[0]
    cand_vectors = tfidf_matrix[1:]
    semantic_scores = cosine_similarity(jd_vector, cand_vectors)[0]
    print("Semantic model ready.\n")

    print("Scoring candidates...")
    results:     List[Dict] = []
    disqualified = 0

    for i, candidate in enumerate(all_candidates):
        score, raw_reasoning = score_candidate(
            candidate, JOB,
            jd_tfidf_vector=jd_vector,
            tfidf_vectorizer=vectorizer
        )

        profile  = candidate.get("profile", {})
        signals  = candidate.get("redrob_signals", {})
        career   = candidate.get("career_history", [])
        title    = profile.get("current_title", "")
        years    = profile.get("years_of_experience", 0)

        full_text = deduplicate_text(
            profile.get("summary", "").lower() + " " +
            profile.get("headline", "").lower() + " " +
            " ".join(j.get("description", "").lower() for j in career)
        )
        matched_skills, missing_skills = get_matched_and_missing_skills(
            candidate, JOB, full_text
        )

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
            "reasoning":    reasoning,
            "_candidate":   candidate,
        })

        if (i + 1) % 10000 == 0:
            elapsed_so_far = time.time() - start_time
            print(
                f"  Processed {i+1:,} "
                f"({elapsed_so_far:.0f}s elapsed)..."
            )

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
    print(f"Runtime      : {elapsed:.1f}s (~{elapsed/60:.1f} min)")

    if len(results) >= 2:
        comparison = compare_candidates(
            results[0]["_candidate"],
            results[1]["_candidate"],
            JOB, results[0]["score"], results[1]["score"],
            jd_vector, vectorizer
        )
        print(f"\nTop-2 comparison: {comparison}")

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
        for rank, r in enumerate(results[:TOP_N_CANDIDATES], 1):
            writer.writerow([
                r["candidate_id"],
                rank,
                r["normalized_score"],
                r["reasoning"]
            ])
    print(f"{output_path} saved with top {TOP_N_CANDIDATES} candidates!")

    print("\nValidating format...")
    result = subprocess.run(
        ["python", "validate_submission.py", output_path],
        capture_output=True, text=True
    )
    print(result.stdout if result.stdout else result.stderr)
    print(f"\nTotal runtime: {elapsed:.1f}s (~{elapsed/60:.1f} min)")
    print("This system is deterministic — same input always produces same output.")
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