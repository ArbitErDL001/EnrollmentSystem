from django.shortcuts import render


def home(request):
    return render(request, 'home.html', {
        'title': 'Enrollment System',
        'sections': [
            {'name': 'Students', 'url': '/students/'},
            {'name': 'Academics', 'url': '/academics/'},
            {'name': 'Enrollments', 'url': '/enrollments/'},
            {'name': 'Finance', 'url': '/finance/'},
            {'name': 'Scheduling', 'url': '/scheduling/'},
            {'name': 'Reports', 'url': '/reports/'},
        ]
    })


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


def list_students(request):
    return render(request, 'students/list.html', {
        'title': 'Student Directory',
        'students': [
            {'name': 'Alicia Gomez', 'program': 'Computer Science', 'year': '2nd Year'},
            {'name': 'Marcus Lee', 'program': 'Business Administration', 'year': '3rd Year'},
            {'name': 'Priya Shah', 'program': 'Nursing', 'year': '1st Year'},
        ]
    })
