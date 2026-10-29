from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, 'reports/dashboard.html', {
        'title': 'Reports Dashboard',
        'module_name': 'Reports',
        'published_url': 'reports_published',
        'requests_url': 'reports_requests',
        'cards': [
            {'title': 'Published Reports', 'value': '24', 'description': 'Current reports in circulation'},
            {'title': 'Pending Requests', 'value': '11', 'description': 'New analysis tasks'},
            {'title': 'Data Accuracy', 'value': '99.2%', 'description': 'Verified data quality'},
        ]
    })


@login_required
def published(request):
    return render(request, 'reports/published.html', {
        'title': 'Published Reports',
        'reports': [
            {
                'name': 'Enrollment Summary',
                'category': 'Enrollment',
                'period': 'First Semester 2026',
                'published': 'October 15, 2026',
                'owner': 'Registrar Office',
            },
            {
                'name': 'Tuition Collection Report',
                'category': 'Finance',
                'period': 'Academic Year 2026',
                'published': 'October 18, 2026',
                'owner': 'Finance Office',
            },
            {
                'name': 'Student Retention Analysis',
                'category': 'Students',
                'period': 'Academic Year 2025',
                'published': 'October 21, 2026',
                'owner': 'Student Affairs',
            },
        ],
    })


@login_required
def requests(request):
    return render(request, 'reports/requests.html', {
        'title': 'Pending Report Requests',
        'requests': [
            {
                'name': 'Department Enrollment Breakdown',
                'requester': 'Academic Affairs',
                'submitted': 'October 25, 2026',
                'priority': 'High',
                'status': 'Pending',
            },
            {
                'name': 'Outstanding Fees by Program',
                'requester': 'Finance Office',
                'submitted': 'October 27, 2026',
                'priority': 'Normal',
                'status': 'Pending',
            },
            {
                'name': 'Faculty Workload Summary',
                'requester': 'Human Resources',
                'submitted': 'October 28, 2026',
                'priority': 'Normal',
                'status': 'Pending',
            },
        ],
    })
