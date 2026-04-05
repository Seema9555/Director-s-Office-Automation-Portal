# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('student_login/', views.student_login_view, name='student_login'),
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin_login/', views.admin_login_view, name='admin_login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.logout_view, name='logout'),
]