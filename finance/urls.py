from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='finance_home'),
    path('payments/', views.payments, name='finance_payments'),
    path('invoices/', views.invoices, name='finance_invoices'),
]