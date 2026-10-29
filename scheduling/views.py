from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, 'scheduling/dashboard.html', {
        'title': 'Scheduling Dashboard',
        'module_name': 'Scheduling',
        'classes_url': 'scheduling_classes',
        'rooms_url': 'scheduling_rooms',
        'cards': [
            {'title': 'Classes Scheduled', 'value': '128', 'description': 'Confirmed class offerings'},
            {'title': 'Room Utilization', 'value': '83%', 'description': 'Average room occupancy'},
            {'title': 'Schedule Conflicts', 'value': '4', 'description': 'Needs review'},
        ]
    })


@login_required
def classes(request):
    return render(request, 'scheduling/classes.html', {
        'title': 'Class Schedule',
        'classes': [
            {
                'course': 'Introduction to Computer Science',
                'section': 'CS101-A',
                'day': 'Monday and Wednesday',
                'time': '9:00 AM - 10:30 AM',
                'room': 'Room 201',
                'instructor': 'Dr. Elena Santos',
            },
            {
                'course': 'Principles of Business Administration',
                'section': 'BA201-B',
                'day': 'Tuesday and Thursday',
                'time': '10:30 AM - 12:00 PM',
                'room': 'Room 105',
                'instructor': 'Prof. Daniel Reyes',
            },
            {
                'course': 'Foundations of Nursing Practice',
                'section': 'NUR110-A',
                'day': 'Friday',
                'time': '1:00 PM - 4:00 PM',
                'room': 'Nursing Lab 1',
                'instructor': 'Dr. Maya Patel',
            },
        ],
    })


@login_required
def rooms(request):
    return render(request, 'scheduling/rooms.html', {
        'title': 'Room Availability',
        'rooms': [
            {
                'room': 'Room 105',
                'building': 'Main Building',
                'capacity': 40,
                'availability': 'Available',
                'next_booking': 'Tuesday, 10:30 AM',
            },
            {
                'room': 'Room 201',
                'building': 'Science Building',
                'capacity': 35,
                'availability': 'In use',
                'next_booking': 'Monday, 9:00 AM',
            },
            {
                'room': 'Nursing Lab 1',
                'building': 'Health Sciences Building',
                'capacity': 25,
                'availability': 'Available',
                'next_booking': 'Friday, 1:00 PM',
            },
        ],
    })
