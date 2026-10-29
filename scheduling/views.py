from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, 'scheduling/dashboard.html', {
        'title': 'Scheduling Dashboard',
        'module_name': 'Scheduling',
        'cards': [
            {'title': 'Classes Scheduled', 'value': '128', 'description': 'Confirmed class offerings'},
            {'title': 'Room Utilization', 'value': '83%', 'description': 'Average room occupancy'},
            {'title': 'Schedule Conflicts', 'value': '4', 'description': 'Needs review'},
        ]
    })
