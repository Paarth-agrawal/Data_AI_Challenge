import streamlit as st
import json
import csv
import io
from scorer import score_candidate, score_skills, score_experience, score_title, score_career, score_signals, score_location, WEIGHTS, fix_title_caps
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
The full pipeline runs on 100,000 candidates via `python main.py --candidates ./candidates.jsonl --out ./submission.csv`
and completes in under 4 minutes on CPU only.
""")

# ── SIDEBAR ───────────────────────────────────────────────────────────
st.sidebar.header("About This System")
st.sidebar.markdown("""
This system ranks candidates for a **Senior AI Engineer** role.

### Scoring Weights
*(Single source of truth from scorer.py)*
""")

for section, pts in WEIGHTS.items():
    st.sidebar.markdown(f"- **{section.title()}** — {pts} pts")

st.sidebar.markdown("""
### Why These Weights?
- **Skills (35pts)** — direct JD requirement match is primary signal
- **Semantic (10pts)** — TF-IDF catches transferable experience
- **Assessment (5pts)** — verified scores > self-reported
- **Experience (15pts)** — JD specifies 5-9yr sweet spot
- **Title (15pts)** — job function alignment is critical
- **Career (10pts)** — product company experience matters
- **Signals (20pts)** — behavioral data reflects real hirability
- **Location (2pts)** — soft preference for Pune/Noida

### Fairness Design
- Consulting penalty only when AI evidence is weak
- Location is bonus only — never penalty
- Education tier is tiebreaker only (3pts)
- Behavioral signals capped at 20pts to prevent popularity bias

Built by **Paarth Agrawal & Piyush Jakhar**
""")

# ── MAIN TABS ─────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📁 Upload & Rank", "📊 How It Works", "⚖️ Fairness"
])

with tab1:
    st.markdown("### Upload Candidates JSON")
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
                results               = []
                required_skills_lower = [
                    s.lower() for s in JOB.get("required_skills", [])
                ]

                with st.spinner(f"Scoring {len(candidates)} candidates..."):
                    for candidate in candidates:
                        score, reasoning = score_candidate(candidate, JOB)
                        profile  = candidate.get("profile", {})
                        signals  = candidate.get("redrob_signals", {})
                        skills   = candidate.get("skills", [])
                        education = candidate.get("education", [])
                        career   = candidate.get("career_history", [])
                        title    = profile.get("current_title", "")
                        years    = profile.get("years_of_experience", 0)
                        location = profile.get("location", "").lower()
                        country  = profile.get("country", "").lower()

                        full_text = (
                            profile.get("summary", "").lower() + " " +
                            " ".join(
                                j.get("description", "").lower()
                                for j in career
                            )
                        )

                        candidate_skills_lower = [
                            s["name"].lower() for s in skills
                        ]
                        matched = [
                            s for s in required_skills_lower
                            if s in candidate_skills_lower
                        ]
                        missing = [
                            s for s in required_skills_lower
                            if s not in candidate_skills_lower
                        ]

                        # Score breakdown for UI
                        s_score, _, _, _ = score_skills(
                            candidate, JOB, full_text
                        )
                        e_score, _  = score_experience(years, JOB)
                        t_score, _  = score_title(
                            profile.get("current_title", "").lower(), JOB
                        )
                        c_score, _  = score_career(
                            career,
                            JOB.get("consulting_firms", []),
                            education, full_text, 0
                        )
                        sig_score, _ = score_signals(signals, JOB)
                        l_score, _  = score_location(country, location)

                        results.append({
                            "candidate_id":   candidate["candidate_id"],
                            "name":           profile.get("anonymized_name", ""),
                            "title":          title,
                            "years":          years,
                            "score":          score,
                            "matched_skills": matched,
                            "missing_skills": missing,
                            "open_to_work":   signals.get("open_to_work_flag", False),
                            "response_rate":  signals.get("recruiter_response_rate", 0),
                            "notice":         signals.get("notice_period_days", 90),
                            "github":         signals.get("github_activity_score", -1),
                            "reasoning":      reasoning,
                            "breakdown": {
                                "Skills":    round(s_score, 1),
                                "Exp":       round(e_score, 1),
                                "Title":     round(t_score, 1),
                                "Career":    round(c_score, 1),
                                "Signals":   round(sig_score, 1),
                                "Location":  round(l_score, 1),
                            }
                        })

                results.sort(key=lambda x: x["score"], reverse=True)
                qualified    = [r for r in results if r["score"] > 0]
                disqualified = [r for r in results if r["score"] == 0]

                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total", len(results))
                col2.metric("Qualified", len(qualified))
                col3.metric("Disqualified", len(disqualified))
                col4.metric("Top Score", qualified[0]["score"] if qualified else 0)

                # Top candidate summary
                if qualified:
                    top = qualified[0]
                    st.markdown("---")
                    st.markdown("### 🥇 Top Candidate Summary")
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**{top['name']}**  \n{top['title']}")
                    c2.markdown(
                        f"**Score:** {top['score']}  \n"
                        f"**Skills matched:** {len(top['matched_skills'])}/14"
                    )
                    c3.markdown(
                        f"**Open to work:** {'✅' if top['open_to_work'] else '❌'}  \n"
                        f"**Notice:** {top['notice']} days"
                    )
                    st.markdown(f"**Why #1:** {top['reasoning']}")

                st.markdown("---")
                st.markdown(
                    f"### Showing all {len(qualified)} qualified candidates"
                )

                for i, r in enumerate(qualified, 1):
                    if r["score"] >= 60:
                        emoji = "🟢"
                    elif r["score"] >= 35:
                        emoji = "🟡"
                    else:
                        emoji = "🔴"

                    with st.expander(
                        f"{emoji} #{i} {r['name']} — "
                        f"{r['title']} — Score: {r['score']}"
                    ):
                        col1, col2, col3, col4 = st.columns(4)
                        col1.markdown(f"**Years:** {r['years']}")
                        col2.markdown(
                            f"**Open:** {'✅' if r['open_to_work'] else '❌'}"
                        )
                        col3.markdown(
                            f"**Response:** {int(r['response_rate']*100)}%"
                        )
                        col4.markdown(f"**Notice:** {r['notice']}d")

                        st.markdown(
                            f"**Skills matched:** "
                            f"`{', '.join(r['matched_skills'][:6]) or 'None'}`"
                        )

                        # Score breakdown
                        st.markdown("**Score breakdown:**")
                        bd_cols = st.columns(len(r["breakdown"]))
                        for j, (key, val) in enumerate(
                            r["breakdown"].items()
                        ):
                            bd_cols[j].metric(key, val)

                        st.markdown(f"**Reasoning:** {r['reasoning']}")

                # Disqualified summary
                if disqualified:
                    st.markdown("---")
                    with st.expander(
                        f"❌ {len(disqualified)} Disqualified Candidates"
                    ):
                        for r in disqualified:
                            st.markdown(
                                f"- **{r['name']}** ({r['title']}) — "
                                f"{r['reasoning']}"
                            )

                # Download
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
            st.error(f"Error: {e}")
            st.exception(e)

with tab2:
    st.markdown("### How Our Scoring Works")
    st.markdown("""
    #### Scoring Breakdown (normalized to 0–1)

    | Signal | Points | What We Check | Why This Weight |
    |--------|--------|---------------|----------------|
    | Skill Match | 35 | 14 required skills from JD | Direct JD requirement — primary signal |
    | Semantic Match | 10 | TF-IDF similarity of career text to JD | Catches transferable experience |
    | Assessments | 5 | Verified test scores | More reliable than self-reported |
    | Bonus Skills | 5 | LoRA, QLoRA, Pinecone etc. | Depth signal |
    | Experience | 15 | 5-9 year sweet spot | JD explicitly specifies range |
    | Job Title | 15 | AI/ML titles | Job function alignment |
    | Career Quality | 10 | Product vs consulting history | Startup-relevant signal |
    | Behavioral Signals | 20 | All 23 Redrob signals | Reflects real hirability |
    | Location | 2 | India-based bonus only | Soft preference, never penalty |
    | Education | 3 | Tier-1/2 institution | Minor tiebreaker |

    #### Instant Disqualifiers
    - Unrelated job functions (Marketing, HR, Sales, Accountant etc.)
    - Less than 2 years experience
    - Junior level titles
    - Honeypot profiles (impossible career timelines)

    #### Consulting Penalty (not disqualification)
    Consulting experience is penalized **only** when combined with weak AI evidence.
    A strong AI engineer from Accenture still scores well.
    """)

with tab3:
    st.markdown("### ⚖️ Fairness Design")
    st.markdown("""
    #### How we prevent bias:

    **Location:** India proximity gives a +2 bonus but there is **no penalty**
    for candidates outside India. Global talent is evaluated fairly.

    **Education:** Tier-1 institutions give a minor +3 bonus — treated as a
    tiebreaker only. A self-taught engineer with strong skills outranks a
    Tier-1 graduate with no skills.

    **Consulting firms:** We apply a scoring penalty only when consulting
    background is combined with weak AI evidence. A brilliant AI engineer
    from TCS who built RAG systems still scores competitively.

    **Behavioral signals:** Capped at 20 points maximum so that popular
    candidates with high profile views cannot rescue weak technical profiles.

    **Honeypot detection:** Conservative thresholds to avoid false positives.
    A senior engineer with 20+ expert skills is only flagged if they also have
    low endorsements and under 8 years experience.
    """)