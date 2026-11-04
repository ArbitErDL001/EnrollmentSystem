from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from students.roles import has_role, roles_required

from .forms import CurriculumEntryForm, ProgramForm, SubjectForm
from .models import CurriculumEntry, Program, Subject

EDIT_ROLES = ('Admin', 'Registrar')
VIEW_ROLES = ('Admin', 'Registrar', 'Instructor')


@roles_required(*VIEW_ROLES)
def index(request):
    program_count = Program.objects.filter(is_active=True).count()
    subject_count = Subject.objects.filter(is_active=True).count()
    curriculum_count = CurriculumEntry.objects.count()
    chart_max = max(program_count, subject_count, curriculum_count, 1)
    return render(request, 'academics/dashboard.html', {
        'title': 'Academic Catalog',
        'module_name': 'Academics',
        'courses_url': 'academics_courses',
        'faculty_url': 'academics_faculty',
        'cards': [
            {'title': 'Programs', 'value': program_count, 'description': 'Active programs',
             'chart_percent': round(program_count / chart_max * 100), 'chart_label': 'Compared with the largest catalog count'},
            {'title': 'Subjects', 'value': subject_count, 'description': 'Active subjects',
             'chart_percent': round(subject_count / chart_max * 100), 'chart_label': 'Compared with the largest catalog count'},
            {'title': 'Curriculum links', 'value': curriculum_count, 'description': 'Program and year-level mappings',
             'chart_percent': round(curriculum_count / chart_max * 100), 'chart_label': 'Compared with the largest catalog count'},
        ],
    })


@roles_required(*VIEW_ROLES)
def courses(request):
    return render(request, 'academics/courses.html', {
        'title': 'Programs, Subjects & Curriculum',
        'programs': Program.objects.all(),
        'subjects': Subject.objects.all(),
        'curriculum': CurriculumEntry.objects.select_related('program', 'subject').prefetch_related('prerequisites'),
        'can_edit': has_role(request.user, *EDIT_ROLES),
    })


@roles_required(*VIEW_ROLES)
def faculty(request):
    from django.contrib.auth import get_user_model
    faculty_members = get_user_model().objects.filter(groups__name='Instructor', is_active=True).distinct()
    return render(request, 'academics/faculty.html', {'title': 'Faculty Directory', 'faculty_members': faculty_members})


def _edit(request, form_class, instance=None, title=''):
    if not has_role(request.user, *EDIT_ROLES):
        raise PermissionDenied
    form = form_class(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        record = form.save()
        messages.success(request, f'{record} saved.')
        return redirect('academics_courses')
    return render(request, 'form.html', {'title': title, 'form': form, 'submit_label': 'Save changes'})


@roles_required(*VIEW_ROLES)
def program_form(request, program_id=None):
    instance = get_object_or_404(Program, pk=program_id) if program_id else None
    return _edit(request, ProgramForm, instance, 'Edit Program' if instance else 'Add Program')


@roles_required(*VIEW_ROLES)
def subject_form(request, subject_id=None):
    instance = get_object_or_404(Subject, pk=subject_id) if subject_id else None
    return _edit(request, SubjectForm, instance, 'Edit Subject' if instance else 'Add Subject')


@roles_required(*VIEW_ROLES)
def curriculum_form(request, entry_id=None):
    instance = get_object_or_404(CurriculumEntry, pk=entry_id) if entry_id else None
    return _edit(request, CurriculumEntryForm, instance, 'Edit Curriculum Entry' if instance else 'Link Subject to Curriculum')


@roles_required(*VIEW_ROLES)
@require_POST
def delete_record(request, kind, object_id):
    if not has_role(request.user, *EDIT_ROLES):
        raise PermissionDenied
    models_by_kind = {'program': Program, 'subject': Subject, 'curriculum': CurriculumEntry}
    model = models_by_kind.get(kind)
    if model is None:
        raise PermissionDenied
    record = get_object_or_404(model, pk=object_id)
    try:
        record.delete()
    except ProtectedError:
        messages.error(request, 'This record is already referenced by active student or schedule records.')
    else:
        messages.success(request, 'Record deleted.')
    return redirect('academics_courses')
