from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='academics_home'),
    path('courses/', views.courses, name='academics_courses'),
    path('faculty/', views.faculty, name='academics_faculty'),
    path('programs/add/', views.program_form, name='program_add'),
    path('programs/<int:program_id>/edit/', views.program_form, name='program_edit'),
    path('subjects/add/', views.subject_form, name='subject_add'),
    path('subjects/<int:subject_id>/edit/', views.subject_form, name='subject_edit'),
    path('curriculum/add/', views.curriculum_form, name='curriculum_add'),
    path('curriculum/<int:entry_id>/edit/', views.curriculum_form, name='curriculum_edit'),
    path('<str:kind>/<int:object_id>/delete/', views.delete_record, name='academic_delete'),
]