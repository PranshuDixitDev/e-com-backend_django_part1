from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    uidb64 = urlsafe_base64_encode(force_bytes(reset_password_token.user.pk))
    reset_url = f"http://127.0.0.1:8000{reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': reset_password_token.key})}"
    
    email_html_message = f"""
    Hi {reset_password_token.user.get_full_name() or "user"},
    <br><br>
    You're receiving this email because you requested a password reset for your user account at Your Website Title.
    <br><br>
    Please go to the following page and choose a new password:
    <a href="{reset_url}">Reset your password</a>
    <br><br>
    Your username, in case you’ve forgotten: {reset_password_token.user.username}
    <br><br>
    Thank you for using our site!
    <br>
    The Your Website Title team
    """

    msg = EmailMultiAlternatives(
        "Password Reset for Your Website Title",  # Subject
        email_html_message,  # HTML content
        "perceptionsofdesign@gmail.com",  # From email
        [reset_password_token.user.email]  # To email
    )
    msg.attach_alternative(email_html_message, "text/html")
    try:
        msg.send()
    except Exception as e:
        print(f"Failed to send email: {e}")
