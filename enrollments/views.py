from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, 'enrollments/dashboard.html', {
        'title': 'Enrollment Dashboard',
        'module_name': 'Enrollments',
        'records_url': 'enrollments_records',
        'requests_url': 'enrollments_requests',
        'cards': [
            {'title': 'Open Seats', 'value': '420', 'description': 'Seats remaining this term'},
            {'title': 'Pending Requests', 'value': '67', 'description': 'Awaiting review'},
            {'title': 'Approval Rate', 'value': '92%', 'description': 'Successful enrollments'},
        ]
    })


@login_required
def records(request):
    return render(request, 'enrollments/records.html', {
        'title': 'Current Enrollments',
        'records': [
            {
                'student': 'Alicia Gomez',
                'course': 'Introduction to Computer Science',
                'term': 'First Semester 2026',
                'status': 'Enrolled',
            },
            {
                'student': 'Marcus Lee',
                'course': 'Principles of Business Administration',
                'term': 'First Semester 2026',
                'status': 'Enrolled',
            },
            {
                'student': 'Priya Shah',
                'course': 'Foundations of Nursing Practice',
                'term': 'First Semester 2026',
                'status': 'Enrolled',
            },
        ],
    })


@login_required
def requests(request):
    return render(request, 'enrollments/requests.html', {
        'title': 'Pending Enrollment Requests',
        'requests': [
            {
                'student': 'Noah Williams',
                'course': 'Data Structures',
                'submitted': 'October 26, 2026',
                'status': 'Awaiting review',
            },
            {
                'student': 'Sofia Chen',
                'course': 'Financial Accounting',
                'submitted': 'October 27, 2026',
                'status': 'Awaiting review',
            },
            {
                'student': 'Ethan Brown',
                'course': 'Community Health Nursing',
                'submitted': 'October 28, 2026',
                'status': 'Awaiting review',
            },
        ],
    })
