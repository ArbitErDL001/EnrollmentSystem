from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='academics_home'),
    path('courses/', views.courses, name='academics_courses'),
    path('faculty/', views.faculty, name='academics_faculty'),
]