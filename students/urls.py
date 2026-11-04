from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='students_home'),
    path('messages/', views.message_inbox, name='message_inbox'),
    path('messages/compose/', views.message_compose, name='message_compose'),
    path('messages/<int:message_id>/', views.message_detail, name='message_detail'),
    path('directory/', views.list_students, name='student_directory'),
    path('admissions/', views.admissions, name='student_admissions'),
    path('profile/', views.profile, name='student_profile'),
    path('directory/<int:student_id>/edit/', views.edit_student, name='student_edit'),
    path('users/', views.user_management, name='user_management'),
    path('users/add/', views.add_user, name='user_add'),
    path('users/<int:user_id>/edit/', views.edit_user, name='user_edit'),
    path('users/<int:user_id>/delete/', views.delete_user, name='user_delete'),
]