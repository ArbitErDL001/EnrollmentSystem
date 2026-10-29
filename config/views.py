from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            student_group, _ = Group.objects.get_or_create(name='Student')
            user.groups.add(student_group)
            messages.success(request, 'Your account was created. You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})
