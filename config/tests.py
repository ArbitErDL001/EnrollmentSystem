from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import Program
from students.models import DirectMessage, StudentProfile

class RegistrationTests(TestCase):
    def test_role_groups_are_available(self):
        self.assertSetEqual(
            set(Group.objects.values_list('name', flat=True)),
            {'Admin', 'Registrar', 'Cashier', 'Instructor', 'Student'},
        )

    def test_registration_page_is_available(self):
        response = self.client.get(reverse('register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create an account')

    def test_valid_registration_signs_in_and_redirects_to_overview(self):
        program = Program.objects.create(code='BSCS', name='Computer Science')
        administrator = get_user_model().objects.create_superuser(
            username='registration-admin',
            password='test-password',
        )
        response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'first_name': 'New',
            'last_name': 'Student',
            'email': 'newstudent@example.invalid',
            'phone': '555-0101',
            'address': '123 Example Street',
            'date_of_birth': '2005-01-02',
            'program': program.pk,
            'year_level': '1',
            'password1': 'A-strong-password-123',
            'password2': 'A-strong-password-123',
        })

        self.assertRedirects(response, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)
        overview = self.client.get(response.url)
        self.assertEqual(overview.status_code, 200)
        self.assertContains(overview, 'Student Dashboard')
        user = get_user_model().objects.get(username='newstudent')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['Student'])
        profile = StudentProfile.objects.get(user=user)
        self.assertTrue(profile.student_id.startswith(f'STU-{timezone.now():%Y}-'))
        self.assertEqual(profile.program, program)
        self.assertEqual(profile.phone, '555-0101')
        notification = DirectMessage.objects.get(recipient=administrator)
        self.assertEqual(notification.sender, user)
        self.assertIn(profile.student_id, notification.body)
        self.assertIn('newstudent', notification.subject)
        administrator_client = Client()
        administrator_client.force_login(administrator)
        inbox = administrator_client.get(reverse('message_inbox'))
        self.assertContains(inbox, notification.subject)
        self.assertContains(inbox, 'aria-label="Messages, 1 unread"')

        profile_page = self.client.get(reverse('student_profile'))
        self.assertContains(profile_page, profile.student_id)

        response = self.client.post(reverse('student_profile'), {
            'first_name': 'New',
            'last_name': 'Student',
            'email': 'newstudent@example.invalid',
            'phone': '555-0202',
            'address': '456 Updated Street',
            'date_of_birth': '2005-01-02',
        })

        self.assertRedirects(response, reverse('student_profile'))
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '555-0202')
        refreshed_profile_page = self.client.get(reverse('student_profile'))
        self.assertContains(refreshed_profile_page, profile.student_id)
        self.assertContains(refreshed_profile_page, '555-0202')

    def test_invalid_registration_does_not_create_user(self):
        response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'password1': 'not-the-same',
            'password2': 'different-password',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username='newstudent').exists()
        )


class AuthenticationPageTests(TestCase):
    def test_service_worker_is_available_with_root_scope(self):
        response = self.client.get(reverse('service_worker'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        self.assertContains(response, "request.mode === 'navigate'")
        self.assertContains(response, '/static/js/theme-toggle.js')

    def test_pages_include_pwa_manifest_and_registration_script(self):
        login = self.client.get(reverse('login'))
        self.assertContains(login, 'rel="manifest"')
        self.assertContains(login, 'js/pwa.js')
        self.assertContains(login, 'data-theme-toggle')
        self.assertContains(login, 'js/workspace-entry.js')

        user = get_user_model().objects.create_superuser(
            username='pwa-admin', password='Strong-pass-123'
        )
        self.client.force_login(user)
        dashboard = self.client.get(reverse('home'))
        self.assertContains(dashboard, 'rel="manifest"')
        self.assertContains(dashboard, 'js/pwa.js')
        self.assertContains(dashboard, 'js/workspace-navigation.js')
        self.assertContains(dashboard, 'js/workspace-entry.js')
        self.assertContains(dashboard, 'data-theme-toggle')

    def test_shared_dashboard_includes_theme_toggle(self):
        user = get_user_model().objects.create_user(
            username='theme-registrar', password='Strong-pass-123'
        )
        registrar_group, _ = Group.objects.get_or_create(name='Registrar')
        user.groups.add(registrar_group)
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-theme-toggle')

    def test_login_page_uses_university_brand_and_post_form(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Palawan State University')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'name="next"')
        self.assertContains(response, 'data-password-toggle="id_password"')
        self.assertContains(response, 'aria-label="Show password"')

    def test_registration_password_fields_have_show_password_controls(self):
        response = self.client.get(reverse('register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'js/workspace-entry.js')
        self.assertContains(response, 'data-password-toggle="id_password1"')
        self.assertContains(response, 'data-password-toggle="id_password2"')

    def test_sign_out_redirects_to_the_branded_login_page(self):
        user = get_user_model().objects.create_user(username='signout-user', password='Strong-pass-123')
        self.client.force_login(user)

        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)
