from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='scheduling_home'),
    path('classes/', views.classes, name='scheduling_classes'),
    path('rooms/', views.rooms, name='scheduling_rooms'),
    path('rooms/add/', views.room_form, name='room_add'),
    path('rooms/<int:room_id>/edit/', views.room_form, name='room_edit'),
    path('offerings/add/', views.offering_form, name='offering_add'),
    path('offerings/<int:offering_id>/edit/', views.offering_form, name='offering_edit'),
    path('<str:kind>/<int:object_id>/delete/', views.delete_record, name='schedule_delete'),
]