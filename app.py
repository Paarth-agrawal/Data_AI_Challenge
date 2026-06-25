import streamlit as st
import json
import csv
import io
from typing import Dict, List
from scorer import (
    score_candidate, score_skills, score_experience,
    score_title, score_career, score_signals, score_location,
    get_score_breakdown, compare_candidates,
    WEIGHTS, fix_title_caps, deduplicate_text
)
from job_description import JOB

st.set_page_config(
    page_title="AI Candidate Ranker",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Candidate Ranking System")
st.subheader("Senior AI Engineer — Redrob Hackathon")
st.info(
    "Upload `sample_candidates.json` to see live rankings. "
    "The full 100K pipeline runs via "
    "`python main.py --candidates ./candidates.jsonl --out ./submission.csv` "
    "in approximately **4 minutes** on CPU only."
)

# ── SIDEBAR ───────────────────────────────────────────────────────────
st.sidebar.header("About This System")
st.sidebar.markdown("### Scoring Weights *(from scorer.py)*")
max_w = max(WEIGHTS.values())
for section, pts in WEIGHTS.items():
    st.sidebar.progress(pts / max_w)
    st.sidebar.caption(f"{section.title()} — {pts} pts")

st.sidebar.markdown("""
---
### Why Not LLM APIs?
- ✅ CPU-only constraint
- ✅ Reproducible results
- ✅ No cost / no rate limits
- ✅ Deterministic ranking
- ✅ Under 4 min runtime

### Fairness Design
- Location is **bonus only** — no penalty for non-India
- Education contributes **only 1 pt** — tiebreaker only
- Consulting penalty **only when** weak AI evidence
- Behavioral signals **capped at 20pts** to prevent popularity bias

Built by **Paarth Agrawal**
""")

# ── TABS ──────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Upload & Rank",
    "🔍 Compare Candidates",
    "📊 How It Works",
    "⚖️ Fairness"
])

with tab1:
    st.markdown("### Upload Candidates JSON")
    uploaded = st.file_uploader(
        "Choose a JSON file", type=["json"],
        help="Upload sample_candidates.json from the dataset"
    )

    if uploaded:
        try:
            candidates = json.load(uploaded)
            st.success(f"✅ Loaded {len(candidates)} candidates!")

            if st.button("🚀 Rank Candidates", type="primary"):
                results: List[Dict] = []
                req_skills = [
                    s.lower() for s in JOB.get("required_skills", [])
                ]

                with st.spinner("Scoring candidates..."):
                    for candidate in candidates:
                        score, reasoning = score_candidate(candidate, JOB)
                        profile   = candidate.get("profile", {})
                        signals   = candidate.get("redrob_signals", {})
                        skills    = candidate.get("skills", [])
                        education = candidate.get("education", [])
                        career    = candidate.get("career_history", [])
                        title     = profile.get("current_title", "")
                        years     = profile.get("years_of_experience", 0)
                        country   = profile.get("country", "").lower()
                        location  = profile.get("location", "").lower()

                        full_text = deduplicate_text(
                            profile.get("summary", "").lower() + " " +
                            " ".join(
                                j.get("description", "").lower()
                                for j in career
                            )
                        )

                        cand_skills = [s["name"].lower() for s in skills]
                        matched = [
                            s for s in req_skills if s in cand_skills
                        ]
                        missing = [
                            s for s in req_skills if s not in cand_skills
                        ]

                        breakdown = get_score_breakdown(candidate, JOB)

                        results.append({
                            "candidate_id":  candidate["candidate_id"],
                            "name":          profile.get("anonymized_name", ""),
                            "title":         title,
                            "years":         years,
                            "score":         score,
                            "matched":       matched,
                            "missing":       missing,
                            "open":          signals.get("open_to_work_flag", False),
                            "response_rate": signals.get("recruiter_response_rate", 0),
                            "notice":        signals.get("notice_period_days", 90),
                            "github":        signals.get("github_activity_score", -1),
                            "confidence":    "High" if len(matched) >= 4 else (
                                             "Medium" if len(matched) >= 2 else "Low"),
                            "reasoning":     reasoning,
                            "breakdown":     breakdown,
                            "_candidate":    candidate,
                        })

                results.sort(key=lambda x: x["score"], reverse=True)
                qualified    = [r for r in results if r["score"] > 0]
                disqualified = [r for r in results if r["score"] == 0]

                # Metrics row
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", len(results))
                c2.metric("Qualified", len(qualified))
                c3.metric("Disqualified", len(disqualified))
                c4.metric("Top Score", qualified[0]["score"] if qualified else 0)

                # ── TOP CANDIDATE SPOTLIGHT ───────────────────────────
                if qualified:
                    top = qualified[0]
                    st.markdown("---")
                    st.markdown("## 🏆 Top Candidate Spotlight")
                    sp1, sp2, sp3, sp4 = st.columns(4)
                    sp1.markdown(
                        f"**{top['name']}**  \n"
                        f"{fix_title_caps(top['title'])}"
                    )
                    sp2.metric("Score", top["score"])
                    sp3.metric(
                        "Confidence",
                        top["confidence"],
                        delta="High" if top["confidence"] == "High" else None
                    )
                    sp4.metric(
                        "Skills Matched",
                        f"{len(top['matched'])}/14"
                    )

                    st.markdown(f"**Why #1:** {top['reasoning']}")

                    # Visual score breakdown for top candidate
                    st.markdown("**Score Breakdown:**")
                    bd = top["breakdown"]
                    max_pts = {
                        "Skills": 50, "Experience": 15, "Title": 15,
                        "Career": 10, "Location": 2, "Signals": 20
                    }
                    bd_cols = st.columns(len(bd))
                    for j, (key, val) in enumerate(bd.items()):
                        max_val = max_pts.get(key, 20)
                        bd_cols[j].metric(key, f"{val}/{max_val}")
                        bd_cols[j].progress(
                            min(1.0, max(0.0, val / max_val))
                        )

                    # Top-2 comparison
                    if len(qualified) >= 2:
                        second = qualified[1]
                        comparison = compare_candidates(
                            top["_candidate"],
                            second["_candidate"],
                            JOB,
                            top["score"],
                            second["score"]
                        )
                        st.info(f"**vs #{2} {second['name']}:** {comparison}")

                # ── ALL QUALIFIED ─────────────────────────────────────
                st.markdown("---")
                st.markdown(
                    f"### All {len(qualified)} Qualified Candidates"
                )

                conf_filter = st.selectbox(
                    "Filter by confidence",
                    ["All", "High", "Medium", "Low"]
                )
                filtered = (
                    qualified if conf_filter == "All"
                    else [r for r in qualified if r["confidence"] == conf_filter]
                )

                for i, r in enumerate(filtered, 1):
                    emoji = (
                        "🟢" if r["score"] >= 60 else
                        "🟡" if r["score"] >= 35 else "🔴"
                    )
                    conf_badge = (
                        "🔵" if r["confidence"] == "High" else
                        "⚪" if r["confidence"] == "Medium" else "🔘"
                    )

                    with st.expander(
                        f"{emoji} #{i} {r['name']} — "
                        f"{fix_title_caps(r['title'])} — "
                        f"Score: {r['score']} {conf_badge} {r['confidence']}"
                    ):
                        col1, col2, col3, col4 = st.columns(4)
                        col1.markdown(f"**Years:** {r['years']}")
                        col2.markdown(
                            f"**Open:** {'✅' if r['open'] else '❌'}"
                        )
                        col3.markdown(
                            f"**Response:** {int(r['response_rate']*100)}%"
                        )
                        col4.markdown(f"**Notice:** {r['notice']}d")

                        st.markdown(
                            f"**Matched:** "
                            f"`{', '.join(r['matched'][:6]) or 'None'}`"
                        )
                        if r["missing"]:
                            st.markdown(
                                f"**Missing:** "
                                f"`{', '.join(r['missing'][:4])}`"
                            )

                        # Score breakdown with progress bars
                        st.markdown("**Score Breakdown:**")
                        max_pts = {
                            "Skills": 50, "Experience": 15, "Title": 15,
                            "Career": 10, "Location": 2, "Signals": 20
                        }
                        bd_c = st.columns(len(r["breakdown"]))
                        for j, (key, val) in enumerate(
                            r["breakdown"].items()
                        ):
                            max_val = max_pts.get(key, 20)
                            bd_c[j].metric(key, f"{val}/{max_val}")
                            bd_c[j].progress(
                                min(1.0, max(0.0, val / max_val))
                            )

                        st.markdown(f"**Reasoning:** {r['reasoning']}")

                # ── DISQUALIFIED ──────────────────────────────────────
                if disqualified:
                    st.markdown("---")
                    with st.expander(
                        f"❌ {len(disqualified)} Disqualified"
                    ):
                        for r in disqualified:
                            st.markdown(
                                f"- **{r['name']}** ({r['title']}) — "
                                f"{r['reasoning']}"
                            )

                # ── DOWNLOAD ──────────────────────────────────────────
                st.markdown("---")
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(
                    ["candidate_id", "rank", "score", "reasoning"]
                )
                for rank, r in enumerate(qualified[:100], 1):
                    writer.writerow([
                        r["candidate_id"], rank,
                        r["score"], r["reasoning"]
                    ])
                st.download_button(
                    "📥 Download submission.csv",
                    data=buf.getvalue(),
                    file_name="submission.csv",
                    mime="text/csv"
                )

                # Store for comparison tab
                st.session_state["results"] = qualified

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)

with tab2:
    st.markdown("### 🔍 Candidate Comparison")
    st.markdown(
        "Select two candidates to see exactly why one ranked above the other."
    )

    if "results" in st.session_state and st.session_state["results"]:
        qualified = st.session_state["results"]
        names     = [
            f"#{i+1} {r['name']} (Score: {r['score']})"
            for i, r in enumerate(qualified[:20])
        ]

        col1, col2 = st.columns(2)
        with col1:
            a_idx = st.selectbox("Candidate A", range(len(names)),
                                  format_func=lambda i: names[i], key="a")
        with col2:
            b_idx = st.selectbox("Candidate B", range(len(names)),
                                  format_func=lambda i: names[i],
                                  index=1, key="b")

        if a_idx != b_idx:
            a = qualified[a_idx]
            b = qualified[b_idx]

            comparison = compare_candidates(
                a["_candidate"], b["_candidate"],
                JOB, a["score"], b["score"]
            )
            st.info(f"**Result:** {comparison}")

            # Side-by-side breakdown
            st.markdown("#### Score Breakdown Comparison")
            max_pts = {
                "Skills": 50, "Experience": 15, "Title": 15,
                "Career": 10, "Location": 2, "Signals": 20
            }
            cols = st.columns(3)
            cols[0].markdown("**Category**")
            cols[1].markdown(f"**{a['name']}**")
            cols[2].markdown(f"**{b['name']}**")

            for cat in a["breakdown"]:
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**{cat}**")
                av = a["breakdown"][cat]
                bv = b["breakdown"][cat]
                diff = av - bv
                c2.metric(
                    cat, av,
                    delta=f"+{round(diff,1)}" if diff > 0 else (
                        str(round(diff, 1)) if diff < 0 else None
                    )
                )
                c3.metric(cat, bv)
    else:
        st.info("Upload and rank candidates in the first tab to enable comparison.")

with tab3:
    st.markdown("### How Our Scoring Works")
    st.markdown("""
    #### Why This Beats Traditional ATS

    | Traditional ATS | Our System |
    |----------------|-----------|
    | Keyword matching only | Exact + alias + semantic matching |
    | No behavioral signals | 23 platform signals |
    | No verification | Verified assessment scores |
    | No honeypot detection | 5-check honeypot filter |
    | Binary pass/fail | Nuanced tiered scoring |

    #### Scoring Breakdown
    """)

    for section, pts in WEIGHTS.items():
        st.markdown(f"**{section.title()} — {pts} pts**")
        st.progress(pts / 35)

    st.markdown("""
    #### Why Not Transformer Embeddings?

    We deliberately chose TF-IDF over models like `all-MiniLM-L6-v2` because:
    - ✅ CPU-only constraint (no GPU)
    - ✅ No model download required
    - ✅ Deterministic, reproducible results
    - ✅ Runs in ~4 minutes total
    - ✅ No external dependencies

    TF-IDF with bigrams captures most semantic overlap for technical terms.

    #### Limitations
    - TF-IDF is lexical, not true semantic understanding
    - Weights are heuristic, not learned from hiring data
    - Alias dictionary cannot be exhaustive
    """)

with tab4:
    st.markdown("### ⚖️ Fairness Design")
    st.markdown("""
    #### Location
    India proximity gives a **+2 bonus**. There is **no penalty** for
    candidates outside India. Global talent is evaluated on equal footing.

    #### Education
    Tier-1 institutions contribute only **1 point** — used solely as a
    tiebreaker. A self-taught engineer with 8 matched skills outranks a
    Tier-1 graduate with 0 matched skills every single time.

    #### Consulting Firms
    We apply a penalty **only** when consulting background is combined with
    weak AI evidence. A strong AI engineer from TCS who built RAG systems
    scores competitively. The penalty is not a disqualification.

    #### Behavioral Signals
    Hard-capped at **20 points maximum** to prevent popular candidates
    from rescuing weak technical profiles. Technical score always dominates.

    #### Salary
    Salary fit contributes only **±1 point**. A perfect candidate who
    earns slightly above budget is not penalised heavily.

    #### What We Cannot Fix
    - Implicit bias in job description language itself
    - Candidates who understated their skills on the platform
    - Historical signal data that may not reflect current intent
    """)