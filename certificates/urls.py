# from django.urls import path
# from . import views


# urlpatterns = [
#     # Certificate Request URLs
#     path('manage/', views.manage_certificate_requests, name='manage_requests'),
#     path('approve/<int:request_id>/', views.approve_request, name='approve_request'),
#     path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    
#     # Student Management URLs
#     path('manage-students/', views.manage_students_view, name='manage_students'),
#     path('add-student/', views.add_student_view, name='add_student'),
#     path('edit-student/<int:student_id>/', views.edit_student_view, name='edit_student'),
#     path('delete-student/<int:student_id>/', views.delete_student_view, name='delete_student'),
# ]

from django.urls import path
from . import views


urlpatterns = [
    # Certificate Request URLs
    path('manage/', views.manage_certificate_requests, name='manage_requests'),
    path('approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    path('generate/<int:request_id>/', views.generate_certificate_pdf, name='generate_certificate'), # <-- ADD THIS LINE
    path('bulk-approve/', views.bulk_approve_requests, name='bulk_approve'),

    # Student Management URLs
    path('manage-students/', views.manage_students_view, name='manage_students'),
    path('add-student/', views.add_student_view, name='add_student'),
    path('edit-student/<int:student_id>/', views.edit_student_view, name='edit_student'),
    path('delete-student/<int:student_id>/', views.delete_student_view, name='delete_student'),
    path('verify/', views.verify_certificate_public, name='verify_certificate'),
    path('student/correction/<int:request_id>/', views.request_correction, name='request_correction'),
    path('manage/edit/<int:request_id>/', views.admin_edit_request, name='admin_edit_request'),
    path('student/help-desk/', views.student_help_desk, name='student_help_desk'),
    path('manage/help-desk/', views.admin_help_desk, name='admin_help_desk'),
    path('manage/edit/<int:request_id>/', views.edit_request_data, name='edit_request_data'),
    # --- TEACHER MANAGEMENT URLs (New) ---
    path('manage-teachers/', views.manage_teachers_view, name='manage_teachers'),
    path('add-teacher/', views.add_teacher_view, name='add_teacher'),
    path('edit-teacher/<int:teacher_id>/', views.edit_teacher_view, name='edit_teacher'),
    path('delete-teacher/<int:teacher_id>/', views.delete_teacher_view, name='delete_teacher'),
]

