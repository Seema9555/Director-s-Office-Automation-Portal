"""
URL configuration for Director_Portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
# ==========================================================
#                  NECESSARY IMPORTS FOR MEDIA FILES
# ==========================================================
from django.conf import settings
from django.conf.urls.static import static
from certificates.views import verify_certificate_public
urlpatterns = [
    path('admin/', admin.site.urls), 
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('certificates/', include('certificates.urls')),
    path('verify/', verify_certificate_public, name='verify_certificate_public'),
    path('social/', include('campus_media.urls')),
]

# ==========================================================
#         URL PATTERN FOR SERVING MEDIA FILES IN DEBUG MODE
# ==========================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
