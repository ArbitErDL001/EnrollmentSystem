# EnrollmentSystem

## Account access

All dashboards require a signed-in account. Create the first administrator with
`python manage.py createsuperuser`, then use the Django admin site to create and
manage accounts.

- **Administrator:** a Django superuser with access to all available admin functions.
- **Staff:** an account with `is_staff` enabled. Staff can enter the data-management
  site and can edit records for which an administrator grants model permissions.
- **Student:** a regular account without `is_staff`; students can view the dashboards
  but cannot edit records.

Sign in at `/accounts/login/`. The current project does not yet define or register
application data models, so there are no application records to edit in the
data-management site yet.