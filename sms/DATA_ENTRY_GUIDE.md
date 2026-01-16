# Data Entry & Fake Content Guide

This guide explains how to populate BusyBee Connect so every module looks like it already has realistic data. Use the Django admin (available at `/admin/`) or the UI screens documented in `README.md` to enter the following values, then tweak them to fit your own school.

## 1. Prep work

1. Run the bootstrap command to ensure a current academic year + settings record exist:
   ```bash
   python manage.py bootstrap_school --year 2025 --class-group "Form 2A" --grade-level "Form 2"
   ```
2. Create a superuser or local admin so you can adjust data quickly:
   ```bash
   python manage.py createsuperuser
   ```
3. Seed sample roles/permissions via admin:
   - Create `rbac.Permission` records like `finance.verify_pop`, `academics.view_assessments`, `reports.view_reports`.
   - Create `rbac.Role` such as `Principal`, `Registrar`, `Teacher`, `Parent` and attach the relevant permissions.

## 2. Accounts & roles

Use the Accounts admin page to add users and mark their role booleans.

| Role | Username | Email | Password* | Role flags | Extra info |
| --- | --- | --- | --- | --- | --- |
| Principal | `principal` | `principal@sunrise.ac` | `KeepItSafe123` | `is_principal=True` | Set `is_staff`/`is_superuser` so the dashboard is available. |
| School admin | `admin` | `admin@sunrise.ac` | `AdminPass456` | `is_school_admin=True` | Leave `terms_accepted_at` populated by logging in once and accepting terms. |
| Teacher | `teacher_ada` | `ada@sunrise.ac` | `TeachWithCare` | `is_teacher=True` | Create a `TeacherProfile` with `staff_number=T-1001`, `phone=+263-772-100-200`. |
| Parent | `parent_edna` | `edna@sunrise.ac` | `ParentFirst` | `is_parent=True` | Create a `ParentProfile` with `phone=+263-772-200-300`, `preferred_language=en`. |

\*Passwords above are for staging/demo only; store real ones securely if you go live.

After the users exist,
1. Accept the terms screen by logging in once per user, or set `terms_accepted_at` manually in admin.
2. Link class-level navigation via `core.navigation` entries (menu for each role).

## 3. People & students

### Classrooms
Create `ClassRoom` entries with names that humanize the UI:

| Name | Notes |
| --- | --- |
| `Grade 3 Blue` | Primary example; use everywhere. |
| `Form 2A` | Use in the registrar/admissions test flows. |

### Students

| Field | Example value |
| --- | --- |
| `student_id` | `S-101` |
| `first_name` | `Ada` |
| `last_name` | `Lovelace` |
| `grade` | `Form 2` |
| `classroom` | `Form 2A` |
| `student_number` | `A101` |
| `guardians` | Link to `parent_edna` (via the ManyToMany field) |

Repeat for a second student (e.g., `S-102`, `Grace Hopper`, `Grade 5`, `Grade 5 Green`) with a different guardian user (`parent_chris`).

Those guardians should each have a `ParentProfile` entry with the phone/email above and optional `preferred_language` set to `en` or `sn` for variety.

### Teachers

Add or update a `TeacherProfile` for `teacher_ada`, including `staff_number=T-1001` and `phone=+263-772-100-200`.

## 4. Academics

Follow the forms in `academics/forms.py`.

### Academic year & terms
Create an `AcademicYear` such as:

| Field | Value |
| --- | --- |
| `name` | `2025-2026` |
| `start_date` | `2025-01-01` |
| `end_date` | `2025-12-31` |
| `is_current` | `True` |

Add term records:

| Term | Start | End |
| --- | --- | --- |
| Term 1 | `2025-01-01` | `2025-03-31` |
| Term 2 | `2025-04-01` | `2025-06-30` |

### Class groups

Use `ClassGroupForm` or admin to enter:

| Field | Value |
| --- | --- |
| `name` | `Form 2A` |
| `grade_level` | `Form 2` |
| `academic_year` | `2025-2026` |
| `capacity` | `40` |
| `homeroom_teacher` | `teacher_ada` |

### Subjects & teaching assignments

| Subject code | Name | Grade level |
| --- | --- | --- |
| `MATH` | `Mathematics` | `Form 2` |
| `ENG` | `English` | `Form 2` |

Assign `teacher_ada` to both with `grade_level=Form 2` via `TeachingAssignmentForm`.

### Timetable entries

Add entries for `Form 2A`:

| Day | Time | Subject | Teacher | Room |
| --- | --- | --- | --- | --- |
| Monday | `08:00–09:30` | `MATH` | `teacher_ada` | `Room 12` |
| Tuesday | `10:00–11:30` | `ENG` | `teacher_ada` | `Room 12` |

### Assessments & grades

Create an assessment:

| Field | Value |
| --- | --- |
| `title` | `Term 1 Maths Test` |
| `type` | `test` |
| `max_score` | `100` |
| `weight` | `100` |
| `class_group` | `Form 2A` |
| `subject` | `MATH` |
| `date` | `2025-03-15` |

Record grades per student:

| Student | Score | Comment |
| --- | --- | --- |
| `S-101` | `92` | `Strong concepts.` |
| `S-102` | `85` | `Needs reinforcing fractions.` |

### Attendance

Mark attendance records for March 15th:

| Student | Status | Recorded by |
| --- | --- | --- |
| `S-101` | `present` | `teacher_ada` |
| `S-102` | `late` | `teacher_ada` |


## 5. Finance

### Fee structures

| Field | Value |
| --- | --- |
| `name` | `Grade 2 Tuition` |
| `grade` | `Form 2` |
| `amount` | `100.00` |

### Invoices

Use `CreateInvoiceForm`. Example values:

| Field | Value |
| --- | --- |
| `student_id` | `S-101` |
| `fee_structure_id` | `1` (ID of `Grade 2 Tuition`) |
| `due_date` | `2025-03-30` |
| `total_amount` | `100.00` |
| `parent_username` | `parent_edna` |

When the invoice appears in Finance ➜ Invoices:
1. Start a payment using `StartPaymentForm` for `amount=50.00`, `method=bank`.
2. Complete a second intent or add a `Payment` to reach `100.00`.
3. Upload a POP file using `UploadPOPForm` with `note="Proof from EcoCash"`.
4. Verify the POP as a staff user; this should flip the status to `paid` and add a `FinanceAudit` entry.

### Payment intents/audits
After mocking a payment (via the Start Payment screen), note that the `PaymentIntent` status should go from `initiated` → `succeeded`. Add a manual note (via admin) to `FinanceAudit` such as `action=payment_marked`, `note=Verified by finance`.


## 6. Registrar & admissions

### Individual application

Use the Registrar ➜ Apply form:

| Field | Example |
| --- | --- |
| `first_name` | `Grace` |
| `last_name` | `Hopper` |
| `date_of_birth` | `2014-08-20` |
| `requested_grade` | `Form 2` |
| `guardian_name` | `Edith Hopper` |
| `guardian_phone` | `+263-772-500-600` |
| `guardian_email` | `edith@sunrise.ac` |
| `guardian_relationship` | `Mother` |
| `notes` | `Strong maths aptitude.` |

### Admit a student

From the Registrar ➜ Admit screen:

| Field | Value |
| --- | --- |
| `student_id` | leave blank to auto-generate `S-103` |
| `class_group` | `Form 2A` |
| `parent_username` | `parent_chris` (create as `is_parent=True`) |
| `create_parent_user` | checked if the parent user does not already exist |
| `parent_email` | `chris@sunrise.ac` |

### CSV uploads

- **Bulk applications**: Upload a `.csv` with headers `first_name,last_name,date_of_birth,requested_grade,guardian_name,guardian_phone,guardian_email,guardian_relationship,notes`. Example line:
  ```
  "Alan","Turing","2013-06-23","Form 2","Eve Turing","+263-772-600-700","eve@sunrise.ac","Mother","Enthusiastic coder."
  ```
- **Bulk admit**: Use headers `student_id,first_name,last_name,date_of_birth,grade,class_group,academic_year,parent_username,parent_email`. Example:
  ```
  "S-104","Mary","Johnson","2015-01-04","Form 2","Form 2A","2025-2026","parent_jane","jane@sunrise.ac"
  ```

## 7. Communications & reports

### Threads & messages

1. Ensure `comms.Thread` exists linking `teacher_ada`, `parent_edna`, and `S-101`.
2. Add messages such as:
   - Teacher: "Please submit the homework by Friday." (use teacher account to post.)
   - Parent: "Noted, thank you."
3. Each thread automatically logs `NotificationLog` entries (`channel=email`, `to=parent@...`, `status=sent`).

### Performance notes & behaviour

| Model | Sample |
| --- | --- |
| `PerformanceNote` | `term_month=2025-03-01`, `summary="Strong numeracy, needs reading practice"`, `teacher_user=teacher_ada` |
| `BehaviourRecord` | `occurred_on=2025-03-10`, `note="Helped peer with revision."` |

### Notification preferences

Create `NotificationPreference` for each user. Example: `enable_email=True`, `enable_sms=False`, `enable_in_app=True`.

### Reports

Use the admin to grant `reports.view_reports` to `principal` and `teacher_ada`. Visit Reports ➜ Dashboard to view attendance/fees summaries. Run the `Generate report` flow to produce a PDF for `S-101`.

## 8. Mock media + proof files

The finance POP upload form stores files under `media/payment_proofs/`. Keep placeholder text files such as `proof.txt` with short notes; these can be reused by re-uploading in the Finance UI (the existing dummy files in the repo can be deleted once you have your own test proofs).

## 9. Dashboard hero & quick actions

Populate the models below so the refreshed dashboard looks full and clickable:

1. **Hero numbers** – Create a handful of `Student`, `User` (teacher/admin), and `Subject` records so that your hero cards read like `Total students: 180`, `Total employees: 32`, `Total subjects: 24`, `Applications: 14 (new 5)`. The KPI card pulls values directly from `Student.objects.count()`, `User.objects.filter(is_teacher=True).count()`, and `Subject.objects.count()`, while `AdmissionApplication` controls the applications total (new/accepted statuses).
2. **Absentee snapshot** – Seed `AttendanceRecord` rows (status=`absent`, `present`, `late`) for the past 30 days. The summary cards use counts (`attendance_summary.present`, `late`, `absent`) and the list uses the latest five absent records (include student name, class group, and date like `2025-03-11`).
3. **Hero links** – Make sure `people:students_list`, `rbac:home`, `academics:subjects_manage`, and `registrar:admissions_list` all contain sample content so the cards lead safely to populated screens.
4. **Quick action targets** – Trigger flows for `registrar:apply`, `rbac:user_create`, `core:academic_years`, `comms:start_thread`, `registrar:bulk_applications_upload`, `registrar:bulk_admit_upload`, and `finance:verification_queue`. Each quick action card is purely navigational, but pre-populating the destination forms (students, roles, calendar, threads, bulk uploads, POP queue) gives the dashboard the “live” feel the hero embodies.

## 10. Verification

After entering the data:

1. Log in as each role to confirm the relevant dashboards (accounts, academics, finance, registrar, comms, reports).
2. Run `python manage.py test` to ensure no regressions.
3. Invite another collaborator to review the filled data and confirm the flows feel "populated."

## Summary

Copy the sample rows above into a spreadsheet or CSV, adjust for your real school context, and paste values straight into the UI forms (fields like `student_id`, `fee_structure_id`, `parent_username`) to quickly mimic a live environment. Use the tables as reference whenever you need to reseed demo accounts or regrow the dataset.
