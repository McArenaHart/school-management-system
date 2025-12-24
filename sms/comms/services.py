from django.utils import timezone
from .models import NotificationLog

class BaseNotificationProvider:
    def send_sms(self, to: str, body: str) -> None:
        raise NotImplementedError

    def send_email(self, to: str, subject: str, body: str) -> None:
        raise NotImplementedError

class ConsoleNotificationProvider(BaseNotificationProvider):
    def send_sms(self, to: str, body: str) -> None:
        print(f"[SMS to {to}] {body}")

    def send_email(self, to: str, subject: str, body: str) -> None:
        print(f"[EMAIL to {to}] {subject}\n{body}")

def get_provider() -> BaseNotificationProvider:
    return ConsoleNotificationProvider()

def send_sms(to: str, body: str) -> NotificationLog:
    log = NotificationLog.objects.create(channel="sms", to=to, body=body, status="queued")
    provider = get_provider()
    try:
        provider.send_sms(to=to, body=body)
        log.status = "sent"
        log.sent_at = timezone.now()
    except Exception as e:
        log.status = "failed"
        log.error = str(e)
    log.save(update_fields=["status", "sent_at", "error"])
    return log

def send_email(to: str, subject: str, body: str) -> NotificationLog:
    log = NotificationLog.objects.create(channel="email", to=to, subject=subject, body=body, status="queued")
    provider = get_provider()
    try:
        provider.send_email(to=to, subject=subject, body=body)
        log.status = "sent"
        log.sent_at = timezone.now()
    except Exception as e:
        log.status = "failed"
        log.error = str(e)
    log.save(update_fields=["status", "sent_at", "error"])
    return log
