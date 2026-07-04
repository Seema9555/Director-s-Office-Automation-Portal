import os
import glob
import sys
import django
from django.core.management import call_command

# Django Environment Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Director_Portal.settings')
django.setup()

def run_import():
    print("==========================================")
    print("🚀 AUTOMATED IMPORT: Smart Mode (Even Sem)")
    print("==========================================\n")
    
    folder_path = 'teacher_data'
    
    if not os.path.exists(folder_path):
        print(f"❌ ERROR: '{folder_path}' फोल्डर नहीं मिला!")
        return

    # 1. Allocation File Dhundna (Teacher Mapping)
    # Logic: File name mein 'course_master' aur '2024-25(2)' hona chahiye (Even Sem)
    files = os.listdir(folder_path)
    alloc_file = None
    
    for f in files:
        if "course_master" in f.lower() and "2024-25(2)" in f and f.endswith(".csv"):
            alloc_file = os.path.join(folder_path, f)
            break
            
    if not alloc_file:
        print("❌ Error: Allocation file (course_master...2024-25(2)) nahi mili!")
        print("   मौजूद फाइलों के नाम चेक करें।")
        return

    print(f"✅ Main Allocation File Found: {os.path.basename(alloc_file)}")

    # 2. Credit File Dhundna (Subject Credits)
    # Logic: File name mein 'QP' aur 'credit' hona chahiye
    credit_files = []
    for f in files:
        if "qp" in f.lower() and "credit" in f.lower() and f.endswith(".csv"):
            credit_files.append(os.path.join(folder_path, f))
            
    if credit_files:
        print(f"✅ Credit Files Found: {len(credit_files)} files")
    else:
        print("⚠️ Warning: Credit वाली फाइल नहीं मिली (Subjects import होंगे पर Credits 4 रहेंगे)।")

    # 3. Import Command Run Karna
    print("\n⏳ Importing Data... (Please wait)")
    try:
        call_command(
            'import_academic_data',
            allocations=alloc_file,
            credits=credit_files,
            session='2024-25(2)'
        )
    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == '__main__':
    run_import()