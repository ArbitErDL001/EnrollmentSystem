from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from faker import Faker

from academics.models import CurriculumEntry, Program, Subject
from enrollments.models import Enrollment
from finance.models import FeePolicy, Payment
from finance.services import refresh_assessment
from scheduling.models import ClassOffering, Room
from students.models import StudentProfile


class Command(BaseCommand):
    help = 'Create repeatable, clearly fictional enrollment demo data.'

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=24, help='Number of fictional student accounts to create.')
        parser.add_argument('--seed', type=int, default=2026, help='Faker random seed.')
        parser.add_argument(
            '--password',
            help='Optional shared password for local role demonstrations; never use on a live system.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        student_count = options['students']
        if student_count < 1:
            raise CommandError('--students must be at least 1.')
        fake = Faker()
        fake.seed_instance(options['seed'])
        user_model = get_user_model()
        roles = {
            role: Group.objects.get_or_create(name=role)[0]
            for role in ('Student', 'Registrar', 'Cashier', 'Instructor')
        }

        program_specs = [
            ('BSCS', 'BS Computer Science'),
            ('BSBA', 'BS Business Administration'),
            ('BSIT', 'BS Information Technology'),
        ]
        programs = []
        for code, name in program_specs:
            program, _ = Program.objects.update_or_create(
                code=code,
                defaults={'name': name, 'description': 'Fictional demo program', 'is_active': True},
            )
            programs.append(program)

        rooms = []
        for index in range(1, 5):
            room, _ = Room.objects.update_or_create(
                name=f'Demo Room {index}',
                defaults={'building': 'Demo Building', 'capacity': 40, 'is_active': True},
            )
            rooms.append(room)

        instructors = []
        for index in range(1, 3):
            username = f'demo.instructor{index:03d}'
            instructor, _ = user_model.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'email': f'{username}@example.invalid',
                    'is_staff': True,
                    'is_active': True,
                },
            )
            if not instructor.email.endswith('@example.invalid'):
                raise CommandError(f'Cannot seed over existing account {username}.')
            if options['password']:
                instructor.set_password(options['password'])
            else:
                instructor.set_unusable_password()
            instructor.is_staff = True
            instructor.save()
            instructor.groups.set([roles['Instructor']])
            instructors.append(instructor)

        staff_users = []
        for role in ('Registrar', 'Cashier'):
            for index in range(1, 3):
                username = f'demo.{role.lower()}{index:03d}'
                account, _ = user_model.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': fake.first_name(),
                        'last_name': fake.last_name(),
                        'email': f'{username}@example.invalid',
                        'is_staff': True,
                        'is_active': True,
                    },
                )
                if not account.email.endswith('@example.invalid'):
                    raise CommandError(f'Cannot seed over existing account {username}.')
                if options['password']:
                    account.set_password(options['password'])
                else:
                    account.set_unusable_password()
                account.is_staff = True
                account.save()
                account.groups.set([roles[role]])
                staff_users.append(account)
        cashier = next(user for user in staff_users if user.username == 'demo.cashier001')

        curriculum_entries = []
        for program_index, program in enumerate(programs):
            prefix = ('CS', 'BA', 'IT')[program_index]
            for year in (1, 2):
                for subject_index in range(1, 4):
                    code = f'{prefix}{year}{subject_index:02d}'
                    subject, _ = Subject.objects.update_or_create(
                        code=code,
                        defaults={
                            'name': f'{program.name} Year {year} Subject {subject_index}',
                            'description': 'Fictional subject for demonstration',
                            'units': 3 if subject_index != 3 else 4,
                            'is_active': True,
                        },
                    )
                    entry, _ = CurriculumEntry.objects.get_or_create(
                        program=program,
                        year_level=year,
                        subject=subject,
                    )
                    if year == 2:
                        prerequisite = Subject.objects.get(code=f'{prefix}1{subject_index:02d}')
                        entry.prerequisites.set([prerequisite])
                    else:
                        entry.prerequisites.clear()
                    curriculum_entries.append(entry)

        term = '2026-1'
        offerings = {}
        for index, entry in enumerate(curriculum_entries):
            start_hour = 8 + index // 5
            start = time(start_hour, 0)
            end = time(start_hour, 50)
            days = ('MON', 'TUE', 'WED', 'THU', 'FRI')[index % 5]
            offering, _ = ClassOffering.objects.update_or_create(
                curriculum_entry=entry,
                section='A',
                term=term,
                defaults={
                    'meeting_days': days,
                    'start_time': start,
                    'end_time': end,
                    'room': rooms[index % len(rooms)],
                    'instructor': instructors[index % len(instructors)],
                    'capacity': 35,
                    'is_active': True,
                },
            )
            offerings[entry.pk] = offering

        FeePolicy.objects.update_or_create(
            pk=1,
            defaults={
                'tuition_per_unit': 1000,
                'registration_fee': 500,
                'technology_fee': 250,
            },
        )

        created_profiles = 0
        for index in range(1, student_count + 1):
            username = f'demo.student{index:03d}'
            user, _ = user_model.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'email': f'{username}@example.invalid',
                    'is_active': True,
                },
            )
            if not user.email.endswith('@example.invalid'):
                raise CommandError(f'Cannot seed over existing account {username}.')
            if options['password']:
                user.set_password(options['password'])
            else:
                user.set_unusable_password()
            user.save()
            user.groups.set([roles['Student']])
            program = programs[(index - 1) % len(programs)]
            year_level = 1 if index % 3 else 2
            profile, was_created = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone': fake.phone_number()[:30],
                    'address': fake.address(),
                    'date_of_birth': fake.date_of_birth(minimum_age=17, maximum_age=30),
                    'program': program,
                    'year_level': year_level,
                    'status': 'active',
                },
            )
            if was_created:
                created_profiles += 1
            if year_level == 1:
                current_entries = [
                    entry for entry in curriculum_entries
                    if entry.program_id == program.pk and entry.year_level == year_level
                ]
                for entry in current_entries[:2]:
                    offering = offerings[entry.pk]
                    enrollment, enrolled = Enrollment.objects.get_or_create(
                        student=profile,
                        offering=offering,
                        defaults={'status': 'enrolled'},
                    )
                    if enrolled:
                        enrollment.full_clean()
                assessment = refresh_assessment(profile, term)
                if index % 2 == 0:
                    reference = f'DEMO-{profile.student_id}'
                    Payment.objects.get_or_create(
                        reference=reference,
                        defaults={
                            'assessment': assessment,
                            'amount': min(500, assessment.balance),
                            'recorded_by': cashier,
                            'note': 'Fictional seed payment',
                        },
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready: {len(programs)} programs, {len(curriculum_entries)} curriculum entries, '
            f'{student_count} student accounts ({created_profiles} newly created profiles), '
            f'{len(offerings)} class offerings. '
            f'{"Demo password set for local role testing." if options["password"] else "Demo accounts have unusable passwords."}'
        ))
