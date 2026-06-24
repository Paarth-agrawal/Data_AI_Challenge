JOB = {
    "title": "Senior AI Engineer",

    "required_skills": [
        "Python", "Machine Learning", "Deep Learning", "NLP",
        "PyTorch", "TensorFlow", "Embeddings", "FAISS",
        "Elasticsearch", "Information Retrieval", "Ranking",
        "Sentence-Transformers", "Vector Database", "LLM"
    ],

    "bonus_skills": [
        "LoRA", "QLoRA", "Fine-tuning", "XGBoost",
        "Qdrant", "Pinecone", "Weaviate", "Milvus"
    ],

    "assessment_skill_map": [
        "NLP", "Machine Learning", "Deep Learning", "Python",
        "PyTorch", "TensorFlow", "Information Retrieval",
        "Fine-tuning LLMs", "LLM", "Embeddings"
    ],

    # Tiered title scoring — AI/ML roles score higher than generic tech
    "tiered_titles": {
        "tier_1": [
            "AI Engineer", "ML Engineer", "Machine Learning Engineer",
            "Applied Scientist", "Research Engineer", "NLP Engineer",
            "Recommendation Systems Engineer", "AI Researcher"
        ],
        "tier_2": [
            "Data Scientist", "Applied ML Engineer", "Staff ML Engineer",
            "Senior Applied Scientist", "Lead AI Engineer"
        ],
        "tier_3": [
            "Data Engineer", "Software Engineer", "Backend Engineer"
        ]
    },

    "avoid_titles": [
        "Marketing", "Sales", "HR Manager", "Human Resource",
        "Graphic Designer", "Content Writer", "Accountant",
        "Customer Support", "Project Manager", "Business Analyst",
        "Civil Engineer", "Mechanical Engineer", "Operations Manager"
    ],

    "junior_title_flags": [
        "junior", "intern", "trainee", "fresher", "entry level"
    ],

    "consulting_firms": [
        "tcs", "infosys", "wipro", "accenture",
        "cognizant", "capgemini"
    ],

    "min_experience_years": 5,
    "max_experience_years": 9,

    # Core AI concepts — boosted in semantic matching
    "ai_core_terms": [
        "embedding", "retrieval", "ranking", "llm", "rag",
        "transformer", "semantic search", "vector", "fine-tuning",
        "information retrieval", "faiss", "dense retrieval"
    ],

    "salary_budget_max_lpa": 40
}