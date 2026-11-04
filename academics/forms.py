from django import forms

from .models import CurriculumEntry, Program, Subject


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ('code', 'name', 'description', 'is_active')


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ('code', 'name', 'description', 'units', 'is_active')


class CurriculumEntryForm(forms.ModelForm):
    class Meta:
        model = CurriculumEntry
        fields = ('program', 'year_level', 'subject', 'prerequisites')
        widgets = {'prerequisites': forms.CheckboxSelectMultiple}

    def clean(self):
        cleaned = super().clean()
        program = cleaned.get('program')
        year_level = cleaned.get('year_level')
        subject = cleaned.get('subject')
        prerequisites = cleaned.get('prerequisites', [])
        if subject in prerequisites:
            self.add_error('prerequisites', 'A subject cannot be its own prerequisite.')
        if program and year_level:
            for prerequisite in prerequisites:
                is_prior_subject = CurriculumEntry.objects.filter(
                    program=program,
                    subject=prerequisite,
                    year_level__lt=year_level,
                ).exists()
                if not is_prior_subject:
                    self.add_error(
                        'prerequisites',
                        f'{prerequisite.code} must be listed in an earlier year of this program first.',
                    )
        return cleaned
