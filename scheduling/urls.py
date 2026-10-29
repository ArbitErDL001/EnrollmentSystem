from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='scheduling_home'),
    path('classes/', views.classes, name='scheduling_classes'),
    path('rooms/', views.rooms, name='scheduling_rooms'),
]