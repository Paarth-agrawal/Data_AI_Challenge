JOB = {
    "title": "Senior AI Engineer",

    # Core required skills — directly from JD
    "required_skills": [
        "Python", "Machine Learning", "Deep Learning", "NLP",
        "PyTorch", "TensorFlow", "Embeddings", "FAISS",
        "Elasticsearch", "Information Retrieval", "Ranking",
        "Sentence-Transformers", "Vector Database", "LLM"
    ],

    # Nice-to-have skills from JD
    "bonus_skills": [
        "LoRA", "QLoRA", "Fine-tuning", "XGBoost",
        "Qdrant", "Pinecone", "Weaviate", "Milvus"
    ],

    # Skill assessment keys that map to our required skills
    # Used to pull actual test scores from skill_assessment_scores
    "assessment_skill_map": [
        "NLP", "Machine Learning", "Deep Learning", "Python",
        "PyTorch", "TensorFlow", "Information Retrieval",
        "Fine-tuning LLMs", "LLM", "Embeddings"
    ],

    # Experience sweet spot from JD
    "min_experience_years": 5,
    "max_experience_years": 9,

    # Titles that strongly match this role
    "preferred_titles": [
        "AI Engineer", "ML Engineer", "Machine Learning Engineer",
        "Data Scientist", "NLP Engineer", "Research Engineer",
        "Applied Scientist", "Recommendation Systems Engineer",
        "Data Engineer", "Backend Engineer", "Software Engineer"
    ],

    # Titles that mean completely wrong job function
    "avoid_titles": [
        "Marketing", "Sales", "HR Manager", "Human Resource",
        "Graphic Designer", "Content Writer", "Accountant",
        "Customer Support", "Project Manager", "Business Analyst",
        "Civil Engineer", "Mechanical Engineer", "Operations Manager"
    ],

    # Junior indicators — JD wants Senior level
    "junior_title_flags": [
        "junior", "intern", "trainee", "fresher", "entry level"
    ],

    # Firms where consulting-only experience is a red flag
    "consulting_firms": [
        "tcs", "infosys", "wipro", "accenture",
        "cognizant", "capgemini"
    ],

    # Salary budget for this role (INR LPA)
    # Candidates expecting way above this may not accept offer
    "salary_budget_max_lpa": 40
}