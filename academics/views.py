from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, 'academics/dashboard.html', {
        'title': 'Academic Dashboard',
        'module_name': 'Academics',
        'courses_url': 'academics_courses',
        'faculty_url': 'academics_faculty',
        'cards': [
            {'title': 'Courses Offered', 'value': '64', 'description': 'Available active courses'},
            {'title': 'Faculty', 'value': '38', 'description': 'Teaching staff onboard'},
            {'title': 'Curriculum Progress', 'value': '87%', 'description': 'Completion rate'},
        ]
    })


@login_required
def courses(request):
    return render(request, 'academics/courses.html', {
        'title': 'Courses Offered',
        'courses': [
            {
                'code': 'CS101',
                'name': 'Introduction to Computer Science',
                'department': 'Computer Science',
                'units': 3,
                'status': 'Active',
            },
            {
                'code': 'BA201',
                'name': 'Principles of Business Administration',
                'department': 'Business Administration',
                'units': 3,
                'status': 'Active',
            },
            {
                'code': 'NUR110',
                'name': 'Foundations of Nursing Practice',
                'department': 'Nursing',
                'units': 4,
                'status': 'Active',
            },
        ],
    })


@login_required
def faculty(request):
    return render(request, 'academics/faculty.html', {
        'title': 'Faculty Directory',
        'faculty_members': [
            {
                'name': 'Dr. Elena Santos',
                'department': 'Computer Science',
                'specialization': 'Software Engineering',
                'status': 'Full-time',
            },
            {
                'name': 'Prof. Daniel Reyes',
                'department': 'Business Administration',
                'specialization': 'Operations Management',
                'status': 'Full-time',
            },
            {
                'name': 'Dr. Maya Patel',
                'department': 'Nursing',
                'specialization': 'Community Health',
                'status': 'Part-time',
            },
        ],
    })
