# AI Candidate Ranking System
### Redrob Data & AI Hackathon — Senior AI Engineer Role

## Team
- Paarth Agrawal
- Piyush Jakhar

## What This Does
Ranks 100,000 candidates for a Senior AI Engineer role using a
multi-signal scoring system that combines exact skill matching,
semantic similarity, career quality analysis, and 23 behavioral
signals from the Redrob platform.

## Single Command to Reproduce Submission

```bash
python main.py --candidates ./candidates.jsonl --out ./submission.csv
```

Processes all 100,000 candidates and outputs a validated
`submission.csv` in **under 5 minutes** on CPU only.
No GPU required. No external API calls.

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
│  • Honeypot detection               │
└─────────────────┬───────────────────┘
                  │ ~24K pass through
                  ▼
┌─────────────────────────────────────┐
│        CONSULTING PENALTY           │
│  (penalty only, not rejection)      │
│  Applied only when consulting       │
│  career + weak AI evidence          │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│           SCORING ENGINE            │
│                                     │
│  Skill Match          35 pts        │
│  Semantic (TF-IDF)    10 pts        │
│  Skill Assessments     5 pts        │
│  Bonus Skills          5 pts        │
│  Experience           15 pts        │
│  Job Title            15 pts        │
│  Career Quality       10 pts        │
│  Location              2 pts        │
│  Education             3 pts        │
│  Behavioral Signals   20 pts        │
│  ─────────────────────────          │
│  Total               120 pts        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      SORT + NORMALIZE (0–1)         │
│   Tie-break: candidate_id ASC       │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│    REASONING + CONFIDENCE           │
│  Strengths: skill depth, verified   │
│  assessments, availability,         │
│  engagement, semantic alignment     │
│  Concerns: missing skills, notice,  │
│  inactivity, location, interview    │
│  Confidence: High / Medium / Low    │
└─────────────────┬───────────────────┘
                  │
                  ▼
         submission.csv
         (Top 100, ranks 1–100,
          scores 0–1 normalized)
```

## Scoring Breakdown

| Signal | Points | What We Check |
|--------|--------|---------------|
| Skill Match | 35 | 14 required skills from JD + alias matching |
| Semantic Match | 10 | TF-IDF cosine similarity of career text to JD |
| Skill Assessments | 5 | Verified platform test scores |
| Bonus Skills | 5 | LoRA, QLoRA, Pinecone, Weaviate, Milvus etc. |
| Experience | 15 | 5–9 year sweet spot from JD |
| Job Title | 15 | AI/ML Engineer, Data Scientist, Applied Scientist etc. |
| Career Quality | 10 | Product company vs consulting history |
| Behavioral Signals | 20 | All 23 Redrob platform signals |
| Location | 2 | Bonus for India-based (never a penalty) |
| Education | 3 | Tier-1/2 institution (tiebreaker only) |

## Weight Selection Methodology

Weights were chosen to reflect how a senior technical recruiter
would prioritise evidence when hiring for this role:

- **Skills (35pts)** — Direct JD requirement match is the strongest signal.
  A candidate who lists the exact skills needed provides explicit evidence.
- **Semantic (10pts)** — TF-IDF captures transferable experience not in
  the skills list. An engineer who "built dense retrieval pipelines" matches
  even without listing "Information Retrieval" as a skill.
- **Assessment scores (5pts)** — Verified platform test scores are more
  reliable than self-reported skills. Weighted lower due to sparse coverage.
- **Experience (15pts)** — The JD explicitly requests 5–9 years. Under/over
  experience is penalised proportionally.
- **Title (15pts)** — Job function must align. A Marketing Manager with Python
  skills is not an AI Engineer regardless of other signals.
- **Career quality (10pts)** — Product company experience indicates hands-on
  engineering vs managed services delivery.
- **Behavioral signals (20pts)** — Capped at 20pts to prevent popular
  candidates from outscoring technically strong ones. Reflects real
  hirability: open-to-work, response rate, notice period, GitHub activity.
- **Location (2pts)** — Soft bonus for India proximity. Never penalises
  global candidates.
- **Education (3pts)** — Minor tiebreaker. A strong self-taught engineer
  always outranks a weak Tier-1 graduate.

## Sample Candidate Flow

Here is exactly how a real top candidate is scored:

```
Candidate: Aarav Trivedi
Role: Senior Machine Learning Engineer, 7.2 years

Scoring:
  Skill match (3/14 matched)        →  7.5 pts
  Alias/semantic skill match        →  5.0 pts  (inferred skills)
  Bonus skills (qlora, pinecone)    →  3.0 pts
  Assessment (Deep Learning: 94)    →  4.7 pts
  Career description keywords       →  5.0 pts  (TF-IDF)
  Experience (7.2 yrs, sweet spot)  → 15.0 pts
  Title (ML Engineer → match)       → 15.0 pts
  Product company history           → 10.0 pts
  Location (India)                  →  2.0 pts
  Education (Tier-2)                →  1.0 pts
  Behavioral signals                → 19.5 pts
  ─────────────────────────────────
  Raw total                         → 87.7 pts
  Normalized                        →  1.000

Reasoning: "Senior Machine Learning Engineer with 7.2 years.
Strengths: deep learning, embeddings, information retrieval
background; verified Deep Learning assessment 94/100;
actively looking, 15-day notice. Concerns: none significant."
```

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

## Honeypot Detection

The dataset contains ~80 synthetic "honeypot" profiles with
impossible characteristics. Our system detects them via:

- **Future graduation year** — grad_year > current_year
- **Experience vs graduation mismatch** — claims more years than
  possible given graduation date
- **Pre-founding employment** — started at company before it existed
- **Career duration overflow** — career months exceed claimed
  experience by more than 4 years
- **Impossible expertise** — 20+ expert skills with under 8 years
  experience AND low endorsements

Conservative thresholds prevent false positives on legitimate
senior engineers with broad skill sets.

## Fairness Design

- **Location:** India proximity is a +2 bonus. There is no penalty
  for candidates outside India.
- **Education:** Tier-1 institutions add at most 3 points — treated
  as a tiebreaker. A strong self-taught engineer outranks a weak
  Tier-1 graduate.
- **Consulting firms:** Penalty applied only when consulting history
  is combined with weak AI evidence. A brilliant AI engineer from
  TCS who built RAG systems scores competitively.
- **Behavioral signals:** Hard-capped at 20 points to prevent
  popular candidates from rescuing weak technical profiles.

## Limitations

- Semantic matching uses TF-IDF (lexical similarity), not transformer
  embeddings. Two phrases with the same meaning but different words
  may not match perfectly.
- Scoring weights are heuristic, not learned from historical hiring
  data.
- Alias dictionary covers common equivalents but cannot be exhaustive.

## Future Improvements

- Sentence Transformers (all-MiniLM-L6-v2) for true semantic matching
- Learning-to-rank calibration from historical hiring outcomes
- Timeline overlap detection for more accurate honeypot detection
- Expanded skill alias dictionary

## Benchmark

Measured on Windows 11, Python 3.12, 16GB RAM, AMD Ryzen 7, CPU only:

```
TF-IDF model build:      ~40 seconds
Candidate scoring:       ~180 seconds
Sort + normalize:        ~5 seconds
Total (100K candidates): ~225 seconds (under 4 minutes)
```

## File Structure

```
main.py                  — Pipeline: load, score, rank, output
scorer.py                — Scoring functions + honeypot detection
job_description.py       — Role spec and signal weights
app.py                   — Streamlit demo
requirements.txt         — Dependencies
submission.csv           — Generated output (top 100)
submission_metadata.yaml — Team and methodology
validate_submission.py   — Official format validator
sample_candidates.json   — 50-candidate test set
```

## AI Tools Used

Claude (Anthropic) — code assistance and debugging