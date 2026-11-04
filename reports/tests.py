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

    def test_students_cannot_access_financial_reports(self):
        student = self.student.user
        self.client.force_login(student)

        response = self.client.get(reverse('reports_published') + '?kind=collection')

        self.assertEqual(response.status_code, 403)

    def test_enrollment_report_includes_term_totals(self):
        response = self.client.get(reverse('reports_published') + '?kind=enrollment')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total enrollments')
        self.assertContains(response, 'Enrollments in 2026-1')
