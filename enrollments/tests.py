from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from academics.models import CurriculumEntry, Program, Subject
from finance.models import Assessment
from scheduling.models import ClassOffering, Room
from students.models import StudentProfile

from .models import Enrollment


class EnrollmentProcessingTests(TestCase):
    def setUp(self):
        self.program = Program.objects.create(code='BSCS', name='Computer Science')
        self.subject = Subject.objects.create(code='CS101', name='Programming', units=3)
        self.second_subject = Subject.objects.create(code='CS102', name='Networks', units=4)
        self.entry = CurriculumEntry.objects.create(
            program=self.program, year_level=1, subject=self.subject
        )
        self.second_entry = CurriculumEntry.objects.create(
            program=self.program, year_level=1, subject=self.second_subject
        )
        self.room = Room.objects.create(name='Room 101', capacity=30)
        user_model = get_user_model()
        instructor = user_model.objects.create_user(username='teacher')
        instructor.groups.add(Group.objects.get(name='Instructor'))
        self.offering = ClassOffering.objects.create(
            curriculum_entry=self.entry,
            section='A',
            term='2026-1',
            meeting_days='MON',
            start_time=time(9),
            end_time=time(10),
            room=self.room,
            instructor=instructor,
            capacity=20,
        )
        self.student_user = user_model.objects.create_user(username='learner', password='pass')
        self.student_user.groups.add(Group.objects.get(name='Student'))
        self.student = StudentProfile.objects.create(
            user=self.student_user, program=self.program, year_level=1
        )
        self.client.force_login(self.student_user)

    def test_student_enrollment_creates_assessment(self):
        response = self.client.post(reverse('enrollment_select'), {
            'term': '2026-1',
            'offering': self.offering.pk,
        })

        self.assertRedirects(response, reverse('enrollments_records'))
        self.assertTrue(Enrollment.objects.filter(student=self.student, offering=self.offering).exists())
        assessment = Assessment.objects.get(student=self.student, term='2026-1')
        self.assertEqual(assessment.units, 3)
        self.assertEqual(assessment.tuition, 3000)
        self.assertEqual(assessment.total, 3750)

    def test_enrollment_rejects_schedule_conflicts(self):
        conflicting = ClassOffering.objects.create(
            curriculum_entry=self.second_entry,
            section='A',
            term='2026-1',
            meeting_days='MON',
            start_time=time(9, 30),
            end_time=time(10, 30),
            room=Room.objects.create(name='Room 102', capacity=30),
            instructor=self.offering.instructor,
            capacity=20,
        )

        self.client.post(reverse('enrollment_select'), {'term': '2026-1', 'offering': self.offering.pk})
        response = self.client.post(reverse('enrollment_select'), {'term': '2026-1', 'offering': conflicting.pk})

        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 1)
        self.assertContains(response, 'conflicts with another enrolled class')

    def test_enrollment_rejects_missing_prerequisite(self):
        prerequisite = Subject.objects.create(code='CS100', name='Foundations')
        year_two_subject = Subject.objects.create(code='CS201', name='Advanced Programming')
        year_two_entry = CurriculumEntry.objects.create(
            program=self.program, year_level=2, subject=year_two_subject
        )
        year_two_entry.prerequisites.add(prerequisite)
        self.student.year_level = 2
        self.student.save()
        offering = ClassOffering.objects.create(
            curriculum_entry=year_two_entry,
            section='A',
            term='2026-1',
            meeting_days='TUE',
            start_time=time(9),
            end_time=time(10),
            room=self.room,
            instructor=self.offering.instructor,
            capacity=20,
        )

        response = self.client.post(reverse('enrollment_select'), {'term': '2026-1', 'offering': offering.pk})

        self.assertFalse(Enrollment.objects.filter(student=self.student).exists())
        self.assertContains(response, 'Complete these prerequisites first')
