import csv
import os
from django.core.management.base import BaseCommand
from certificates.models import Teacher, Subject, CourseAllocation
from django.db import transaction

class Command(BaseCommand):
    help = 'Import academic data (Teachers, Subjects, Allocations) from CSV'

    def add_arguments(self, parser):
        # Default assumes file is in project root
        parser.add_argument('--file', type=str, default='student data.csv', help='Path to CSV file')

    def handle(self, *args, **options):
        file_path = options['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            self.stdout.write(self.style.WARNING('Please place "student data.csv" in the same folder as manage.py'))
            return

        self.stdout.write(self.style.SUCCESS(f'Reading file: {file_path}...'))

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # Clean header names (remove spaces like ' Course code')
                reader.fieldnames = [name.strip() for name in reader.fieldnames]
                
                created_teachers = 0
                created_subjects = 0
                created_allocations = 0

                with transaction.atomic():
                    for row in reader:
                        # 1. Extract Data
                        course_code = row.get('Course code', '').strip()
                        branch = row.get('Branch', '').strip()
                        faculty_name = row.get('Faculty Name', '').strip()
                        sem_str = row.get('semester', '').strip()

                        # Skip empty rows
                        if not course_code or not sem_str:
                            continue

                        # Convert Semester to Int
                        try:
                            semester = int(float(sem_str))
                        except ValueError:
                            continue

                        # 2. Handle TEACHER
                        teacher = None
                        # Ignore placeholders like (FL), empty, or nan
                        if faculty_name and faculty_name.lower() not in ['(fl)', 'nan', '']:
                            # Try to find existing teacher first
                            teacher = Teacher.objects.filter(full_name__iexact=faculty_name).first()
                            
                            if not teacher:
                                # Create new teacher
                                teacher = Teacher.objects.create(
                                    full_name=faculty_name,
                                    employee_id='TEMP' # Placeholder
                                )
                                # Generate ID: FAC + DB ID (e.g., FAC005)
                                teacher.employee_id = f"FAC{teacher.id:03d}"
                                teacher.save()
                                created_teachers += 1

                        # 3. Handle SUBJECT
                        # Since CSV has no subject name, we use course_code as name for now
                        subject, sub_created = Subject.objects.get_or_create(
                            course_code=course_code,
                            defaults={
                                'name': course_code, 
                                'credits': 0, # Default until credit CSV is imported
                                'is_practical': False
                            }
                        )
                        if sub_created:
                            created_subjects += 1

                        # 4. Handle ALLOCATION & SESSION Logic
                        # Odd Sem -> 2025-26(1), Even Sem -> 2024-25(2)
                        if semester % 2 == 1:
                            session = "2025-26(1)"
                        else:
                            session = "2024-25(2)"

                        # Update or Create Allocation
                        CourseAllocation.objects.update_or_create(
                            session=session,
                            branch=branch,
                            semester=semester,
                            subject=subject,
                            defaults={'teacher': teacher}
                        )
                        created_allocations += 1

            self.stdout.write(self.style.SUCCESS('--------------------------------------------------'))
            self.stdout.write(self.style.SUCCESS(f'IMPORT COMPLETE!'))
            self.stdout.write(f'Teachers Created : {created_teachers}')
            self.stdout.write(f'Subjects Created : {created_subjects}')
            self.stdout.write(f'Allocations Processed : {created_allocations}')
            self.stdout.write(self.style.SUCCESS('--------------------------------------------------'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error occurred: {str(e)}'))