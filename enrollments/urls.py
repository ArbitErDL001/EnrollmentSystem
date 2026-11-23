from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='enrollments_home'),
    path('records/', views.records, name='enrollments_records'),
    path('requests/', views.requests, name='enrollments_requests'),
    path('requests/<int:request_id>/decision/', views.decide_request, name='enrollment_request_decision'),
    path('select/', views.enroll, name='enrollment_select'),
    path('<int:enrollment_id>/status/', views.update_status, name='enrollment_status'),
]