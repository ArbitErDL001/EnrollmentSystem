from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='students_home'),
    path('directory/', views.list_students, name='student_directory'),
    path('admissions/', views.admissions, name='student_admissions'),
]