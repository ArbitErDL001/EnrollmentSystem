from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
            ('admin', {'is_staff': True, 'is_superuser': True}, 'Admin Dashboard', True),
            ('registrar', {'is_staff': True}, 'Registrar Dashboard', True),
            ('student', {}, 'Student Dashboard', False),
        ]

        for username, flags, dashboard_title, can_manage in roles:
            with self.subTest(role=username):
                user = self.user_model.objects.create_user(username=username, password='test-password', **flags)
                if username == 'registrar':
                    user.groups.add(Group.objects.get(name='Registrar'))
                elif username == 'student':
                    user.groups.add(Group.objects.get(name='Student'))
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


class UserRoleAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='administrator',
            password='test-password',
        )
        self.user = get_user_model().objects.create_user(
            username='staffmember',
            password='test-password',
        )
        self.client.force_login(self.admin)

    def test_user_change_form_offers_all_roles(self):
        response = self.client.get(
            reverse('admin:auth_user_change', args=[self.user.pk])
        )

        self.assertEqual(response.status_code, 200)
        for role in ('Admin', 'Registrar', 'Cashier', 'Instructor', 'Student'):
            with self.subTest(role=role):
                self.assertContains(response, f'>{role}</option>')

    def test_changing_user_role_updates_group_and_staff_access(self):
        for role in ('Admin', 'Registrar', 'Cashier', 'Instructor', 'Student'):
            with self.subTest(role=role):
                response = self.client.post(
                    reverse('admin:auth_user_change', args=[self.user.pk]),
                    {
                        'username': self.user.username,
                        'first_name': '',
                        'last_name': '',
                        'email': '',
                        'role': role,
                        '_save': 'Save',
                    },
                )

                self.assertEqual(response.status_code, 302)
                self.user.refresh_from_db()
                self.assertEqual(self.user.is_superuser, role == 'Admin')
                self.assertEqual(
                    self.user.is_staff,
                    role in {'Admin', 'Registrar', 'Cashier', 'Instructor'},
                )
                self.assertEqual(
                    list(self.user.groups.values_list('name', flat=True)),
                    [role],
                )
