from django.contrib import admin
from django.utils.html import format_html
from .models import Student, Signatory, CertificateTemplate, CertificateRequest, GeneratedCertificate


class GeneratedCertificateInline(admin.StackedInline):
    model = GeneratedCertificate
    can_delete = False
    extra = 0 
    
    # These fields will be shown as read-only.
    readonly_fields = ('short_certificate_id', 'issue_date', 'reference_no', 'pdf_download_link', 'created_at')
    
    # Display the custom method for the PDF link instead of the raw file path.
    fields = ('short_certificate_id', 'issue_date', 'reference_no', 'pdf_download_link', 'created_at')

    def pdf_download_link(self, obj):
        if obj.generated_pdf:
            return format_html('<a href="{}" target="_blank" style="font-weight: bold;">Download PDF</a>', obj.generated_pdf.url)
        return "PDF not generated yet"
    pdf_download_link.short_description = "Certificate File"

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'enrollment_no', 'branch', 'academic_session')
    search_fields = ('full_name', 'enrollment_no')
    list_filter = ('branch', 'academic_session')

@admin.register(Signatory)
class SignatoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'created_at')
    search_fields = ('name', 'designation')

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'template', 'status', 'created_at')
    list_filter = ('status', 'template')
    search_fields = ('student__full_name', 'student__enrollment_no')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)
    
    # The inline is added here.
    inlines = [GeneratedCertificateInline]

@admin.register(GeneratedCertificate)
class GeneratedCertificateAdmin(admin.ModelAdmin):
    # Added 'pdf_link' to the list display for a clean download link.
    list_display = ('request', 'short_certificate_id', 'issue_date', 'reference_no', 'pdf_link')
    search_fields = ('request__student__full_name', 'reference_no')
    readonly_fields = ('created_at', 'certificate_id', 'short_certificate_id', 'generated_pdf')

    def pdf_link(self, obj):
        if obj.generated_pdf:
            return format_html('<a href="{}" target="_blank" style="font-weight: bold;">Download PDF</a>', obj.generated_pdf.url)
        return "No file"
    pdf_link.short_description = "Certificate PDF"