import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from certificates.models import Student
from datetime import datetime

class Command(BaseCommand):
    help = 'Import students from CSV files (Cols C-W Covered)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Importing data from {csv_file_path}...'))

        with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            count = 0
            for row in reader:
                try:
                    # 1. Date Parsing
                    dob_str = row.get('DOB', '').strip()
                    dob_obj = None
                    if dob_str:
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                            try:
                                dob_obj = datetime.strptime(dob_str, fmt).date()
                                break
                            except ValueError:
                                continue

                    # 2. Key Data
                    roll_no = row['RollNo'].strip()     # Col C
                    first_name = row['Name'].strip()    # Col E
                    email_addr = row.get('email', '').strip() # Col W
                    
                    # 3. User Creation
                    user, created = User.objects.get_or_create(username=roll_no)
                    if created:
                        user.set_password(roll_no)
                        user.email = email_addr
                        user.save()

                    # 4. Student Data Update (Columns C to W Mapped)
                    student, created = Student.objects.update_or_create(
                        enrollment_no=roll_no,
                        defaults={
                            'user': user,
                            'branch': row.get('Branch', 'CSE'),          # Col D
                            'full_name': first_name,                     # Col E
                            'date_of_birth': dob_obj,                    # Col F
                            'father_name': row.get('FatherName', ''),    # Col G
                            'mother_name': row.get('MotherName', ''),    # Col H
                            'gender': row.get('Gender', 'MALE').upper(), # Col I
                            'category': row.get('Category', ''),         # Col J
                            'sub_category': row.get('SubCategory', ''),  # Col K
                            'blood_group': row.get('BloodGroupType', ''),# Col L
                            
                            # Permanent Address
                            'permanent_address': row.get('PermanentAddress', ''), # Col M
                            'district': row.get('District', ''),                  # Col N
                            'state': row.get('State', ''),                        # Col O
                            'country': row.get('Country', 'INDIA'),               # Col P (Added)
                            'pincode': row.get('PinCode', ''),                    # Col Q
                            
                            # Contact
                            'parent_contact': row.get('ParentContactNo', ''),     # Col R
                            'phone_number': row.get('LocalContactNo', ''),        # Col V (Mapped as Student Phone)
                            'email': email_addr,                                  # Col W

                            # Local Address
                            'local_address': row.get('LocalAddress', ''),         # Col S
                            'local_district': row.get('LocalDistrict', ''),       # Col T (Added)
                            'local_pincode': row.get('LocalPinCode', ''),         # Col U (Added)
                        }
                    )
                    count += 1
                    if count % 50 == 0:
                        self.stdout.write(f"Processed {count} students...")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error Row {count}: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Done! Successfully imported {count} students.'))