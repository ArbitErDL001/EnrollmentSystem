from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from students.roles import has_role, roles_required

from .forms import ClassOfferingForm, RoomForm
from .models import ClassOffering, Room

EDIT_ROLES = ('Admin', 'Registrar')
VIEW_ROLES = ('Admin', 'Registrar', 'Instructor', 'Student')


@roles_required(*VIEW_ROLES)
def index(request):
    offerings = ClassOffering.objects.all()
    if has_role(request.user, 'Student'):
        profile = getattr(request.user, 'student_profile', None)
        offerings = offerings.filter(
            curriculum_entry__program=getattr(profile, 'program', None),
            curriculum_entry__year_level=getattr(profile, 'year_level', None),
            is_active=True,
        )
    elif has_role(request.user, 'Instructor') and not has_role(request.user, *EDIT_ROLES):
        offerings = offerings.filter(instructor=request.user)
    offering_count = offerings.count()
    room_count = Room.objects.filter(is_active=True).count()
    chart_max = max(offering_count, room_count, 1)
    return render(request, 'scheduling/dashboard.html', {
        'title': 'Class Scheduling',
        'module_name': 'Scheduling',
        'classes_url': 'scheduling_classes',
        'rooms_url': 'scheduling_rooms',
        'cards': [
            {'title': 'Class offerings', 'value': offering_count, 'description': 'Visible class sections',
             'chart_percent': round(offering_count / chart_max * 100), 'chart_label': 'Compared with the larger scheduling count'},
            {'title': 'Rooms', 'value': room_count, 'description': 'Active classrooms',
             'chart_percent': round(room_count / chart_max * 100), 'chart_label': 'Compared with the larger scheduling count'},
        ],
    })


@roles_required(*VIEW_ROLES)
def classes(request):
    offerings = ClassOffering.objects.select_related(
        'curriculum_entry__subject', 'curriculum_entry__program', 'room', 'instructor'
    ).order_by('term', 'meeting_days', 'start_time')
    if has_role(request.user, 'Student'):
        profile = getattr(request.user, 'student_profile', None)
        offerings = offerings.filter(
            curriculum_entry__program=getattr(profile, 'program', None),
            curriculum_entry__year_level=getattr(profile, 'year_level', None),
            is_active=True,
        )
    elif has_role(request.user, 'Instructor') and not has_role(request.user, *EDIT_ROLES):
        offerings = offerings.filter(instructor=request.user)
    return render(request, 'scheduling/classes.html', {
        'title': 'Class Schedule',
        'classes': offerings,
        'can_edit': has_role(request.user, *EDIT_ROLES),
    })


@roles_required(*VIEW_ROLES)
def rooms(request):
    return render(request, 'scheduling/rooms.html', {
        'title': 'Room Directory',
        'rooms': Room.objects.all(),
        'can_edit': has_role(request.user, *EDIT_ROLES),
    })


def _edit(request, form_class, instance, title):
    if not has_role(request.user, *EDIT_ROLES):
        raise PermissionDenied
    form = form_class(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        record = form.save()
        messages.success(request, f'{record} saved.')
        return redirect('scheduling_classes')
    return render(request, 'form.html', {'title': title, 'form': form, 'submit_label': 'Save changes'})


@roles_required(*VIEW_ROLES)
def room_form(request, room_id=None):
    instance = get_object_or_404(Room, pk=room_id) if room_id else None
    return _edit(request, RoomForm, instance, 'Edit Room' if instance else 'Add Room')


@roles_required(*VIEW_ROLES)
def offering_form(request, offering_id=None):
    instance = get_object_or_404(ClassOffering, pk=offering_id) if offering_id else None
    return _edit(request, ClassOfferingForm, instance, 'Edit Class Offering' if instance else 'Add Class Offering')


@roles_required(*VIEW_ROLES)
@require_POST
def delete_record(request, kind, object_id):
    if not has_role(request.user, *EDIT_ROLES):
        raise PermissionDenied
    model = {'room': Room, 'offering': ClassOffering}.get(kind)
    if model is None:
        raise PermissionDenied
    record = get_object_or_404(model, pk=object_id)
    try:
        record.delete()
    except ProtectedError:
        messages.error(request, 'This record is referenced by active enrollment data and cannot be deleted.')
    else:
        messages.success(request, 'Record deleted.')
    return redirect('scheduling_classes')
