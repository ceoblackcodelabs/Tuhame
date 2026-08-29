"""
Sends outbound email via Brevo's transactional HTTP API instead of SMTP.

Why: outbound SMTP (ports 587/465) is frequently blocked or rate-limited
on shared cPanel hosting, which makes Django's built-in SMTP backend
unreliable there. Brevo's API goes out over plain HTTPS (443), which
always works. This is a drop-in Django EMAIL_BACKEND - nothing else in
the codebase needs to know it isn't SMTP; Tuhame/emails.py and
email_utils.py still just call send_mail() as normal.

Setup: set BREVO_API_KEY in .env to a Brevo API key (not an SMTP
password - those are different credentials in Brevo's dashboard), and
set EMAIL_BACKEND=Tuhame.email_backends.BrevoAPIBackend. See DEPLOY.md.

The sender address in DEFAULT_FROM_EMAIL must be a sender verified in
your Brevo account (Settings -> Senders) - Brevo rejects sends from
unverified addresses regardless of what the API key can otherwise do.
"""
import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoAPIBackend(BaseEmailBackend):
    """Django email backend that posts each message to Brevo's API.
    Honors fail_silently the same way Django's built-in backends do -
    callers going through send_mail_async() rely on failures raising so
    they get caught and logged by that function's own try/except."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, 'BREVO_API_KEY', '')
        if not api_key:
            msg = "Brevo email skipped: BREVO_API_KEY is not configured"
            if not self.fail_silently:
                raise ValueError(msg)
            logger.error(msg)
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send_one(message, api_key):
                sent_count += 1
        return sent_count

    def _send_one(self, message, api_key):
        try:
            from_name, from_email = parseaddr(message.from_email)

            to_recipients = []
            for addr in message.to:
                name, email = parseaddr(addr)
                to_recipients.append({'email': email, 'name': name or email})

            # send_mail(..., html_message=...) attaches the HTML body as
            # an alternative on the underlying EmailMultiAlternatives -
            # message.body stays the plain-text version either way.
            html_content = None
            for content, mimetype in getattr(message, 'alternatives', []):
                if mimetype == 'text/html':
                    html_content = content
                    break

            payload = {
                'sender': {'email': from_email, 'name': from_name or from_email},
                'to': to_recipients,
                'subject': message.subject,
                'textContent': message.body,
            }
            if html_content:
                payload['htmlContent'] = html_content

            response = requests.post(
                BREVO_SEND_URL,
                json=payload,
                headers={
                    'api-key': api_key,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                timeout=15,
            )

            if response.status_code in (200, 201):
                return True

            logger.error(
                "Brevo send failed (status=%s, subject=%r): %s",
                response.status_code, message.subject, response.text[:300],
            )
            if not self.fail_silently:
                raise RuntimeError(f"Brevo API error {response.status_code}: {response.text[:300]}")
            return False

        except Exception:
            logger.exception("Brevo email send failed (subject=%r)", getattr(message, 'subject', '?'))
            if not self.fail_silently:
                raise
            return False
