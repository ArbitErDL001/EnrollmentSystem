from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from finance.services import refresh_assessment
from students.models import StudentProfile
from students.roles import has_role, roles_required

from .models import Enrollment

ENROLLMENT_ROLES = ('Admin', 'Registrar', 'Instructor', 'Student')


@roles_required(*ENROLLMENT_ROLES)
def index(request):
    visible = Enrollment.objects.all()
    if has_role(request.user, 'Student'):
        visible = visible.filter(student__user=request.user)
    elif has_role(request.user, 'Instructor') and not has_role(request.user, 'Admin', 'Registrar'):
        visible = visible.filter(offering__instructor=request.user)
    visible_count = visible.count()
    enrolled_count = visible.filter(status='enrolled').count()
    completed_count = visible.filter(status='completed').count()
    return render(request, 'enrollments/dashboard.html', {
        'title': 'Enrollment Dashboard',
        'module_name': 'Enrollments',
        'records_url': 'enrollments_records',
        'requests_url': 'enrollments_requests',
        'cards': [
            {'title': 'Enrolled records', 'value': enrolled_count, 'description': 'Current enrollment records',
             'chart_percent': round(enrolled_count / visible_count * 100) if visible_count else 0,
             'chart_label': 'Share of visible records currently enrolled'},
            {'title': 'Completed subjects', 'value': completed_count, 'description': 'Recorded completions',
             'chart_percent': round(completed_count / visible_count * 100) if visible_count else 0,
             'chart_label': 'Share of visible records completed'},
        ],
        'can_enroll': has_role(request.user, 'Student'),
    })


@roles_required(*ENROLLMENT_ROLES)
def records(request):
    enrollments = Enrollment.objects.select_related(
        'student__user', 'student__program', 'offering__curriculum_entry__subject',
        'offering__room', 'offering__instructor',
    )
    if has_role(request.user, 'Student'):
        enrollments = enrollments.filter(student__user=request.user)
    elif has_role(request.user, 'Instructor') and not has_role(request.user, 'Admin', 'Registrar'):
        enrollments = enrollments.filter(offering__instructor=request.user)
    elif not has_role(request.user, 'Admin', 'Registrar'):
        raise PermissionDenied
    return render(request, 'enrollments/records.html', {
        'title': 'Enrollment Records',
        'records': enrollments,
        'can_update': has_role(request.user, 'Admin', 'Registrar'),
    })


@roles_required(*ENROLLMENT_ROLES)
def requests(request):
    if has_role(request.user, 'Student'):
        return redirect('enrollment_select')
    return redirect('enrollments_records')


@roles_required('Student')
def enroll(request):
    student = StudentProfile.objects.filter(user=request.user).select_related('program').first()
    if not student:
        messages.info(request, 'Complete your student profile before selecting classes.')
        return redirect('student_profile')
    from scheduling.models import ClassOffering
    term = request.GET.get('term') or request.POST.get('term') or ''
    available = ClassOffering.objects.filter(
        is_active=True,
        curriculum_entry__program=student.program,
        curriculum_entry__year_level=student.year_level,
    ).select_related('curriculum_entry__subject', 'room', 'instructor').order_by('term', 'start_time')
    if term:
        available = available.filter(term=term)
    elif available.exists():
        term = available.values_list('term', flat=True).last()
        available = available.filter(term=term)
    if request.method == 'POST':
        offering = get_object_or_404(available, pk=request.POST.get('offering'))
        try:
            with transaction.atomic():
                enrollment = Enrollment(student=student, offering=offering)
                enrollment.full_clean()
                enrollment.save()
                assessment = refresh_assessment(student, offering.term)
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        except IntegrityError:
            messages.error(request, 'You are already enrolled in this class.')
        else:
            messages.success(request, f'Enrolled in {offering}. Current balance: {assessment.balance:.2f}.')
            return redirect('enrollments_records')
    existing_subject_ids = student.enrollments.filter(
        status='enrolled', offering__term=term
    ).values_list('offering__curriculum_entry__subject_id', flat=True)
    available = available.exclude(curriculum_entry__subject_id__in=existing_subject_ids)
    return render(request, 'enrollments/select.html', {
        'title': 'Select Classes',
        'offerings': available,
        'term': term,
        'terms': ClassOffering.objects.filter(
            is_active=True,
            curriculum_entry__program=student.program,
            curriculum_entry__year_level=student.year_level,
        ).values_list('term', flat=True).distinct().order_by('term'),
    })


@roles_required('Admin', 'Registrar')
@require_POST
def update_status(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('student', 'offering'), pk=enrollment_id
    )
    status = request.POST.get('status')
    if status not in {'enrolled', 'completed', 'dropped'}:
        messages.error(request, 'Invalid enrollment status.')
    else:
        enrollment.status = status
        enrollment.full_clean()
        enrollment.save(update_fields=('status',))
        refresh_assessment(enrollment.student, enrollment.offering.term)
        messages.success(request, 'Enrollment status updated.')
    return redirect('enrollments_records')
