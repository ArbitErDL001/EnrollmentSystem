from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    if request.user.is_superuser:
        dashboard_role = 'Administrator'
    elif request.user.is_staff:
        dashboard_role = 'Staff'
    else:
        dashboard_role = 'Student'

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
            {'name': 'Alicia Gomez', 'program': 'Computer Science', 'year': '2nd Year'},
            {'name': 'Marcus Lee', 'program': 'Business Administration', 'year': '3rd Year'},
            {'name': 'Priya Shah', 'program': 'Nursing', 'year': '1st Year'},
        ]
    })
