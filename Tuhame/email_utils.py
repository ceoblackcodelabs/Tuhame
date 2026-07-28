"""
Fire-and-forget email sending.

A synchronous `send_mail()` call blocks the whole request on an SMTP
round-trip (often 1-3+ seconds, longer if the mail server is slow) - the
user just sits there waiting for a page response that has nothing to do
with email delivery. This runs the send on a background thread instead, so
the response goes out immediately and the email follows a moment later.

For heavier volume than a contact form / occasional notification, a real
task queue (Celery + Redis) is the next step up from this - this is meant
as a zero-extra-infrastructure improvement, not a replacement for one.
"""
import logging
import threading

from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_mail_async(subject, message, from_email, recipient_list, fail_silently=True, **kwargs):
    """Same signature as django.core.mail.send_mail, but returns immediately
    and does the actual SMTP send on a background thread."""

    def _send():
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
                **kwargs,
            )
        except Exception:
            logger.exception("Background email send failed (subject=%r)", subject)
            if not fail_silently:
                raise

    threading.Thread(target=_send, daemon=True).start()
