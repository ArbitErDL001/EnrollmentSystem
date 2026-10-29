from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group

from .roles import ROLE_NAMES, STAFF_ROLES

User = get_user_model()
admin.site.unregister(User)


class UserRoleChangeForm(UserChangeForm):
    role = forms.ChoiceField(choices=[(role, role) for role in ROLE_NAMES])

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.is_superuser:
            self.initial['role'] = 'Admin'
        else:
            self.initial['role'] = self.instance.groups.filter(
                name__in=ROLE_NAMES
            ).values_list('name', flat=True).first() or 'Student'

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data['role']
        user.is_superuser = role == 'Admin'
        user.is_staff = role in STAFF_ROLES
        if commit:
            user.save()
            self.save_m2m()
        return user


@admin.register(User)
class ManagedUserAdmin(UserAdmin):
    form = UserRoleChangeForm
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Role', {'fields': ('role',)}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        role = form.cleaned_data.get('role', 'Student')
        obj.groups.set([Group.objects.get(name=role)])
