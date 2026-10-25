from django.shortcuts import render


def index(request):
    return render(request, 'academics/dashboard.html', {
        'title': 'Academic Dashboard',
        'module_name': 'Academics',
        'cards': [
            {'title': 'Courses Offered', 'value': '64', 'description': 'Available active courses'},
            {'title': 'Faculty', 'value': '38', 'description': 'Teaching staff onboard'},
            {'title': 'Curriculum Progress', 'value': '87%', 'description': 'Completion rate'},
        ]
    })
