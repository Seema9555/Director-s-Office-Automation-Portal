from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Count, Q
import json
import os
# Correctly import models from the 'certificates' app where they are defined.
from certificates.models import CertificateRequest, Student, CertificateTemplate

from certificates.services import SpamDetector , DocumentQualityChecker , UrgencyAnalyzer
# --- Student Views ---

def student_login_view(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('portal_gateway')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if not user.is_superuser and not user.is_staff:
                    login(request, user)
                    return redirect('portal_gateway')
                else:
                    messages.error(request, "Access denied. Please use the admin login page.")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request, "accounts/student_login.html", {"form": form})

# @login_required(login_url='student_login')
# def student_dashboard(request):
#     """
#     Manages the student dashboard.
#     - On GET: Displays the certificate request form and the student's past requests.
#     - On POST: Handles the submission of a new certificate request including Anti-Spam details.
#     """
#     try:
#         # Fetch the student profile linked to the logged-in user.
#         student = request.user.student_profile
#     except Student.DoesNotExist:
#         # Handle cases where a student profile doesn't exist for the user.
#         return render(request, 'accounts/student_dashboard.html', {'error_message': "Student profile not found."})

#     # --- Handle POST request (Form Submission) ---
#     if request.method == 'POST':
#         template_id = request.POST.get('certificate_template')
#         verification_doc = request.FILES.get('verification_document')
        
#         # ✅ NEW: Capture Anti-Spam Fields
#         purpose_text = request.POST.get('purpose')
#         org_name = request.POST.get('submitting_to')
#         self_declared = request.POST.get('is_self_declared') == 'on'  # Checkbox returns 'on' if checked

#         if not template_id:
#             messages.error(request, "Please select a certificate type.")
#             return redirect('student_dashboard')

#         template = get_object_or_404(CertificateTemplate, id=template_id)
        
#         # Dynamically collect data from the form based on the template's required fields.
#         dynamic_data = {}
#         if hasattr(template, 'required_fields') and isinstance(template.required_fields, dict):
#             for key, is_required in template.required_fields.items():
#                 # We skip the standard fields we handled manually above
#                 if is_required:
#                     value = request.POST.get(key)
#                     if value is not None:
#                         dynamic_data[key] = value

#         try:
#             # Create the new certificate request in the database.
#             CertificateRequest.objects.create(
#                 student=student,
#                 template=template,
#                 request_data=dynamic_data,
#                 verification_document=verification_doc,
                
#                 # ✅ NEW: Save Anti-Spam Fields
#                 purpose=purpose_text,
#                 submitting_to=org_name,
#                 is_self_declared=self_declared
#             )
            
#             messages.success(request, f"Your request for '{template.name}' has been submitted successfully.")
#             return redirect('student_dashboard')
            
#         except Exception as e:
#             messages.error(request, f"An error occurred while submitting: {str(e)}")
#             return redirect('student_dashboard')

#     # --- Prepare data for GET request (Displaying the page) ---
#     # Use select_related for an efficient database query.
#     past_requests = CertificateRequest.objects.select_related(
#         'template', 'generatedcertificate'
#     ).filter(student=student).order_by('-created_at')
    
#     certificate_templates = CertificateTemplate.objects.all()
    
#     # This loop adds the 'required_fields_json' attribute to each template object for JS.
#     for template in certificate_templates:
#         fields_data = template.required_fields if isinstance(template.required_fields, dict) else {}
#         template.required_fields_json = json.dumps(fields_data)

#     # Aggregate counts for different request statuses to display stats on the dashboard.
#     status_counts = past_requests.aggregate(
#         pending_count=Count('id', filter=Q(status='PENDING')),
#         approved_count=Count('id', filter=Q(status='APPROVED')),
#         rejected_count=Count('id', filter=Q(status='REJECTED'))
#     )

#     context = {
#         'student': student,
#         'past_requests': past_requests,
#         'certificate_templates': certificate_templates,
#         'pending_count': status_counts.get('pending_count', 0),
#         'approved_count': status_counts.get('approved_count', 0),
#         'rejected_count': status_counts.get('rejected_count', 0),
#     }
        
#     return render(request, 'accounts/student_dashboard.html', context)




@login_required(login_url='student_login')
def student_dashboard(request):
    """
    Final Student Dashboard.
    Features: 
    1. AI Spam Detection (NLP)
    2. Document Upload
    3. Direct Submission (No Payment)
    """
    try:
        student = request.user.student_profile
    except Student.DoesNotExist:
        return render(request, 'accounts/student_dashboard.html', {'error_message': "Student profile not found."})

    # ====================================================
    # 🟢 POST REQUEST: FORM SUBMISSION
    # ====================================================
    if request.method == 'POST':
            try:
                # 1. Capture Basic Data
                template_id = request.POST.get('certificate_template')
                verification_doc = request.FILES.get('verification_document')
                
                # =========================================================
                # ✅ ADDED: Capture the new Signed Application File
                # =========================================================
                signed_application_doc = request.FILES.get('signed_application')
                # =========================================================
                
                # 2. Capture Anti-Spam Fields (Renamed variables for consistency)
                purpose = request.POST.get('purpose', '')       # <-- Changed to 'purpose'
                submitting_to = request.POST.get('submitting_to', '') # <-- Changed to 'submitting_to'
                is_self_declared = request.POST.get('is_self_declared') == 'on'

                if not template_id:
                    messages.error(request, "Please select a certificate type.")
                    return redirect('student_dashboard')

                template = get_object_or_404(CertificateTemplate, id=template_id)

                # 3. Dynamic JSON Data Capture
                dynamic_data = {}
                if template.required_fields:
                    for key, is_required in template.required_fields.items():
                        value = request.POST.get(key)
                        if value:
                            dynamic_data[key] = value

                # ---------------------------------------------------
                # 🛡️ STEP 1: AI SPAM CHECK (Smart Guard)
                # ---------------------------------------------------
                # Fix: Dono text ko jod kar ek string banao
                full_text_check = f"{purpose} {submitting_to}"
                
                # Ab sirf ek argument pass kar rahe hain (Jo sahi hai)
                spam_detector = SpamDetector(full_text_check) 
                is_valid, error_msg = spam_detector.validate()

                if not is_valid:
                    messages.error(request, f"⚠️ Application Rejected by AI: {error_msg}")
                    return redirect('student_dashboard')

                # ---------------------------------------------------
                # 🔒 SECURITY CHECK (File Type & Size)
                # ---------------------------------------------------
                if verification_doc:
                    import os # Ensure import inside or at top
                    # 1. Extension Check
                    ext = os.path.splitext(verification_doc.name)[1].lower()
                    if ext not in ['.jpg', '.jpeg', '.png']:
                        messages.error(request, "❌ Invalid format! Only JPG, JPEG, or PNG images are allowed.")
                        return redirect('student_dashboard')

                    # 2. Size Check (2MB Limit)
                    if verification_doc.size > (2 * 1024 * 1024):
                        messages.error(request, "📁 File too large! Max size is 2MB.")
                        return redirect('student_dashboard')

                # =========================================================
                # ✅ ADDED: SECURITY CHECK FOR SIGNED APPLICATION
                # =========================================================
                if signed_application_doc:
                    import os
                    ext = os.path.splitext(signed_application_doc.name)[1].lower()
                    # Accepting PDF along with images for external applications
                    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
                        messages.error(request, "❌ Invalid format! Only PDF, JPG, JPEG, or PNG are allowed for the signed application.")
                        return redirect('student_dashboard')

                    if signed_application_doc.size > (2 * 1024 * 1024):
                        messages.error(request, "📁 Signed application file is too large! Max size is 2MB.")
                        return redirect('student_dashboard')
                # =========================================================

                # ---------------------------------------------------
                # 📸 STEP 2: COMPUTER VISION CHECK (Blurry Document?)
                # ---------------------------------------------------
                if verification_doc: 
                    quality_checker = DocumentQualityChecker(verification_doc)
                    is_clean, quality_msg = quality_checker.validate()

                    if not is_clean:
                        messages.error(request, f"📷 Document Error: {quality_msg}")
                        return redirect('student_dashboard')

                # ---------------------------------------------------
                # 🔥 STEP 4: AI URGENCY ANALYSIS
                # ---------------------------------------------------
                # Ab yahan 'purpose' variable defined hai, error nahi aayega
                urgency_scanner = UrgencyAnalyzer(purpose)
                calculated_priority = urgency_scanner.get_priority()

                # ---------------------------------------------------
                # 💾 STEP 3: SAVE TO DATABASE
                # ---------------------------------------------------
                cpi_value = request.POST.get('cpi_or_cgpa')
                if cpi_value:
                    dynamic_data['cpi_or_cgpa'] = cpi_value
                    
                CertificateRequest.objects.create(
                    student=student,
                    template=template,
                    # Agar aapke model me 'request_data' field hai JSON ke liye to ye sahi hai
                    # Agar alag fields hain (cpi, backlog etc) to unhe alag se map karna padega
                    # Filhal aapke dynamic_data logic ke hisaab se:
                    request_data=dynamic_data, 
                    verification_document=verification_doc,
                    
                    # =========================================================
                    # ✅ ADDED: Save Signed Application to DB
                    # =========================================================
                    signed_application=signed_application_doc, 
                    # =========================================================
                    
                    purpose=purpose,              # <-- Correct variable
                    submitting_to=submitting_to,  # <-- Correct variable
                    is_self_declared=is_self_declared,
                    priority=calculated_priority
                )

                # Success Message
                if calculated_priority == 'High':
                    messages.success(request, "✅ Request Submitted! Marked as 'High Priority' due to urgency.")
                else:
                    messages.success(request, "✅ Request Submitted Successfully!")
                
                return redirect('student_dashboard')

            except Exception as e:
                # Debugging ke liye error print bhi kara lo console me
                print(f"Error in Dashboard View: {e}")
                messages.error(request, f"Error: {str(e)}")
                return redirect('student_dashboard')

    # ====================================================
    # 🔵 GET REQUEST: DISPLAY DASHBOARD
    # ====================================================
    
    # Fetch Past Requests (Removed payment_details from select_related)
    past_requests = CertificateRequest.objects.select_related(
        'template', 'generatedcertificate'
    ).filter(student=student).order_by('-created_at')
    
    certificate_templates = CertificateTemplate.objects.all()
    
    # JSON for Dynamic Fields (JS ke liye)
    for template in certificate_templates:
        fields_data = template.required_fields if isinstance(template.required_fields, dict) else {}
        template.required_fields_json = json.dumps(fields_data)

    # Dashboard Stats
    status_counts = past_requests.aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        approved=Count('id', filter=Q(status='APPROVED')),
        rejected=Count('id', filter=Q(status='REJECTED'))
    )

    context = {
        'student': student,
        'past_requests': past_requests,
        'certificate_templates': certificate_templates,
        'pending_count': status_counts.get('pending', 0),
        'approved_count': status_counts.get('approved', 0),
        'rejected_count': status_counts.get('rejected', 0),
    }

    return render(request, 'accounts/student_dashboard.html', context)







# --- Admin Views ---
def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('portal_gateway')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_superuser or user.is_staff:
                    login(request, user)
                    return redirect('portal_gateway')
                else:
                    messages.error(request, "You are not authorized to access the admin panel.")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request, "accounts/admin_login.html", {"form": form})

def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_staff or user.is_superuser

@user_passes_test(is_admin, login_url='admin_login')
def admin_dashboard(request):
    """
    Renders the admin dashboard with statistics and charts.
    """
    # 1. Basic Stats (Purana wala logic)
    all_requests = CertificateRequest.objects.all()
    stats = all_requests.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='PENDING')),
        approved=Count('id', filter=Q(status='APPROVED')),
        rejected=Count('id', filter=Q(status='REJECTED'))
    )
    total_students = Student.objects.count()

    # 2. NEW: Fetch Requests by Certificate Type (Chart Data)
    # Yeh query template ke naam ke hisaab se group karegi aur count nikaleghi
    type_stats = CertificateRequest.objects.values('template__name').annotate(count=Count('id'))

    # Data ko list format mein convert karein taaki JS mein use ho sake
    cert_type_labels = [item['template__name'] for item in type_stats]
    cert_type_counts = [item['count'] for item in type_stats]
    
    # 3. NEW: Fetch Recent Pending Requests (Table Data)
    recent_requests = CertificateRequest.objects.filter(status='PENDING').order_by('-created_at')[:5]

    context = {
        'total_requests': stats['total'],
        'total_students': total_students,
        'pending_requests': stats['pending'],
        'approved_requests': stats['approved'],
        'rejected_requests': stats['rejected'],
        
        # New Context Variables for Chart & Table
        'cert_type_labels': cert_type_labels, 
        'cert_type_counts': cert_type_counts,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'accounts/admin_dashboard.html', context)

def logout_view(request):
    logout(request)
    return redirect('home')


# ==========================================
# 🚀 NEW GATEWAY & ROUTING LOGIC
# ==========================================

@login_required
def portal_gateway(request):
    """
    Authentication ke baad sabse pehle ye page khulega.
    Yahan user choose karega: Academic Portal vs UIET Media.
    """
    user = request.user
    
    # User ka role pata karo taaki hum page par dikha sakein
    role = 'Guest'
    if user.is_superuser:
        role = 'Director'
    elif hasattr(user, 'teacher_profile'):
        role = 'Faculty'
    elif hasattr(user, 'student_profile'):
        role = 'Student'
    
    context = {
        'user_name': user.first_name if user.first_name else user.username,
        'role': role
    }
    return render(request, 'accounts/gateway.html', context)


@login_required
def dashboard_redirect(request):
    """
    Ye view 'Router' ka kaam karega.
    Gateway se user jo bhi click karega (Academic/Social), ye usse sahi jagah bhejega.
    Usage: /account/redirect/?mode=academic  OR  /account/redirect/?mode=social
    """
    mode = request.GET.get('mode', 'academic') # Default Academic hai
    user = request.user

    # 1. SOCIAL MODE (Media App)
    if mode == 'social':
        # Jab hum campus_media app banayenge, tab uska URL name yahan aayega
        # Filhal ke liye main placeholder laga raha hu
        return redirect('campus_feed') 

    # 2. ACADEMIC MODE (Certificates & Work)
    # Check karo user kaun hai aur uske dashboard par bhejo
    if user.is_superuser:
        return redirect('admin_dashboard')
    
    elif hasattr(user, 'teacher_profile'):
        # Teacher Dashboard abhi banana baki hai, par link yahi hoga
        return redirect('teacher_dashboard') 
        
    elif hasattr(user, 'student_profile'):
        return redirect('student_dashboard')
    
    # Agar kuch samajh na aaye to Home bhej do
    return redirect('home')