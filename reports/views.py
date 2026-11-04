from io import BytesIO
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_GET

from enrollments.models import Enrollment
from finance.models import Assessment
from students.roles import ROLE_NAMES, has_role, roles_required


def _term_filter(queryset, request):
    term = request.GET.get('term', '').strip()
    if term:
        queryset = queryset.filter(**{'offering__term' if queryset.model is Enrollment else 'term': term})
    return queryset, term


def _enrollment_rows(request):
    queryset, term = _term_filter(
        Enrollment.objects.filter(status='enrolled').select_related(
            'student__user', 'student__program', 'offering__curriculum_entry__subject'
        ).order_by('student__program__code', 'student__year_level', 'student__user__last_name'),
        request,
    )
    rows = [[
        enrollment.student.student_id,
        enrollment.student.user.get_full_name() or enrollment.student.user.username,
        enrollment.student.program.code if enrollment.student.program else '',
        enrollment.student.year_level,
        enrollment.offering.curriculum_entry.subject.code,
        enrollment.offering.section,
        enrollment.offering.term,
    ] for enrollment in queryset]
    counts = queryset.values('offering__term').annotate(total=Count('pk')).order_by('offering__term')
    summary = [['Total enrollments', queryset.count()]] + [
        [f"Enrollments in {item['offering__term']}", item['total']]
        for item in counts
    ]
    return ['Student ID', 'Student', 'Program', 'Year', 'Subject', 'Section', 'Term'], rows, term, summary


def _collection_rows(request):
    queryset, term = _term_filter(
        Assessment.objects.select_related('student__user').annotate(
            paid_total=Coalesce(Sum('payments__amount'), Decimal('0.00'))
        ).order_by('term', 'student__student_id'),
        request,
    )
    rows = [[
        assessment.student.student_id,
        assessment.student.user.get_full_name() or assessment.student.user.username,
        assessment.term,
        f'{assessment.total:.2f}',
        f'{assessment.paid_total:.2f}',
        f'{assessment.total - assessment.paid_total:.2f}',
    ] for assessment in queryset]
    summary = [
        ['Assessments', len(rows)],
        ['Total assessed', f'{sum((assessment.total for assessment in queryset), 0):.2f}'],
        ['Total collected', f'{sum((assessment.paid_total for assessment in queryset), Decimal("0.00")):.2f}'],
        ['Outstanding balance', f'{sum((assessment.total - assessment.paid_total for assessment in queryset), Decimal("0.00")):.2f}'],
    ]
    return ['Student ID', 'Student', 'Term', 'Assessed', 'Collected', 'Balance'], rows, term, summary


def _report_data(kind, request):
    if kind == 'enrollment':
        if not has_role(request.user, 'Admin', 'Registrar'):
            raise PermissionDenied
        headers, rows, term, summary = _enrollment_rows(request)
        return 'Enrollment by Program and Year', headers, rows, term, summary
    if kind == 'collection':
        if not has_role(request.user, 'Admin', 'Cashier'):
            raise PermissionDenied
        headers, rows, term, summary = _collection_rows(request)
        return 'Fee Collection', headers, rows, term, summary
    raise PermissionDenied


@roles_required(*ROLE_NAMES)
def index(request):
    can_enrollment = has_role(request.user, 'Admin', 'Registrar')
    can_collection = has_role(request.user, 'Admin', 'Cashier')
    if not can_enrollment and not can_collection:
        raise PermissionDenied
    return render(request, 'reports/dashboard.html', {
        'title': 'Operational Reports',
        'can_enrollment': can_enrollment,
        'can_collection': can_collection,
    })


@roles_required(*ROLE_NAMES)
def published(request):
    kind = request.GET.get('kind', 'enrollment')
    title, headers, rows, term, summary = _report_data(kind, request)
    return render(request, 'reports/published.html', {
        'title': title,
        'headers': headers,
        'rows': rows,
        'term': term,
        'summary': summary,
        'kind': kind,
        'terms': (
            Enrollment.objects.values_list('offering__term', flat=True).distinct().order_by('offering__term')
            if kind == 'enrollment' else
            Assessment.objects.values_list('term', flat=True).distinct().order_by('term')
        ),
    })


@roles_required(*ROLE_NAMES)
@require_GET
def export_report(request, kind, file_format):
    title, headers, rows, term, summary = _report_data(kind, request)
    filename = slugify(f'{kind}-{term or "all-terms"}')
    if file_format == 'xlsx':
        from openpyxl import Workbook
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = title[:31]
        worksheet.append(headers)
        for row in rows:
            worksheet.append(row)
            for cell in worksheet[worksheet.max_row]:
                if isinstance(cell.value, str):
                    cell.data_type = 's'
        worksheet.append([])
        worksheet.append(['Summary', 'Value'])
        for row in summary:
            worksheet.append(row)
        worksheet.freeze_panes = 'A2'
        worksheet.auto_filter.ref = worksheet.dimensions
        for column in worksheet.columns:
            width = max((len(str(cell.value or '')) for cell in column), default=10)
            worksheet.column_dimensions[column[0].column_letter].width = min(width + 2, 40)
        output = BytesIO()
        workbook.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    if file_format == 'pdf':
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=landscape(letter), title=title)
        summary_rows = [
            ['Summary', *([''] * (len(headers) - 1))],
            *[[label, value, *([''] * (len(headers) - 2))] for label, value in summary],
        ]
        table = Table([headers, *rows, *summary_rows], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f6feb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dfe7f5')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f7fb')]),
        ]))
        document.build([table])
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response
    raise PermissionDenied


@roles_required(*ROLE_NAMES)
def requests(request):
    destination = reverse('reports_published')
    if has_role(request.user, 'Cashier') and not has_role(request.user, 'Admin'):
        destination += '?kind=collection'
    return redirect(destination)
