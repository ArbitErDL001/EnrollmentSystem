from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Program(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('code',)

    def __str__(self):
        return f'{self.code} - {self.name}'


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    units = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('code',)

    def __str__(self):
        return f'{self.code} - {self.name}'


class CurriculumEntry(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='curriculum')
    year_level = models.PositiveSmallIntegerField(choices=[(year, f'Year {year}') for year in range(1, 7)])
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='curriculum_entries')
    prerequisites = models.ManyToManyField(Subject, blank=True, related_name='required_for_entries')

    class Meta:
        ordering = ('program', 'year_level', 'subject__code')
        constraints = [
            models.UniqueConstraint(fields=('program', 'year_level', 'subject'), name='unique_curriculum_subject'),
        ]

    def clean(self):
        if self.pk and self.prerequisites.filter(pk=self.subject_id).exists():
            raise ValidationError({'prerequisites': 'A subject cannot be its own prerequisite.'})

    def __str__(self):
        return f'{self.program.code} Year {self.year_level}: {self.subject.code}'
