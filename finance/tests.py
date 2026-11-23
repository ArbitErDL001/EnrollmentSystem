from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from academics.models import Program
from students.models import StudentProfile

from students.models import DirectMessage

from .models import Assessment, Payment


class FinanceWorkflowTests(TestCase):
    def setUp(self):
        program = Program.objects.create(code='BSBA', name='Business Administration')
        student_user = get_user_model().objects.create_user(username='student')
        student_user.groups.add(Group.objects.get(name='Student'))
        self.student = StudentProfile.objects.create(user=student_user, program=program)
        cashier = get_user_model().objects.create_user(username='cashier')
        cashier.groups.add(Group.objects.get(name='Cashier'))
        self.cashier = cashier
        self.assessment = Assessment.objects.create(
            student=self.student,
            term='2026-1',
            units=3,
            tuition_per_unit=1000,
            tuition=3000,
            registration_fee=500,
            technology_fee=250,
        )

    def test_cashier_records_payment_and_balance_updates(self):
        self.client.force_login(self.cashier)
        response = self.client.post(
            reverse('record_payment', args=[self.assessment.pk]),
            {'amount': '1250.00', 'note': 'First installment'},
        )

        self.assertRedirects(response, reverse('assessment_detail', args=[self.assessment.pk]))
        payment = Payment.objects.get(assessment=self.assessment)
        self.assertEqual(payment.recorded_by, self.cashier)
        self.assertEqual(payment.amount, 1250)
        self.assertEqual(self.assessment.balance, 2500)
        notification = DirectMessage.objects.get(recipient=self.student.user)
        self.assertEqual(notification.sender, self.cashier)
        self.assertIn('remaining balance is 2500.00', notification.body)
        student_client = Client()
        student_client.force_login(self.student.user)
        inbox = student_client.get(reverse('message_inbox'))
        self.assertContains(inbox, notification.subject)
        self.assertContains(inbox, 'aria-label="Messages, 1 unread"')

    def test_admin_can_view_student_assessments(self):
        administrator = get_user_model().objects.create_superuser(
            username='administrator',
            password='test-password',
        )
        self.client.force_login(administrator)

        response = self.client.get(reverse('finance_invoices'))

        self.assertContains(response, self.student.student_id)
        self.assertContains(response, '3750.00')

    def test_student_invoice_page_offers_print_and_financial_exports(self):
        self.client.force_login(self.student.user)

        response = self.client.get(reverse('finance_invoices'))

        self.assertContains(response, 'Print balances')
        self.assertContains(response, reverse('report_export', args=('collection', 'pdf')))
        self.assertContains(response, reverse('report_export', args=('collection', 'xlsx')))

    def test_cashier_cannot_accept_more_than_balance(self):
        self.client.force_login(self.cashier)
        response = self.client.post(
            reverse('record_payment', args=[self.assessment.pk]),
            {'amount': '4000.00'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Payment.objects.filter(assessment=self.assessment).exists())
        self.assertContains(response, 'Payment cannot exceed the outstanding balance.')

    def test_cashier_cannot_record_zero_or_negative_payments(self):
        self.client.force_login(self.cashier)
        for amount in ('0', '-0.01'):
            with self.subTest(amount=amount):
                response = self.client.post(
                    reverse('record_payment', args=[self.assessment.pk]),
                    {'amount': amount},
                )

                self.assertEqual(response.status_code, 200)
                self.assertFalse(Payment.objects.filter(assessment=self.assessment).exists())

    def test_students_cannot_view_another_students_assessment(self):
        user = get_user_model().objects.create_user(username='other')
        user.groups.add(Group.objects.get(name='Student'))
        self.client.force_login(user)

        response = self.client.get(reverse('assessment_detail', args=[self.assessment.pk]))

        self.assertEqual(response.status_code, 403)

    def test_registrar_cannot_record_payments(self):
        registrar = get_user_model().objects.create_user(username='registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)

        response = self.client.get(reverse('finance_payments'))

        self.assertEqual(response.status_code, 403)
