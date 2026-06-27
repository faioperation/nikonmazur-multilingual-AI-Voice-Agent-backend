import random
from django.utils import timezone
from datetime import timedelta
from accounts.models import PasswordResetOTP
from django.template.loader import render_to_string
from django.core.mail import EmailMessage


def human_readable_time_ago(timestamp):
    """
    Returns human readable difference between now and given timestamp
    """
    if not timestamp:
        return "Never active"

    now = timezone.now()
    diff = now - timestamp
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return f"{seconds} sec ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    days = hours // 24
    if days < 30:
        return f"{days} day ago"
    months = days // 30
    if months < 12:
        return f"{months} month ago"
    years = months // 12
    return f"{years} year ago"


def generate_otp():
    return str(random.randint(100000, 999999))


def can_resend_otp(user):
    last_otp = (
        PasswordResetOTP.objects.filter(user=user).order_by("-created_at").first()
    )
    if not last_otp:
        return True
    return timezone.now() > last_otp.created_at + timedelta(seconds=30)


def create_otp(user):
    PasswordResetOTP.objects.filter(user=user, verified=False).delete()

    return PasswordResetOTP.objects.create(user=user, code=generate_otp())


def verify_otp(user, otp_code):
    otp_obj = PasswordResetOTP.objects.filter(user=user, verified=False).first()

    if not otp_obj:
        return False, "OTP expired or invalid"

    if otp_obj.is_expired():
        otp_obj.delete()
        return False, "OTP expired"

    if otp_obj.code != otp_code:
        return False, "Invalid OTP"

    otp_obj.verified = True
    otp_obj.save()
    return True, "OTP verified"


def send_otp_email(email, otp, name):
    subject = "Verify Your Password"
    html_content = render_to_string(
        "emails/verify_email.html", {"OTP": otp, "name": name}
    )

    email_msg = EmailMessage(
        subject=subject,
        body=html_content,
        to=[email],
    )
    email_msg.content_subtype = "html"
    email_msg.send()
