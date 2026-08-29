"""
Central place for every transactional email 2Hame sends.

Design goals:
  - Every send goes through `send_mail_async()` (Tuhame/email_utils.py) --
    no other module should call django.core.mail directly. That function
    is the low-level choke point: it never raises, and it sends on a
    background thread so a slow/broken mail server never blocks the
    request that triggered it.
  - We deliberately only wire up THREE emails right now:
      1. signup email verification
      2. password reset
      3. the existing "someone submitted the Contact form" notice to the
         team inbox (moved here so it goes through the same choke point
         instead of calling send_mail_async ad hoc from home/views.py)
  - Every high-frequency, low-value event in this app (a new saved
    property, a move-checklist item ticked, a profile view, a chart
    render, ...) is deliberately NOT emailed here. Nothing else should be
    added to this module without an explicit decision to spend send
    quota on it.
  - A send failure (bad SMTP creds, provider down, etc.) is logged and
    swallowed -- it must never break signup, login, or a password reset
    request.
"""
import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from Tuhame.email_utils import send_mail_async

logger = logging.getLogger(__name__)


def _base_context(extra=None):
    """Shared branding context merged into every email template."""
    ctx = {
        'site_url': settings.SITE_URL,
        'site_name': getattr(settings, 'SITE_NAME', '2Hame'),
    }
    if extra:
        ctx.update(extra)
    return ctx


def _send(*, to_email, subject, template_name, context):
    """
    THE single choke point for outbound email. Renders
    `templates/emails/<template_name>` with `context` (merged with the
    shared branding context), derives a plain-text body from the
    rendered HTML, and hands both to send_mail_async(). Guard clauses
    below no-op quietly on a missing recipient rather than raising --
    callers never need their own try/except around this.
    """
    if not to_email:
        logger.warning("Skipped email '%s': no recipient address", subject)
        return

    html_body = render_to_string(f'emails/{template_name}', _base_context(context))
    text_body = strip_tags(html_body)

    send_mail_async(
        subject=subject,
        message=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=True,
        html_message=html_body,
    )


# ---------------------------------------------------------------------------
# Auth: signup email verification
# ---------------------------------------------------------------------------

def send_verification_email(user, verification_url):
    """Sent once, right after a new account is created (RegisterView).
    Deliberately does NOT block login -- the user can use the site
    straight away, this just gets a "confirm your email" link into their
    inbox. Also reused by ResendVerificationEmailView."""
    _send(
        to_email=user.email,
        subject=f"Confirm your email - {getattr(settings, 'SITE_NAME', '2Hame')}",
        template_name='verify_email.html',
        context={'user': user, 'verification_url': verification_url},
    )


# ---------------------------------------------------------------------------
# Auth: password reset
# ---------------------------------------------------------------------------

def send_password_reset_email(user, reset_url):
    """Sent when a password reset is requested for an email address that
    matches an account (PasswordResetRequestView). Never sent when the
    address doesn't match anything -- that branch shows the same generic
    "check your inbox" message without calling this, so the request form
    can't be used to probe which emails are registered."""
    _send(
        to_email=user.email,
        subject=f"Reset your password - {getattr(settings, 'SITE_NAME', '2Hame')}",
        template_name='password_reset.html',
        context={'user': user, 'reset_url': reset_url},
    )


# ---------------------------------------------------------------------------
# Contact form notification (pre-existing feature, moved behind the choke
# point -- behavior is unchanged from what home/views.py did inline before)
# ---------------------------------------------------------------------------

def send_contact_notification_email(contact_message):
    """Sent to the team inbox when the public Contact form is submitted."""
    _send(
        to_email=settings.DEFAULT_FROM_EMAIL,
        subject=f"[2Hame Contact] {contact_message.get_subject_display()} from {contact_message.name}",
        template_name='contact_notification.html',
        context={'contact_message': contact_message},
    )
