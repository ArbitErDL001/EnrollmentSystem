# End-to-end test checklist

Follow one step at a time. Sign out before switching accounts.

## Start the app

Run these commands from the project folder:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_demo_data --reset --students 6 --seed 2026 --password "DemoPass123!"
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

> **Warning:** `--reset` deletes all database records, including accounts. Use
> this command only with local test data. Never use it on a live database.

## Demo accounts

Use the password `DemoPass123!` for each demo account.

| Role | Username |
|---|---|
| Admin | `demo.admin` |
| Registrar | `demo.registrar001` |
| Cashier | `demo.cashier001` |
| Instructor | `demo.instructor001` |
| Student with no enrollments | `demo.student001` |
| Student with a payment | `demo.student002` |
| Year 2 student | `demo.student003` |

## Checklist

### 1. Check the starting data — Admin

- [ ] Sign in as `demo.admin`.
- [ ] Confirm the users, programs, subjects, rooms, classes, enrollments,
  assessments, and payments are visible.
- [ ] Confirm the starting counts: 13 accounts, 3 programs, 18 subjects,
  4 rooms, 19 classes, 8 enrollments, 4 assessments, and 2 payments.
- [ ] Confirm `demo.student001` has no enrollments.

### 2. Register and update a student profile

- [ ] Sign out.
- [ ] Register a student with personal, contact, program, and year-level
  details.
- [ ] Choose a unique username and a password that meets the displayed rules.
- [ ] Sign in as the new student and open **My profile**.
- [ ] Confirm the student ID starts with `STU-2026-`.
- [ ] Change the phone number or address. Save, reload, and confirm the change
  remains.
- [ ] Sign in as `demo.admin`. Open **Messages** and confirm the new-account
  notification arrived.

### 3. Add and remove temporary curriculum — Registrar

- [ ] Sign in as `demo.registrar001`.
- [ ] Open **Academics → Programs, Subjects & Curriculum**.
- [ ] Create one temporary program and two temporary subjects.
- [ ] Edit one subject's units.
- [ ] Link the first subject to Year 1.
- [ ] Link the second subject to Year 2. Set the Year 1 subject as its
  prerequisite.
- [ ] Delete both curriculum links, both subjects, and the temporary program.
- [ ] Confirm the existing Year 2 subjects still have prerequisites.

### 4. Check class conflicts and class visibility

- [ ] As the registrar, try to save a class with an overlapping room or
  instructor schedule. Confirm the form rejects it.
- [ ] Sign out. Sign in as `demo.student001`.
- [ ] Open **Enrollments → Select classes**.
- [ ] Confirm only BSCS Year 1 classes are listed.

### 5. Request a class and get instructor approval

- [ ] As `demo.student001`, request BSCS Year 1 `CS101`, section `A`.
- [ ] Sign out. Sign in as `demo.instructor001`.
- [ ] Open **Messages** and confirm the request notification arrived.
- [ ] Open **Enrollments → Enrollment requests** and accept the request.
- [ ] Confirm its status is **Accepted**.
- [ ] Sign in as `demo.registrar001`. Confirm an approval notification arrived.
- [ ] Sign in as `demo.cashier001`. Confirm the assessment-ready notification
  arrived.
- [ ] Sign out. Sign in as `demo.student001`.
- [ ] Open **Enrollment Records** and confirm `CS101`, section `A`, is
  **Enrolled**.
- [ ] Request `CS102`, section `B`. Confirm the overlapping schedule is
  rejected.
- [ ] Sign in as `demo.student003` (BSIT Year 2). Try a Year 2 class. Confirm
  the missing Year 1 prerequisite is reported.
- [ ] Try a class from another program or year. Confirm the server rejects it.

### 6. Check balances, payments, and exports

- [ ] As `demo.student001`, open **Finance → Fee Assessments**.
- [ ] Confirm tuition is enrolled units × 1,000, plus 500 registration and
  250 technology fees.
- [ ] Try **Print balances**, **Download PDF**, and **Download Excel**.
  Confirm each contains only your records.
- [ ] Sign out. Sign in as `demo.cashier001` and record a payment.
- [ ] Confirm the balance decreases by exactly the payment amount.
- [ ] Sign in as `demo.student001`. Open **Messages** and confirm the payment
  notification shows the remaining balance.
- [ ] Confirm zero, negative, and over-balance payments are rejected.
- [ ] Sign in as `demo.student002`. Confirm a partial payment and remaining
  balance are shown.

### 7. Check instructor access and completed classes

- [ ] Sign in as `demo.instructor001`.
- [ ] Confirm only assigned classes and their student rosters are visible.
- [ ] Sign out. Sign in as `demo.registrar001`.
- [ ] Change an enrollment status to **Completed**.
- [ ] Confirm the enrollment and assessment pages update.

### 8. Run automated checks

```powershell
python manage.py check
python manage.py test
```

## Restore the starting demo data

Run this only if you want to restart the walkthrough. It deletes all local
database records and recreates the demo data:

```powershell
python manage.py seed_demo_data --reset --students 6 --seed 2026 --password "DemoPass123!"
```
