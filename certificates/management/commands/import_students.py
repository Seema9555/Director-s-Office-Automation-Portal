# import csv
# import os
# from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
# from certificates.models import Student
# from datetime import datetime

# class Command(BaseCommand):
#     help = 'Import students from CSV files (Cols C-W Covered)'

#     def add_arguments(self, parser):
#         parser.add_argument('csv_file', type=str, help='Path to the CSV file')

#     def handle(self, *args, **kwargs):
#         csv_file_path = kwargs['csv_file']
        
#         if not os.path.exists(csv_file_path):
#             self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
#             return

#         self.stdout.write(self.style.SUCCESS(f'Importing data from {csv_file_path}...'))

#         with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
#             reader = csv.DictReader(file)
            
#             count = 0
#             for row in reader:
#                 try:
#                     # 1. Date Parsing
#                     dob_str = row.get('DOB', '').strip()
#                     dob_obj = None
#                     if dob_str:
#                         for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
#                             try:
#                                 dob_obj = datetime.strptime(dob_str, fmt).date()
#                                 break
#                             except ValueError:
#                                 continue

#                     # 2. Key Data
#                     roll_no = row['RollNo'].strip()     # Col C
#                     first_name = row['Name'].strip()    # Col E
#                     email_addr = row.get('email', '').strip() # Col W
                    
#                     # 3. User Creation
#                     user, created = User.objects.get_or_create(username=roll_no)
#                     if created:
#                         user.set_password(roll_no)
#                         user.email = email_addr
#                         user.save()

#                     # 4. Student Data Update (Columns C to W Mapped)
#                     student, created = Student.objects.update_or_create(
#                         enrollment_no=roll_no,
#                         defaults={
#                             'user': user,
#                             'branch': row.get('Branch', 'CSE'),          # Col D
#                             'full_name': first_name,                     # Col E
#                             'date_of_birth': dob_obj,                    # Col F
#                             'father_name': row.get('FatherName', ''),    # Col G
#                             'mother_name': row.get('MotherName', ''),    # Col H
#                             'gender': row.get('Gender', 'MALE').upper(), # Col I
#                             'category': row.get('Category', ''),         # Col J
#                             'sub_category': row.get('SubCategory', ''),  # Col K
#                             'blood_group': row.get('BloodGroupType', ''),# Col L
                            
#                             # Permanent Address
#                             'permanent_address': row.get('PermanentAddress', ''), # Col M
#                             'district': row.get('District', ''),                  # Col N
#                             'state': row.get('State', ''),                        # Col O
#                             'country': row.get('Country', 'INDIA'),               # Col P (Added)
#                             'pincode': row.get('PinCode', ''),                    # Col Q
                            
#                             # Contact
#                             'parent_contact': row.get('ParentContactNo', ''),     # Col R
#                             'phone_number': row.get('LocalContactNo', ''),        # Col V (Mapped as Student Phone)
#                             'email': email_addr,                                  # Col W

#                             # Local Address
#                             'local_address': row.get('LocalAddress', ''),         # Col S
#                             'local_district': row.get('LocalDistrict', ''),       # Col T (Added)
#                             'local_pincode': row.get('LocalPinCode', ''),         # Col U (Added)
#                         }
#                     )
#                     count += 1
#                     if count % 50 == 0:
#                         self.stdout.write(f"Processed {count} students...")

#                 except Exception as e:
#                     self.stdout.write(self.style.ERROR(f"Error Row {count}: {e}"))

#         self.stdout.write(self.style.SUCCESS(f'Done! Successfully imported {count} students.'))


# import csv
# import os
# from datetime import datetime
# from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
# from django.db import transaction
# from certificates.models import Student

# class Command(BaseCommand):
#     help = 'Imports students from CSV files (CSE, ECE, MEE, etc.)'

#     def add_arguments(self, parser):
#         parser.add_argument('csv_files', nargs='+', type=str, help='Paths to the CSV files to import')

#     def handle(self, *args, **options):
#         csv_files = options['csv_files']

#         for file_path in csv_files:
#             self.stdout.write(self.style.WARNING(f'Processing file: {file_path}...'))
#             self.import_csv(file_path)

#     def import_csv(self, file_path):
#         if not os.path.exists(file_path):
#             self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
#             return

#         with open(file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM if present
#             reader = csv.DictReader(f)
            
#             # Normalize column names (strip spaces)
#             reader.fieldnames = [name.strip() for name in reader.fieldnames]

#             count = 0
#             for row in reader:
#                 # 1. Extract Mandatory Key Data
#                 roll_no = row.get('RollNo', '').strip()
#                 if not roll_no:
#                     continue  # Skip empty rows

#                 try:
#                     with transaction.atomic():
#                         # 2. Create or Get User (Username = RollNo, Password = RollNo)
#                         user, created = User.objects.get_or_create(username=roll_no)
#                         if created:
#                             user.set_password(roll_no) # Password is same as RollNo
#                             user.save()
                        
#                         # 3. Parse Date of Birth
#                         dob_str = row.get('DOB', '').strip()
#                         dob_obj = None
#                         if dob_str:
#                             try:
#                                 # Start by trying YYYY-MM-DD
#                                 dob_obj = datetime.strptime(dob_str, '%Y-%m-%d').date()
#                             except ValueError:
#                                 # Fallback for other formats if necessary
#                                 dob_obj = None

#                         # 4. Map CSV Columns to Student Model
#                         student_data = {
#                             'user': user,
#                             'branch': row.get('Branch', '').strip(),
#                             'full_name': row.get('Name', '').strip(),
#                             'date_of_birth': dob_obj,
#                             'father_name': row.get('FatherName', '').strip(),
#                             'mother_name': row.get('MotherName', '').strip(),
#                             'gender': row.get('Gender', '').upper().strip(), # Ensure uppercase for Model Choice
#                             'category': row.get('Category', '').strip(),
#                             'sub_category': row.get('SubCategory', '').strip(),
#                             'blood_group': row.get('BloodGroupType', '').strip(),
                            
#                             # Address Info
#                             'permanent_address': row.get('PermanentAddress', '').strip(),
#                             'district': row.get('District', '').strip(),
#                             'state': row.get('State', '').strip(),
#                             'country': row.get('Country', '').strip(),
#                             'pincode': row.get('PinCode', '').strip(),
                            
#                             # Contact Info
#                             'parent_contact': row.get('ParentContactNo', '').strip(),
#                             'phone_number': row.get('LocalContactNo', '').strip(), # Assumed LocalContact is Student Phone
#                             'email': row.get('email', '').strip(),
                            
#                             # Local Address
#                             'local_address': row.get('LocalAddress', '').strip(),
#                             'local_district': row.get('LocalDistrict', '').strip(),
#                             'local_pincode': row.get('LocalPinCode', '').strip(),

#                             # Defaults (Override model defaults if specific batch is known)
#                             'degree': 'B.Tech',
#                             'academic_session': '2023-2027', # Inferred from dates (2023 admission)
#                         }

#                         # 5. Update or Create Student Record
#                         Student.objects.update_or_create(
#                             enrollment_no=roll_no,
#                             defaults=student_data
#                         )
#                         count += 1

#                 except Exception as e:
#                     self.stdout.write(self.style.ERROR(f"Error importing {roll_no}: {str(e)}"))

#             self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} students from {file_path}'))

# import csv
# import os
# from datetime import datetime
# from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
# from django.db import transaction
# from certificates.models import Student

# class Command(BaseCommand):
#     help = 'Imports students with Enhanced DOB Debugging (Supports MM/DD/YYYY)'

#     def add_arguments(self, parser):
#         parser.add_argument('csv_files', nargs='+', type=str, help='Paths to the CSV files')

#     def handle(self, *args, **options):
#         csv_files = options['csv_files']
        
#         for csv_file_path in csv_files:
#             if not os.path.exists(csv_file_path):
#                 self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
#                 continue

#             self.stdout.write(self.style.WARNING(f'\nProcessing: {os.path.basename(csv_file_path)}...'))
#             self.import_file(csv_file_path)

#     def import_file(self, csv_file_path):
#         with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
#             reader = csv.DictReader(file)
            
#             # 1. Normalize Headers
#             reader.fieldnames = [name.strip() for name in reader.fieldnames]
            
#             if 'DOB' not in reader.fieldnames:
#                 self.stdout.write(self.style.ERROR(f"  CRITICAL ERROR: 'DOB' column not found! Found: {reader.fieldnames}"))
#                 return
#             else:
#                 self.stdout.write(self.style.SUCCESS(f"  OK: Found 'DOB' column."))

#             count = 0
#             updated_dob_count = 0
            
#             for row in reader:
#                 roll_no = row.get('RollNo', '').strip()
#                 if not roll_no: continue

#                 # 2. Robust Date Parsing
#                 dob_str = row.get('DOB', '').strip()
#                 dob_obj = None
                
#                 if dob_str:
#                     # Added '%m/%d/%Y' and '%m-%d-%Y' to handle your current error
#                     date_formats = [
#                         '%Y-%m-%d',             # 2004-08-23
#                         '%d-%m-%Y',             # 23-08-2004
#                         '%d/%m/%Y',             # 23/08/2004
#                         '%m/%d/%Y',             # 08/23/2004 (Ye format miss ho raha tha)
#                         '%m-%d-%Y',             # 08-23-2004
#                         '%Y/%m/%d',             # 2004/08/23
#                         '%d-%b-%y',             # 23-Aug-04
#                         '%d-%b-%Y'              # 23-Aug-2004
#                     ]
#                     for fmt in date_formats:
#                         try:
#                             dob_obj = datetime.strptime(dob_str, fmt).date()
#                             break
#                         except ValueError:
#                             continue
                    
#                     if dob_obj is None:
#                         self.stdout.write(self.style.ERROR(f"  Warning: Could not parse DOB '{dob_str}' for {roll_no}"))

#                 try:
#                     with transaction.atomic():
#                         # Update specific fields
#                         defaults_data = {}
#                         if dob_obj:
#                             defaults_data['date_of_birth'] = dob_obj
                        
#                         # Add other fields if you want them to update on re-run
#                         # defaults_data['academic_session'] = '2023-2027' 

#                         student, created = Student.objects.update_or_create(
#                             enrollment_no=roll_no,
#                             defaults=defaults_data
#                         )
#                         if dob_obj:
#                             updated_dob_count += 1
#                         count += 1

#                 except Exception as e:
#                     self.stdout.write(self.style.ERROR(f"  Error {roll_no}: {e}"))

#             self.stdout.write(self.style.SUCCESS(f'  Finished: Checked {count} students. Updated DOB for {updated_dob_count}.'))

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from certificates.models import Student

class Command(BaseCommand):
    help = 'Imports 2024-2028 Batch students from CSV files'

    def add_arguments(self, parser):
        parser.add_argument('csv_files', nargs='+', type=str, help='Paths to the CSV files')

    def handle(self, *args, **options):
        csv_files = options['csv_files']
        
        for csv_file_path in csv_files:
            if not os.path.exists(csv_file_path):
                self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
                continue

            self.stdout.write(self.style.WARNING(f'\nProcessing: {os.path.basename(csv_file_path)}...'))
            self.import_file(csv_file_path)

    def import_file(self, csv_file_path):
        with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            # Normalize headers
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            
            if 'DOB' not in reader.fieldnames:
                self.stdout.write(self.style.ERROR(f"  CRITICAL: 'DOB' column missing in {os.path.basename(csv_file_path)}"))
                return

            count = 0
            for row in reader:
                roll_no = row.get('RollNo', '').strip()
                if not roll_no: continue

                # 1. Robust Date Parsing (Prioritizing MM/DD/YYYY for this batch)
                dob_str = row.get('DOB', '').strip()
                dob_obj = None
                if dob_str:
                    date_formats = [
                        '%m/%d/%Y', # 12/30/2005 (Most common in this batch)
                        '%d/%m/%Y', # 30/12/2005
                        '%Y-%m-%d', 
                        '%d-%m-%Y',
                        '%d-%b-%y'
                    ]
                    for fmt in date_formats:
                        try:
                            dob_obj = datetime.strptime(dob_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if dob_obj is None:
                        self.stdout.write(self.style.ERROR(f"  Warning: Date parse failed '{dob_str}' for {roll_no}"))

                try:
                    with transaction.atomic():
                        # 2. Create User
                        user, created = User.objects.get_or_create(username=roll_no)
                        if created:
                            user.set_password(roll_no)
                            user.email = row.get('email', '').strip()
                            user.save()

                        # 3. Create/Update Student
                        Student.objects.update_or_create(
                            enrollment_no=roll_no,
                            defaults={
                                'user': user,
                                'branch': row.get('Branch', 'CSE').strip(),
                                'full_name': row.get('Name', '').strip(),
                                'date_of_birth': dob_obj,
                                'father_name': row.get('FatherName', '').strip(),
                                'mother_name': row.get('MotherName', '').strip(),
                                'gender': row.get('Gender', 'MALE').upper().strip(),
                                'category': row.get('Category', '').strip(),
                                'sub_category': row.get('SubCategory', '').strip(),
                                'blood_group': row.get('BloodGroupType', '').strip(),
                                
                                # Addresses
                                'permanent_address': row.get('PermanentAddress', '').strip(),
                                'district': row.get('District', '').strip(),
                                'state': row.get('State', '').strip(),
                                'country': row.get('Country', 'INDIA').strip(),
                                'pincode': row.get('PinCode', '').strip(),
                                
                                'local_address': row.get('LocalAddress', '').strip(),
                                'local_district': row.get('LocalDistrict', '').strip(),
                                'local_pincode': row.get('LocalPinCode', '').strip(),

                                # Contact
                                'parent_contact': row.get('ParentContactNo', '').strip(),
                                'phone_number': row.get('LocalContactNo', '').strip(),
                                'email': row.get('email', '').strip(),

                                # BATCH SETTING (Important)
                                'academic_session': '2024-2028',
                                'degree': 'B.Tech',
                            }
                        )
                        count += 1
                        if count % 50 == 0:
                            self.stdout.write(f"  Processed {count}...")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error {roll_no}: {e}"))

            self.stdout.write(self.style.SUCCESS(f'  Done! Imported {count} students from {os.path.basename(csv_file_path)}'))