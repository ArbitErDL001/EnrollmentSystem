from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


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

    def test_valid_registration_creates_regular_user_and_redirects_to_login(self):
        response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'password1': 'A-strong-password-123',
            'password2': 'A-strong-password-123',
        })

        self.assertRedirects(response, reverse('login'))
        user = get_user_model().objects.get(username='newstudent')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['Student'])

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
