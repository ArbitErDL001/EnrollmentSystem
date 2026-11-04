from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='reports_home'),
    path('published/', views.published, name='reports_published'),
    path('requests/', views.requests, name='reports_requests'),
    path('export/<str:kind>/<str:file_format>/', views.export_report, name='report_export'),
]