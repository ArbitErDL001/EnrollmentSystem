from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, 'finance/dashboard.html', {
        'title': 'Finance Dashboard',
        'module_name': 'Finance',
        'payments_url': 'finance_payments',
        'invoices_url': 'finance_invoices',
        'cards': [
            {'title': 'Tuition Collected', 'value': '$1.4M', 'description': 'Current academic year'},
            {'title': 'Outstanding Fees', 'value': '$180K', 'description': 'Pending invoices'},
            {'title': 'Collection Rate', 'value': '96%', 'description': 'On-time payments'},
        ]
    })


@login_required
def payments(request):
    return render(request, 'finance/payments.html', {
        'title': 'Payment Records',
        'payments': [
            {
                'student': 'Alicia Gomez',
                'reference': 'PAY-2026-001',
                'amount': '$2,400.00',
                'date': 'October 20, 2026',
                'status': 'Paid',
            },
            {
                'student': 'Marcus Lee',
                'reference': 'PAY-2026-002',
                'amount': '$2,400.00',
                'date': 'October 22, 2026',
                'status': 'Paid',
            },
            {
                'student': 'Priya Shah',
                'reference': 'PAY-2026-003',
                'amount': '$2,750.00',
                'date': 'October 24, 2026',
                'status': 'Paid',
            },
        ],
    })


@login_required
def invoices(request):
    return render(request, 'finance/invoices.html', {
        'title': 'Outstanding Invoices',
        'invoices': [
            {
                'student': 'Noah Williams',
                'invoice': 'INV-2026-041',
                'amount': '$2,400.00',
                'due_date': 'November 5, 2026',
                'status': 'Outstanding',
            },
            {
                'student': 'Sofia Chen',
                'invoice': 'INV-2026-042',
                'amount': '$2,150.00',
                'due_date': 'November 8, 2026',
                'status': 'Outstanding',
            },
            {
                'student': 'Ethan Brown',
                'invoice': 'INV-2026-043',
                'amount': '$2,750.00',
                'due_date': 'November 10, 2026',
                'status': 'Outstanding',
            },
        ],
    })
