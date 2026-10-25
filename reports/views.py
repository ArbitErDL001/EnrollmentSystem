from django.shortcuts import render


def index(request):
    return render(request, 'reports/dashboard.html', {
        'title': 'Reports Dashboard',
        'module_name': 'Reports',
        'cards': [
            {'title': 'Published Reports', 'value': '24', 'description': 'Current reports in circulation'},
            {'title': 'Pending Requests', 'value': '11', 'description': 'New analysis tasks'},
            {'title': 'Data Accuracy', 'value': '99.2%', 'description': 'Verified data quality'},
        ]
    })
