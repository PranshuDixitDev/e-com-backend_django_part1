from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
import six


class CustomPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

custom_token_generator = CustomPasswordResetTokenGenerator()

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp) + six.text_type(user.email)
        )

email_verification_token = EmailVerificationTokenGenerator()
print("EmailVerificationTokenGenerator 000000:",email_verification_token)
