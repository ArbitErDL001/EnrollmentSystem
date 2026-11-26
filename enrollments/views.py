from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from finance.services import refresh_assessment
from scheduling.models import ClassOffering
from students.models import StudentProfile
from students.notifications import notify_role_members, notify_user
from students.roles import has_role, roles_required

from .models import Enrollment, EnrollmentRequest

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
    is_student = has_role(request.user, 'Student') and not has_role(
        request.user, 'Admin', 'Instructor', 'Registrar'
    )
    can_decide = has_role(request.user, 'Admin', 'Instructor')
    enrollment_requests = EnrollmentRequest.objects.select_related(
        'student__user', 'student__program', 'offering__curriculum_entry__subject',
        'offering__instructor',
    )
    if is_student:
        enrollment_requests = enrollment_requests.filter(student__user=request.user)
        title = 'My Enrollment Requests'
    elif has_role(request.user, 'Instructor') and not has_role(request.user, 'Admin'):
        enrollment_requests = enrollment_requests.filter(offering__instructor=request.user)
        title = 'Enrollment Requests'
    else:
        title = 'Enrollment Requests'
    return render(request, 'enrollments/requests.html', {
        'title': title,
        'enrollment_requests': enrollment_requests,
        'can_decide': can_decide,
        'is_student': is_student,
    })


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
                if EnrollmentRequest.objects.filter(
                    student=student,
                    status='pending',
                    offering__term=offering.term,
                    offering__curriculum_entry__subject=offering.curriculum_entry.subject,
                ).exists():
                    raise ValidationError('You already have a pending request for this subject.')
                Enrollment(student=student, offering=offering).full_clean()
                enrollment_request = EnrollmentRequest.objects.create(
                    student=student,
                    offering=offering,
                )
                subject = offering.curriculum_entry.subject
                notification = notify_user(
                    offering.instructor,
                    sender=request.user,
                    subject=f'Enrollment request: {subject.code} {offering.section}',
                    body=(
                        f'{student.user.get_full_name() or student.user.username} '
                        f'({student.student_id}) requested {subject.code}, section '
                        f'{offering.section}, for {offering.term}.\n'
                        'Open Enrollments → Enrollment requests to review it.'
                    ),
                )
                enrollment_request.notification_message = notification
                enrollment_request.save(update_fields=('notification_message',))
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        except IntegrityError:
            messages.error(request, 'A request for this class is already pending.')
        else:
            messages.success(request, f'Enrollment request submitted for {offering}.')
            return redirect('enrollments_requests')
    existing_subject_ids = student.enrollments.filter(
        status='enrolled', offering__term=term
    ).values_list('offering__curriculum_entry__subject_id', flat=True)
    available = available.exclude(curriculum_entry__subject_id__in=existing_subject_ids)
    pending_subject_ids = EnrollmentRequest.objects.filter(
        student=student, status='pending', offering__term=term,
    ).values_list('offering__curriculum_entry__subject_id', flat=True)
    available = available.exclude(curriculum_entry__subject_id__in=pending_subject_ids)
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


@roles_required('Admin', 'Instructor')
@require_POST
def decide_request(request, request_id):
    enrollment_request = get_object_or_404(
        EnrollmentRequest.objects.select_related('offering__instructor'), pk=request_id
    )
    if not has_role(request.user, 'Admin') and enrollment_request.offering.instructor_id != request.user.pk:
        raise PermissionDenied

    decision = request.POST.get('decision')
    if decision not in {'accept', 'reject'}:
        messages.error(request, 'Choose whether to accept or reject this request.')
        return redirect('enrollments_requests')

    try:
        with transaction.atomic():
            enrollment_request = EnrollmentRequest.objects.select_for_update().select_related(
                'student'
            ).get(pk=request_id)
            offering = ClassOffering.objects.select_for_update().select_related(
                'curriculum_entry__subject'
            ).get(pk=enrollment_request.offering_id)
            if not has_role(request.user, 'Admin') and offering.instructor_id != request.user.pk:
                raise PermissionDenied
            if enrollment_request.status != 'pending':
                messages.error(request, 'This enrollment request has already been decided.')
                return redirect('enrollments_requests')

            if decision == 'accept':
                enrollment = Enrollment(
                    student=enrollment_request.student,
                    offering=offering,
                )
                enrollment.full_clean()
                enrollment.save()
                refresh_assessment(enrollment_request.student, offering.term)
                enrollment_request.status = 'accepted'
                success_message = 'Enrollment request accepted.'
            else:
                enrollment_request.status = 'rejected'
                success_message = 'Enrollment request rejected.'

            enrollment_request.decided_at = timezone.now()
            enrollment_request.decided_by = request.user
            enrollment_request.save(update_fields=('status', 'decided_at', 'decided_by'))
            student = enrollment_request.student
            subject = offering.curriculum_entry.subject
            if decision == 'accept':
                notify_user(
                    student.user,
                    sender=request.user,
                    subject=f'Enrollment approved: {subject.code}',
                    body=(
                        f'Your request for {subject.code}, section {offering.section}, '
                        f'for {offering.term} was accepted. Open Enrollment Records '
                        'to view your enrolled subjects.'
                    ),
                )
                notify_role_members(
                    ('Registrar', 'Cashier'),
                    sender=request.user,
                    subject=f'Enrollment approved: {student.student_id}',
                    body=(
                        f'{student.student_id} is enrolled in {subject.code}, section '
                        f'{offering.section}, for {offering.term}.\n'
                        'The assessment has been refreshed. Review Enrollment Records '
                        'or open Finance → Fee Assessments to process the balance.'
                    ),
                )
            else:
                notify_user(
                    student.user,
                    sender=request.user,
                    subject=f'Enrollment request rejected: {subject.code}',
                    body=(
                        f'Your request for {subject.code}, section {offering.section}, '
                        f'for {offering.term} was rejected. Open My Enrollment Requests '
                        'for its status.'
                    ),
                )
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    except IntegrityError:
        messages.error(request, 'The enrollment could not be accepted because the student is already enrolled.')
    else:
        messages.success(request, success_message)
    return redirect('enrollments_requests')


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
