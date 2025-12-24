from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.utils import timezone

from people.models import Student
from comms.models import PerformanceNote, BehaviourRecord

def generate_student_monthly_report_pdf(student: Student, month_first_day):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 60, "BusyBee Connect - Monthly Student Report")

    c.setFont("Helvetica", 11)
    c.drawString(40, height - 85, f"Student: {student.first_name} {student.last_name} ({student.student_id})")
    c.drawString(40, height - 105, f"Grade: {student.grade}")
    c.drawString(40, height - 125, f"Month: {month_first_day:%B %Y}")
    c.drawString(40, height - 145, f"Generated: {timezone.now():%Y-%m-%d %H:%M}")

    y = height - 185

    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Performance Summary")
    y -= 20

    notes = PerformanceNote.objects.filter(student=student, term_month=month_first_day).order_by("created_at")
    c.setFont("Helvetica", 11)
    if not notes.exists():
        c.drawString(40, y, "- No performance notes recorded for this month.")
        y -= 18
    else:
        for n in notes:
            teacher = n.teacher_user.get_full_name() if n.teacher_user else "Teacher"
            y = _draw_wrapped(c, f"- ({teacher}) {n.summary}", 40, y, width - 80)
            y -= 8

    y -= 10
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Behaviour Notes")
    y -= 20

    behaviours = BehaviourRecord.objects.filter(
        student=student,
        occurred_on__year=month_first_day.year,
        occurred_on__month=month_first_day.month
    ).order_by("occurred_on")

    c.setFont("Helvetica", 11)
    if not behaviours.exists():
        c.drawString(40, y, "- No behaviour records recorded for this month.")
        y -= 18
    else:
        for b in behaviours:
            teacher = b.teacher_user.get_full_name() if b.teacher_user else "Teacher"
            y = _draw_wrapped(c, f"- ({b.occurred_on:%Y-%m-%d}, {teacher}) {b.note}", 40, y, width - 80)
            y -= 8

    c.showPage()
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 60, "Suggestions for Parents (MVP)")
    c.setFont("Helvetica", 11)
    c.drawString(40, height - 90, "1) Review performance notes with your child weekly.")
    c.drawString(40, height - 110, "2) Encourage consistent homework routines and attendance.")
    c.drawString(40, height - 130, "3) Communicate with the teacher via BusyBee messages if unclear.")

    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf

def _draw_wrapped(c, text, x, y, max_width):
    words = text.split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, "Helvetica", 11) <= max_width:
            line = test
        else:
            c.drawString(x, y, line)
            y -= 14
            line = w
            if y < 60:
                c.showPage()
                y = 780
                c.setFont("Helvetica", 11)
    if line:
        c.drawString(x, y, line)
        y -= 14
    return y
