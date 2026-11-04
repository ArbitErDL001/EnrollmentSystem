from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import ClassOffering, Room


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ('name', 'building', 'capacity', 'is_active')


class ClassOfferingForm(forms.ModelForm):
    meeting_days = forms.MultipleChoiceField(
        choices=ClassOffering.DAYS,
        widget=forms.CheckboxSelectMultiple,
        label='Meeting days',
    )

    class Meta:
        model = ClassOffering
        fields = (
            'curriculum_entry', 'section', 'term', 'meeting_days', 'start_time',
            'end_time', 'room', 'instructor', 'capacity', 'is_active',
        )
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from academics.models import CurriculumEntry
        from django.contrib.auth import get_user_model
        self.fields['curriculum_entry'].queryset = CurriculumEntry.objects.select_related(
            'program', 'subject'
        ).order_by('program__code', 'year_level', 'subject__code')
        self.fields['instructor'].queryset = get_user_model().objects.filter(
            groups__name='Instructor', is_active=True
        ).distinct()
        if self.instance and self.instance.pk:
            self.initial['meeting_days'] = self.instance.day_codes
        elif not self.is_bound:
            self.initial['meeting_days'] = ['MON', 'WED']

    def clean_meeting_days(self):
        days = self.cleaned_data['meeting_days']
        if not days:
            raise ValidationError('Select at least one meeting day.')
        return ','.join(days)

    def clean(self):
        cleaned = super().clean()
        if all(cleaned.get(name) for name in ('start_time', 'end_time', 'meeting_days', 'room', 'instructor', 'term')):
            offering = self.instance
            conflicts = ClassOffering.objects.filter(
                term=cleaned['term'],
                start_time__lt=cleaned['end_time'],
                end_time__gt=cleaned['start_time'],
            ).filter(
                Q(room=cleaned['room']) | Q(instructor=cleaned['instructor'])
            )
            if offering.pk:
                conflicts = conflicts.exclude(pk=offering.pk)
            new_days = set(cleaned['meeting_days'].split(','))
            for other in conflicts:
                if new_days.intersection(other.day_codes):
                    raise ValidationError('The selected room or instructor is already booked at that time.')
        return cleaned

    def save(self, commit=True):
        offering = super().save(commit=False)
        offering.meeting_days = self.cleaned_data['meeting_days']
        if commit:
            offering.save()
            self.save_m2m()
        return offering
