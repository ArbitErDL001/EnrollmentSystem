from io import BytesIO
from decimal import Decimal
from xml.sax.saxutils import escape

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


def _enrollment_queryset(user):
    queryset = Enrollment.objects.filter(status='enrolled')
    if has_role(user, 'Admin', 'Registrar'):
        return queryset
    if has_role(user, 'Instructor'):
        return queryset.filter(offering__instructor_id=user.pk)
    if has_role(user, 'Student'):
        return queryset.filter(student__user_id=user.pk)
    return queryset.none()


def _assessment_queryset(user):
    queryset = Assessment.objects.all()
    if has_role(user, 'Admin', 'Cashier'):
        return queryset
    if has_role(user, 'Student'):
        return queryset.filter(student__user_id=user.pk)
    return queryset.none()


def _term_filter(queryset, request):
    term = request.GET.get('term', '').strip()
    if term:
        queryset = queryset.filter(**{'offering__term' if queryset.model is Enrollment else 'term': term})
    return queryset, term


def _enrollment_rows(request):
    queryset, term = _term_filter(
        _enrollment_queryset(request.user).select_related(
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
        _assessment_queryset(request.user).select_related('student__user').annotate(
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
        if not has_role(request.user, 'Admin', 'Registrar', 'Instructor', 'Student'):
            raise PermissionDenied
        headers, rows, term, summary = _enrollment_rows(request)
        return 'Enrollment by Program and Year', headers, rows, term, summary
    if kind == 'collection':
        if not has_role(request.user, 'Admin', 'Cashier', 'Student'):
            raise PermissionDenied
        headers, rows, term, summary = _collection_rows(request)
        return 'Fee Collection', headers, rows, term, summary
    raise PermissionDenied


@roles_required(*ROLE_NAMES)
def index(request):
    can_enrollment = has_role(request.user, 'Admin', 'Registrar', 'Instructor', 'Student')
    can_collection = has_role(request.user, 'Admin', 'Cashier', 'Student')
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
            _enrollment_queryset(request.user).values_list('offering__term', flat=True).distinct().order_by('offering__term')
            if kind == 'enrollment' else
            _assessment_queryset(request.user).values_list('term', flat=True).distinct().order_by('term')
        ),
        'scope_label': 'All records' if has_role(request.user, 'Admin') else 'Records available to your account',
    })


@roles_required(*ROLE_NAMES)
@require_GET
def export_report(request, kind, file_format):
    title, headers, rows, term, summary = _report_data(kind, request)
    filename = slugify(f'{kind}-{term or "all-terms"}')
    if file_format == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = title[:31]
        worksheet.append(headers)
        for row in rows:
            worksheet.append(row)
            for cell in worksheet[worksheet.max_row]:
                if isinstance(cell.value, str):
                    cell.data_type = 's'
        header_fill = PatternFill('solid', fgColor='17324D')
        header_font = Font(color='FFFFFF', bold=True, size=11)
        accent_fill = PatternFill('solid', fgColor='DCECF5')
        stripe_fill = PatternFill('solid', fgColor='F4F8FA')
        border = Border(bottom=Side(style='thin', color='D8E2E8'))
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        worksheet.row_dimensions[1].height = 30
        for row_number in range(2, worksheet.max_row + 1):
            for cell in worksheet[row_number]:
                cell.border = border
                cell.alignment = Alignment(vertical='top', wrap_text=True)
                if row_number % 2 == 0:
                    cell.fill = stripe_fill
        worksheet.append([])
        summary_start = worksheet.max_row + 1
        worksheet.append(['SUMMARY', 'VALUE'])
        for row in summary:
            worksheet.append(row)
        for cell in worksheet[summary_start]:
            cell.fill = accent_fill
            cell.font = Font(bold=True, color='17324D')
        for row_number in range(summary_start + 1, worksheet.max_row + 1):
            worksheet.cell(row_number, 1).font = Font(bold=True, color='415A6B')
            worksheet.cell(row_number, 2).alignment = Alignment(horizontal='right')
        worksheet.freeze_panes = 'A2'
        worksheet.auto_filter.ref = f'A1:{get_column_letter(len(headers))}{len(rows) + 1}'
        for column in worksheet.columns:
            width = max((len(str(cell.value or '')) for cell in column), default=10)
            worksheet.column_dimensions[column[0].column_letter].width = min(max(width + 3, 12), 40)
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.oddFooter.center.text = 'Enrollment System | Generated report'
        worksheet.oddFooter.right.text = 'Page &P of &N'
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
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        output = BytesIO()
        document = SimpleDocTemplate(
            output, pagesize=landscape(letter), title=title,
            leftMargin=0.45 * inch, rightMargin=0.45 * inch,
            topMargin=0.55 * inch, bottomMargin=0.5 * inch,
        )
        styles = getSampleStyleSheet()
        report_title = ParagraphStyle('ReportTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#17324D'), spaceAfter=4)
        report_meta = ParagraphStyle('ReportMeta', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#5B7180'), spaceAfter=12)
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#22313B'))
        header_style = ParagraphStyle('Header', parent=cell_style, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)
        table_data = [[Paragraph(escape(str(value)), header_style) for value in headers]]
        table_data += [[Paragraph(escape(str(value)), cell_style) for value in row] for row in rows]
        table = Table(table_data, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17324D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D8E2E8')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F8FA')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        summary_table = Table([['SUMMARY', 'VALUE'], *summary], colWidths=[2.5 * inch, 1.5 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DCECF5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#17324D')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D8E2E8')),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F8FA')]),
        ]))
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#5B7180'))
            canvas.drawString(document.leftMargin, 0.25 * inch, 'Enrollment System | Generated report')
            canvas.drawRightString(landscape(letter)[0] - document.rightMargin, 0.25 * inch, f'Page {doc.page}')
            canvas.restoreState()
        document.build([
            Paragraph(title, report_title),
            Paragraph(f'{"Term: " + term if term else "All terms"} &nbsp; | &nbsp; {"All records" if has_role(request.user, "Admin") else "Records available to your account"}', report_meta),
            table, Spacer(1, 14), summary_table,
        ], onFirstPage=footer, onLaterPages=footer)
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
