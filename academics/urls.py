from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='academics_home'),
]