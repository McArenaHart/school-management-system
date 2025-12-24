from django.core.management.base import BaseCommand
from django.utils import timezone
from finance.models import FeeInvoice
from comms.services import send_sms, send_email

class Command(BaseCommand):
    help = "Send fee reminders (MVP: logs + prints via ConsoleNotificationProvider)."

    def add_arguments(self, parser):
        parser.add_argument("--days-overdue", type=int, default=15)

    def handle(self, *args, **options):
        days = options["days_overdue"]
        cutoff = timezone.now().date() - timezone.timedelta(days=days)

        invoices = FeeInvoice.objects.filter(
            status__in=["unpaid", "partial"],
            due_date__lte=cutoff,
        ).select_related("parent_user", "student")

        if not invoices.exists():
            self.stdout.write("No reminders to send.")
            return

        for inv in invoices:
            parent = inv.parent_user
            student = inv.student

            msg = (
                f"School Fees Reminder: {student.first_name} {student.last_name} "
                f"(ID {student.student_id}) outstanding invoice #{inv.id}. "
                f"Amount {inv.total_amount}. Due {inv.due_date}."
            )

            email = getattr(parent, "email", "") if parent else ""
            phone = ""
            if parent and hasattr(parent, "parent_profile"):
                phone = parent.parent_profile.phone or ""

            if email:
                send_email(to=email, subject="School Fees Reminder", body=msg)
            elif phone:
                send_sms(to=phone, body=msg)
            else:
                send_sms(to="UNKNOWN_PHONE", body=msg)

            self.stdout.write(f"Reminder queued for invoice {inv.id}")
