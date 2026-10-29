from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='enrollments_home'),
    path('records/', views.records, name='enrollments_records'),
    path('requests/', views.requests, name='enrollments_requests'),
]