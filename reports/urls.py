from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='reports_home'),
    path('published/', views.published, name='reports_published'),
    path('requests/', views.requests, name='reports_requests'),
]