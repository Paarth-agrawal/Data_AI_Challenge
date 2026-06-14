import json
from job_description import JOB
from scorer import score_candidate

# Load candidates
print("Loading candidates...")
with open("sample_candidates.json") as f:
    candidates = json.load(f)

print(f"Total candidates loaded: {len(candidates)}")

# Score every candidate
print("Scoring candidates...")
results = []
for candidate in candidates:
    score, reasoning = score_candidate(candidate, JOB)
    results.append({
        "candidate_id": candidate["candidate_id"],
        "name": candidate["profile"]["anonymized_name"],
        "title": candidate["profile"]["current_title"],
        "score": score,
        "reasoning": reasoning
    })

# Sort by score (highest first)
results.sort(key=lambda x: x["score"], reverse=True)

# Print top 10
print("\n========== TOP CANDIDATES ==========\n")
for i, r in enumerate(results[:10], 1):
    print(f"#{i} {r['name']} — {r['title']}")
    print(f"    Score: {r['score']}")
    print(f"    Why: {r['reasoning']}")
    print()

print("===== DONE =====")