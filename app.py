import streamlit as st
import json
import csv
import io
from scorer import score_candidate
from job_description import JOB

st.set_page_config(
    page_title="AI Candidate Ranker",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Candidate Ranking System")
st.subheader("Senior AI Engineer — Redrob Hackathon")

st.info("""
**How this works:** Upload a candidate JSON file to see live rankings.
The full pipeline runs on 100,000 candidates via `python main.py` and 
completes in under 3 minutes on CPU only.
""")

# ── SIDEBAR ───────────────────────────────────────────────────────────
st.sidebar.header("About This System")
st.sidebar.markdown("""
This system ranks candidates for a **Senior AI Engineer** role using:

- **Skill matching** — 50 points
- **Experience** — 15 points
- **Job title** — 15 points
- **Career quality** — 10 points
- **Behavioral signals** — 15 points

**Full pipeline:** 100,000 candidates → Top 100 ranked CSV in under 3 minutes

Built by **Paarth Agrawal & Piyush Jakhar**
""")

# ── MAIN TABS ─────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📁 Upload & Rank", "📊 How It Works"])

with tab1:
    st.markdown("### Upload Candidates JSON")
    st.markdown(
        "Upload `sample_candidates.json` from the dataset bundle to see the "
        "ranking system in action. The full 100K run uses `candidates.jsonl` "
        "via `python main.py`."
    )

    uploaded_file = st.file_uploader(
        "Choose a JSON file",
        type=["json"],
        help="Upload sample_candidates.json from the dataset"
    )

    if uploaded_file:
        try:
            candidates = json.load(uploaded_file)
            st.success(f"✅ Loaded {len(candidates)} candidates!")

            if st.button("🚀 Rank Candidates", type="primary"):
                results = []
                required_skills_lower = [s.lower() for s in JOB.get("required_skills", [])]

                with st.spinner(f"Scoring {len(candidates)} candidates..."):
                    for candidate in candidates:
                        score, reasoning = score_candidate(candidate, JOB)
                        profile  = candidate.get("profile", {})
                        signals  = candidate.get("redrob_signals", {})
                        skills   = candidate.get("skills", [])

                        candidate_skills_lower = [s["name"].lower() for s in skills]
                        matched = [
                            s for s in required_skills_lower
                            if s in candidate_skills_lower
                        ]

                        results.append({
                            "candidate_id":   candidate["candidate_id"],
                            "name":           profile.get("anonymized_name", ""),
                            "title":          profile.get("current_title", ""),
                            "years":          profile.get("years_of_experience", 0),
                            "score":          score,
                            "matched_skills": ", ".join(matched[:5]) if matched else "None",
                            "open_to_work":   signals.get("open_to_work_flag", False),
                            "response_rate":  f"{int(signals.get('recruiter_response_rate', 0) * 100)}%",
                            "github":         signals.get("github_activity_score", -1),
                            "notice":         signals.get("notice_period_days", 90),
                            "reasoning":      reasoning
                        })

                results.sort(key=lambda x: x["score"], reverse=True)

                qualified    = [r for r in results if r["score"] > 0]
                disqualified = [r for r in results if r["score"] == 0]

                # ── METRICS ───────────────────────────────────────────
                st.markdown("### 🏆 Results")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Candidates", len(results))
                col2.metric("Qualified", len(qualified))
                col3.metric("Disqualified", len(disqualified))
                col4.metric("Top Score", qualified[0]["score"] if qualified else 0)

                st.markdown("---")

                # ── SHOW ALL QUALIFIED ────────────────────────────────
                st.markdown(f"### Showing all {len(qualified)} qualified candidates")

                for i, r in enumerate(qualified, 1):
                    # Colour code by score
                    if r["score"] >= 60:
                        emoji = "🟢"
                    elif r["score"] >= 40:
                        emoji = "🟡"
                    else:
                        emoji = "🔴"

                    with st.expander(
                        f"{emoji} #{i} {r['name']} — {r['title']} — Score: {r['score']}"
                    ):
                        col1, col2, col3, col4 = st.columns(4)
                        col1.markdown(f"**Years Exp:** {r['years']}")
                        col2.markdown(f"**Open to Work:** {'✅' if r['open_to_work'] else '❌'}")
                        col3.markdown(f"**Response Rate:** {r['response_rate']}")
                        col4.markdown(f"**Notice Period:** {r['notice']} days")

                        st.markdown(f"**Matched Skills:** `{r['matched_skills']}`")
                        st.markdown(f"**Reasoning:** {r['reasoning']}")

                # ── DISQUALIFIED SUMMARY ──────────────────────────────
                if disqualified:
                    st.markdown("---")
                    with st.expander(f"❌ {len(disqualified)} Disqualified Candidates"):
                        for r in disqualified:
                            st.markdown(f"- **{r['name']}** ({r['title']}) — {r['reasoning']}")

                # ── DOWNLOAD ──────────────────────────────────────────
                st.markdown("---")
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["candidate_id", "rank", "score", "reasoning"])
                for rank, r in enumerate(qualified[:100], 1):
                    writer.writerow([
                        r["candidate_id"], rank,
                        r["score"], r["reasoning"]
                    ])

                st.download_button(
                    label="📥 Download submission.csv",
                    data=output.getvalue(),
                    file_name="submission.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.exception(e)

with tab2:
    st.markdown("### How Our Scoring Works")
    st.markdown("""
    #### Scoring Breakdown (100 points total)

    | Signal | Points | What We Check |
    |--------|--------|---------------|
    | Skill Match | 50 | Python, ML, Deep Learning, NLP, PyTorch, TensorFlow, Embeddings, FAISS etc. |
    | Experience | 15 | Sweet spot 5-9 years; overqualified (12+) penalised |
    | Job Title | 15 | AI Engineer, ML Engineer, Data Scientist etc. |
    | Career Quality | 10 | Product company history vs consulting firms |
    | Behavioral Signals | 15 | Open to work, recency, GitHub activity, response rate |

    #### Instant Disqualifiers
    - Unrelated job functions (Marketing, HR, Sales, Accountant etc.)
    - Entire career at consulting firms (TCS, Infosys, Wipro etc.)
    - Less than 2 years experience
    - Junior level titles
    - Honeypot profiles (impossible career timelines)

    #### Why This Approach?
    Most systems just match keywords. Ours reads the **full picture** —
    a Marketing Manager with Python skills is NOT an AI Engineer.
    We look at career trajectory, availability, and engagement signals
    to find candidates a recruiter can actually hire.

    #### Full Pipeline Performance
    - **100,000 candidates** processed in **under 3 minutes**
    - **CPU only** — no GPU required
    - **No external API calls** — fully self-contained
    - Outputs a validated `submission.csv` with top 100 candidates
    """)

    st.markdown("### Sample Top Candidate")
    st.code("""
#1 Dhruv Naidu — Senior Applied Scientist
   Score: 75.13
   Skills: Deep Learning, NLP, PyTorch, TensorFlow, Embeddings
   Why: 5.3 yrs experience | 0-day notice | 
        GitHub active (75.2) | Open to work | Will relocate
    """)