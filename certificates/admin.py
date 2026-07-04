from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Student, 
    Signatory, 
    CertificateTemplate, 
    CertificateRequest, 
    GeneratedCertificate, 
    HelpQuery,
    Teacher,
    Subject,
    CourseAllocation,
    AcademicRecord
)

# ======================================================================
# INLINES (For Nested Views)
# ======================================================================

class GeneratedCertificateInline(admin.StackedInline):
    """
    Shows the generated certificate directly inside the Request page.
    """
    model = GeneratedCertificate
    can_delete = False
    extra = 0 
    
    # These fields will be shown as read-only.
    readonly_fields = ('short_certificate_id', 'issue_date', 'reference_no', 'pdf_download_link', 'created_at')
    
    # Display the custom method for the PDF link instead of the raw file path.
    fields = ('short_certificate_id', 'issue_date', 'reference_no', 'pdf_download_link', 'created_at')

    def pdf_download_link(self, obj):
        if obj.generated_pdf:
            return format_html('<a href="{}" target="_blank" style="font-weight: bold; color: #2563eb;">Download PDF</a>', obj.generated_pdf.url)
        return "PDF not generated yet"
    pdf_download_link.short_description = "Certificate File"


class AcademicRecordInline(admin.TabularInline):
    """
    Shows academic records (SGPA/CPI) directly inside the Student profile.
    """
    model = AcademicRecord
    extra = 0
    can_delete = True
    fields = ('semester', 'sgpa', 'cpi', 'total_backlogs')
    ordering = ['semester']


# ======================================================================
# CORE MODEL ADMINS
# ======================================================================

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'enrollment_no', 'branch', 'academic_session', 'current_semester')
    search_fields = ('full_name', 'enrollment_no', 'email')
    list_filter = ('branch', 'academic_session', 'gender')
    ordering = ['enrollment_no']
    
    # This allows you to add/edit marks directly from the Student page
    inlines = [AcademicRecordInline] 

@admin.register(Signatory)
class SignatoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'has_signature', 'created_at')
    search_fields = ('name', 'designation')

    def has_signature(self, obj):
        return bool(obj.signature_image)
    has_signature.boolean = True
    has_signature.short_description = "Signature Uploaded?"

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_short')
    search_fields = ('name',)

    def description_short(self, obj):
        return obj.description[:50] + "..." if obj.description else ""
    description_short.short_description = "Description"

@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'enrollment', 'template', 'status', 'priority', 'created_at')
    list_filter = ('status', 'template', 'priority', 'is_self_declared')
    search_fields = ('student__full_name', 'student__enrollment_no', 'reference_no')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)
    
    # Shows the certificate detail inside the request
    inlines = [GeneratedCertificateInline]

    def student_name(self, obj):
        return obj.student.full_name
    
    def enrollment(self, obj):
        return obj.student.enrollment_no

@admin.register(GeneratedCertificate)
class GeneratedCertificateAdmin(admin.ModelAdmin):
    list_display = ('get_student', 'short_certificate_id', 'issue_date', 'reference_no', 'pdf_link')
    search_fields = ('request__student__full_name', 'request__student__enrollment_no', 'reference_no', 'certificate_id')
    readonly_fields = ('created_at', 'certificate_id', 'short_certificate_id', 'generated_pdf')
    list_filter = ('issue_date',)

    def get_student(self, obj):
        return f"{obj.request.student.full_name} ({obj.request.student.enrollment_no})"
    get_student.short_description = "Student"

    def pdf_link(self, obj):
        if obj.generated_pdf:
            return format_html('<a href="{}" target="_blank" style="font-weight: bold; color: #2563eb;">Download PDF</a>', obj.generated_pdf.url)
        return "No file"
    pdf_link.short_description = "Certificate PDF"


# ======================================================================
# 📚 ACADEMIC MANAGEMENT ADMINS (New)
# ======================================================================

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_id', 'department', 'email', 'phone')
    list_filter = ('department',)
    search_fields = ('full_name', 'employee_id', 'email')
    ordering = ['full_name']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'name', 'credits', 'is_practical')
    list_filter = ('is_practical', 'credits')
    search_fields = ('course_code', 'name')
    ordering = ['course_code']

@admin.register(CourseAllocation)
class CourseAllocationAdmin(admin.ModelAdmin):
    list_display = ('subject_info', 'teacher_name', 'branch', 'semester', 'session')
    list_filter = ('session', 'semester', 'branch')
    search_fields = ('subject__name', 'subject__course_code', 'teacher__full_name')
    autocomplete_fields = ['subject', 'teacher'] # Makes dropdowns searchable

    def subject_info(self, obj):
        return f"{obj.subject.course_code} - {obj.subject.name}"
    subject_info.short_description = "Subject"

    def teacher_name(self, obj):
        return obj.teacher.full_name if obj.teacher else "⚠️ Not Assigned"
    teacher_name.short_description = "Faculty"

@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'sgpa', 'cpi', 'total_backlogs')
    list_filter = ('semester', 'total_backlogs')
    search_fields = ('student__full_name', 'student__enrollment_no')
    ordering = ['student', 'semester']


# ======================================================================
# HELP DESK ADMIN
# ======================================================================

@admin.register(HelpQuery)
class HelpQueryAdmin(admin.ModelAdmin):
    list_display = ('student', 'category', 'subject', 'status', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('student__full_name', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)
    
    fieldsets = (
        ('Ticket Details', {
            'fields': ('student', 'category', 'subject', 'message', 'screenshot')
        }),
        ('Resolution', {
            'fields': ('status', 'admin_reply')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )