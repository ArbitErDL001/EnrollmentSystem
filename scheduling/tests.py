from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from academics.models import CurriculumEntry, Program, Subject

from .forms import ClassOfferingForm
from .models import ClassOffering, Room


class ScheduleConflictTests(TestCase):
    def setUp(self):
        program = Program.objects.create(code='BSCS', name='Computer Science')
        self.entry = CurriculumEntry.objects.create(
            program=program,
            year_level=1,
            subject=Subject.objects.create(code='CS101', name='Programming'),
        )
        self.another_entry = CurriculumEntry.objects.create(
            program=program,
            year_level=1,
            subject=Subject.objects.create(code='CS102', name='Networks'),
        )
        self.room = Room.objects.create(name='Room A', capacity=30)
        instructor = get_user_model().objects.create_user(username='instructor')
        instructor.groups.add(Group.objects.get(name='Instructor'))
        self.instructor = instructor
        ClassOffering.objects.create(
            curriculum_entry=self.entry,
            section='A',
            term='2026-1',
            meeting_days='MON,WED',
            start_time=time(9),
            end_time=time(10),
            room=self.room,
            instructor=instructor,
            capacity=25,
        )

    def test_prevents_room_double_booking_on_overlapping_days_and_times(self):
        form = ClassOfferingForm({
            'curriculum_entry': self.another_entry.pk,
            'section': 'A',
            'term': '2026-1',
            'meeting_days': ['WED'],
            'start_time': '09:30',
            'end_time': '10:30',
            'room': self.room.pk,
            'instructor': self.instructor.pk,
            'capacity': 25,
            'is_active': 'on',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('already booked', str(form.errors))

    def test_prevents_instructor_double_booking_in_a_different_room(self):
        other_room = Room.objects.create(name='Room B', capacity=30)
        form = ClassOfferingForm({
            'curriculum_entry': self.another_entry.pk,
            'section': 'A',
            'term': '2026-1',
            'meeting_days': ['WED'],
            'start_time': '09:30',
            'end_time': '10:30',
            'room': other_room.pk,
            'instructor': self.instructor.pk,
            'capacity': 25,
            'is_active': 'on',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('already booked', str(form.errors))

    def test_admin_can_view_and_manage_class_offerings(self):
        administrator = get_user_model().objects.create_superuser(
            username='administrator',
            password='test-password',
        )
        self.client.force_login(administrator)

        response = self.client.get(reverse('scheduling_classes'))

        self.assertContains(response, self.entry.subject.code)
        self.assertContains(response, 'Add class offering')

    def test_allows_same_time_on_different_day(self):
        other_room = Room.objects.create(name='Room B', capacity=30)
        form = ClassOfferingForm({
            'curriculum_entry': self.another_entry.pk,
            'section': 'A',
            'term': '2026-1',
            'meeting_days': ['TUE'],
            'start_time': '09:00',
            'end_time': '10:00',
            'room': other_room.pk,
            'instructor': self.instructor.pk,
            'capacity': 25,
            'is_active': 'on',
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_prevents_capacity_exceeding_room_limit(self):
        form = ClassOfferingForm({
            'curriculum_entry': self.another_entry.pk,
            'section': 'B',
            'term': '2026-1',
            'meeting_days': ['TUE'],
            'start_time': '11:00',
            'end_time': '12:00',
            'room': self.room.pk,
            'instructor': self.instructor.pk,
            'capacity': 40,
            'is_active': 'on',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('capacity', form.errors)
