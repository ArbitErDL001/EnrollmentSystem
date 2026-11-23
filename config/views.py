from pathlib import Path

from django.conf import settings
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from students.forms import StudentRegistrationForm
from students.models import StudentProfile
from students.notifications import notify_new_account


@require_GET
def service_worker(request):
    worker_path = Path(settings.BASE_DIR, 'static', 'js', 'service-worker.js')
    response = HttpResponse(
        worker_path.read_text(encoding='utf-8'),
        content_type='application/javascript',
    )
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                user.groups.add(Group.objects.get(name='Student'))
                profile = StudentProfile.objects.create(
                    user=user,
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                    date_of_birth=form.cleaned_data['date_of_birth'],
                    program=form.cleaned_data['program'],
                    year_level=form.cleaned_data['year_level'],
                )
                notify_new_account(user, 'Student', sender=user, student_profile=profile)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(
                request,
                f'Your account was created. Student ID: {user.student_profile.student_id}. Welcome to your overview.',
            )
            return redirect('home')
    else:
        form = StudentRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})
