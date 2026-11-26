from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    DirectMessageForm,
    ManagedUserCreateForm,
    ManagedUserUpdateForm,
    StudentProfileForm,
    StudentRecordForm,
    StudentRegistrationForm,
)
from .models import DirectMessage, StudentProfile
from .notifications import notify_new_account
from .roles import ROLE_NAMES, STAFF_ROLES, has_role, roles_required

User = get_user_model()
STAFF_MANAGERS = ('Admin', 'Registrar')


@login_required
def message_inbox(request):
    folder = 'sent' if request.GET.get('folder') == 'sent' else 'inbox'
    if folder == 'sent':
        direct_messages = DirectMessage.objects.filter(sender=request.user)
    else:
        direct_messages = DirectMessage.objects.filter(recipient=request.user)
    return render(request, 'students/messages/inbox.html', {
        'title': 'Messages',
        'folder': folder,
        'direct_messages': direct_messages.select_related(
            'sender',
            'recipient',
            'enrollment_request__offering__instructor',
        ),
        'is_instructor': has_role(request.user, 'Instructor'),
    })


@login_required
def message_compose(request):
    if request.method == 'POST':
        form = DirectMessageForm(request.POST, sender=request.user)
        if form.is_valid():
            direct_message = form.save(sender=request.user)
            messages.success(request, 'Message sent.')
            return redirect('message_detail', message_id=direct_message.pk)
    else:
        initial = {}
        recipient_id = request.GET.get('to')
        if recipient_id:
            initial['recipient'] = recipient_id
        form = DirectMessageForm(sender=request.user, initial=initial)
    return render(request, 'students/messages/compose.html', {
        'title': 'New message',
        'form': form,
    })


@login_required
def message_detail(request, message_id):
    direct_message = get_object_or_404(
        DirectMessage.objects.select_related('sender', 'recipient').filter(
            Q(sender=request.user) | Q(recipient=request.user)
        ),
        pk=message_id,
    )
    if direct_message.recipient_id == request.user.pk and direct_message.read_at is None:
        direct_message.read_at = timezone.now()
        direct_message.save(update_fields=('read_at',))
    from enrollments.models import EnrollmentRequest

    enrollment_request = EnrollmentRequest.objects.select_related(
        'offering__instructor'
    ).filter(notification_message=direct_message).first()
    return render(request, 'students/messages/detail.html', {
        'title': direct_message.subject,
        'direct_message': direct_message,
        'enrollment_request': enrollment_request,
        'can_accept_enrollment_request': (
            enrollment_request is not None
            and enrollment_request.status == 'pending'
            and enrollment_request.offering.instructor_id == request.user.pk
            and has_role(request.user, 'Instructor')
        ),
    })


@roles_required(*ROLE_NAMES)
def home(request):
    if request.user.is_superuser:
        dashboard_role = 'Admin'
    else:
        dashboard_role = request.user.groups.filter(
            name__in=ROLE_NAMES
        ).values_list('name', flat=True).first() or 'Student'
    if request.user.is_superuser:
        from academics.models import Program
        from enrollments.models import Enrollment
        from finance.models import Assessment, Payment
        from scheduling.models import ClassOffering

        current_term = ClassOffering.objects.order_by('-term').values_list('term', flat=True).first()
        current_enrollments = Enrollment.objects.filter(
            status='enrolled',
            offering__term=current_term,
        ) if current_term else Enrollment.objects.none()
        assessment_totals = Assessment.objects.aggregate(
            tuition=Sum('tuition'),
            registration=Sum('registration_fee'),
            technology=Sum('technology_fee'),
        )
        total_assessed = sum(
            (assessment_totals.get(key) or 0)
            for key in ('tuition', 'registration', 'technology')
        )
        total_collected = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        program_enrollments = list(
            current_enrollments.values('student__program__code').annotate(total=Count('pk'))
            .order_by('-total')[:5]
        )
        recent_payments = Payment.objects.select_related(
            'assessment__student__user', 'recorded_by'
        )[:5]
        recent_students = StudentProfile.objects.select_related('user', 'program').order_by('-created_at')[:5]
        total_students = StudentProfile.objects.count()
        active_students = StudentProfile.objects.filter(status='active').count()
        current_enrollment_count = current_enrollments.count()
        student_activity_percent = round(active_students / total_students * 100) if total_students else 0
        enrollment_percent = min(round(current_enrollment_count / total_students * 100), 100) if total_students else 0
        collection_percent = min(round(total_collected / total_assessed * 100), 100) if total_assessed else 0
        balance_percent = min(round(max(total_assessed - total_collected, 0) / total_assessed * 100), 100) if total_assessed else 0
        return render(request, 'admin_dashboard.html', {
            'title': 'Administrator Dashboard',
            'dashboard_role': 'Admin',
            'current_term': current_term or 'No term configured',
            'total_students': total_students,
            'active_students': active_students,
            'program_count': Program.objects.filter(is_active=True).count(),
            'current_enrollment_count': current_enrollment_count,
            'total_collected': total_collected,
            'total_balance': max(total_assessed - total_collected, 0),
            'total_assessed': total_assessed,
            'student_activity_percent': student_activity_percent,
            'enrollment_percent': enrollment_percent,
            'collection_percent': collection_percent,
            'balance_percent': balance_percent,
            'role_counts': [
                {
                    'name': role,
                    'count': User.objects.filter(is_superuser=True).count()
                    if role == 'Admin' else User.objects.filter(groups__name=role).count(),
                }
                for role in ROLE_NAMES
            ],
            'program_enrollments': program_enrollments,
            'recent_payments': recent_payments,
            'recent_students': recent_students,
        })
    if request.user.is_superuser:
        sections = [
            ('Students', 'students_home'), ('Academics', 'academics_home'),
            ('Enrollments', 'enrollments_home'), ('Finance', 'finance_home'),
            ('Scheduling', 'scheduling_home'), ('Reports', 'reports_home'),
            ('User management', 'user_management'),
        ]
    elif dashboard_role == 'Registrar':
        sections = [('Students', 'students_home'), ('Academics', 'academics_home'),
                    ('Enrollments', 'enrollments_home'), ('Scheduling', 'scheduling_home'),
                    ('Reports', 'reports_home')]
    elif dashboard_role == 'Cashier':
        sections = [('Finance', 'finance_home'), ('Reports', 'reports_home')]
    elif dashboard_role == 'Instructor':
        sections = [('Enrollments', 'enrollments_home'), ('Scheduling', 'scheduling_home')]
    else:
        sections = [('Students', 'student_profile'), ('Enrollments', 'enrollments_home'),
                    ('Scheduling', 'scheduling_home'), ('Finance', 'finance_home')]
    return render(request, 'home.html', {
        'dashboard_role': dashboard_role,
        'sections': [{'name': name, 'url': reverse(url_name)} for name, url_name in sections],
    })


@roles_required('Admin', 'Registrar', 'Student')
def index(request):
    profile = getattr(request.user, 'student_profile', None)
    if profile:
        profiles = StudentProfile.objects.filter(pk=profile.pk)
    elif has_role(request.user, *STAFF_MANAGERS):
        profiles = StudentProfile.objects.select_related('user', 'program')
    else:
        profiles = StudentProfile.objects.none()
    total_students = profiles.count()
    active_students = profiles.filter(status='active').count()
    return render(request, 'students/dashboard.html', {
        'title': 'Student Records',
        'module_name': 'Students',
        'directory_url': 'student_directory',
        'admissions_url': 'student_admissions',
        'is_student': has_role(request.user, 'Student') and not has_role(request.user, 'Admin', 'Registrar'),
        'can_manage_users': request.user.is_superuser,
        'cards': [
            {
                'title': 'Registered students',
                'value': total_students,
                'description': 'Visible to your role',
                'chart_percent': 100 if total_students else 0,
                'chart_label': 'All visible student records',
            },
            {
                'title': 'Active students',
                'value': active_students,
                'description': 'Current active records',
                'chart_percent': round(active_students / total_students * 100) if total_students else 0,
                'chart_label': 'Share of visible student records that are active',
            },
        ],
    })


@roles_required(*STAFF_MANAGERS)
def list_students(request):
    students = StudentProfile.objects.select_related('user', 'program').all()
    return render(request, 'students/list.html', {'title': 'Student Directory', 'students': students})


@roles_required(*STAFF_MANAGERS)
def admissions(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                user.groups.add(Group.objects.get(name='Student'))
                profile = StudentProfile.objects.create(
                    user=user,
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                    date_of_birth=form.cleaned_data['date_of_birth'],
                    program=form.cleaned_data['program'],
                    year_level=form.cleaned_data['year_level'],
                )
                notify_new_account(
                    user, 'Student', sender=request.user, student_profile=profile
                )
            messages.success(request, f'Student account created with username {user.username}.')
            return redirect('student_directory')
    else:
        form = StudentRegistrationForm()
    return render(request, 'form.html', {
        'title': 'Register a Student',
        'form': form,
        'submit_label': 'Register student',
    })


@roles_required('Student')
def profile(request):
    student = StudentProfile.objects.filter(user=request.user).first()
    if not student:
        if request.method != 'POST':
            form = StudentProfileForm()
            return render(request, 'form.html', {'title': 'Create Student Profile', 'form': form, 'submit_label': 'Save profile'})
        form = StudentProfileForm(request.POST)
        if form.is_valid():
            form.instance.user = request.user
            student = form.save()
            messages.success(request, 'Your student profile has been created.')
            return redirect('student_profile')
    elif request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('student_profile')
    else:
        form = StudentProfileForm(instance=student)
    return render(request, 'form.html', {
        'title': 'My Student Profile',
        'form': form,
        'submit_label': 'Save profile',
        'student_id': student.student_id if student else None,
    })


@roles_required(*STAFF_MANAGERS)
def edit_student(request, student_id):
    student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=student_id)
    if request.method == 'POST':
        form = StudentRecordForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student profile updated.')
            return redirect('student_directory')
    else:
        form = StudentRecordForm(instance=student)
    return render(request, 'form.html', {'title': f'Edit {student.student_id}', 'form': form, 'submit_label': 'Save changes'})


def _require_admin(request):
    if not request.user.is_superuser:
        raise PermissionDenied


@login_required
def user_management(request):
    _require_admin(request)
    users = User.objects.prefetch_related('groups').order_by('username')
    return render(request, 'students/user_management.html', {
        'title': 'User Management',
        'users': users,
    })


@login_required
def add_user(request):
    _require_admin(request)
    if request.method == 'POST':
        form = ManagedUserCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                role = form.cleaned_data['role']
                user.is_superuser = role == 'Admin'
                user.is_staff = role in STAFF_ROLES
                user.save()
                user.groups.set([Group.objects.get(name=role)])
                profile = None
                if role == 'Student':
                    profile, _ = StudentProfile.objects.get_or_create(user=user)
                notify_new_account(
                    user, role, sender=request.user, student_profile=profile
                )
            messages.success(request, f'{role} account created.')
            return redirect('user_management')
    else:
        form = ManagedUserCreateForm()
    return render(request, 'form.html', {'title': 'Create User Account', 'form': form, 'submit_label': 'Create account'})


@login_required
def edit_user(request, user_id):
    _require_admin(request)
    managed_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = ManagedUserUpdateForm(request.POST, instance=managed_user)
        if form.is_valid():
            if managed_user.pk == request.user.pk:
                if form.cleaned_data['role'] != 'Admin':
                    form.add_error('role', 'You cannot remove your own administrator role.')
                if not form.cleaned_data['is_active']:
                    form.add_error('is_active', 'You cannot deactivate your own account.')
            if form.errors:
                return render(request, 'form.html', {
                    'title': f'Edit account: {managed_user.username}',
                    'form': form,
                    'submit_label': 'Save account',
                })
            user = form.save(commit=False)
            role = form.cleaned_data['role']
            user.is_superuser = role == 'Admin'
            user.is_staff = role in STAFF_ROLES
            user.save()
            user.groups.set([Group.objects.get(name=role)])
            if role == 'Student':
                StudentProfile.objects.get_or_create(user=user)
            messages.success(request, 'User account and role updated.')
            return redirect('user_management')
    else:
        form = ManagedUserUpdateForm(instance=managed_user)
    return render(request, 'form.html', {'title': f'Edit account: {managed_user.username}', 'form': form, 'submit_label': 'Save account'})


@login_required
@require_POST
def delete_user(request, user_id):
    _require_admin(request)
    managed_user = get_object_or_404(User, pk=user_id)
    if managed_user.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account.')
    else:
        try:
            managed_user.delete()
        except ProtectedError:
            messages.error(request, 'This student account has enrollment or finance records and cannot be deleted.')
        else:
            messages.success(request, 'User account deleted.')
    return redirect('user_management')
