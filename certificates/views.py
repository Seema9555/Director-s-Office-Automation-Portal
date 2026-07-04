# ==========================================================
#                  ALL NECESSARY IMPORTS
# ==========================================================
from django.conf import settings
import os
from io import BytesIO
from xhtml2pdf import pisa
from django.core.files.base import ContentFile
from django.template import Context, Template
from django.template.loader import get_template
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from .models import CertificateRequest, Student, Signatory, GeneratedCertificate, CertificateTemplate
from django.contrib import messages
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from urllib.parse import unquote
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
import json
from .models import HelpQuery
from django.db.models import Q
from .models import Teacher
# ==========================================================
#           HELPER FUNCTION FOR PDF IMAGE PATHS
# ==========================================================
def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources
    """
    if uri.startswith('data:'):
        return uri  # Isko file mat samjho, ye direct image data hai.
    # 1. HANDLE MEDIA FILES (Signatures, Stamps) - Do this MANUALLY to avoid SuspiciousFileOperation
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    
    # 2. HANDLE STATIC FILES (Logos, Fonts, CSS) - Use Django's finders
    elif uri.startswith(settings.STATIC_URL):
        # Remove the STATIC_URL prefix to get the relative path (e.g., /static/img.png -> img.png)
        static_path = uri.replace(settings.STATIC_URL, "")
        
        # Ask Django where this static file really is (searches all static folders)
        result = finders.find(static_path)
        
        if result:
            if isinstance(result, (list, tuple)):
                path = result[0]
            else:
                path = result
        else:
            # Fallback: manually construct path if finders fail
            path = os.path.join(settings.STATIC_ROOT, static_path)

    # 3. HANDLE EVERYTHING ELSE (Absolute paths or external URLs)
    else:
        path = uri

    # 4. FINAL CHECK
    if not os.path.isfile(path):
        # Optional: Print error to console for debugging
        print(f"PDF ERROR: File not found at {path} (URI: {uri})")
        return None
        
    return path
# ==========================================================
#                     ADMIN CHECKER
# ==========================================================
def is_admin(user):
    """Checks if a user is a staff member or superuser."""
    return user.is_staff or user.is_superuser

# ✨ NEW: APEC aur Director ke liye checks
def is_apec(user):
    return user.groups.filter(name='APEC_Staff').exists() or user.is_superuser

def is_director(user):
    return user.groups.filter(name='Director').exists() or user.is_superuser


# ==========================================================
#           CERTIFICATE REQUEST MANAGEMENT VIEWS
# ==========================================================
@user_passes_test(is_admin, login_url='admin_login')
def manage_certificate_requests(request):
    all_requests = CertificateRequest.objects.select_related(
    'student', 'template', 'generatedcertificate' # Make sure this says 'template'
    ).all().order_by('-created_at')
    
    context = {'requests': all_requests}
    return render(request, 'certificates/manage_requests.html', context)

@user_passes_test(is_admin, login_url='admin_login')
def approve_request(request, request_id):
    cert_request = get_object_or_404(CertificateRequest, id=request_id)
    cert_request.status = 'APPROVED'
    cert_request.save()
    messages.success(request, f"Request for {cert_request.student.full_name} has been approved.")
    return redirect('manage_requests')

@user_passes_test(is_admin, login_url='admin_login')
def reject_request(request, request_id):
    cert_request = get_object_or_404(CertificateRequest, id=request_id)
    cert_request.status = 'REJECTED'
    cert_request.save()
    messages.warning(request, f"Request for {cert_request.student.full_name} has been rejected.")
    return redirect('manage_requests')

import qrcode
import base64
from django.core.mail import EmailMessage

# import hashlib
# @user_passes_test(is_admin, login_url='admin_login')
# def generate_certificate_pdf(request, request_id):
#     # 1. Get the Request
#     cert_request = get_object_or_404(CertificateRequest, id=request_id)
#     student = cert_request.student
#     template_name = cert_request.template.name
    
#     # 2. Update Status to APPROVED (Fixes UI button issue)
#     if cert_request.status != 'APPROVED':
#         cert_request.status = 'APPROVED'
#         cert_request.save()

#     # 3. Create/Get the DB Record
#     generated_cert, created = GeneratedCertificate.objects.get_or_create(
#         request=cert_request
#     )

#     # 4. Generate QR Code (Dynamic Link)
#     verify_url = request.build_absolute_uri(f'/verify/?certificate_id={generated_cert.certificate_id}')
#     qr = qrcode.QRCode(version=1, box_size=10, border=1)
#     qr.add_data(verify_url)
#     qr.make(fit=True)
#     img = qr.make_image(fill='black', back_color='white')
#     buffered = BytesIO()
#     img.save(buffered, format="PNG")
#     qr_base64 = base64.b64encode(buffered.getvalue()).decode()

#     # 5. Prepare Context for PDF
#     template_obj = CertificateTemplate.objects.get(name=template_name)
#     body = template_obj.body_template

#     context = {
#         'student': student,
#         'request': cert_request,
#         'MEDIA_URL': settings.MEDIA_URL,
#         'certificate': generated_cert,
#     }
    
#     from django.template import Context, Template
#     template = Template(body)
#     rendered_body = template.render(Context(context))
    
#     pdf_template = get_template('certificates/pdf_template.html')
#     final_context = {
#         'rendered_body': rendered_body,
#         'signatories': Signatory.objects.all(),
#         'generated_certificate': generated_cert,
#         'media_url': settings.MEDIA_URL,
#         'settings': settings,
#         'qr_code': qr_base64, 
#     }
    
#     html = pdf_template.render(final_context)
#     buffer = BytesIO()

#     # 6. Load Fonts
#     try:
#         font_path = os.path.join(settings.STATIC_ROOT, 'fonts', 'TiroDevanagariHindi-Regular.ttf')
#         pdfmetrics.registerFont(TTFont('TiroHindi', font_path))
#     except Exception as e:
#         print(f"ERROR loading font: {e}")
    
#     # 7. Generate PDF
#     pisa_status = pisa.CreatePDF(html.encode('UTF-8'), dest=buffer, link_callback=link_callback)
    
#     if pisa_status.err:
#         return HttpResponse('We had some errors <pre>' + html + '</pre>')
        
#     # 8. Save PDF and Hash to Database (✨ EDITED PART ✨)
#     buffer.seek(0)
#     pdf_content = buffer.getvalue()
    
#     # --- START: BLOCKCHAIN HASH GENERATION ---
#     # PDF ka unique fingerprint (Hash) generate kar rahe hain
#     pdf_hash = hashlib.sha256(pdf_content).hexdigest()
#     generated_cert.certificate_hash = pdf_hash
#     # --- END: BLOCKCHAIN HASH GENERATION ---

#     filename = f"{student.enrollment_no}_{template_name.replace(' ', '_')}.pdf"
    
#     from django.core.files.base import ContentFile
#     # save=True se model update hoga, aur humara hash bhi save ho jayega
#     generated_cert.generated_pdf.save(filename, ContentFile(pdf_content), save=True)

#     # 9. ✨ SMART EMAIL CONSTRUCTION & SENDING ✨
#     try:
#         # A. Construct Email Address (Format: enrollment + branch + @csjmu.ac.in)
#         clean_branch = student.branch.lower().replace('-', '').replace(' ', '')
#         clean_enrollment = student.enrollment_no.lower()
        
#         student_email = f"{clean_enrollment}{clean_branch}@csjmu.ac.in"
        
#         print(f"📧 Attempting to send certificate to: {student_email}")

#         # B. Prepare Email Content
#         subject = f"Certificate Approved: {template_name}"
#         message_body = f"""
#         Dear {student.full_name},

#         Congratulations! Your request for a {template_name} has been approved.
        
#         Please find your official digital certificate attached to this email.
        
#         You can verify this document anytime using Certificate ID: {generated_cert.certificate_id}
        
#         Regards,
#         Director Office
#         University Institute of Engineering and Technology
#         """
        
#         # C. Send Email
#         email = EmailMessage(
#             subject,
#             message_body,
#             settings.DEFAULT_FROM_EMAIL,
#             [student_email], 
#         )
#         email.attach(filename, pdf_content, 'application/pdf')
#         email.send(fail_silently=False)
        
#         # D. Success Feedback
#         messages.success(request, f"Certificate generated and sent to {student_email}")

#     except Exception as e:
#         print(f"❌ EMAIL FAILED: {str(e)}")
#         # We use 'warning' so the user knows PDF is generated but email failed
#         messages.warning(request, f"Certificate generated, but email failed: {e}")

#     # 10. ✨ REDIRECT BACK ✨
#     return redirect('manage_requests')

# import hashlib
# @user_passes_test(is_admin, login_url='admin_login')
# def generate_certificate_pdf(request, request_id):
#     # 1. Get the Request
#     cert_request = get_object_or_404(CertificateRequest, id=request_id)
#     student = cert_request.student
#     template_name = cert_request.template.name
    
#     # 2. Update Status to APPROVED (Fixes UI button issue)
#     if cert_request.status != 'APPROVED':
#         cert_request.status = 'APPROVED'
#         cert_request.save()

#     # 3. Create/Get the DB Record
#     generated_cert, created = GeneratedCertificate.objects.get_or_create(
#         request=cert_request
#     )

#     # 4. Generate QR Code (Dynamic Link)
#     verify_url = request.build_absolute_uri(f'/verify/?certificate_id={generated_cert.certificate_id}')
#     qr = qrcode.QRCode(version=1, box_size=10, border=1)
#     qr.add_data(verify_url)
#     qr.make(fit=True)
#     img = qr.make_image(fill='black', back_color='white')
#     buffered = BytesIO()
#     img.save(buffered, format="PNG")
#     qr_base64 = base64.b64encode(buffered.getvalue()).decode()

#     # 5. Prepare Context for PDF
#     template_obj = CertificateTemplate.objects.get(name=template_name)
#     body = template_obj.body_template

#     context = {
#         'student': student,
#         'request': cert_request,
#         'MEDIA_URL': settings.MEDIA_URL,
#         'certificate': generated_cert,
#     }
    
#     # --- START: NEW FEE STRUCTURE LOGIC ADDED HERE ---
#     year_words_map = {1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth'}
#     year_in_words = year_words_map.get(student.current_year, str(student.current_year))

#     fixed_fees = {
#         1: 104200,
#         2: 104200,
#         3: 104200,
#         4: 105400
#     }

#     fee_data = []
#     grand_total = 0
#     try:       # request_data ek dictionary/JSON hoti hai jisme extra fields aate hain
#         requested_year = int(cert_request.request_data.get('fee_year', student.current_year))
#     except (TypeError, ValueError, AttributeError):
#         requested_year = student.current_year # Fallback agar koi error aaye

#     if "Fee Structure" in template_name:
#         for year in range(requested_year, 5):
#             amount = fixed_fees.get(year, 0)
#             if year == 1: suffix = "1st"
#             elif year == 2: suffix = "2nd"
#             elif year == 3: suffix = "3rd"
#             else: suffix = "4th"
            
#             fee_data.append({
#                 'year_label': f"{suffix} Year",
#                 'amount': amount
#             })
#             grand_total += amount

#     # Append to context
#     context['year_in_words'] = year_in_words
#     context['requested_year'] = requested_year
#     context['fee_data'] = fee_data
#     context['grand_total'] = grand_total
#     # --- END: NEW FEE STRUCTURE LOGIC ---

#     from django.template import Context, Template
#     template = Template(body)
#     rendered_body = template.render(Context(context))
    
#     pdf_template = get_template('certificates/pdf_template.html')
#     final_context = {
#         'rendered_body': rendered_body,
#         'signatories': Signatory.objects.all(),
#         'generated_certificate': generated_cert,
#         'media_url': settings.MEDIA_URL,
#         'settings': settings,
#         'qr_code': qr_base64, 
#     }
    
#     html = pdf_template.render(final_context)
#     buffer = BytesIO()

#     # 6. Load Fonts
#     try:
#         font_path = os.path.join(settings.STATIC_ROOT, 'fonts', 'TiroDevanagariHindi-Regular.ttf')
#         pdfmetrics.registerFont(TTFont('TiroHindi', font_path))
#     except Exception as e:
#         print(f"ERROR loading font: {e}")
    
#     # 7. Generate PDF
#     pisa_status = pisa.CreatePDF(html.encode('UTF-8'), dest=buffer, link_callback=link_callback)
    
#     if pisa_status.err:
#         return HttpResponse('We had some errors <pre>' + html + '</pre>')
        
#     # 8. Save PDF and Hash to Database (✨ EDITED PART ✨)
#     buffer.seek(0)
#     pdf_content = buffer.getvalue()
    
#     # --- START: BLOCKCHAIN HASH GENERATION ---
#     # PDF ka unique fingerprint (Hash) generate kar rahe hain
#     pdf_hash = hashlib.sha256(pdf_content).hexdigest()
#     generated_cert.certificate_hash = pdf_hash
#     # --- END: BLOCKCHAIN HASH GENERATION ---

#     filename = f"{student.enrollment_no}_{template_name.replace(' ', '_')}.pdf"
    
#     from django.core.files.base import ContentFile
#     # save=True se model update hoga, aur humara hash bhi save ho jayega
#     generated_cert.generated_pdf.save(filename, ContentFile(pdf_content), save=True)

#     # 9. ✨ SMART EMAIL CONSTRUCTION & SENDING ✨
#     try:
#         # A. Construct Email Address (Format: enrollment + branch + @csjmu.ac.in)
#         clean_branch = student.branch.lower().replace('-', '').replace(' ', '')
#         clean_enrollment = student.enrollment_no.lower()
        
#         student_email = f"{clean_enrollment}{clean_branch}@csjmu.ac.in"
        
#         print(f"📧 Attempting to send certificate to: {student_email}")

#         # B. Prepare Email Content
#         subject = f"Certificate Approved: {template_name}"
#         message_body = f"""
#         Dear {student.full_name},

#         Congratulations! Your request for a {template_name} has been approved.
        
#         Please find your official digital certificate attached to this email.
        
#         You can verify this document anytime using Certificate ID: {generated_cert.certificate_id}
        
#         Regards,
#         Director Office
#         University Institute of Engineering and Technology
#         """
        
#         # C. Send Email
#         email = EmailMessage(
#             subject,
#             message_body,
#             settings.DEFAULT_FROM_EMAIL,
#             [student_email], 
#         )
#         email.attach(filename, pdf_content, 'application/pdf')
#         email.send(fail_silently=False)
        
#         # D. Success Feedback
#         messages.success(request, f"Certificate generated and sent to {student_email}")

#     except Exception as e:
#         print(f"❌ EMAIL FAILED: {str(e)}")
#         # We use 'warning' so the user knows PDF is generated but email failed
#         messages.warning(request, f"Certificate generated, but email failed: {e}")

#     # 10. ✨ REDIRECT BACK ✨
#     return redirect('manage_requests')

import hashlib
@user_passes_test(is_admin, login_url='admin_login')
def generate_certificate_pdf(request, request_id):
    # 1. Get the Request
    cert_request = get_object_or_404(CertificateRequest, id=request_id)
    student = cert_request.student
    template_name = cert_request.template.name
    
    # 2. Update Status to APPROVED (Fixes UI button issue)
    if cert_request.status != 'APPROVED':
        cert_request.status = 'APPROVED'
        cert_request.save()

    # 3. Create/Get the DB Record
    generated_cert, created = GeneratedCertificate.objects.get_or_create(
        request=cert_request
    )

    # 4. Generate QR Code (Dynamic Link)
    verify_url = request.build_absolute_uri(f'/verify/?certificate_id={generated_cert.certificate_id}')
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    # 5. Prepare Context for PDF
    template_obj = CertificateTemplate.objects.get(name=template_name)
    body = template_obj.body_template

    context = {
        'student': student,
        'request': cert_request,
        'MEDIA_URL': settings.MEDIA_URL,
        'certificate': generated_cert,
    }

    # --- START: DYNAMIC FEE STRUCTURE LOGIC ---
    try:
        # academic_session format "2022-2026" se admission_year nikalna
        admission_year = int(student.academic_session.split('-')[0])
        current_date_year = 2026
        current_year_val = (current_date_year - admission_year) + 1
        current_year_val = max(1, min(4, current_year_val))
    except:
        current_year_val = 1

    year_words_map = {1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth'}
    year_in_words = year_words_map.get(current_year_val, str(current_year_val))

    fixed_fees = {1: 104200, 2: 104200, 3: 104200, 4: 105400}
    fee_data = []
    grand_total = 0
    
    # Form se aaya hua fee_year lein, agar nahi hai toh calculated year lein
    try:
        requested_year = int(cert_request.request_data.get('fee_year', current_year_val))
    except:
        requested_year = current_year_val

    if "Fee Structure" in template_name:
        for year in range(requested_year, 5):
            amount = fixed_fees.get(year, 0)
            suffix = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(year, "")
            fee_data.append({'year_label': f"{suffix} Year", 'amount': amount})
            grand_total += amount

    context['year_in_words'] = year_in_words
    context['requested_year'] = requested_year
    context['fee_data'] = fee_data
    context['grand_total'] = grand_total
    # --- END: DYNAMIC FEE STRUCTURE LOGIC ---
    
    from django.template import Context, Template
    template = Template(body)
    rendered_body = template.render(Context(context))
    
    pdf_template = get_template('certificates/pdf_template.html')
    final_context = {
        'rendered_body': rendered_body,
        'signatories': Signatory.objects.all(),
        'generated_certificate': generated_cert,
        'media_url': settings.MEDIA_URL,
        'settings': settings,
        'qr_code': qr_base64, 
    }
    
    html = pdf_template.render(final_context)
    buffer = BytesIO()

    # 6. Load Fonts
    try:
        font_path = os.path.join(settings.STATIC_ROOT, 'fonts', 'TiroDevanagariHindi-Regular.ttf')
        pdfmetrics.registerFont(TTFont('TiroHindi', font_path))
    except Exception as e:
        print(f"ERROR loading font: {e}")
    
    # 7. Generate PDF
    pisa_status = pisa.CreatePDF(html.encode('UTF-8'), dest=buffer, link_callback=link_callback)
    
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
        
    # 8. Save PDF and Hash to Database
    buffer.seek(0)
    pdf_content = buffer.getvalue()
    
    # --- START: BLOCKCHAIN HASH GENERATION ---
    pdf_hash = hashlib.sha256(pdf_content).hexdigest()
    generated_cert.certificate_hash = pdf_hash
    # --- END: BLOCKCHAIN HASH GENERATION ---

    filename = f"{student.enrollment_no}_{template_name.replace(' ', '_')}.pdf"
    
    from django.core.files.base import ContentFile
    generated_cert.generated_pdf.save(filename, ContentFile(pdf_content), save=True)

    # 9. ✨ SMART EMAIL CONSTRUCTION & SENDING ✨
    try:
        clean_branch = student.branch.lower().replace('-', '').replace(' ', '')
        clean_enrollment = student.enrollment_no.lower()
        
        student_email = f"{clean_enrollment}{clean_branch}@csjmu.ac.in"
        
        print(f"📧 Attempting to send certificate to: {student_email}")

        subject = f"Certificate Approved: {template_name}"
        message_body = f"""
        Dear {student.full_name},

        Congratulations! Your request for a {template_name} has been approved.
        
        Please find your official digital certificate attached to this email.
        
        You can verify this document anytime using Certificate ID: {generated_cert.certificate_id}
        
        Regards,
        Director Office
        University Institute of Engineering and Technology
        """
        
        email = EmailMessage(
            subject,
            message_body,
            settings.DEFAULT_FROM_EMAIL,
            [student_email], 
        )
        email.attach(filename, pdf_content, 'application/pdf')
        email.send(fail_silently=False)
        
        messages.success(request, f"Certificate generated and sent to {student_email}")

    except Exception as e:
        print(f"❌ EMAIL FAILED: {str(e)}")
        messages.warning(request, f"Certificate generated, but email failed: {e}")

    # 10. ✨ REDIRECT BACK ✨
    return redirect('manage_requests')


# ==========================================================
#               STUDENT MANAGEMENT VIEWS
# ==========================================================
@user_passes_test(is_admin, login_url='admin_login')
def manage_students_view(request):
    all_students = Student.objects.all().order_by('full_name')
    context = {'students': all_students}
    return render(request, 'certificates/manage_students.html', context)

@user_passes_test(is_admin, login_url='admin_login')
def add_student_view(request):
    if request.method == 'POST':
        username = request.POST.get('enrollment_no')
        password = request.POST.get('password')
        try:
            if User.objects.filter(username=username).exists():
                messages.error(request, f"A user with enrollment number '{username}' already exists.")
                return render(request, 'certificates/add_student.html')

            user = User.objects.create_user(username=username, password=password)
            
            Student.objects.create(
                user=user,
                full_name=request.POST.get('full_name'),
                father_name=request.POST.get('father_name'),
                enrollment_no=request.POST.get('enrollment_no'),
                gender=request.POST.get('gender'),
                degree=request.POST.get('degree'),
                branch=request.POST.get('branch'),
                academic_session=request.POST.get('academic_session')
            )
            messages.success(request, f"Student '{request.POST.get('full_name')}' has been added successfully.")
            return redirect('manage_students')
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")

    return render(request, 'certificates/add_student.html')

@user_passes_test(is_admin, login_url='admin_login')
def edit_student_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.full_name = request.POST.get('full_name')
        student.father_name = request.POST.get('father_name')
        student.enrollment_no = request.POST.get('enrollment_no')
        student.gender = request.POST.get('gender')
        student.degree = request.POST.get('degree')
        student.branch = request.POST.get('branch')
        student.academic_session = request.POST.get('academic_session')
        student.save()
        
        if student.user and student.user.username != student.enrollment_no:
            student.user.username = student.enrollment_no
            student.user.save()

        messages.success(request, f"Details for {student.full_name} have been updated.")
        return redirect('manage_students')

    context = {'student': student}
    return render(request, 'certificates/edit_student.html', context)

@user_passes_test(is_admin, login_url='admin_login')
def delete_student_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student_name = student.full_name
        
        if student.user:
            student.user.delete()
        else:
            student.delete()
            
        messages.info(request, f"Student '{student_name}' has been deleted.")
        return redirect('manage_students')
    
    return redirect('manage_students')

# ==========================================================
#      ✨ UNIFIED VERIFICATION VIEW (ID + BLOCKCHAIN) ✨
# ==========================================================
import hashlib
from django.shortcuts import render
from django.http import HttpResponse
from .models import GeneratedCertificate

def verify_certificate_public(request):
    """
    Ek hi view jo ID Verification aur Blockchain File Verification dono handle karega.
    """
    context = {}
    
    # --- 1. HANDLE POST REQUESTS (User ne button dabaya) ---
    if request.method == 'POST':
        
        # CASE A: User ne Certificate ID daali hai
        if 'certificate_id' in request.POST:
            cert_id = request.POST.get('certificate_id', '').strip()
            context['searched_id'] = cert_id
            context['mode'] = 'id' # Tab ID wala active rahega
            
            try:
                cert = GeneratedCertificate.objects.select_related('request__student').get(certificate_id=cert_id)
                
                # Success Context Set karo
                context['success'] = True
                context['cert'] = cert
                context['student'] = cert.request.student
                context['verification_type'] = "Database Record Match" # Simple Verification
                
            except GeneratedCertificate.DoesNotExist:
                context['error'] = "❌ No record found! Please check the Certificate ID."
            except Exception:
                context['error'] = "Invalid ID format."

        # CASE B: User ne PDF File Upload ki hai (Blockchain Logic)
        elif 'certificate_file' in request.FILES:
            uploaded_file = request.FILES['certificate_file']
            context['mode'] = 'file' # Tab File wala active rahega
            
            try:
                # 1. File ka cryptographic hash nikalo (Blockchain Fingerprint)
                file_content = uploaded_file.read()
                uploaded_hash = hashlib.sha256(file_content).hexdigest()
                
                # 2. Database mein same Hash dhoondo
                cert = GeneratedCertificate.objects.select_related('request__student').get(certificate_hash=uploaded_hash)
                
                # Agar mil gaya to BINGO!
                context['success'] = True
                context['cert'] = cert
                context['student'] = cert.request.student
                context['verification_type'] = "Cryptographic Blockchain Hash Match"
                context['is_blockchain_verified'] = True # Ye template me "Blockchain Badge" dikhayega
                
            except GeneratedCertificate.DoesNotExist:
                context['error'] = "❌ TAMPERED DOCUMENT: The uploaded file's digital fingerprint does not match our records."
            except Exception as e:
                context['error'] = f"Error processing file: {str(e)}"

    # --- 2. HANDLE GET REQUESTS (QR Code Scan) ---
    elif request.method == 'GET':
        cert_id = request.GET.get('certificate_id', '').strip()
        if cert_id:
            context['searched_id'] = cert_id
            context['mode'] = 'id'
            try:
                cert = GeneratedCertificate.objects.select_related('request__student').get(certificate_id=cert_id)
                context['success'] = True
                context['cert'] = cert
                context['student'] = cert.request.student
                context['verification_type'] = "QR Code Scan"
            except GeneratedCertificate.DoesNotExist:
                context['error'] = "Invalid or Expired QR Code Link."

    # Sab kuch ek hi sundar template me render hoga
    return render(request, 'certificates/verify_certificate.html', context)

@login_required(login_url='login')
def request_correction(request, request_id):
    if request.method == 'POST':
        # 1. Get the request object (Ensure it belongs to the logged-in student)
        cert_request = get_object_or_404(CertificateRequest, id=request_id, student__user=request.user)
        
        # 2. Check Validations
        if not cert_request.is_correction_window_open:
            messages.error(request, "Correction window has expired (7 days passed).")
            return redirect('student_dashboard')
            
        if cert_request.status != CertificateRequest.StatusChoices.APPROVED:
            messages.error(request, "Corrections can only be requested for issued certificates.")
            return redirect('student_dashboard')

        # 3. Process Logic
        reason = request.POST.get('correction_reason')
        if reason:
            cert_request.status = CertificateRequest.StatusChoices.CORRECTION
            cert_request.correction_reason = reason
            cert_request.save()
            messages.success(request, "Correction request submitted successfully. Admin will review it.")
        else:
            messages.error(request, "Please provide a reason for correction.")
            
    return redirect('student_dashboard')

@user_passes_test(is_admin)
def admin_edit_request(request, request_id):
    cert_request = get_object_or_404(CertificateRequest, id=request_id)
    
    if request.method == 'POST':
        # 1. Update Request Data (JSON)
        new_data = cert_request.request_data or {}
        
        # Form se saara data utha kar JSON update karein
        for key in new_data.keys():
            if key in request.POST:
                new_data[key] = request.POST.get(key)
        
        cert_request.request_data = new_data
        
        # 2. Update Status (Optional: keep it as CORRECTION until generated, or reset)
        # Hum save kar rahe hain, regeneration alag step hoga
        cert_request.save()
        
        messages.success(request, "Data updated successfully! Now click 'Approve & Sign' to regenerate.")
        return redirect('manage_requests')

    return render(request, 'certificates/admin_edit_request.html', {'req': cert_request})

@login_required(login_url='login')
def student_help_desk(request):
    # Student Profile Get karo
    try:
        student = request.user.student_profile
    except:
        # Agar user admin hai ya student profile nahi hai
        return redirect('student_dashboard')

    # Handle New Ticket Submission
    if request.method == 'POST':
        category = request.POST.get('category')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        screenshot = request.FILES.get('screenshot')

        HelpQuery.objects.create(
            student=student,
            category=category,
            subject=subject,
            message=message,
            screenshot=screenshot
        )
        messages.success(request, 'Ticket raised successfully! Support team will reply soon.')
        return redirect('student_help_desk')

    # Fetch Past Queries
    my_queries = HelpQuery.objects.filter(student=student)
    
    # Context
    context = {
        'student': student,
        'my_queries': my_queries
    }
    return render(request, 'certificates/student_help_desk.html', context)

@user_passes_test(is_admin, login_url='admin_login')
def admin_help_desk(request):
    # 1. Handle Reply Submission
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        reply_text = request.POST.get('admin_reply')
        
        ticket = get_object_or_404(HelpQuery, id=ticket_id)
        ticket.admin_reply = reply_text
        ticket.status = HelpQuery.Status.RESOLVED # Auto-close ticket
        ticket.save()
        
        messages.success(request, f"Reply sent to {ticket.student.full_name}. Ticket marked as Resolved.")
        return redirect('admin_help_desk')

    # 2. Fetch Tickets
    tickets = HelpQuery.objects.select_related('student').all().order_by('-created_at')
    
    context = {
        'tickets': tickets,
        'open_count': tickets.filter(status=HelpQuery.Status.OPEN).count(),
        'resolved_count': tickets.filter(status=HelpQuery.Status.RESOLVED).count()
    }
    return render(request, 'certificates/admin_help_desk.html', context)

@user_passes_test(is_admin)
def edit_request_data(request, request_id):
    req = get_object_or_404(CertificateRequest, id=request_id)
    
    if request.method == 'POST':
        # Create a copy of existing data to update
        updated_data = req.request_data.copy()
        
        # Loop through existing keys and update from POST
        for key in updated_data.keys():
            if key in request.POST:
                updated_data[key] = request.POST.get(key)
        
        # Save updated JSON
        req.request_data = updated_data
        
        # Correction done, move back to Pending or Approve directly?
        # Let's keep it 'CORRECTION' so Admin can click 'Regenerate' in the main list
        # OR switch to PENDING to review again. 
        # Ideally, we keep it as is, just save data.
        
        req.save()
        messages.success(request, "Data updated successfully! You can now regenerate the certificate.")
        return redirect('manage_requests')

    return render(request, 'certificates/edit_request.html', {'req': req})

# ==========================================================
#               TEACHER MANAGEMENT VIEWS
# ==========================================================

@user_passes_test(is_admin, login_url='admin_login')
def manage_teachers_view(request):
    """
    Displays the Teacher Database with the same UI/UX as Student Database.
    """
    all_teachers = Teacher.objects.all().order_by('full_name')
    context = {'teachers': all_teachers}
    return render(request, 'certificates/manage_teachers.html', context)

@user_passes_test(is_admin, login_url='admin_login')
def add_teacher_view(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        
        # Check for Duplicate Employee ID
        if Teacher.objects.filter(employee_id=employee_id).exists():
            messages.error(request, f"A faculty with Employee ID '{employee_id}' already exists.")
            return render(request, 'certificates/add_teacher.html')

        try:
            Teacher.objects.create(
                full_name=request.POST.get('full_name'),
                employee_id=employee_id,
                department=request.POST.get('department'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone')
            )
            messages.success(request, f"Faculty Member '{request.POST.get('full_name')}' added successfully.")
            return redirect('manage_teachers')
        except Exception as e:
            messages.error(request, f"Error adding teacher: {e}")

    return render(request, 'certificates/add_teacher.html')

@user_passes_test(is_admin, login_url='admin_login')
def edit_teacher_view(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    if request.method == 'POST':
        try:
            teacher.full_name = request.POST.get('full_name')
            # Employee ID usually shouldn't change, but if needed:
            # teacher.employee_id = request.POST.get('employee_id') 
            teacher.department = request.POST.get('department')
            teacher.email = request.POST.get('email')
            teacher.phone = request.POST.get('phone')
            teacher.save()
            
            messages.success(request, f"Profile for {teacher.full_name} updated.")
            return redirect('manage_teachers')
        except Exception as e:
            messages.error(request, f"Error updating profile: {e}")

    return render(request, 'certificates/edit_teacher.html', {'teacher': teacher})

@user_passes_test(is_admin, login_url='admin_login')
def delete_teacher_view(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST': # Usually deletion is a POST request for safety
        name = teacher.full_name
        teacher.delete()
        messages.info(request, f"Faculty '{name}' has been removed.")
        return redirect('manage_teachers')
    
    # Fallback if accessed via GET (though linking via POST form is better)
    return redirect('manage_teachers')

from django.http import JsonResponse
from django.core.mail import send_mass_mail # Bulk mail ke liye best

def bulk_approve_requests(request):
    if request.method == 'POST':
        request_ids = request.POST.getlist('request_ids') # ['1', '2', '5', ...]
        requests = CertificateRequest.objects.filter(id__in=request_ids, status='PENDING')
        
        messages_to_send = []
        for req in requests:
            # 1. Approve logic
            req.status = 'APPROVED'
            req.save()
            
            # 2. Certificate Generation (Aapka existing function call karein)
            # generate_certificate_pdf(req) 
            
            # 3. Email prepare karein
            subject = f"Certificate Approved: {req.template.name}"
            message = f"Dear {req.student.full_name}, your request has been approved."
            messages_to_send.append((subject, message, 'admin@uiet.ac.in', [req.student.email]))
        
        # 4. Mass email (ek baar mein saare mails)
        send_mass_mail(messages_to_send, fail_silently=False)
        
        return JsonResponse({'status': 'success', 'message': f'{len(requests)} requests processed!'})