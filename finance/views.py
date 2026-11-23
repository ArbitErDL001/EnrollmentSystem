from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from students.roles import ROLE_NAMES, has_role, roles_required
from students.models import StudentProfile
from students.notifications import notify_user

from .forms import PaymentForm
from .models import Assessment, Payment


@roles_required(*ROLE_NAMES)
def index(request):
    assessments = Assessment.objects.all()
    payments = Payment.objects.all()
    if has_role(request.user, 'Student'):
        assessments = assessments.filter(student__user=request.user)
        payments = payments.filter(assessment__student__user=request.user)
    elif not has_role(request.user, 'Admin', 'Cashier'):
        raise PermissionDenied
    outstanding = sum((assessment.balance for assessment in assessments), 0)
    collected = payments.aggregate(total=Sum('amount'))['total'] or 0
    assessment_totals = assessments.aggregate(
        tuition=Sum('tuition'),
        registration=Sum('registration_fee'),
        technology=Sum('technology_fee'),
    )
    total_assessed = sum(
        (assessment_totals.get(key) or 0)
        for key in ('tuition', 'registration', 'technology')
    )
    assessment_count = assessments.count()
    assessed_student_count = assessments.values('student_id').distinct().count()
    visible_student_count = (
        StudentProfile.objects.filter(user=request.user).count()
        if has_role(request.user, 'Student') else StudentProfile.objects.count()
    )
    balance_percent = min(round(max(outstanding, 0) / total_assessed * 100), 100) if total_assessed else 0
    collected_percent = min(round(collected / total_assessed * 100), 100) if total_assessed else 0
    assessed_students_percent = min(round(assessed_student_count / visible_student_count * 100), 100) if visible_student_count else 0
    return render(request, 'finance/dashboard.html', {
        'title': 'Finance Dashboard',
        'module_name': 'Finance',
        'payments_url': 'finance_payments',
        'invoices_url': 'finance_invoices',
        'can_manage': has_role(request.user, 'Admin', 'Cashier'),
        'cards': [
            {'title': 'Outstanding balance', 'value': f'{outstanding:,.2f}', 'description': 'Unpaid assessments',
             'chart_percent': balance_percent, 'chart_label': 'Share of assessed fees still outstanding'},
            {'title': 'Payments received', 'value': f'{collected:,.2f}', 'description': 'Recorded payments',
             'chart_percent': collected_percent, 'chart_label': 'Share of assessed fees collected'},
            {'title': 'Assessments', 'value': assessment_count, 'description': 'Student term assessments',
             'chart_percent': assessed_students_percent,
             'chart_label': 'Share of visible students with an assessment'},
        ],
    })


@roles_required('Admin', 'Cashier', 'Student')
def invoices(request):
    assessments = Assessment.objects.select_related('student__user', 'student__program').prefetch_related('payments')
    if has_role(request.user, 'Student'):
        assessments = assessments.filter(student__user=request.user)
    return render(request, 'finance/invoices.html', {'title': 'Fee Assessments', 'invoices': assessments})


@roles_required('Admin', 'Cashier', 'Student')
def assessment_detail(request, assessment_id):
    assessment = get_object_or_404(
        Assessment.objects.select_related('student__user', 'student__program').prefetch_related(
            'payments', 'student__enrollments__offering__curriculum_entry__subject'
        ),
        pk=assessment_id,
    )
    if has_role(request.user, 'Student') and assessment.student.user_id != request.user.pk:
        raise PermissionDenied
    return render(request, 'finance/assessment.html', {'assessment': assessment})


@roles_required('Admin', 'Cashier')
def payments(request):
    payment_records = Payment.objects.select_related('assessment__student__user', 'recorded_by')
    return render(request, 'finance/payments.html', {'title': 'Payment Records', 'payments': payment_records})


@roles_required('Admin', 'Cashier')
def record_payment(request, assessment_id):
    if request.method == 'POST':
        with transaction.atomic():
            assessment = get_object_or_404(
                Assessment.objects.select_for_update().select_related('student__user'),
                pk=assessment_id,
            )
            form = PaymentForm(request.POST, assessment=assessment, recorded_by=request.user)
            if form.is_valid():
                payment = form.save()
                notify_user(
                    assessment.student.user,
                    sender=request.user,
                    subject=f'Payment received: {payment.reference}',
                    body=(
                        f'Your payment of {payment.amount:.2f} was recorded for '
                        f'{assessment.term}. Your remaining balance is '
                        f'{assessment.balance:.2f}.'
                    ),
                )
                messages.success(request, f'Payment {payment.reference} recorded.')
                return redirect('assessment_detail', assessment_id=assessment.pk)
    else:
        assessment = get_object_or_404(
            Assessment.objects.select_related('student__user'), pk=assessment_id
        )
        form = PaymentForm(assessment=assessment, recorded_by=request.user)
    return render(request, 'form.html', {
        'title': f'Record payment for {assessment.student.student_id}',
        'form': form,
        'submit_label': 'Record payment',
        'cancel_url': 'assessment_detail',
        'cancel_id': assessment.pk,
    })
