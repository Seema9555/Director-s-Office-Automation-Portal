from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import TextChoices
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import uuid
import datetime
from datetime import timedelta
from datetime import date
# ========================================================================
# HELPER FUNCTIONS (for dynamic paths and defaults)
# ========================================================================

def get_signature_path(instance, filename):
    """Generates a unique path for each signatory's signature image."""
    # Replaces spaces with underscores for cleaner paths
    name = instance.name.replace(' ', '_')
    return f"signatures/{name}/{filename}"

def get_verification_document_path(instance, filename):
    """Generates a unique path for each student's verification document."""
    return f"verifications/{instance.student.enrollment_no}/{filename}"

def get_generated_certificate_path(instance, filename):
    """Generates a unique path for each generated certificate PDF."""
    return f"certificates/{instance.request.student.enrollment_no}/{filename}"

def generate_reference_no():
    """Generates a unique reference number, e.g., UIET-2025-A1B2C3D4."""
    year = datetime.date.today().year
    unique_part = uuid.uuid4().hex[:8].upper()
    return f"UIET-{year}-{unique_part}"

def get_default_required_fields():
    """Provides a clear, default structure for required fields in a template."""
    return {
        "cpi_or_cgpa": False,
        "backlog_status": False,
        "internship_company": False,
        "internship_duration": False,
        "application_id": False,
        "fee_amount": False
    }

# ======================================================================
# 1. SIGNATORY MODEL
# Stores details of individuals (or stamps) that can sign a certificate.
# ======================================================================
class Signatory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Full Name or Stamp Name")
    designation = models.CharField(max_length=255, blank=True, verbose_name="Designation (if applicable)")
    
    # Field to store the signature or stamp image file
    signature_image = models.ImageField(
        upload_to=get_signature_path, 
        null=True, 
        blank=True, 
        verbose_name="Digital Signature/Stamp Image"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Signatories & Stamps"

    def __str__(self):
        return f"{self.name}, {self.designation}" if self.designation else self.name

# ======================================================================
# 2. STUDENT MODEL (MASTER TABLE)
# Stores permanent information about each student.
# ======================================================================
class Student(models.Model):
    class Gender(TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'

    # Link to Django User (Login System)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')
    
    # --- 1. Basic Info (From CSV Cols C-L) ---
    enrollment_no = models.CharField(max_length=255, unique=True, verbose_name="Enrollment Number") # Col C
    branch = models.CharField(max_length=100, verbose_name="Branch")           # Col D
    full_name = models.CharField(max_length=255, verbose_name="Full Name")     # Col E
    date_of_birth = models.DateField(null=True, blank=True)                    # Col F
    father_name = models.CharField(max_length=255, verbose_name="Father Name") # Col G
    mother_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mother Name") # Col H
    gender = models.CharField(max_length=10, choices=Gender.choices, verbose_name="Gender") # Col I
    category = models.CharField(max_length=50, blank=True, null=True)          # Col J
    sub_category = models.CharField(max_length=50, blank=True, null=True)      # Col K
    blood_group = models.CharField(max_length=10, blank=True, null=True)       # Col L
    
    # Default fields for Session/Degree (Can be updated later via Admin if needed)
    degree = models.CharField(max_length=100, default="B.Tech", verbose_name="Degree")
    academic_session = models.CharField(max_length=20, default="2022-2026", verbose_name="Academic Session")

    # --- 2. Permanent Address (From CSV Cols M-Q) ---
    permanent_address = models.TextField(blank=True, null=True, verbose_name="Permanent Address") # Col M
    district = models.CharField(max_length=100, blank=True, null=True, verbose_name="Permanent District") # Col N
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name="State")   # Col O
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Country") # Col P
    pincode = models.CharField(max_length=10, blank=True, null=True, verbose_name="Permanent Pincode") # Col Q

    # --- 3. Contact Info (From CSV Cols R, V, W) ---
    parent_contact = models.CharField(max_length=15, blank=True, null=True, verbose_name="Parent Contact No") # Col R
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Student Contact No")  # Col V
    email = models.EmailField(max_length=255, blank=True, null=True)        # Col W

    # --- 4. Local Address (From CSV Cols S-U) ---
    local_address = models.TextField(blank=True, null=True, verbose_name="Local Address")       # Col S
    local_district = models.CharField(max_length=100, blank=True, null=True, verbose_name="Local District") # Col T
    local_pincode = models.CharField(max_length=10, blank=True, null=True, verbose_name="Local Pincode")   # Col U

    class Meta:
        # Changed ordering to sort by Enrollment Number instead of Name
        ordering = ['enrollment_no']
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.full_name} ({self.enrollment_no})"
    
    # --- Helper Properties (Required for Certificates) ---
    @property
    def current_semester(self):
        """
        Calculates current semester based on registration dates.
        Even Sem Starts: 5th Jan
        Odd Sem Starts: 17th July
        """
        try:
            # Batch "2022-2026" se start year 2022 nikala
            start_year = int(str(self.academic_session).split('-')[0].strip())
        except:
            return 1  # Fallback

        today = date.today()
        current_year = today.year
        
        # Fixed Registration Dates
        even_sem_start = date(current_year, 1, 5)   # 5th Jan
        odd_sem_start = date(current_year, 7, 17)   # 17th July

        years_passed = current_year - start_year

        if today < even_sem_start:
            # Case: 1 Jan - 4 Jan (Still previous Odd Sem logic)
            # e.g., Jan 2 2023 for 2022 batch -> (1-1)*2 + 1 = Sem 1
            sem = ((years_passed - 1) * 2) + 1
            return max(1, sem)

        elif even_sem_start <= today < odd_sem_start:
            # Case: 5 Jan - 16 July (Even Semester)
            # e.g., Feb 2023 for 2022 batch -> 1 year passed -> Sem 2
            return max(1, years_passed * 2)

        else:
            # Case: After 17 July (New Odd Semester)
            # e.g., Aug 2023 for 2022 batch -> 1 year passed -> Sem 3
            return (years_passed * 2) + 1
    @property
    def parent_relation(self):
        """Returns 'D/o' for Female and 'S/o' for Male."""
        return "D/o" if self.gender == self.Gender.FEMALE else "S/o"

    @property
    def pronoun_he_she(self):
        """Returns 'She' for Female and 'He' for Male."""
        return "She" if self.gender == self.Gender.FEMALE else "He"
        
    @property
    def pronoun_his_her(self):
        """Returns 'Her' for Female and 'His' for Male."""
        return "Her" if self.gender == self.Gender.FEMALE else "His"

# ======================================================================
# 3. CERTIFICATE TEMPLATE MODEL
# Defines the structure and content of each certificate type.
# ======================================================================
class CertificateTemplate(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Certificate Name")
    description = models.TextField(blank=True, null=True)
    body_template = models.TextField(help_text="The main text of the certificate with placeholders like {{ student.full_name }}.")
    required_fields = models.JSONField(default=get_default_required_fields, blank=True, help_text="Defines extra fields needed for this certificate type.")

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Certificate Templates"

    def __str__(self):
        return f"{self.name} - Template"

# ========================================================================
# 4. CERTIFICATE REQUEST MODEL
# Tracks every certificate request made by a student.
# ========================================================================
# class CertificateRequest(models.Model):
#     class StatusChoices(TextChoices):
#         PENDING = 'PENDING', 'Pending'
#         APPROVED = 'APPROVED', 'Approved'
#         REJECTED = 'REJECTED', 'Rejected'

#     student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='requests')
#     template = models.ForeignKey(CertificateTemplate, on_delete=models.PROTECT, verbose_name="Certificate Type")
#     status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)
#     request_data = models.JSONField(null=True, blank=True, help_text="Stores dynamic data like CPI, company name etc.")
#     verification_document = models.FileField(upload_to=get_verification_document_path, null=True, blank=True, help_text="Marksheet for CPI/CGPA verification")
#     rejection_reason = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['-created_at']
#         verbose_name_plural = "Certificate Requests"

#     def __str__(self):
#         return f"Request for {self.template.name} by {self.student.full_name}"

#     def clean(self):
#         """Validates request_data against the template's required_fields before saving."""
#         super().clean()
#         if not self.template or not self.request_data:
#             return

#         required = self.template.required_fields
#         errors = {}
#         for field, is_required in required.items():
#             if is_required and not self.request_data.get(field):
#                 errors[field] = "This field is required for the selected certificate type."
        
#         if errors:
#             raise ValidationError(errors)

# # ======================================================================
# # 5. GENERATED CERTIFICATE MODEL
# # Stores the final, approved certificate details.
# # ======================================================================
# class GeneratedCertificate(models.Model):
#     request = models.OneToOneField(CertificateRequest, on_delete=models.CASCADE, primary_key=True)
#     certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text="Publicly verifiable unique ID")
#     issue_date = models.DateField(default=timezone.now)
#     reference_no = models.CharField(max_length=100, blank=True, default=generate_reference_no)
#     generated_pdf = models.FileField(upload_to=get_generated_certificate_path, null=True, blank=True)
#     signatories = models.ManyToManyField(Signatory, related_name='signed_certificates', blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     certificate_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 Hash for Blockchain Verification")
    
#     class Meta:
#         ordering = ['-created_at']
#         verbose_name_plural = "Generated Certificates"

#     def __str__(self):
#         return f"Certificate ({self.certificate_id}) for {self.request.student.full_name}"
    
#     @property
#     def short_certificate_id(self):
#         return str(self.certificate_id)[:8]

# # ======================================================================
# # 6. DJANGO SIGNALS FOR AUTOMATION
# # ======================================================================

# @receiver(pre_save, sender=CertificateRequest)
# def store_previous_status(sender, instance, **kwargs):
#     """Stores the old status before a request is saved."""
#     if instance.pk:
#         try:
#             instance._previous_status = CertificateRequest.objects.get(pk=instance.pk).status
#         except CertificateRequest.DoesNotExist:
#             instance._previous_status = None
#     else:
#         instance._previous_status = None

# @receiver(post_save, sender=CertificateRequest)
# def create_generated_certificate_on_approval(sender, instance, **kwargs):
#     """
#     Creates a GeneratedCertificate object automatically only when the status
#     changes from a non-approved state to 'APPROVED'.
#     """
#     status_changed_to_approved = (
#         instance._previous_status != CertificateRequest.StatusChoices.APPROVED and
#         instance.status == CertificateRequest.StatusChoices.APPROVED
#     )
    
#     if status_changed_to_approved and not hasattr(instance, 'generatedcertificate'):
#         GeneratedCertificate.objects.create(request=instance)

# ======================================================================
# 4. CERTIFICATE REQUEST MODEL
# ======================================================================
class CertificateRequest(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CORRECTION = 'CORRECTION', 'Correction Requested'

    student = models.ForeignKey('Student', on_delete=models.PROTECT, related_name='requests')
    template = models.ForeignKey('CertificateTemplate', on_delete=models.PROTECT, verbose_name="Certificate Type")
    
    # =========================================================
    # ✅ NEW ANTI-SPAM & DETAIL FIELDS
    # =========================================================
    purpose = models.TextField(help_text="Reason for applying (e.g. Visa, Higher Studies)")
    submitting_to = models.CharField(max_length=255, help_text="Organization Name (e.g. TCS, Passport Office)")
    is_self_declared = models.BooleanField(default=False, help_text="Student accepted profile correctness")
    # =========================================================

    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    
    # Stores dynamic data (e.g. {'cpi': '8.5', 'company': 'Google'})
    request_data = models.JSONField(null=True, blank=True, help_text="Stores dynamic data like CPI, company name etc.")
    
    verification_document = models.FileField(upload_to='verification_docs/', null=True, blank=True, help_text="Marksheet for verification")
    
    # =========================================================
    # ✅ ADDED FIELD: EXTERNALLY SIGNED APPLICATION
    # =========================================================
    signed_application = models.FileField(
        upload_to='external_signed_applications/', 
        null=True, 
        blank=True, 
        help_text="Application signed by the external authority where the document is to be submitted."
    )
    # =========================================================

    rejection_reason = models.TextField(blank=True, null=True)
    

    priority = models.CharField(max_length=20, default='Normal', choices=[('Normal', 'Normal'), ('High', 'High')])
    # Stores why the student wants a change
    correction_reason = models.TextField(blank=True, null=True, help_text="Reason provided by student for correction")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Certificate Requests"

    def __str__(self):
        return f"Request for {self.template.name} by {self.student.full_name}"

    @property
    def is_correction_window_open(self):
        """Checks if 7 days have passed since issue date (requires Approved status)"""
        if self.status != self.StatusChoices.APPROVED:
            return False
        # Access the related GeneratedCertificate safely
        if hasattr(self, 'generatedcertificate'):
            issue_date = self.generatedcertificate.issue_date
            # Assuming 'timezone.now()' usage, make sure timezone is imported if used here
            # For simplicity, returning True for now or using issue_date logic:
            from django.utils import timezone
            deadline = issue_date + timedelta(days=7)
            return timezone.now() <= deadline
        return False

    def clean(self):
        """Validates request_data against the template's required_fields before saving."""
        super().clean()
        if not self.template or not self.request_data:
            return

        required = self.template.required_fields
        errors = {}
        # Ensure request_data is a dict (handle potential NoneType)
        data = self.request_data if isinstance(self.request_data, dict) else {}

        for field, is_required in required.items():
            if is_required and not data.get(field):
                errors[field] = "This field is required for the selected certificate type."
        
        if errors:
            raise ValidationError(errors)

    # ✅ Logic: Check if 7-day correction window is active
    @property
    def is_correction_window_open(self):
        """
        Returns True if the certificate was issued within the last 7 days.
        """
        # Only applicable if currently Approved
        if self.status != self.StatusChoices.APPROVED:
            return False
            
        # Check if GeneratedCertificate exists via OneToOne relation
        if hasattr(self, 'generatedcertificate'):
            issue_date = self.generatedcertificate.issue_date
            # Ensure issue_date is aware datetime or date
            if isinstance(issue_date, str): 
                return False # Safety check
            
            # Calculate deadline
            deadline = issue_date + timedelta(days=7)
            
            # Compare dates (timezone.now().date() ensures compatibility)
            return timezone.now().date() <= deadline
            
        return False
    
    
# ======================================================================
# 5. GENERATED CERTIFICATE MODEL
# Stores the final, approved certificate details.
# ======================================================================
class GeneratedCertificate(models.Model):
    request = models.OneToOneField(CertificateRequest, on_delete=models.CASCADE, primary_key=True)
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text="Publicly verifiable unique ID")
    issue_date = models.DateField(default=timezone.now)
    reference_no = models.CharField(max_length=100, blank=True) # Logic to generate handled in View/Signal
    generated_pdf = models.FileField(upload_to='generated_certificates/', null=True, blank=True)
    
    # Assuming Signatory model exists elsewhere
    signatories = models.ManyToManyField('Signatory', related_name='signed_certificates', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    certificate_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 Hash for Blockchain Verification")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Generated Certificates"

    def __str__(self):
        return f"Certificate ({self.certificate_id}) for {self.request.student.full_name}"
    
    @property
    def short_certificate_id(self):
        return str(self.certificate_id)[:8]

# ======================================================================
# 6. DJANGO SIGNALS FOR AUTOMATION
# ======================================================================

@receiver(pre_save, sender=CertificateRequest)
def store_previous_status(sender, instance, **kwargs):
    """Stores the old status before a request is saved."""
    if instance.pk:
        try:
            instance._previous_status = CertificateRequest.objects.get(pk=instance.pk).status
        except CertificateRequest.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

@receiver(post_save, sender=CertificateRequest)
def create_generated_certificate_on_approval(sender, instance, **kwargs):
    """
    Creates a GeneratedCertificate object automatically when status becomes APPROVED.
    Using get_or_create to handle re-approvals after correction safely.
    """
    if instance.status == CertificateRequest.StatusChoices.APPROVED:
        # Check if status JUST changed to APPROVED
        if instance._previous_status != CertificateRequest.StatusChoices.APPROVED:
            # ✅ Use get_or_create: If it exists (from before correction), get it. If not, create it.
            GeneratedCertificate.objects.get_or_create(request=instance)
            
# --- HELP DESK MODEL ---
class HelpQuery(models.Model):
    class Category(models.TextChoices):
        CERTIFICATE = 'CERTIFICATE', 'Certificate Issue'
        PROFILE = 'PROFILE', 'Profile Correction'
        TECHNICAL = 'TECHNICAL', 'Technical Bug'
        OTHER = 'OTHER', 'Other Inquiry'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'

    # Student link
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='queries')
    
    # Ticket Details
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    screenshot = models.ImageField(upload_to='help_desk_screenshots/', blank=True, null=True)
    
    # Admin Interaction
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    admin_reply = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} - {self.subject} ({self.status})"
    

# ======================================================================
# 📚 ACADEMIC MANAGEMENT MODELS (New Tables)
# ======================================================================

class Teacher(models.Model):
    """
    Stores teacher details. 
    Note: 'employee_id' logic (e.g., FAC001) will be handled during data import.
    """
    full_name = models.CharField(max_length=255, verbose_name="Faculty Name")
    employee_id = models.CharField(max_length=50, unique=True, verbose_name="Employee ID")
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    # Audit timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Faculty Member"
        verbose_name_plural = "Faculty Members"
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.department})"


class Subject(models.Model):
    """
    Stores Course/Subject Master data (e.g., MTH-S101).
    """
    course_code = models.CharField(max_length=50, unique=True, verbose_name="Course Code")
    name = models.CharField(max_length=255, verbose_name="Subject Name")
    credits = models.IntegerField(default=0, verbose_name="Credits")
    is_practical = models.BooleanField(default=False, verbose_name="Is Practical?")

    class Meta:
        ordering = ['course_code']

    def __str__(self):
        return f"{self.course_code} - {self.name}"


class CourseAllocation(models.Model):
    """
    Connects Teacher -> Subject -> Branch -> Semester.
    Defines who teaches what, to whom, and when.
    """
    session = models.CharField(max_length=50, default="2025-26(1)", help_text="e.g. 2025-26(1) or 2024-25(2)")
    branch = models.CharField(max_length=100, verbose_name="Branch") # Matches Student.branch
    semester = models.IntegerField(verbose_name="Semester") # Matches Student.current_semester logic
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        # Ensures one subject is taught by only one teacher per branch/sem/session
        unique_together = ('session', 'branch', 'semester', 'subject')
        verbose_name = "Course Allocation"
        verbose_name_plural = "Course Allocations"

    def __str__(self):
        teacher_name = self.teacher.full_name if self.teacher else "Not Assigned"
        return f"{self.branch} Sem-{self.semester}: {self.subject.course_code} ({teacher_name})"


class AcademicRecord(models.Model):
    """
    Stores semester-wise performance (CPI/SGPA) for a student.
    """
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='academic_records')
    semester = models.IntegerField(verbose_name="Semester")
    sgpa = models.FloatField(verbose_name="SGPA", default=0.0)
    cpi = models.FloatField(verbose_name="CPI", default=0.0)
    total_backlogs = models.IntegerField(default=0)
    
    # Optional: To track when this record was added
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['semester']
        unique_together = ('student', 'semester') # A student has only one record per semester

    def __str__(self):
        # Note: Accessing student.enrollment_no requires the Student model to be loaded
        return f"Sem {self.semester} (CPI: {self.cpi})"