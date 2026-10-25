from django.shortcuts import render


def index(request):
    return render(request, 'finance/dashboard.html', {
        'title': 'Finance Dashboard',
        'module_name': 'Finance',
        'cards': [
            {'title': 'Tuition Collected', 'value': '$1.4M', 'description': 'Current academic year'},
            {'title': 'Outstanding Fees', 'value': '$180K', 'description': 'Pending invoices'},
            {'title': 'Collection Rate', 'value': '96%', 'description': 'On-time payments'},
        ]
    })
