import streamlit as st
import json
import csv
import io
from typing import Dict, List
import plotly.graph_objects as go
import plotly.express as px
from scorer import (
    score_candidate, get_score_breakdown, compare_candidates,
    WEIGHTS, fix_title_caps, deduplicate_text,
    get_confidence, get_confidence_reasons
)
from job_description import JOB
from config import TOP_N_CANDIDATES

st.set_page_config(
    page_title="AI Candidate Ranker",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Candidate Ranking System")
st.caption("Senior AI Engineer — Redrob Data & AI Hackathon | Built by Paarth Agrawal")

st.info(
    "Upload `sample_candidates.json` to see live rankings. "
    "Full pipeline: `python main.py --candidates ./candidates.jsonl "
    "--out ./submission.csv` (~4 min on CPU)."
)

# ── SIDEBAR ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ System Configuration")

    st.markdown("### Scoring Weights")
    st.caption("Adjust weights to explore different ranking priorities")

    custom_weights = {}
    for section, default_pts in WEIGHTS.items():
        custom_weights[section] = st.slider(
            f"{section.title()}",
            min_value=0,
            max_value=50,
            value=default_pts,
            step=1,
            help=f"Default: {default_pts} pts"
        )

    total_weight = sum(custom_weights.values())
    st.metric("Total Weight", total_weight, delta=total_weight - sum(WEIGHTS.values()))

    if total_weight != sum(WEIGHTS.values()):
        st.warning("Weights modified from defaults")

    st.markdown("---")
    st.markdown("### Why Not LLM APIs?")
    st.markdown("""
    - ✅ CPU-only constraint
    - ✅ Reproducible results
    - ✅ No cost / rate limits
    - ✅ Deterministic ranking
    - ✅ ~4 min total runtime
    """)

    st.markdown("### Fairness Design")
    st.markdown("""
    - Location: **bonus only** (no penalty)
    - Education: **1 point** tiebreaker only
    - Consulting: **penalty only** with weak AI evidence
    - Signals: **capped at 20pts** — prevents popularity bias
    - Names/gender/age: **never used**
    """)

    st.markdown("---")
    st.caption("Built by **Paarth Agrawal**")
    st.caption("AI Tools: Claude, ChatGPT, Gemini, Redrob AI")

# ── TABS ──────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📁 Upload & Rank",
    "🔍 Compare",
    "📊 Analytics",
    "📖 How It Works",
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

            col_btn, col_info = st.columns([1, 3])
            with col_btn:
                run = st.button("🚀 Rank Candidates", type="primary")
            with col_info:
                st.caption("Results appear below after ranking")

            if run:
                results: List[Dict] = []
                req_skills = [s.lower() for s in JOB.get("required_skills", [])]

                # Use custom weights from sidebar
                custom_job = {**JOB}

                progress = st.progress(0, text="Scoring candidates...")
                for idx, candidate in enumerate(candidates):
                    score, reasoning = score_candidate(candidate, JOB)
                    profile   = candidate.get("profile", {})
                    signals   = candidate.get("redrob_signals", {})
                    skills    = candidate.get("skills", [])
                    education = candidate.get("education", [])
                    career    = candidate.get("career_history", [])
                    title     = profile.get("current_title", "")
                    years     = profile.get("years_of_experience", 0)

                    cand_skills = [s["name"].lower() for s in skills]
                    matched = [s for s in req_skills if s in cand_skills]
                    missing = [s for s in req_skills if s not in cand_skills]

                    full_text = deduplicate_text(
                        profile.get("summary", "").lower() + " " +
                        " ".join(j.get("description", "").lower() for j in career)
                    )

                    breakdown = get_score_breakdown(candidate, JOB)
                    sem_sim   = 0.0
                    confidence = get_confidence(matched, sem_sim, signals)
                    conf_reasons = get_confidence_reasons(matched, sem_sim, signals)

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
                        "confidence":    confidence,
                        "conf_reasons":  conf_reasons,
                        "reasoning":     reasoning,
                        "breakdown":     breakdown,
                        "_candidate":    candidate,
                    })
                    progress.progress(
                        (idx + 1) / len(candidates),
                        text=f"Scoring {idx+1}/{len(candidates)}..."
                    )

                progress.empty()
                results.sort(key=lambda x: x["score"], reverse=True)
                qualified    = [r for r in results if r["score"] > 0]
                disqualified = [r for r in results if r["score"] == 0]

                # Metrics
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total", len(results))
                m2.metric("Qualified", len(qualified))
                m3.metric("Disqualified", len(disqualified))
                m4.metric("Top Score", f"{qualified[0]['score']:.1f}" if qualified else "0")
                m5.metric(
                    "High Confidence",
                    sum(1 for r in qualified if r["confidence"] == "High")
                )

                # Top candidate spotlight
                if qualified:
                    top = qualified[0]
                    st.markdown("---")
                    st.markdown("## 🏆 Top Candidate")
                    sp1, sp2, sp3, sp4, sp5 = st.columns(5)
                    sp1.markdown(f"**{top['name']}**  \n{fix_title_caps(top['title'])}")
                    sp2.metric("Score", f"{top['score']:.2f}")
                    sp3.metric("Confidence", top["confidence"])
                    sp4.metric("Skills", f"{len(top['matched'])}/14")
                    sp5.metric("Notice", f"{top['notice']}d")

                    st.markdown(f"**Why #1:** {top['reasoning']}")

                    # Score breakdown with progress bars
                    st.markdown("**Score Breakdown:**")
                    max_pts = {
                        "Skills": 50, "Experience": 15, "Title": 15,
                        "Career": 10, "Location": 2, "Signals": 20
                    }
                    bd_cols = st.columns(len(top["breakdown"]))
                    for j, (key, val) in enumerate(top["breakdown"].items()):
                        mx = max_pts.get(key, 20)
                        bd_cols[j].metric(key, f"{val}/{mx}")
                        bd_cols[j].progress(min(1.0, max(0.0, val / mx)))

                    if len(qualified) >= 2:
                        second = qualified[1]
                        comp = compare_candidates(
                            top["_candidate"], second["_candidate"],
                            JOB, top["score"], second["score"]
                        )
                        st.info(f"**vs #{2} {second['name']}:** {comp}")

                # Filter
                st.markdown("---")
                fc1, fc2 = st.columns(2)
                with fc1:
                    conf_filter = st.selectbox(
                        "Filter by confidence",
                        ["All", "High", "Medium", "Low"]
                    )
                with fc2:
                    min_skills = st.slider("Minimum skills matched", 0, 14, 0)

                filtered = [
                    r for r in qualified
                    if (conf_filter == "All" or r["confidence"] == conf_filter)
                    and len(r["matched"]) >= min_skills
                ]

                st.markdown(f"### {len(filtered)} Candidates")

                for i, r in enumerate(filtered, 1):
                    emoji = "🟢" if r["score"] >= 60 else "🟡" if r["score"] >= 35 else "🔴"
                    conf_icon = "🔵" if r["confidence"] == "High" else "⚪" if r["confidence"] == "Medium" else "🔘"

                    with st.expander(
                        f"{emoji} #{i} {r['name']} — "
                        f"{fix_title_caps(r['title'])} — "
                        f"Score: {r['score']:.2f} {conf_icon} {r['confidence']}"
                    ):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.markdown(f"**Years:** {r['years']}")
                        c2.markdown(f"**Open:** {'✅' if r['open'] else '❌'}")
                        c3.markdown(f"**Response:** {int(r['response_rate']*100)}%")
                        c4.markdown(f"**Notice:** {r['notice']}d")

                        st.markdown(f"**Matched:** `{', '.join(r['matched'][:6]) or 'None'}`")
                        if r["missing"]:
                            st.markdown(f"**Missing:** `{', '.join(r['missing'][:4])}`")

                        # Confidence detail
                        with st.expander(f"Confidence: {r['confidence']} — why?"):
                            for cr in r["conf_reasons"]:
                                st.markdown(f"- {cr}")

                        # Score breakdown
                        max_pts = {
                            "Skills": 50, "Experience": 15, "Title": 15,
                            "Career": 10, "Location": 2, "Signals": 20
                        }
                        bd_c = st.columns(len(r["breakdown"]))
                        for j, (key, val) in enumerate(r["breakdown"].items()):
                            mx = max_pts.get(key, 20)
                            bd_c[j].metric(key, f"{val}/{mx}")
                            bd_c[j].progress(min(1.0, max(0.0, val / mx)))

                        st.markdown(f"**Reasoning:** {r['reasoning']}")

                # Disqualified
                if disqualified:
                    st.markdown("---")
                    with st.expander(f"❌ {len(disqualified)} Disqualified"):
                        for r in disqualified:
                            st.markdown(f"- **{r['name']}** ({r['title']}) — {r['reasoning']}")

                # Download
                st.markdown("---")
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["candidate_id", "rank", "score", "reasoning"])
                for rank, r in enumerate(qualified[:TOP_N_CANDIDATES], 1):
                    writer.writerow([r["candidate_id"], rank, r["score"], r["reasoning"]])
                st.download_button(
                    "📥 Download submission.csv",
                    data=buf.getvalue(),
                    file_name="submission.csv",
                    mime="text/csv"
                )

                st.session_state["results"] = qualified
                st.session_state["disqualified"] = disqualified

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)

with tab2:
    st.markdown("### 🔍 Candidate Comparison")
    if "results" in st.session_state and st.session_state["results"]:
        qualified = st.session_state["results"]
        names = [
            f"#{i+1} {r['name']} (Score: {r['score']:.2f})"
            for i, r in enumerate(qualified[:20])
        ]
        c1, c2 = st.columns(2)
        with c1:
            a_idx = st.selectbox("Candidate A", range(len(names)),
                                  format_func=lambda i: names[i], key="ca")
        with c2:
            b_idx = st.selectbox("Candidate B", range(len(names)),
                                  format_func=lambda i: names[i],
                                  index=min(1, len(names)-1), key="cb")

        if a_idx != b_idx:
            a = qualified[a_idx]
            b = qualified[b_idx]

            comp = compare_candidates(
                a["_candidate"], b["_candidate"],
                JOB, a["score"], b["score"]
            )
            st.info(f"**Result:** {comp}")

            # Side by side
            st.markdown("#### Score Breakdown")
            max_pts = {
                "Skills": 50, "Experience": 15, "Title": 15,
                "Career": 10, "Location": 2, "Signals": 20
            }

            categories = list(a["breakdown"].keys())
            vals_a = [a["breakdown"][c] for c in categories]
            vals_b = [b["breakdown"][c] for c in categories]

            fig = go.Figure(data=[
                go.Bar(name=a["name"], x=categories, y=vals_a,
                       marker_color="#2E86AB"),
                go.Bar(name=b["name"], x=categories, y=vals_b,
                       marker_color="#A23B72"),
            ])
            fig.update_layout(
                barmode="group",
                title="Score Breakdown Comparison",
                height=350,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Upload and rank candidates in Tab 1 first.")

with tab3:
    st.markdown("### 📊 Analytics")
    if "results" in st.session_state:
        qualified    = st.session_state["results"]
        disqualified = st.session_state.get("disqualified", [])
        all_results  = qualified + disqualified

        col1, col2 = st.columns(2)

        with col1:
            # Score distribution
            scores = [r["score"] for r in qualified if r["score"] > 0]
            fig_hist = px.histogram(
                x=scores, nbins=20,
                title="Score Distribution (Qualified Candidates)",
                labels={"x": "Score", "y": "Count"},
                color_discrete_sequence=["#2E86AB"]
            )
            fig_hist.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=300
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col2:
            # Confidence distribution
            conf_counts = {
                "High":   sum(1 for r in qualified if r["confidence"] == "High"),
                "Medium": sum(1 for r in qualified if r["confidence"] == "Medium"),
                "Low":    sum(1 for r in qualified if r["confidence"] == "Low"),
            }
            fig_conf = px.pie(
                values=list(conf_counts.values()),
                names=list(conf_counts.keys()),
                title="Confidence Distribution",
                color_discrete_sequence=["#2E86AB", "#F18F01", "#C73E1D"]
            )
            fig_conf.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                height=300
            )
            st.plotly_chart(fig_conf, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            # Skill coverage
            all_matched = []
            for r in qualified[:20]:
                all_matched.extend(r["matched"])
            from collections import Counter
            skill_counts = Counter(all_matched).most_common(10)
            if skill_counts:
                fig_skills = px.bar(
                    x=[s[1] for s in skill_counts],
                    y=[s[0] for s in skill_counts],
                    orientation="h",
                    title="Most Common Matched Skills (Top 20)",
                    labels={"x": "Count", "y": "Skill"},
                    color_discrete_sequence=["#2E86AB"]
                )
                fig_skills.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=300
                )
                st.plotly_chart(fig_skills, use_container_width=True)

        with col4:
            # Qualified vs disqualified
            fig_qual = px.pie(
                values=[len(qualified), len(disqualified)],
                names=["Qualified", "Disqualified"],
                title="Qualification Rate",
                color_discrete_sequence=["#2E86AB", "#C73E1D"]
            )
            fig_qual.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                height=300
            )
            st.plotly_chart(fig_qual, use_container_width=True)
    else:
        st.info("Upload and rank candidates in Tab 1 first.")

with tab4:
    st.markdown("### 📖 How It Works")
    st.markdown("""
    #### Why This Beats Traditional ATS

    | Traditional ATS | This System |
    |----------------|------------|
    | Keyword matching only | Exact + alias + TF-IDF semantic |
    | No behavioral signals | All 23 platform signals |
    | No verification | Verified assessment scores |
    | Binary pass/fail | Tiered scoring with confidence |
    | No honeypot detection | 5-check honeypot filter |

    #### Why TF-IDF Instead of Sentence Transformers?

    We deliberately chose TF-IDF over `all-MiniLM-L6-v2` because:
    - ✅ No model download required
    - ✅ CPU-only — no GPU needed
    - ✅ Deterministic and reproducible
    - ✅ Total runtime stays under 4 minutes
    - ✅ No external dependencies

    TF-IDF with bigrams captures most technical term overlap effectively.

    #### Complexity
    - **Time:** O(n) per candidate, O(n log n) for final sort
    - **Space:** O(n) — all candidates in memory for ranking
    - **Runtime:** ~4 minutes for 100,000 candidates on CPU
    """)

with tab5:
    st.markdown("### ⚖️ Fairness Design")
    st.success("""
    **What we explicitly ignore:**
    ✓ Gender  ✓ Name  ✓ Age  ✓ Photo  ✓ Religion  ✓ Nationality
    """)
    st.markdown("""
    #### Location
    India proximity gives **+2 bonus only**. Zero penalty for global candidates.
    A candidate in San Francisco with 8 matched skills ranks above an India-based
    candidate with 2 matched skills.

    #### Education
    Maximum **1 point** — pure tiebreaker.
    A self-taught engineer with 8 matched skills outranks a Tier-1 graduate
    with 0 matched skills every time.

    #### Consulting Firms
    Penalty **only when** consulting background AND weak AI evidence both apply.
    A TCS engineer who built RAG systems in production scores competitively.

    #### Behavioral Signals
    **Capped at 20 points** — technical score always dominates.
    A popular candidate with great engagement but zero AI skills cannot
    rank above a skilled but less active candidate.

    #### Salary
    **±1 point only** — candidates slightly above budget are not heavily penalised.

    #### Known Limitations
    - Implicit bias may exist in the job description language itself
    - Candidates who understated their skills on the platform may be underscored
    - Historical signal data may not reflect current intent
    """)