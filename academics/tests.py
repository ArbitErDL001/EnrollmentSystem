from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import CurriculumEntry, Program, Subject


class AcademicCatalogTests(TestCase):
    def setUp(self):
        self.program = Program.objects.create(code='BSCS', name='Computer Science')
        self.first_year_subject = Subject.objects.create(code='CS101', name='Programming')
        self.second_year_subject = Subject.objects.create(code='CS201', name='Advanced Programming')
        CurriculumEntry.objects.create(
            program=self.program,
            year_level=1,
            subject=self.first_year_subject,
        )

    def test_registrar_can_create_programs(self):
        registrar = get_user_model().objects.create_user(username='registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)

        response = self.client.post(reverse('program_add'), {
            'code': 'BSIT',
            'name': 'Information Technology',
            'description': 'Technology program',
            'is_active': 'on',
        })

        self.assertRedirects(response, reverse('academics_courses'))
        self.assertTrue(Program.objects.filter(code='BSIT').exists())

    def test_program_save_and_catalog_delete_prompts_are_rendered(self):
        registrar = get_user_model().objects.create_user(username='registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)

        edit_response = self.client.get(reverse('program_edit', args=(self.program.pk,)))
        self.assertContains(edit_response, 'data-confirm="Are you sure you want to save changes?"')

        catalog_response = self.client.get(reverse('academics_courses'))
        self.assertContains(
            catalog_response,
            f'data-confirm="Delete {self.program}? This action cannot be undone."',
        )

    def test_student_cannot_edit_academic_catalog(self):
        student = get_user_model().objects.create_user(username='student')
        student.groups.add(Group.objects.get(name='Student'))
        self.client.force_login(student)

        response = self.client.get(reverse('program_add'))

        self.assertEqual(response.status_code, 403)

    def test_curriculum_prerequisites_must_be_offered_in_an_earlier_year(self):
        registrar = get_user_model().objects.create_user(username='registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)
        response = self.client.post(reverse('curriculum_add'), {
            'program': self.program.pk,
            'year_level': '2',
            'subject': self.second_year_subject.pk,
            'prerequisites': [self.second_year_subject.pk],
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A subject cannot be its own prerequisite.')
        self.assertFalse(CurriculumEntry.objects.filter(subject=self.second_year_subject).exists())

    def test_prerequisite_requires_an_earlier_curriculum_entry(self):
        registrar = get_user_model().objects.create_user(username='registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)
        unlisted_subject = Subject.objects.create(code='CS099', name='Unlisted subject')

        response = self.client.post(reverse('curriculum_add'), {
            'program': self.program.pk,
            'year_level': '2',
            'subject': self.second_year_subject.pk,
            'prerequisites': [unlisted_subject.pk],
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'must be listed in an earlier year')
        self.assertFalse(CurriculumEntry.objects.filter(subject=self.second_year_subject).exists())

    def test_registrar_can_create_edit_link_and_delete_temporary_catalog_records(self):
        registrar = get_user_model().objects.create_user(username='registrar')
        registrar.groups.add(Group.objects.get(name='Registrar'))
        self.client.force_login(registrar)

        response = self.client.post(reverse('program_add'), {
            'code': 'TMP',
            'name': 'Temporary Program',
            'description': 'Temporary test program',
            'is_active': 'on',
        })
        self.assertRedirects(response, reverse('academics_courses'))
        program = Program.objects.get(code='TMP')

        for code, name, units in (
            ('TMP101', 'Temporary prerequisite', '3'),
            ('TMP201', 'Temporary subject', '3'),
        ):
            response = self.client.post(reverse('subject_add'), {
                'code': code,
                'name': name,
                'description': '',
                'units': units,
                'is_active': 'on',
            })
            self.assertRedirects(response, reverse('academics_courses'))

        prerequisite = Subject.objects.get(code='TMP101')
        subject = Subject.objects.get(code='TMP201')
        response = self.client.post(reverse('subject_edit', args=(subject.pk,)), {
            'code': subject.code,
            'name': subject.name,
            'description': subject.description,
            'units': '4',
            'is_active': 'on',
        })
        self.assertRedirects(response, reverse('academics_courses'))
        subject.refresh_from_db()
        self.assertEqual(subject.units, 4)

        response = self.client.post(reverse('curriculum_add'), {
            'program': program.pk,
            'year_level': '1',
            'subject': prerequisite.pk,
        })
        self.assertRedirects(response, reverse('academics_courses'))
        first_year_entry = CurriculumEntry.objects.get(
            program=program,
            year_level=1,
            subject=prerequisite,
        )

        response = self.client.post(reverse('curriculum_add'), {
            'program': program.pk,
            'year_level': '2',
            'subject': subject.pk,
            'prerequisites': [prerequisite.pk],
        })
        self.assertRedirects(response, reverse('academics_courses'))
        second_year_entry = CurriculumEntry.objects.get(
            program=program,
            year_level=2,
            subject=subject,
        )
        self.assertQuerySetEqual(
            second_year_entry.prerequisites.all(),
            [prerequisite],
        )

        for entry in (second_year_entry, first_year_entry):
            response = self.client.post(
                reverse('academic_delete', args=('curriculum', entry.pk))
            )
            self.assertRedirects(response, reverse('academics_courses'))
        for temporary_subject in (subject, prerequisite):
            response = self.client.post(
                reverse('academic_delete', args=('subject', temporary_subject.pk))
            )
            self.assertRedirects(response, reverse('academics_courses'))
        response = self.client.post(
            reverse('academic_delete', args=('program', program.pk))
        )
        self.assertRedirects(response, reverse('academics_courses'))
        self.assertFalse(Program.objects.filter(pk=program.pk).exists())
        self.assertFalse(Subject.objects.filter(code__startswith='TMP').exists())
