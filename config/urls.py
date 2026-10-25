from django.contrib import admin
from django.urls import include, path

from students.views import home

urlpatterns = [
    path('', home, name='home'),
    path('students/', include('students.urls')),
    path('academics/', include('academics.urls')),
    path('enrollments/', include('enrollments.urls')),
    path('finance/', include('finance.urls')),
    path('scheduling/', include('scheduling.urls')),
    path('reports/', include('reports.urls')),
    path('admin/', admin.site.urls),
]
