from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .models import DirectMessage, StudentProfile


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
        role_users = [
            ('admin', {'is_staff': True, 'is_superuser': True}, 'Admin'),
            ('registrar', {'is_staff': True}, 'Registrar'),
            ('cashier', {'is_staff': True}, 'Cashier'),
            ('instructor', {'is_staff': True}, 'Instructor'),
            ('student', {}, 'Student'),
        ]

        for username, flags, role in role_users:
            with self.subTest(role=role):
                user = self.user_model.objects.create_user(
                    username=username,
                    password='test-password',
                    **flags,
                )
                user.groups.add(Group.objects.get(name=role))

                response = self.client.post(reverse('login'), {
                    'username': username,
                    'password': 'test-password',
                })

                self.assertRedirects(response, reverse('home'))
                self.assertIn('_auth_user_id', self.client.session)
                self.client.logout()

    def test_dashboard_is_selected_for_each_account_role(self):
        roles = [
            ('admin', {'is_staff': True, 'is_superuser': True}, 'Admin Dashboard', True),
            ('registrar', {'is_staff': True}, 'Registrar Dashboard', True),
            ('cashier', {'is_staff': True}, 'Cashier Dashboard', True),
            ('instructor', {'is_staff': True}, 'Instructor Dashboard', True),
            ('student', {}, 'Student Dashboard', False),
        ]

        for username, flags, dashboard_title, can_manage in roles:
            with self.subTest(role=username):
                user = self.user_model.objects.create_user(username=username, password='test-password', **flags)
                if username == 'registrar':
                    user.groups.add(Group.objects.get(name='Registrar'))
                elif username == 'cashier':
                    user.groups.add(Group.objects.get(name='Cashier'))
                elif username == 'instructor':
                    user.groups.add(Group.objects.get(name='Instructor'))
                elif username == 'student':
                    user.groups.add(Group.objects.get(name='Student'))
                self.client.force_login(user)

                response = self.client.get(reverse('home'))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, dashboard_title)
                self.assertEqual('Open data management' in response.content.decode(), can_manage)
                if username == 'admin':
                    self.assertContains(response, 'data-system-admin="true"')
                    self.assertContains(response, 'admin-dashboard.css')
                    self.assertContains(response, 'Enrollment by program')
                    self.assertContains(response, 'Accounts by role')
                    self.assertContains(response, 'Create user')

                self.client.logout()

    def test_metric_dashboards_include_live_chart_indicators(self):
        admin = self.user_model.objects.create_superuser(
            username='chart-admin',
            email='chart-admin@example.invalid',
            password='test-password',
        )
        self.client.force_login(admin)

        dashboard = self.client.get(reverse('home'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.content.decode().count('class="admin-metric-chart"'), 4)

        dashboard_paths = (
            ('students_home', 2),
            ('academics_home', 3),
            ('enrollments_home', 2),
            ('finance_home', 3),
            ('scheduling_home', 2),
        )
        for route_name, chart_count in dashboard_paths:
            with self.subTest(dashboard=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.decode().count('class="stat-card-chart"'), chart_count)

    def test_student_can_view_modules_but_not_edit_data(self):
        student = self.user_model.objects.create_user(username='student', password='test-password')
        student.groups.add(Group.objects.get(name='Student'))
        self.client.force_login(student)

        for path in [
            reverse('students_home'),
            reverse('student_profile'),
            reverse('enrollments_home'),
            reverse('finance_home'),
            reverse('scheduling_home'),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

        for path in [
            reverse('student_directory'),
            reverse('student_admissions'),
            reverse('academics_home'),
        ]:
            with self.subTest(forbidden_path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

        self.assertEqual(self.client.get(reverse('reports_home')).status_code, 200)

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

    def test_only_administrators_can_manage_user_roles(self):
        registrar = self.user_model.objects.create_user(username='registrar', password='test-password')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)
        self.assertEqual(self.client.get(reverse('user_management')).status_code, 403)
        administrator = self.user_model.objects.create_superuser(username='root', password='test-password')
        self.client.force_login(administrator)
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_section'], 'users')
        self.assertEqual(response.context['title'], 'User Management')
        self.assertContains(response, 'Workspace <b>/ User Management</b>')
        navigation = response.content.decode().split('aria-label="Main navigation"', 1)[1].split('</nav>', 1)[0]
        self.assertLess(navigation.index('Overview'), navigation.index('User management'))
        self.assertLess(navigation.index('User management'), navigation.index('Student records'))
        self.assertIn('Academic catalog', navigation)
        self.assertIn('Class schedule', navigation)
        self.assertContains(
            response,
            f'data-confirm="Delete account {registrar.username}? This action cannot be undone."',
        )

        overview = self.client.get(reverse('home'))
        self.assertEqual(overview.status_code, 200)
        admin_navigation = overview.content.decode().split(
            'aria-label="Administrator navigation"', 1
        )[1].split('</nav>', 1)[0]
        self.assertLess(admin_navigation.index('Overview'), admin_navigation.index('User management'))
        self.assertLess(admin_navigation.index('User management'), admin_navigation.index('Student records'))
        self.assertIn('Academic catalog', admin_navigation)
        self.assertIn('Class schedule', admin_navigation)

    def test_administrator_can_create_account_with_assigned_role(self):
        administrator = self.user_model.objects.create_superuser(username='root', password='test-password')
        self.client.force_login(administrator)

        response = self.client.post(reverse('user_add'), {
            'username': 'newcashier',
            'first_name': 'New',
            'last_name': 'Cashier',
            'email': 'cashier@example.invalid',
            'role': 'Cashier',
            'password1': 'A-strong-password-123',
            'password2': 'A-strong-password-123',
        })

        self.assertRedirects(response, reverse('user_management'))
        cashier = self.user_model.objects.get(username='newcashier')
        self.assertTrue(cashier.is_staff)
        self.assertFalse(cashier.is_superuser)
        self.assertEqual(list(cashier.groups.values_list('name', flat=True)), ['Cashier'])

    def test_create_user_form_has_password_visibility_controls(self):
        administrator = self.user_model.objects.create_superuser(username='root', password='test-password')
        self.client.force_login(administrator)

        response = self.client.get(reverse('user_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-password-toggle="id_password1"')
        self.assertContains(response, 'data-password-toggle="id_password2"')
        self.assertContains(response, "js/password-toggle.js")

    def test_registrar_can_open_student_intake_and_directory_forms(self):
        registrar = self.user_model.objects.create_user(username='registrar', password='test-password')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)

        self.assertEqual(self.client.get(reverse('student_admissions')).status_code, 200)
        self.assertEqual(self.client.get(reverse('student_directory')).status_code, 200)

    def test_faker_seed_command_is_repeatable(self):
        call_command('seed_demo_data', students=2, seed=77, verbosity=0)
        first_profile_count = StudentProfile.objects.count()

        call_command('seed_demo_data', students=2, seed=77, verbosity=0)

        self.assertEqual(
            StudentProfile.objects.count(),
            first_profile_count,
        )
        call_command('seed_demo_data', students=2, seed=77, password='local-demo-password', verbosity=0)
        demo_student = self.user_model.objects.get(username='demo.student001')
        self.assertTrue(demo_student.check_password('local-demo-password'))


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


class DirectMessageTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.sender = self.user_model.objects.create_user(
            username='message-sender',
            password='test-password',
        )
        self.sender.groups.add(Group.objects.get(name='Student'))
        self.recipient = self.user_model.objects.create_user(
            username='message-recipient',
            password='test-password',
        )
        self.recipient.groups.add(Group.objects.get(name='Instructor'))
        self.other_user = self.user_model.objects.create_user(
            username='message-other',
            password='test-password',
        )
        self.client.force_login(self.sender)

    def test_all_roles_can_access_messages_and_see_header_link(self):
        roles = ('Admin', 'Registrar', 'Cashier', 'Instructor', 'Student')
        for index, role in enumerate(roles):
            with self.subTest(role=role):
                user = self.user_model.objects.create_user(
                    username=f'message-role-{index}',
                    password='test-password',
                    is_staff=role in {'Admin', 'Registrar', 'Cashier', 'Instructor'},
                    is_superuser=role == 'Admin',
                )
                user.groups.add(Group.objects.get(name=role))
                client = Client()
                client.force_login(user)

                response = client.get(reverse('message_inbox'))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-label="Messages, 0 unread"')
                if role == 'Admin':
                    dashboard_response = client.get(reverse('home'))
                    self.assertContains(
                        dashboard_response,
                        'aria-label="Messages, 0 unread"',
                    )

    def test_sending_message_notifies_recipient_and_opening_marks_read(self):
        response = self.client.post(reverse('message_compose'), {
            'recipient': self.recipient.pk,
            'subject': 'Enrollment question',
            'body': 'Could you help me with enrollment?',
        })

        direct_message = DirectMessage.objects.get()
        self.assertRedirects(
            response,
            reverse('message_detail', args=(direct_message.pk,)),
        )

        recipient_client = Client()
        recipient_client.force_login(self.recipient)
        inbox_response = recipient_client.get(reverse('message_inbox'))
        self.assertContains(inbox_response, 'aria-label="Messages, 1 unread"')
        self.assertContains(inbox_response, 'Enrollment question')

        detail_response = recipient_client.get(
            reverse('message_detail', args=(direct_message.pk,))
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Could you help me with enrollment?')
        self.assertContains(detail_response, 'Reply')
        direct_message.refresh_from_db()
        self.assertIsNotNone(direct_message.read_at)

        read_inbox_response = recipient_client.get(reverse('message_inbox'))
        self.assertContains(read_inbox_response, 'aria-label="Messages, 0 unread"')

    def test_messages_are_private_and_recipients_cannot_message_themselves(self):
        direct_message = DirectMessage.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Private',
            body='Private message body',
        )

        other_client = Client()
        other_client.force_login(self.other_user)
        self.assertEqual(
            other_client.get(
                reverse('message_detail', args=(direct_message.pk,))
            ).status_code,
            404,
        )

        response = self.client.post(reverse('message_compose'), {
            'recipient': self.sender.pk,
            'subject': 'Self message',
            'body': 'This should not be sent.',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DirectMessage.objects.count(), 1)
