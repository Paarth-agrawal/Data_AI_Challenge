"""
Central configuration for the AI Candidate Ranking System.
All thresholds, weights, and constants live here.
Change values here — no need to touch scorer.py or main.py.
"""

# ── SCORING WEIGHTS ───────────────────────────────────────────────────
WEIGHTS = {
    "skills":      35,  # Direct JD skill match — primary signal
    "assessment":   5,  # Verified platform test scores
    "bonus":        5,  # Nice-to-have skills (LoRA, QLoRA etc.)
    "semantic":    10,  # TF-IDF cosine similarity to JD text
    "experience":  15,  # Years of experience (5-9yr sweet spot)
    "title":       15,  # Job title alignment
    "career":      10,  # Product company history
    "signals":     20,  # All 23 behavioral signals (capped)
    "location":     2,  # India-based bonus (never a penalty)
    "education":    1,  # Tier-1 institution tiebreaker only
}

# ── EXPERIENCE ────────────────────────────────────────────────────────
MIN_EXPERIENCE_YEARS = 5
MAX_EXPERIENCE_YEARS = 9
MIN_YEARS_TO_QUALIFY = 2   # Below this = instant disqualification

# ── SEMANTIC SIMILARITY THRESHOLDS ───────────────────────────────────
SEMANTIC_HIGH   = 0.15     # Strong semantic alignment
SEMANTIC_MEDIUM = 0.08     # Moderate semantic alignment

# ── CONFIDENCE SCORE THRESHOLDS ──────────────────────────────────────
CONFIDENCE_HIGH   = 7      # Evidence score >= this = High confidence
CONFIDENCE_MEDIUM = 4      # Evidence score >= this = Medium confidence

CONFIDENCE_SKILL_STRONG  = 6   # Skills matched for max skill evidence
CONFIDENCE_SKILL_GOOD    = 4   # Skills matched for good skill evidence
CONFIDENCE_SKILL_PARTIAL = 2   # Skills matched for partial evidence

CONFIDENCE_PROFILE_STRONG = 75  # Profile completeness % for strong signal
CONFIDENCE_PROFILE_MEDIUM = 50  # Profile completeness % for medium signal

# ── BEHAVIORAL SIGNAL THRESHOLDS ─────────────────────────────────────
SIGNAL_MAX_SCORE          = 20   # Hard cap on behavioral signal score
SIGNAL_MIN_SCORE          = -5   # Floor on behavioral signal score

RESPONSE_RATE_HIGH        = 0.7  # Above this = high response rate
RESPONSE_RATE_LOW         = 0.3  # Below this = low response rate

RECENCY_VERY_ACTIVE_DAYS  = 7    # Active within 7 days
RECENCY_ACTIVE_DAYS       = 30   # Active within 30 days
RECENCY_RECENT_DAYS       = 90   # Active within 90 days

NOTICE_IMMEDIATE          = 0    # Immediate joiner
NOTICE_SHORT              = 30   # Short notice period
NOTICE_LONG               = 90   # Long notice period

GITHUB_STRONG             = 70   # Strong GitHub activity score
GITHUB_MODERATE           = 40   # Moderate GitHub activity score

RECRUITERS_SAVED_HIGH     = 5    # Saved by this many = strong signal
RECRUITERS_SAVED_LOW      = 2    # Saved by this many = minor signal

INTERVIEW_RATE_GOOD       = 0.8  # Good interview completion rate
INTERVIEW_RATE_POOR       = 0.4  # Poor interview completion rate

OFFER_RATE_GOOD           = 0.7  # Good offer acceptance rate
OFFER_RATE_POOR           = 0.3  # Poor offer acceptance rate

PROFILE_COMPLETE_STRONG   = 80   # Profile completeness for bonus
PROFILE_COMPLETE_WEAK     = 50   # Profile completeness for penalty

VIEWS_HIGH                = 20   # High profile views in 30 days
VIEWS_MEDIUM              = 10   # Medium profile views
APPS_VERY_ACTIVE          = 5    # Very actively applying
APPS_ACTIVE               = 1    # Actively applying

CONNECTIONS_STRONG        = 500  # Strong network signal
CONNECTIONS_MODERATE      = 300  # Moderate network signal
ENDORSEMENTS_STRONG       = 30   # Strong endorsements
ENDORSEMENTS_MODERATE     = 15   # Moderate endorsements
PLATFORM_TENURE_DAYS      = 180  # Days on platform for tenure bonus
SEARCH_APPEARANCE_HIGH    = 200  # High search appearance signal

SALARY_WITHIN_RATIO       = 0.8  # Salary max <= budget * this = within budget
SALARY_ABOVE_RATIO        = 1.2  # Salary max > budget * this = above budget

# ── HONEYPOT DETECTION ────────────────────────────────────────────────
HONEYPOT_CAREER_TOLERANCE_MONTHS = 48   # Extra months allowed for parallel work
HONEYPOT_GRAD_YEAR_TOLERANCE     = 2    # Extra years allowed for grad year mismatch
HONEYPOT_MIN_ENDORSEMENTS        = 5    # Below this = suspicious if many expert skills

# ── CONSULTING ────────────────────────────────────────────────────────
CONSULTING_ALL_PENALTY          = 15   # Entire career consulting + weak AI evidence
CONSULTING_ALL_WEAK_PENALTY     = 7    # Entire career consulting + some AI evidence
CONSULTING_MAJORITY_PENALTY     = 4    # >50% consulting
CONSULTING_MAJORITY_THRESHOLD   = 0.5  # Ratio above which = majority consulting
CONSULTING_AI_EVIDENCE_MIN      = 3    # Min AI keywords to reduce penalty

# ── TF-IDF ────────────────────────────────────────────────────────────
TFIDF_MAX_FEATURES    = 8000
TFIDF_NGRAM_MIN       = 1
TFIDF_NGRAM_MAX       = 2
TFIDF_MAX_WORD_REPEAT = 3    # Max times a word can appear (anti-exploitation)

# ── SALARY ────────────────────────────────────────────────────────────
SALARY_BUDGET_MAX_LPA = 40   # Maximum salary budget in LPA

# ── OUTPUT ────────────────────────────────────────────────────────────
TOP_N_CANDIDATES = 100   # Number of candidates to output