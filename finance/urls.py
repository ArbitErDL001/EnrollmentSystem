from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='finance_home'),
    path('payments/', views.payments, name='finance_payments'),
    path('invoices/', views.invoices, name='finance_invoices'),
    path('assessments/<int:assessment_id>/', views.assessment_detail, name='assessment_detail'),
    path('assessments/<int:assessment_id>/payment/', views.record_payment, name='record_payment'),
]