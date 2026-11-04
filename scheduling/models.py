from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Room(models.Model):
    name = models.CharField(max_length=80, unique=True)
    building = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('building', 'name')

    def __str__(self):
        return f'{self.name} ({self.building})' if self.building else self.name


class ClassOffering(models.Model):
    DAYS = [('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'),
            ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday')]

    curriculum_entry = models.ForeignKey(
        'academics.CurriculumEntry', on_delete=models.PROTECT, related_name='offerings'
    )
    section = models.CharField(max_length=20)
    term = models.CharField(max_length=30, help_text='For example: 2026-1')
    meeting_days = models.CharField(max_length=24, help_text='Comma-separated days, e.g. MON,WED')
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='offerings')
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='teaching_offerings'
    )
    capacity = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('term', 'meeting_days', 'start_time')
        constraints = [
            models.UniqueConstraint(fields=('curriculum_entry', 'section', 'term'), name='unique_offering_section_term'),
        ]

    @property
    def day_codes(self):
        return {day for day in self.meeting_days.split(',') if day}

    def clean(self):
        errors = {}
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors['end_time'] = 'End time must be after start time.'
        if self.room_id and self.capacity and self.capacity > self.room.capacity:
            errors['capacity'] = 'Class capacity cannot exceed room capacity.'
        if self.curriculum_entry_id and self.meeting_days and self.start_time and self.end_time and self.room_id and self.instructor_id:
            conflicts = ClassOffering.objects.filter(
                term=self.term,
                meeting_days__isnull=False,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            ).exclude(pk=self.pk).filter(
                models.Q(room_id=self.room_id) | models.Q(instructor_id=self.instructor_id)
            )
            for other in conflicts:
                if self.day_codes.intersection(other.day_codes):
                    errors['meeting_days'] = 'This room or instructor is already booked during that time.'
                    break
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.curriculum_entry.subject.code} {self.section} ({self.term})'
