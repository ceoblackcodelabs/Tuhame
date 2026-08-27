"""
Token generators for one-time auth links (email verification links).

Password reset re-uses Django's own `default_token_generator`
(django.contrib.auth.tokens) directly -- it already hashes the user's
password + last_login + is_active, so it becomes invalid the moment the
password actually changes. No need to reinvent that one.

Email verification needs its own generator: it must become invalid once
the user has verified (not once their password changes), so it hashes in
`profile.is_email_verified` instead.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        profile = getattr(user, 'profile', None)
        verified = getattr(profile, 'is_email_verified', False)
        return f"{user.pk}{timestamp}{user.email}{verified}"


email_verification_token = EmailVerificationTokenGenerator()
