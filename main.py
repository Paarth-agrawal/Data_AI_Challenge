import json
from job_description import JOB
from scorer import score_candidate

# ── LOAD CANDIDATES ───────────────────────────────────────────────────
print("Loading candidates...")
with open("sample_candidates.json") as f:
    candidates = json.load(f)
print(f"Loaded {len(candidates)} candidates")

# ── SCORE EVERY CANDIDATE ─────────────────────────────────────────────
print("Scoring candidates...")
results = []
for candidate in candidates:
    score, reasoning = score_candidate(candidate, JOB)
    results.append({
        "candidate_id": candidate["candidate_id"],
        "name": candidate["profile"]["anonymized_name"],
        "title": candidate["profile"]["current_title"],
        "years": candidate["profile"]["years_of_experience"],
        "score": score,
        "reasoning": reasoning
    })

# ── SORT BY SCORE ─────────────────────────────────────────────────────
results.sort(key=lambda x: x["score"], reverse=True)

# ── PRINT TOP 10 ──────────────────────────────────────────────────────
print("\n========== TOP 10 CANDIDATES ==========\n")
for i, r in enumerate(results[:10], 1):
    print(f"#{i} {r['name']}")
    print(f"    Title : {r['title']}")
    print(f"    Years : {r['years']}")
    print(f"    Score : {r['score']}")
    print(f"    Why   : {r['reasoning']}")
    print()

# ── PRINT BOTTOM 3 (sanity check) ────────────────────────────────────
print("========== BOTTOM 3 (should be weak candidates) ==========\n")
for i, r in enumerate(results[-3:], 1):
    print(f"#{i} {r['name']} — {r['title']} — Score: {r['score']}")
    print(f"    Why: {r['reasoning']}")
    print()

print("===== DONE =====")