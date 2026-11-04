from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from academics.models import Program
from .models import DirectMessage, StudentProfile
from .roles import ROLE_NAMES

User = get_user_model()


class DirectMessageForm(forms.Form):
    recipient = forms.ModelChoiceField(queryset=User.objects.none())
    subject = forms.CharField(max_length=150)
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 6}))

    def __init__(self, *args, sender, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient'].queryset = User.objects.filter(
            is_active=True,
        ).exclude(pk=sender.pk).order_by('username')

    def save(self, sender):
        return DirectMessage.objects.create(
            sender=sender,
            recipient=self.cleaned_data['recipient'],
            subject=self.cleaned_data['subject'],
            body=self.cleaned_data['body'],
        )


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=30)
    address = forms.CharField(widget=forms.Textarea)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    program = forms.ModelChoiceField(queryset=Program.objects.none())
    year_level = forms.ChoiceField(choices=StudentProfile.YEAR_LEVELS)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['program'].queryset = Program.objects.filter(is_active=True)

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data['date_of_birth']
        if date_of_birth > timezone.localdate():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        return date_of_birth


class StudentProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = StudentProfile
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'date_of_birth')
        widgets = {'date_of_birth': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > timezone.localdate():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        return date_of_birth

    def save(self, commit=True):
        profile = super().save(commit=commit)
        profile.user.first_name = self.cleaned_data['first_name']
        profile.user.last_name = self.cleaned_data['last_name']
        profile.user.email = self.cleaned_data['email']
        if commit:
            profile.user.save(update_fields=('first_name', 'last_name', 'email'))
        return profile


class StudentRecordForm(StudentProfileForm):
    class Meta(StudentProfileForm.Meta):
        fields = (
            'first_name', 'last_name', 'email', 'phone', 'address', 'date_of_birth',
            'program', 'year_level', 'status',
        )


class ManagedUserCreateForm(UserCreationForm):
    role = forms.ChoiceField(choices=[(role, role) for role in ROLE_NAMES])
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')


class ManagedUserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=[(role, role) for role in ROLE_NAMES])

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = (
            'Admin' if self.instance.is_superuser else
            self.instance.groups.filter(name__in=ROLE_NAMES).values_list('name', flat=True).first() or 'Student'
        )
