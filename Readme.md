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

This processes all 100,000 candidates and outputs a validated 
`submission.csv` in under 3 minutes on CPU.

## How It Works

### Scoring Breakdown (100 points → normalized 0-1)

| Signal | Points | What We Check |
|--------|--------|---------------|
| Skill Match | 35 | 14 required skills from JD |
| Skill Assessments | 5 | Verified test scores per skill |
| Bonus Skills | 5 | LoRA, QLoRA, Pinecone, Weaviate etc. |
| Experience | 15 | Sweet spot 5-9 years |
| Job Title | 15 | AI/ML Engineer, Data Scientist etc. |
| Career Quality | 10 | Product company vs consulting history |
| All 23 Behavioral Signals | 20 | Full Redrob signal suite |

### All 23 Behavioral Signals Used
1. profile_completeness_score
2. last_active_date (recency)
3. open_to_work_flag
4. profile_views_received_30d
5. applications_submitted_30d
6. recruiter_response_rate
7. avg_response_time_hours
8. skill_assessment_scores (verified test scores)
9. connection_count
10. endorsements_received
11. notice_period_days
12. expected_salary_range_inr_lpa
13. preferred_work_mode
14. willing_to_relocate
15. github_activity_score
16. search_appearance_30d
17. saved_by_recruiters_30d
18. interview_completion_rate
19. offer_acceptance_rate
20. verified_email
21. verified_phone
22. linkedin_connected
23. signup_date

### Instant Disqualifiers
- Unrelated job functions (Marketing, HR, Sales, Accountant etc.)
- Entire career at IT consulting firms (TCS, Infosys, Wipro etc.)
- Less than 2 years experience
- Junior level titles
- Honeypot profiles (impossible career timelines detected)

### Why This Approach
Most systems match keywords. Ours reads the full picture —
a Marketing Manager with Python skills is NOT an AI Engineer.
Career trajectory, verified assessments, and real engagement 
signals find candidates a recruiter can actually hire.

## File Structure
main.py              — Main ranking pipeline

scorer.py            — Scoring logic + honeypot detection

job_description.py   — Role requirements and signal weights

app.py               — Streamlit demo

submission.csv       — Generated output (top 100 candidates)

## Compute Environment
Windows 11, Python 3.12, 16GB RAM, CPU only
Runtime: under 3 minutes for 100,000 candidates

## AI Tools Used
Claude (Anthropic) — used for code assistance and debugging