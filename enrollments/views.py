from django.shortcuts import render


def index(request):
    return render(request, 'enrollments/dashboard.html', {
        'title': 'Enrollment Dashboard',
        'module_name': 'Enrollments',
        'cards': [
            {'title': 'Open Seats', 'value': '420', 'description': 'Seats remaining this term'},
            {'title': 'Pending Requests', 'value': '67', 'description': 'Awaiting review'},
            {'title': 'Approval Rate', 'value': '92%', 'description': 'Successful enrollments'},
        ]
    })
