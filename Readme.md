# AI Candidate Ranking System
### Redrob Data & AI Hackathon — Senior AI Engineer Role

## About
Built by **Paarth Agrawal** — solo submission.

## What This Does
Ranks 100,000 candidates for a Senior AI Engineer role using a
multi-signal scoring system combining exact skill matching, TF-IDF
semantic similarity, career quality analysis, and all 23 behavioral
signals from the Redrob platform.

## Single Command to Reproduce Submission

```bash
python main.py --candidates ./candidates.jsonl --out ./submission.csv
```

Processes all 100,000 candidates and outputs a validated
`submission.csv` in **approximately 4 minutes** on CPU only.
No GPU. No external API calls. Fully deterministic — same input
always produces the same output.

## Setup

```bash
pip install -r requirements.txt
```

Place `candidates.jsonl` in the same folder as `main.py`.

## Architecture

```
candidates.jsonl (100,000 profiles)
        │
        ▼
┌─────────────────────────────────────┐
│         INSTANT DISQUALIFIERS       │
│  • Unrelated job function           │
│  • Under 2 years experience         │
│  • Junior title                     │
│  • Honeypot detection (5 checks)    │
└─────────────────┬───────────────────┘
                  │ ~24K pass through
                  ▼
┌─────────────────────────────────────┐
│        CONSULTING PENALTY           │
│  Penalty only — not rejection       │
│  Applied only when consulting +     │
│  weak AI evidence combined          │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│           SCORING ENGINE            │
│                                     │
│  Skill Match          35 pts        │
│  TF-IDF Semantic      10 pts        │
│  Skill Assessments     5 pts        │
│  Bonus Skills          5 pts        │
│  Experience           15 pts        │
│  Job Title            15 pts        │
│  Career Quality       10 pts        │
│  Behavioral Signals   20 pts        │
│  Location              2 pts        │
│  Education             1 pt         │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  SORT → NORMALIZE (0–1) → RANK      │
│  Tie-break: candidate_id ASC        │
│  Confidence: High / Medium / Low    │
└─────────────────┬───────────────────┘
                  │
                  ▼
         submission.csv
         (Top 100, ranks 1–100)
```

## Scoring Breakdown

| Signal | Points | What We Check | Why This Weight |
|--------|--------|---------------|----------------|
| Skill Match | 35 | 14 required skills + alias matching | Direct JD requirement — primary evidence |
| TF-IDF Semantic | 10 | Cosine similarity of career text to JD | Catches transferable experience |
| Assessments | 5 | Verified platform test scores | More reliable than self-reported |
| Bonus Skills | 5 | LoRA, QLoRA, Pinecone, Weaviate etc. | Depth signal |
| Experience | 15 | 5–9 year sweet spot from JD | JD explicitly specifies range |
| Job Title | 15 | Tiered — AI titles score higher | Job function must align |
| Career Quality | 10 | Product vs consulting history | Startup relevance |
| Behavioral Signals | 20 | All 23 Redrob signals (capped) | Real hirability signal |
| Location | 2 | India-based bonus only | Soft preference, never penalty |
| Education | 1 | Tier-1 tiebreaker only | Minimal bias impact |

## Weight Selection Methodology

Weights reflect how a senior technical recruiter prioritises evidence:

- **Skills (35pts):** Direct match is the strongest verifiable signal
- **Semantic (10pts):** TF-IDF catches "dense retrieval" when "FAISS" isn't listed
- **Assessments (5pts):** Verified scores are more reliable than self-reported
- **Experience (15pts):** JD specifies 5-9 years — over/under is penalised
- **Title (15pts):** A Marketing Manager with Python is NOT an AI Engineer
- **Career (10pts):** Product company experience signals startup readiness
- **Signals (20pts):** Capped to prevent popular candidates outscoring skilled ones
- **Location (2pts):** Soft bonus — global candidates evaluated on equal footing
- **Education (1pt):** Tiebreaker only — a strong self-taught engineer always wins

## Design Decisions

| Decision | Reason | Trade-off |
|----------|--------|-----------|
| TF-IDF not Sentence Transformers | CPU-only, no model download, runs in 4 min | Less semantic than embeddings |
| Consulting = penalty not rejection | Strong AI engineers exist at TCS/Infosys | May still affect some good candidates |
| Location = bonus only | Fairness — global talent evaluated equally | Slightly less signal for location fit |
| Education = 1 point only | Prevents institutional prestige bias | Underweights some quality signals |
| No LLM APIs | Reproducible, deterministic, offline | Less flexible reasoning |
| Behavioral cap at 20pts | Prevents popularity from rescuing weak profiles | May underreward highly engaged candidates |
| Single `WEIGHTS` source of truth | `config.py` defines weights once; `scorer.py` accepts an optional `weights` override that every scoring function threads through, so the Streamlit sliders in `app.py` change real rankings, not just labels | Slightly more parameter-passing through the call chain |

### Why TF-IDF (and not embeddings)
We need to score 100,000 candidates in minutes, on CPU, with no external
API calls, and the same input must always produce the same output for
judging. Sentence-Transformer embeddings would mean a model download,
GPU-friendly batching to stay fast, and a non-trivial dependency surface.
TF-IDF with bigrams gives "good enough" lexical/semantic overlap
(e.g. catching "dense retrieval" when "FAISS" isn't listed) while keeping
the pipeline self-contained, fast, and fully reproducible.

### Why education is low-weight
Tier-1 institution background is a *correlated*, not *causal*, signal for
engineering ability, and weighting it heavily would bias the ranking
toward candidates with privileged access to elite institutions. We treat
it strictly as a tiebreaker (1 point) — it can never lift a weak profile
above a strong one, only nudge between two otherwise-similar candidates.

### How we ensure fairness
- Gender, name, age, and photo are never read or used in scoring.
- Location is a bonus only (+2 max) — never a penalty for being elsewhere.
- Consulting-firm background is only penalized when *combined* with weak
  AI/ML evidence, so a strong AI engineer at TCS is not auto-penalized.
- Behavioral signals are hard-capped at 20 points so platform popularity
  can never outrank verified technical evidence.
- All thresholds and weights live in `config.py` as named constants —
  nothing is a "magic number" buried in scoring logic, so any reviewer
  can audit exactly how a number was chosen.

## Sample Candidate Flow

```
Input:  Senior ML Engineer, 7.2 yrs, India
        Skills: Deep Learning, Embeddings, Information Retrieval
        Signals: Open to work, 15-day notice, GitHub: 94.8

Scoring:
  Skill match (3/14)            →  7.5 pts
  Alias/semantic inferred       →  5.0 pts
  TF-IDF semantic alignment     →  8.5 pts
  Experience (7.2 yrs)          → 15.0 pts
  Title (Senior ML Engineer)    → 15.0 pts
  Career (product history)      → 10.0 pts
  Location (India)              →  2.0 pts
  Education (Tier-2)            →  1.0 pts
  Behavioral signals            → 19.5 pts
                                ─────────
  Raw total                     → 83.5 pts
  Normalized                    →  1.000
  Confidence                    →  High

Reasoning: "Senior Machine Learning Engineer with 7.2 years.
Strengths: deep learning, embeddings, information retrieval
background matches JD; verified Deep Learning 94/100;
actively looking, 15-day notice. Concerns: none significant."
```

## Honeypot Detection

Catches ~80 synthetic profiles via 5 checks:

1. **Future graduation** — graduation year > current year
2. **Experience mismatch** — claims more years than possible since graduation
3. **Pre-founding employment** — started at company before it was founded
4. **Duration overflow** — career months exceed claimed experience by 4+ years
5. **Skill inflation** — dynamic threshold based on experience + endorsements

Conservative thresholds prevent false positives on genuine senior engineers.

## Fairness Design

- **Gender/name/age:** Never used — fully anonymized candidate IDs only
- **Location:** India is +2 bonus only. Zero penalty for global candidates
- **Education:** Maximum 1 point — pure tiebreaker only
- **Consulting firms:** Penalty only when AI evidence is also weak
- **Behavioral signals:** Hard-capped at 20pts to prevent popularity bias
- **Reproducibility:** Identical input → identical output every time

## All 23 Behavioral Signals Used

1. profile_completeness_score
2. signup_date (platform tenure)
3. last_active_date (recency)
4. open_to_work_flag
5. profile_views_received_30d
6. applications_submitted_30d
7. recruiter_response_rate
8. avg_response_time_hours
9. skill_assessment_scores (verified)
10. connection_count
11. endorsements_received
12. notice_period_days
13. expected_salary_range_inr_lpa
14. preferred_work_mode
15. willing_to_relocate
16. github_activity_score
17. search_appearance_30d
18. saved_by_recruiters_30d
19. interview_completion_rate
20. offer_acceptance_rate
21. verified_email
22. verified_phone
23. linkedin_connected

## Changelog — Consistency Fixes

A self-review pass caught three places where displayed information could
disagree with what was actually scored. All are fixed and covered by
new tests:

- **Alias-matched skills now show as matched, not missing.** Previously
  `main.py`'s reasoning and `app.py`'s UI recomputed matched/missing
  skills with exact-name matching only, while the actual score credited
  alias matches too (e.g. "approximate nearest neighbour" → FAISS).
  A candidate could be scored as having a skill but shown as missing it.
  Fixed by adding `get_matched_and_missing_skills()` in `scorer.py` as a
  single source of truth, used by `score_skills`, `main.py`, and `app.py`
  alike. Covered by `test_alias_matched_skill_not_shown_as_missing`.
- **The Streamlit demo now uses real TF-IDF semantic matching.**
  `app.py` previously called `score_candidate()` without a TF-IDF vector,
  which silently fell back to a cruder keyword-hit heuristic — the
  interactive demo never actually exercised the semantic matching
  described in this README. `app.py` now builds a TF-IDF model over the
  uploaded batch (same approach as `main.py`) and threads it through
  scoring, confidence, and comparison calls.
- **The "no skills matched" penalty now scales with `weights["skills"]`**
  instead of being a flat `-15`, matching how every other scoring branch
  in `scorer.py` already respects weight overrides. Covered by
  `test_no_skill_penalty_scales_with_weight`.
- **`consulting_firms` list widened** from 6 to 22 entries (added HCL,
  Tech Mahindra, LTIMindtree, IBM, Deloitte, Genpact, and others) so the
  consulting-penalty logic isn't blind to major firms outside the
  original short list.

## Limitations

- TF-IDF is lexical similarity, not true semantic understanding
- Scoring weights are heuristic, not learned from historical hiring data
- Alias dictionary cannot be exhaustive

## Future Improvements

- Sentence Transformers (all-MiniLM-L6-v2) for true semantic matching
- Learning-to-rank calibration from historical hiring outcomes
- Timeline overlap detection for more accurate honeypot detection

## Complexity

- **Time:** O(n) — each candidate scored independently
- **Space:** O(n) — all candidates held in memory for sorting
- **TF-IDF build:** O(n × vocab) — one-time cost at startup
- **Runtime (100K candidates):** approximately 4 minutes on CPU

## Benchmark

Measured on Windows 11, Python 3.12, 16GB RAM, AMD Ryzen 7, CPU only:

```
Dataset load:            ~15 seconds
TF-IDF model build:      ~40 seconds
Candidate scoring:       ~180 seconds
Sort + normalize:        ~5 seconds
─────────────────────────────────────
Total (100K candidates): ~240 seconds (~4 minutes)
```

## File Structure

```
config.py                — All thresholds and weights (single source of truth)
main.py                  — Pipeline: load, score, rank, normalize, output
scorer.py                — All scoring functions + honeypot detection
job_description.py       — Role specification
app.py                   — Streamlit interactive demo (weight sliders live-affect ranking)
test_scoring.py          — 36 unit tests: scoring, honeypot, edge cases, weight-override parity, alias/skill consistency
requirements.txt         — Pinned dependencies
submission.csv           — Generated output (top 100 candidates)
submission_metadata.yaml — Submission details
validate_submission.py   — Official format validator
sample_candidates.json   — 50-candidate test set
```

## AI Tools Used

- **Claude (Anthropic)** — code architecture, debugging, scoring logic
- **ChatGPT (OpenAI)** — code review, audit suggestions
- **Gemini (Google)** — additional review and suggestions
- **Redrob AI** — challenge-specific feedback and auditing