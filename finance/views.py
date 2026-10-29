from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
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
