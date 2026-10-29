# EnrollmentSystem

## Account access

All dashboards require a signed-in account. Create the first administrator with
`python manage.py createsuperuser`, then run `python manage.py migrate` to create
the application roles.

The available account roles are **Admin**, **Registrar**, **Cashier**,
**Instructor**, and **Student**. A superuser can assign a role through
**Manage data → Users**. The registration page creates Student accounts by
default; users cannot select a privileged role during registration.

Admin accounts have full Django administration access. Registrar, Cashier, and
Instructor accounts are staff accounts; grant them only the model permissions
they need. Student accounts have read-only dashboard access. Sign in at
`/accounts/login/`.

The project does not yet define or register application data models, so there
are no application records to edit in the data-management site yet.