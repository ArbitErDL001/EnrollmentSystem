from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    if request.user.is_superuser:
        dashboard_role = 'Admin'
    else:
        dashboard_role = request.user.groups.filter(
            name__in=('Registrar', 'Cashier', 'Instructor', 'Student')
        ).values_list('name', flat=True).first()
        if dashboard_role is None:
            dashboard_role = 'Staff' if request.user.is_staff else 'Student'

    return render(request, 'home.html', {
        'dashboard_role': dashboard_role,
        'sections': [
            {'name': 'Students', 'url': '/students/'},
            {'name': 'Academics', 'url': '/academics/'},
            {'name': 'Enrollments', 'url': '/enrollments/'},
            {'name': 'Finance', 'url': '/finance/'},
            {'name': 'Scheduling', 'url': '/scheduling/'},
            {'name': 'Reports', 'url': '/reports/'},
        ]
    })


@login_required
def index(request):
    return render(request, 'students/dashboard.html', {
        'title': 'Student Dashboard',
        'module_name': 'Students',
        'directory_url': 'student_directory',
        'admissions_url': 'student_admissions',
        'cards': [
            {'title': 'Student Records', 'value': '1,240', 'description': 'Active student records'},
            {'title': 'New Admissions', 'value': '86', 'description': 'Applications this term'},
            {'title': 'Retention Rate', 'value': '94%', 'description': 'Retention across departments'},
        ]
    })


@login_required
def list_students(request):
    return render(request, 'students/list.html', {
        'title': 'Student Directory',
        'students': [
            {
                'name': 'Alicia Gomez',
                'student_id': 'STU-2026-001',
                'program': 'Computer Science',
                'year': '2nd Year',
                'status': 'Active',
            },
            {
                'name': 'Marcus Lee',
                'student_id': 'STU-2026-002',
                'program': 'Business Administration',
                'year': '3rd Year',
                'status': 'Active',
            },
            {
                'name': 'Priya Shah',
                'student_id': 'STU-2026-003',
                'program': 'Nursing',
                'year': '1st Year',
                'status': 'Active',
            },
        ]
    })


@login_required
def admissions(request):
    return render(request, 'students/admissions.html', {
        'title': 'New Admissions',
        'admissions': [
            {
                'applicant': 'Noah Williams',
                'program': 'Computer Science',
                'submitted': 'October 24, 2026',
                'status': 'Under review',
            },
            {
                'applicant': 'Sofia Chen',
                'program': 'Business Administration',
                'submitted': 'October 26, 2026',
                'status': 'Documents pending',
            },
            {
                'applicant': 'Ethan Brown',
                'program': 'Nursing',
                'submitted': 'October 28, 2026',
                'status': 'Under review',
            },
        ],
    })
