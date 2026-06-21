# AI Candidate Ranking System
### Redrob Data & AI Hackathon — Senior AI Engineer Role

## What This Does
Ranks 100,000 candidates for a Senior AI Engineer role using a 
multi-signal scoring system. Evaluates skill match, experience, 
career quality, and all 23 behavioral signals from the Redrob platform.

## Team
- Paarth Agrawal
- Piyush Jakhar

## Setup

### Requirements
- Python 3.12
- 16GB RAM
- CPU only (no GPU needed)

### Install dependencies
pip install -r requirements.txt

### Place the dataset
Put `candidates.jsonl` in the same folder as `main.py`

## Single Command to Reproduce Submission
python main.py --candidates ./candidates.jsonl --out ./submission.csv

Processes all 100,000 candidates and outputs a validated
`submission.csv` in under 3 minutes on CPU.

## Architecture
candidates.jsonl (100K profiles)

│

▼

┌─────────────────────────────────────┐

│         INSTANT DISQUALIFIERS       │

│  • Unrelated job function           │

│  • Consulting-only career           │

│  • Under 2 years experience         │

│  • Junior title                     │

│  • Honeypot detection               │

└─────────────────┬───────────────────┘

│ ~24K qualified

▼

┌─────────────────────────────────────┐

│           SCORING ENGINE            │

│                                     │

│  Skill Match        35 pts          │

│  Skill Assessments   5 pts          │

│  Bonus Skills        5 pts          │

│  Career Descriptions 5 pts          │

│  Experience         15 pts          │

│  Job Title          15 pts          │

│  Career Quality     10 pts          │

│  Location            3 pts          │

│  Education Tier      3 pts          │

│  23 Behavioral Sigs 20 pts          │

└─────────────────┬───────────────────┘

│

▼

┌─────────────────────────────────────┐

│      SORT + NORMALIZE (0-1)         │

│   Tie-break: candidate_id ASC       │

└─────────────────┬───────────────────┘

│

▼

┌─────────────────────────────────────┐

│    REASONING GENERATOR              │

│  5 specific facts per candidate:    │

│  • Skill depth                      │

│  • Verified assessment scores       │

│  • Availability/notice period       │

│  • Engagement signals               │

│  • Location/education               │

└─────────────────┬───────────────────┘

│

▼

submission.csv

(Top 100, ranks 1-100)

## Sample Candidate Flow

A real example of how candidate CAND_0086022 (Dhruv Naidu) gets scored:
Input:  Senior Applied Scientist, 5.3 yrs, India

Skills: Deep Learning, NLP, PyTorch, TensorFlow, Embeddings

Signals: Open to work, 0-day notice, GitHub: 75.2
Scoring:

Skill match (5/14 skills)     → 12.5 pts

Assessment avg: 79.9/100      →  4.0 pts

Career description keywords   →  3.0 pts

Experience (5.3 yrs)          → 15.0 pts

Title (Applied Scientist)     → 15.0 pts

Product company history       → 10.0 pts

Location (India)              →  3.0 pts

Behavioral signals            → 18.2 pts

─────────

Total                         → 80.7 pts → normalized: 1.0
Output: Rank #1

Reasoning: "Senior Applied Scientist with 5.3 years; strong

alignment across 6 skills including deep learning, nlp, pytorch;

immediately available; highly responsive (91%); India-based."

## Scoring Breakdown

| Signal | Points | What We Check |
|--------|--------|---------------|
| Skill Match | 35 | 14 required skills from JD |
| Skill Assessments | 5 | Verified test scores |
| Bonus Skills | 5 | LoRA, QLoRA, Pinecone etc. |
| Career Descriptions | 5 | AI keywords in actual work done |
| Experience | 15 | Sweet spot 5-9 years |
| Job Title | 15 | AI/ML Engineer, Data Scientist etc. |
| Career Quality | 10 | Product vs consulting history |
| Location | 3 | India-based, Pune/Noida area |
| Education | 3 | Tier-1/2 institution bonus |
| 23 Behavioral Signals | 20 | Full Redrob signal suite |

## All 23 Behavioral Signals Used
1. profile_completeness_score
2. signup_date
3. last_active_date
4. open_to_work_flag
5. profile_views_received_30d
6. applications_submitted_30d
7. recruiter_response_rate
8. avg_response_time_hours
9. skill_assessment_scores
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

## Instant Disqualifiers
- Unrelated job functions (Marketing, HR, Sales, Accountant etc.)
- Entire career at IT consulting firms (TCS, Infosys, Wipro etc.)
- Less than 2 years experience
- Junior level titles
- Honeypot profiles (impossible career timelines)

## File Structure
main.py                 — Main ranking pipeline + reasoning generator

scorer.py               — Scoring logic + honeypot detection

job_description.py      — Role requirements and signal weights

app.py                  — Streamlit demo

submission.csv          — Generated output (top 100 candidates)

submission_metadata.yaml — Team and methodology details

## Compute Environment
Windows 11, Python 3.12, 16GB RAM, CPU only
Runtime: under 3 minutes for 100,000 candidates
No GPU, no external API calls, fully self-contained

## AI Tools Used
Claude (Anthropic) — used for code assistance and debugging