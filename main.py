import csv
import sys
import subprocess
import jsonlines
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from job_description import JOB
from scorer import score_candidate, fix_title_caps

# ── JOB DESCRIPTION TEXT FOR SEMANTIC MATCHING ────────────────────────
JD_TEXT = """
Senior AI Engineer embeddings vector database FAISS elasticsearch
NLP information retrieval ranking sentence transformers PyTorch TensorFlow
machine learning deep learning LLM fine-tuning RAG semantic search
retrieval augmented generation dense retrieval hybrid search reranking
recommendation systems ANN approximate nearest neighbour Pinecone Weaviate
Qdrant Milvus OpenSearch production deployment evaluation NDCG MAP
Python strong code quality product company startup scrappy shipper
cross encoder learning to rank XGBoost neural ranking LoRA QLoRA
PEFT fine-tuning open source contributions
"""


def build_reasoning(candidate, title, years, matched_skills,
                    missing_skills, signals, score, semantic_sim=0.0):
    """
    Build strengths + concerns reasoning for each candidate.
    Fix: all engagement signals checked independently.
    Fix: explicit missing skills for weak candidates.
    Fix: balanced strengths AND concerns format.
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

    strengths = []
    concerns  = []

    # ── STRENGTHS ─────────────────────────────────────────────────────

    # Skill depth
    if len(matched_skills) >= 5:
        top = ", ".join(matched_skills[:4])
        strengths.append(
            f"strong alignment across {len(matched_skills)} required "
            f"skills including {top}"
        )
    elif len(matched_skills) >= 3:
        top = ", ".join(matched_skills[:3])
        strengths.append(f"{top} background matches core JD requirements")
    elif len(matched_skills) >= 1:
        strengths.append(
            f"matched {len(matched_skills)} required skill(s): "
            f"{', '.join(matched_skills[:2])}"
        )

    # Semantic similarity
    if semantic_sim >= 0.15:
        strengths.append(
            f"career history shows strong semantic alignment with JD "
            f"(similarity: {round(semantic_sim, 2)})"
        )

    # Verified assessments
    rel_assessments = {
        k: v for k, v in assessment.items()
        if k.lower() in [s.lower() for s in JOB.get("assessment_skill_map", [])]
    }
    if rel_assessments:
        best_skill = max(rel_assessments, key=rel_assessments.get)
        best_score = rel_assessments[best_skill]
        strengths.append(
            f"verified {best_skill} assessment: {best_score}/100"
        )

    # Availability
    if open_to_work and notice == 0:
        strengths.append("immediately available")
    elif open_to_work and notice <= 30:
        strengths.append(f"actively looking, {notice}-day notice")

    # Engagement — all checked independently
    if response_rate >= 0.75:
        strengths.append(
            f"highly responsive to recruiters ({int(response_rate*100)}%)"
        )
    if github >= 70:
        strengths.append(f"strong GitHub activity ({github})")
    if saved >= 5:
        strengths.append(f"saved by {saved} other recruiters recently")
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
            strengths.append(f"Tier-1 institution ({inst})")

    # Location
    if country and country.lower() == "india":
        strengths.append("India-based, matches role location")

    # ── CONCERNS ──────────────────────────────────────────────────────

    # Missing skills
    if len(missing_skills) >= 8:
        concerns.append(f"missing {len(missing_skills)} of 14 required JD skills")
    elif len(matched_skills) == 0:
        full_text = summary.lower()
        for j in career:
            full_text += j.get("description", "").lower()
        ai_terms = ["embedding", "retrieval", "ranking", "nlp", "vector"]
        found = [t for t in ai_terms if t in full_text]
        if not found:
            concerns.append("no direct AI skill evidence in profile or career")

    # Availability concerns
    if not open_to_work:
        concerns.append("not marked open to work — outreach needed")
    elif notice > 90:
        concerns.append(f"long notice period ({notice} days)")

    # Engagement concerns
    if response_rate < 0.25:
        concerns.append(
            f"low recruiter response rate ({int(response_rate*100)}%)"
        )
    if interview_rate < 0.4:
        concerns.append("low interview completion rate")
    if 0 <= offer_rate < 0.3:
        concerns.append("historically declines offers")

    # Experience concerns
    if years > 12:
        concerns.append(f"may be overqualified ({years} yrs)")

    # Location concern
    if country and country.lower() != "india":
        concerns.append(
            f"based outside India ({location}) — relocation required"
        )

    # ── BUILD FINAL REASONING ─────────────────────────────────────────
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


def run_ranking(candidates_path, output_path):
    print(f"Loading and scoring candidates from {candidates_path}...")
    print("Please wait — this takes 2-4 minutes...\n")

    # ── STEP 1: Build TF-IDF semantic model from all candidate texts ──
    print("Building semantic similarity model...")
    all_candidate_texts = []
    all_candidates      = []

    with jsonlines.open(candidates_path) as reader:
        for candidate in reader:
            profile = candidate.get("profile", {})
            career  = candidate.get("career_history", [])
            summary = profile.get("summary", "").lower()
            headline = profile.get("headline", "").lower()
            skills_text = " ".join(
                s["name"].lower() for s in candidate.get("skills", [])
            )
            desc_text = " ".join(
                j.get("description", "").lower() for j in career
            )
            candidate_text = (
                summary + " " + headline + " " +
                skills_text + " " + desc_text
            )
            all_candidate_texts.append(candidate_text)
            all_candidates.append(candidate)

    total = len(all_candidates)

    # Fit TF-IDF on JD + all candidates
    print(f"  Loaded {total:,} candidates. Computing semantic scores...")
    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    all_texts  = [JD_TEXT.lower()] + all_candidate_texts
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    jd_vector    = tfidf_matrix[0]
    candidate_vectors = tfidf_matrix[1:]
    semantic_scores = cosine_similarity(jd_vector, candidate_vectors)[0]
    print("  Semantic model ready!")

    # ── STEP 2: Score all candidates ──────────────────────────────────
    print("  Scoring all candidates...\n")
    results      = []
    disqualified = 0

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
            matched_skills, missing_skills,
            signals, score,
            semantic_sim=float(semantic_scores[i])
        )

        results.append({
            "candidate_id": candidate["candidate_id"],
            "name":         profile.get("anonymized_name", ""),
            "title":        title,
            "years":        years,
            "score":        score,
            "reasoning":    reasoning
        })

        if (i + 1) % 10000 == 0:
            print(f"  Processed {i+1:,} candidates...")

    # ── STEP 3: Sort + normalize ───────────────────────────────────────
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

    # ── STEP 4: Save CSV ──────────────────────────────────────────────
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