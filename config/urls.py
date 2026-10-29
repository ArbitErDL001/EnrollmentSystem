from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from config.views import register
from students.views import home

urlpatterns = [
    path('accounts/login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/register/', register, name='register'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('', home, name='home'),
    path('students/', include('students.urls')),
    path('academics/', include('academics.urls')),
    path('enrollments/', include('enrollments.urls')),
    path('finance/', include('finance.urls')),
    path('scheduling/', include('scheduling.urls')),
    path('reports/', include('reports.urls')),
    path('admin/', admin.site.urls),
]
