from io import BytesIO
from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from academics.models import Program
from academics.models import CurriculumEntry, Subject
from enrollments.models import Enrollment
from finance.models import Assessment
from scheduling.models import ClassOffering, Room
from students.models import StudentProfile


class ReportExportTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='pass')
        user = get_user_model().objects.create_user(
            username='student', first_name='Example', last_name='Student'
        )
        user.groups.add(Group.objects.get(name='Student'))
        program = Program.objects.create(code='BSCS', name='Computer Science')
        self.student = StudentProfile.objects.create(
            user=user,
            program=program,
        )
        entry = CurriculumEntry.objects.create(
            program=program,
            year_level=1,
            subject=Subject.objects.create(code='CS101', name='Programming'),
        )
        instructor = get_user_model().objects.create_user(username='instructor')
        instructor.groups.add(Group.objects.get(name='Instructor'))
        offering = ClassOffering.objects.create(
            curriculum_entry=entry,
            section='A',
            term='2026-1',
            meeting_days='MON',
            start_time=time(9),
            end_time=time(10),
            room=Room.objects.create(name='Report Room'),
            instructor=instructor,
            capacity=20,
        )
        Enrollment.objects.create(student=self.student, offering=offering)
        Assessment.objects.create(
            student=self.student,
            term='2026-1',
            units=3,
            tuition_per_unit=1000,
            tuition=3000,
            registration_fee=500,
            technology_fee=250,
        )
        self.client.force_login(admin)

    def test_collection_report_exports_valid_xlsx(self):
        response = self.client.get(reverse('report_export', args=('collection', 'xlsx')))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        workbook = load_workbook(BytesIO(response.content), read_only=True)
        self.assertEqual(workbook.active['A1'].value, 'Student ID')
        self.assertEqual(workbook.active['C2'].value, '2026-1')

    def test_collection_report_exports_pdf(self):
        response = self.client.get(reverse('report_export', args=('collection', 'pdf')))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_students_can_access_only_their_financial_reports(self):
        student = self.student.user
        self.client.force_login(student)

        response = self.client.get(reverse('reports_published') + '?kind=collection')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.student_id)
        self.assertContains(response, 'Records available to your account')

    def test_students_can_export_only_their_own_financial_balances(self):
        other_user = get_user_model().objects.create_user(username='other-finance-student')
        other_student = StudentProfile.objects.create(user=other_user)
        Assessment.objects.create(
            student=other_student,
            term='2026-1',
            units=1,
            tuition_per_unit=1000,
            tuition=1000,
            registration_fee=500,
            technology_fee=250,
        )
        self.client.force_login(self.student.user)

        response = self.client.get(reverse('report_export', args=('collection', 'xlsx')))

        self.assertEqual(response.status_code, 200)
        worksheet = load_workbook(BytesIO(response.content), read_only=True).active
        self.assertEqual(worksheet['A2'].value, self.student.student_id)
        self.assertEqual(worksheet['F2'].value, '3750.00')
        exported_values = {
            cell.value
            for row in worksheet.iter_rows()
            for cell in row
            if isinstance(cell.value, str)
        }
        self.assertNotIn(other_student.student_id, exported_values)

    def test_student_enrollment_report_is_scoped_to_their_records(self):
        other_user = get_user_model().objects.create_user(username='other-student', first_name='Other')
        other_student = StudentProfile.objects.create(user=other_user)
        Enrollment.objects.create(student=other_student, offering=Enrollment.objects.first().offering)

        self.client.force_login(self.student.user)
        response = self.client.get(reverse('reports_published') + '?kind=enrollment')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.student_id)
        self.assertNotContains(response, other_student.student_id)

    def test_instructor_enrollment_report_is_scoped_to_taught_classes(self):
        instructor = get_user_model().objects.get(username='instructor')
        other_instructor = get_user_model().objects.create_user(username='other-instructor')
        other_instructor.groups.add(Group.objects.get(name='Instructor'))
        other_offering = ClassOffering.objects.create(
            curriculum_entry=Enrollment.objects.first().offering.curriculum_entry,
            section='B', term='2026-2', meeting_days='TUE', start_time=time(9), end_time=time(10),
            room=Room.objects.create(name='Other Report Room'), instructor=other_instructor, capacity=20,
        )
        Enrollment.objects.create(student=self.student, offering=other_offering, status='completed')

        self.client.force_login(instructor)
        response = self.client.get(reverse('reports_published') + '?kind=enrollment')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2026-1')
        self.assertNotContains(response, '2026-2')

    def test_enrollment_report_includes_term_totals(self):
        response = self.client.get(reverse('reports_published') + '?kind=enrollment')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total enrollments')
        self.assertContains(response, 'Enrollments in 2026-1')
