# seed.py
from supabase import create_client
import os

# Load environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# -----------------------------
# 1. Seed Classes
# -----------------------------
classes = [
    {"name": "Grade 1", "category": "Lower Primary"},
    {"name": "Grade 2", "category": "Lower Primary"},
    {"name": "Grade 3", "category": "Lower Primary"},
    {"name": "Grade 4", "category": "Upper Primary"},
    {"name": "Grade 5", "category": "Upper Primary"},
    {"name": "Grade 6", "category": "Upper Primary"},
    {"name": "Grade 7", "category": "Junior Secondary"},
    {"name": "Grade 8", "category": "Junior Secondary"},
    {"name": "Grade 9", "category": "Junior Secondary"},
    {"name": "Form 1", "category": "Secondary"},
    {"name": "Form 2", "category": "Secondary"},
    {"name": "Form 3", "category": "Secondary"},
    {"name": "Form 4", "category": "Secondary"},
]

existing_classes = supabase.table("classes").select("id").execute().data
if not existing_classes:
    supabase.table("classes").insert(classes).execute()
    print("✅ Classes seeded successfully")
else:
    print("⚠️ Classes already exist, skipping seeding")


# -----------------------------
# 2. Seed Subjects
# -----------------------------
subjects = [
    # Lower Primary
    {"name": "English", "category": "Lower Primary"},
    {"name": "Kiswahili", "category": "Lower Primary"},
    {"name": "Mathematics", "category": "Lower Primary"},
    {"name": "Environmental Activities", "category": "Lower Primary"},
    {"name": "Creative Arts", "category": "Lower Primary"},
    {"name": "Hygiene and Nutrition", "category": "Lower Primary"},
    # Upper Primary
    {"name": "English", "category": "Upper Primary"},
    {"name": "Kiswahili", "category": "Upper Primary"},
    {"name": "Mathematics", "category": "Upper Primary"},
    {"name": "Science and Technology", "category": "Upper Primary"},
    {"name": "Social Studies", "category": "Upper Primary"},
    {"name": "CRE", "category": "Upper Primary"},
    {"name": "Arts and Crafts", "category": "Upper Primary"},
    # Junior Secondary
    {"name": "English", "category": "Junior Secondary"},
    {"name": "Kiswahili", "category": "Junior Secondary"},
    {"name": "Mathematics", "category": "Junior Secondary"},
    {"name": "Integrated Science", "category": "Junior Secondary"},
    {"name": "Social Studies", "category": "Junior Secondary"},
    {"name": "CRE", "category": "Junior Secondary"},
    {"name": "Pre-Technical Studies", "category": "Junior Secondary"},
    # Secondary
    {"name": "English", "category": "Secondary"},
    {"name": "Kiswahili", "category": "Secondary"},
    {"name": "Mathematics", "category": "Secondary"},
    {"name": "Biology", "category": "Secondary"},
    {"name": "Physics", "category": "Secondary"},
    {"name": "Chemistry", "category": "Secondary"},
    {"name": "History", "category": "Secondary"},
    {"name": "Geography", "category": "Secondary"},
    {"name": "CRE", "category": "Secondary"},
    {"name": "Business Studies", "category": "Secondary"},
    {"name": "Computer Studies", "category": "Secondary"},
]

existing_subjects = supabase.table("subjects").select("id").execute().data
if not existing_subjects:
    supabase.table("subjects").insert(subjects).execute()
    print("✅ Subjects seeded successfully")
else:
    print("⚠️ Subjects already exist, skipping seeding")


# -----------------------------
# 3. Link Classes and Subjects
# -----------------------------
class_rows = supabase.table("classes").select("id,name,category").execute().data
subject_rows = supabase.table("subjects").select("id,name,category").execute().data

existing_links = supabase.table("class_subjects").select("id").execute().data

if not existing_links:
    mappings = []
    for cls in class_rows:
        for subj in subject_rows:
            if cls["category"] == subj["category"]:
                mappings.append({"class_id": cls["id"], "subject_id": subj["id"]})

    supabase.table("class_subjects").insert(mappings).execute()
    print("✅ Class-Subject mappings seeded successfully")
else:
    print("⚠️ Class-Subject mappings already exist, skipping seeding")
