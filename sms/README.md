# BusyBee Connect (MVP)

Aligned to axioma sms document:
- Role-based login (principal/admin/teacher/parent)
- Teacher-parent communication + notification logs
- Timetable + attendance + assessments + grades
- Fees + POP upload + verification
- Fee reminders (management command)
- Monthly PDF report (ReportLab)
- i18n-ready (English/Shona/Ndebele)

## Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
