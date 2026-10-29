from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_dashboards_require_login(self):
        protected_paths = [
            reverse('home'),
            reverse('students_home'),
            reverse('student_directory'),
            reverse('academics_home'),
            reverse('enrollments_home'),
            reverse('finance_home'),
            reverse('scheduling_home'),
            reverse('reports_home'),
        ]

        for path in protected_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertRedirects(response, f'{reverse("login")}?next={path}')

    def test_login_page_is_available(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Log in')

    def test_login_redirects_to_dashboard(self):
        self.user_model.objects.create_user(username='student', password='test-password')

        response = self.client.post(reverse('login'), {
            'username': 'student',
            'password': 'test-password',
        })

        self.assertRedirects(response, reverse('home'))

    def test_dashboard_is_selected_for_each_account_role(self):
        roles = [
            ('admin', {'is_staff': True, 'is_superuser': True}, 'Administrator Dashboard', True),
            ('staff', {'is_staff': True}, 'Staff Dashboard', True),
            ('student', {}, 'Student Dashboard', False),
        ]

        for username, flags, dashboard_title, can_manage in roles:
            with self.subTest(role=username):
                user = self.user_model.objects.create_user(username=username, password='test-password', **flags)
                self.client.force_login(user)

                response = self.client.get(reverse('home'))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, dashboard_title)
                self.assertEqual('Open data management' in response.content.decode(), can_manage)

                self.client.logout()

    def test_student_can_view_modules_but_not_edit_data(self):
        student = self.user_model.objects.create_user(username='student', password='test-password')
        self.client.force_login(student)

        for path in [
            reverse('students_home'),
            reverse('student_directory'),
            reverse('academics_home'),
            reverse('enrollments_home'),
            reverse('finance_home'),
            reverse('scheduling_home'),
            reverse('reports_home'),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_student_cannot_open_data_management(self):
        student = self.user_model.objects.create_user(username='student', password='test-password')
        self.client.force_login(student)

        response = self.client.get(reverse('admin:index'))

        self.assertRedirects(response, f'{reverse("admin:login")}?next={reverse("admin:index")}')

    def test_staff_can_open_data_management(self):
        staff = self.user_model.objects.create_user(username='staff', password='test-password', is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
