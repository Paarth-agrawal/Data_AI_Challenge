import json

# Open the sample file (small, only 10 candidates - perfect for testing)
with open("sample_candidates.json") as f:
    candidates = json.load(f)

print(f"Total candidates loaded: {len(candidates)}")

# Look at the first candidate in detail
first = candidates[0]

print("\n--- CANDIDATE PROFILE ---")
print("ID:", first["candidate_id"])
print("Name:", first["profile"]["anonymized_name"])
print("Headline:", first["profile"]["headline"])
print("Years of experience:", first["profile"]["years_of_experience"])
print("Current title:", first["profile"]["current_title"])

print("\n--- SKILLS ---")
for skill in first["skills"]:
    print(f"  {skill['name']} — {skill['proficiency']}")

print("\n--- CAREER HISTORY ---")
for job in first["career_history"]:
    print(f"  {job['title']} at {job['company']} ({job['duration_months']} months)")