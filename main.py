import json
import csv
import jsonlines
from job_description import JOB
from scorer import score_candidate

# ── STEP 1: READ AND SCORE ALL 100K CANDIDATES ───────────────────────
print("Loading and scoring all candidates...")
print("This will take 2-4 minutes. Please wait...\n")

results      = []
disqualified = 0
total        = 0

with jsonlines.open("candidates.jsonl") as reader:
    for candidate in reader:
        total += 1
        score, reasoning = score_candidate(candidate, JOB)

        if score == 0:
            disqualified += 1

        results.append({
            "candidate_id": candidate["candidate_id"],
            "name":         candidate["profile"]["anonymized_name"],
            "title":        candidate["profile"]["current_title"],
            "years":        candidate["profile"]["years_of_experience"],
            "score":        score,
            "reasoning":    reasoning
        })

        # Show progress every 10,000 candidates
        if total % 10000 == 0:
            print(f"  Processed {total:,} candidates...")

# ── STEP 2: SORT BY SCORE ─────────────────────────────────────────────
print("\nSorting results...")
results.sort(key=lambda x: x["score"], reverse=True)

# ── STEP 3: PRINT TOP 10 TO SCREEN ───────────────────────────────────
qualified = total - disqualified
print(f"\nTotal candidates : {total:,}")
print(f"Disqualified     : {disqualified:,}")
print(f"Qualified        : {qualified:,}")

print("\n========== TOP 10 CANDIDATES ==========\n")
for i, r in enumerate(results[:10], 1):
    print(f"#{i}  {r['name']}")
    print(f"     Title : {r['title']}")
    print(f"     Years : {r['years']}")
    print(f"     Score : {r['score']}")
    print(f"     Why   : {r['reasoning']}")
    print()

# ── STEP 4: SAVE TOP 100 TO submission.csv ────────────────────────────
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

print("submission.csv saved with top 100 candidates!")
print("\n===== DONE =====")