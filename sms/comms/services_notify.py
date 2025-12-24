from .services import send_email, send_sms
from .models import NotificationPreference

def notify_user(user, subject: str, body: str):
    # default preferences if not created yet
    pref, _ = NotificationPreference.objects.get_or_create(user=user)

    email = getattr(user, "email", "") or ""
    phone = ""
    if hasattr(user, "parent_profile"):
        phone = user.parent_profile.phone or ""

    if pref.enable_email and email:
        send_email(to=email, subject=subject, body=body)

    if pref.enable_sms and phone:
        send_sms(to=phone, body=body)

    # in-app is already covered by NotificationLog (we log sms/email).
    # If you want explicit "in-app inbox notifications", we can add a model later.
