from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from academics.models import CurriculumEntry, Program, Subject
from finance.models import Assessment
from scheduling.models import ClassOffering, Room
from students.models import DirectMessage, StudentProfile

from .models import Enrollment, EnrollmentRequest


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

        self.assertRedirects(response, reverse('enrollments_requests'))
        enrollment_request = EnrollmentRequest.objects.get(student=self.student, offering=self.offering)
        self.assertEqual(enrollment_request.status, 'pending')
        self.assertFalse(Enrollment.objects.filter(student=self.student).exists())
        self.assertFalse(Assessment.objects.filter(student=self.student, term='2026-1').exists())
        instructor_notification = DirectMessage.objects.get(
            recipient=self.offering.instructor,
            subject='Enrollment request: CS101 A',
        )
        self.assertEqual(instructor_notification.sender, self.student_user)
        self.assertIn(self.student.student_id, instructor_notification.body)

        registrar = get_user_model().objects.create_user(username='approval-registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        cashier = get_user_model().objects.create_user(username='approval-cashier')
        cashier.groups.add(Group.objects.get(name='Cashier'))
        instructor_client = Client()
        instructor_client.force_login(self.offering.instructor)
        instructor_inbox = instructor_client.get(reverse('message_inbox'))
        self.assertContains(instructor_inbox, instructor_notification.subject)
        self.assertContains(instructor_inbox, 'Accept enrollment')
        self.assertContains(
            instructor_inbox,
            reverse('enrollment_request_decision', args=(enrollment_request.pk,)),
        )
        self.assertContains(instructor_inbox, 'aria-label="Messages, 1 unread"')
        instructor_message = instructor_client.get(
            reverse('message_detail', args=(instructor_notification.pk,))
        )
        self.assertContains(instructor_message, 'Accept enrollment')
        self.assertNotContains(
            self.client.get(reverse('message_detail', args=(instructor_notification.pk,))),
            'Accept enrollment',
        )
        response = instructor_client.post(
            reverse('enrollment_request_decision', args=(enrollment_request.pk,)),
            {'decision': 'accept'},
        )

        self.assertRedirects(response, reverse('enrollments_requests'))
        self.assertTrue(Enrollment.objects.filter(student=self.student, offering=self.offering).exists())
        enrollment_request.refresh_from_db()
        self.assertEqual(enrollment_request.status, 'accepted')
        self.assertEqual(enrollment_request.decided_by, self.offering.instructor)
        self.assertNotContains(
            instructor_client.get(reverse('message_detail', args=(instructor_notification.pk,))),
            'Accept enrollment',
        )
        self.assertSetEqual(
            set(DirectMessage.objects.filter(
                subject=f'Enrollment approved: {self.student.student_id}'
            ).values_list('recipient_id', flat=True)),
            {registrar.pk, cashier.pk},
        )
        for recipient in (registrar, cashier):
            with self.subTest(notification_recipient=recipient.username):
                recipient_client = Client()
                recipient_client.force_login(recipient)
                inbox = recipient_client.get(reverse('message_inbox'))
                self.assertContains(inbox, f'Enrollment approved: {self.student.student_id}')
                self.assertContains(inbox, 'aria-label="Messages, 1 unread"')
        assessment = Assessment.objects.get(student=self.student, term='2026-1')
        self.assertEqual(assessment.units, 3)
        self.assertEqual(assessment.tuition, 3000)
        self.assertEqual(assessment.total, 3750)
        student_records = self.client.get(reverse('enrollments_records'))
        self.assertContains(student_records, 'CS101')
        self.assertContains(student_records, 'Enrolled')
        self.assertContains(
            self.client.get(reverse('message_inbox')),
            'Enrollment approved: CS101',
        )
        self.assertContains(self.client.get(reverse('enrollments_requests')), 'Accepted')

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
        enrollment_request = EnrollmentRequest.objects.get(student=self.student, offering=self.offering)
        instructor_client = Client()
        instructor_client.force_login(self.offering.instructor)
        instructor_client.post(
            reverse('enrollment_request_decision', args=(enrollment_request.pk,)),
            {'decision': 'accept'},
        )
        response = self.client.post(reverse('enrollment_select'), {'term': '2026-1', 'offering': conflicting.pk})

        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 1)
        self.assertContains(response, 'conflicts with another enrolled class')
        self.assertFalse(EnrollmentRequest.objects.filter(student=self.student, offering=conflicting).exists())

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
        self.assertFalse(EnrollmentRequest.objects.filter(student=self.student).exists())
        self.assertContains(response, 'Complete these prerequisites first')

    def test_student_cannot_request_multiple_sections_of_one_subject(self):
        alternate_offering = ClassOffering.objects.create(
            curriculum_entry=self.entry,
            section='B',
            term='2026-1',
            meeting_days='TUE',
            start_time=time(11),
            end_time=time(12),
            room=Room.objects.create(name='Room 102', capacity=30),
            instructor=self.offering.instructor,
            capacity=20,
        )
        self.client.post(reverse('enrollment_select'), {
            'term': '2026-1',
            'offering': self.offering.pk,
        })

        response = self.client.post(reverse('enrollment_select'), {
            'term': '2026-1',
            'offering': alternate_offering.pk,
        })

        self.assertEqual(
            EnrollmentRequest.objects.filter(student=self.student, status='pending').count(),
            1,
        )
        self.assertContains(response, 'You already have a pending request for this subject')

    def test_select_classes_only_shows_assigned_program_and_year(self):
        other_program = Program.objects.create(code='BSIT', name='Information Technology')
        other_program_entry = CurriculumEntry.objects.create(
            program=other_program,
            year_level=1,
            subject=Subject.objects.create(code='IT101', name='IT Foundations'),
        )
        other_year_entry = CurriculumEntry.objects.create(
            program=self.program,
            year_level=2,
            subject=Subject.objects.create(code='CS201', name='Advanced Programming'),
        )
        other_program_offering = ClassOffering.objects.create(
            curriculum_entry=other_program_entry,
            section='A',
            term='2026-1',
            meeting_days='TUE',
            start_time=time(11),
            end_time=time(12),
            room=Room.objects.create(name='Room 102', capacity=30),
            instructor=self.offering.instructor,
            capacity=20,
        )
        other_year_offering = ClassOffering.objects.create(
            curriculum_entry=other_year_entry,
            section='A',
            term='2026-1',
            meeting_days='WED',
            start_time=time(11),
            end_time=time(12),
            room=Room.objects.create(name='Room 103', capacity=30),
            instructor=self.offering.instructor,
            capacity=20,
        )

        response = self.client.get(reverse('enrollment_select'), {'term': '2026-1'})

        self.assertContains(response, self.subject.code)
        self.assertNotContains(response, 'IT101')
        self.assertNotContains(response, 'CS201')
        for offering in (other_program_offering, other_year_offering):
            response = self.client.post(reverse('enrollment_select'), {
                'term': '2026-1',
                'offering': offering.pk,
            })
            self.assertEqual(response.status_code, 404)
            self.assertFalse(Enrollment.objects.filter(student=self.student).exists())

    def test_instructor_sees_only_assigned_classes_and_enrollment_rosters(self):
        other_instructor = get_user_model().objects.create_user(username='other-teacher')
        other_instructor.groups.add(Group.objects.get(name='Instructor'))
        other_offering = ClassOffering.objects.create(
            curriculum_entry=self.second_entry,
            section='A',
            term='2026-1',
            meeting_days='TUE',
            start_time=time(11),
            end_time=time(12),
            room=Room.objects.create(name='Room 102', capacity=30),
            instructor=other_instructor,
            capacity=20,
        )
        other_student_user = get_user_model().objects.create_user(username='other-learner')
        other_student_user.groups.add(Group.objects.get(name='Student'))
        other_student = StudentProfile.objects.create(
            user=other_student_user,
            program=self.program,
            year_level=1,
        )
        own_enrollment = Enrollment.objects.create(student=self.student, offering=self.offering)
        other_enrollment = Enrollment.objects.create(student=other_student, offering=other_offering)
        own_request = EnrollmentRequest.objects.create(student=self.student, offering=self.offering)
        other_request = EnrollmentRequest.objects.create(student=other_student, offering=other_offering)
        instructor_client = Client()
        instructor_client.force_login(self.offering.instructor)

        classes_response = instructor_client.get(reverse('scheduling_classes'))
        self.assertContains(classes_response, self.subject.code)
        self.assertNotContains(classes_response, self.second_subject.code)

        records_response = instructor_client.get(reverse('enrollments_records'))
        self.assertContains(records_response, own_enrollment.student.student_id)
        self.assertContains(records_response, self.subject.code)
        self.assertNotContains(records_response, other_enrollment.student.student_id)
        self.assertNotContains(records_response, self.second_subject.code)

        requests_response = instructor_client.get(reverse('enrollments_requests'))
        self.assertContains(requests_response, own_request.student.student_id)
        self.assertContains(requests_response, self.subject.code)
        self.assertNotContains(requests_response, other_request.student.student_id)
        student_requests_response = self.client.get(reverse('enrollments_requests'))
        self.assertContains(student_requests_response, self.subject.code)
        self.assertNotContains(student_requests_response, self.second_subject.code)

    def test_unassigned_instructor_cannot_decide_request(self):
        enrollment_request = EnrollmentRequest.objects.create(
            student=self.student,
            offering=self.offering,
        )
        other_instructor = get_user_model().objects.create_user(username='other-teacher')
        other_instructor.groups.add(Group.objects.get(name='Instructor'))
        instructor_client = Client()
        instructor_client.force_login(other_instructor)

        response = instructor_client.post(
            reverse('enrollment_request_decision', args=(enrollment_request.pk,)),
            {'decision': 'accept'},
        )

        self.assertEqual(response.status_code, 403)
        enrollment_request.refresh_from_db()
        self.assertEqual(enrollment_request.status, 'pending')
        self.assertFalse(Enrollment.objects.filter(student=self.student).exists())

    def test_assigned_instructor_can_reject_without_creating_enrollment(self):
        enrollment_request = EnrollmentRequest.objects.create(
            student=self.student,
            offering=self.offering,
        )
        instructor_client = Client()
        instructor_client.force_login(self.offering.instructor)

        response = instructor_client.post(
            reverse('enrollment_request_decision', args=(enrollment_request.pk,)),
            {'decision': 'reject'},
        )

        self.assertRedirects(response, reverse('enrollments_requests'))
        enrollment_request.refresh_from_db()
        self.assertEqual(enrollment_request.status, 'rejected')
        self.assertEqual(enrollment_request.decided_by, self.offering.instructor)
        self.assertFalse(Enrollment.objects.filter(student=self.student).exists())
        self.assertTrue(DirectMessage.objects.filter(
            recipient=self.student_user,
            subject='Enrollment request rejected: CS101',
        ).exists())

    def test_acceptance_revalidates_current_enrollment_rules(self):
        response = self.client.post(reverse('enrollment_select'), {
            'term': '2026-1',
            'offering': self.offering.pk,
        })
        enrollment_request = EnrollmentRequest.objects.get(student=self.student, offering=self.offering)
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
        Enrollment.objects.create(student=self.student, offering=conflicting)
        instructor_client = Client()
        instructor_client.force_login(self.offering.instructor)

        response = instructor_client.post(
            reverse('enrollment_request_decision', args=(enrollment_request.pk,)),
            {'decision': 'accept'},
            follow=True,
        )

        enrollment_request.refresh_from_db()
        self.assertEqual(enrollment_request.status, 'pending')
        self.assertContains(response, 'conflicts with another enrolled class')
        self.assertFalse(Enrollment.objects.filter(student=self.student, offering=self.offering).exists())

    def test_admin_can_view_all_enrollment_records(self):
        enrollment = Enrollment.objects.create(student=self.student, offering=self.offering)
        administrator = get_user_model().objects.create_superuser(
            username='administrator',
            password='test-password',
        )
        self.client.force_login(administrator)

        response = self.client.get(reverse('enrollments_records'))

        self.assertContains(response, enrollment.student.student_id)
        self.assertContains(response, self.subject.code)
        self.assertContains(response, 'Update status')

    def test_completing_enrollment_refreshes_enrollment_and_assessment_pages(self):
        self.client.post(reverse('enrollment_select'), {
            'term': '2026-1',
            'offering': self.offering.pk,
        })
        enrollment_request = EnrollmentRequest.objects.get(student=self.student, offering=self.offering)
        instructor_client = Client()
        instructor_client.force_login(self.offering.instructor)
        instructor_client.post(
            reverse('enrollment_request_decision', args=(enrollment_request.pk,)),
            {'decision': 'accept'},
        )
        enrollment = Enrollment.objects.get(student=self.student, offering=self.offering)
        assessment = Assessment.objects.get(student=self.student, term='2026-1')
        self.assertEqual(assessment.units, 3)
        self.assertEqual(assessment.tuition, 3000)

        registrar = get_user_model().objects.create_user(username='registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        registrar_client = Client()
        registrar_client.force_login(registrar)
        response = registrar_client.post(
            reverse('enrollment_status', args=(enrollment.pk,)),
            {'status': 'completed'},
        )

        self.assertRedirects(response, reverse('enrollments_records'))
        enrollment.refresh_from_db()
        assessment.refresh_from_db()
        self.assertEqual(enrollment.status, 'completed')
        self.assertEqual(assessment.units, 0)
        self.assertEqual(assessment.tuition, 0)
        self.assertContains(
            registrar_client.get(reverse('enrollments_records')),
            'Completed',
        )

        assessment_page = self.client.get(
            reverse('assessment_detail', args=(assessment.pk,))
        )
        self.assertContains(assessment_page, 'Tuition (0 units x 1000.00)')
        self.assertContains(assessment_page, '0.00')
