from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .tokens import custom_token_generator


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    uidb64 = urlsafe_base64_encode(force_bytes(reset_password_token.user.pk))
    token = custom_token_generator.make_token(reset_password_token.user)
    reset_url = "{}://{}{}".format(
        "http",
        "127.0.0.1:8000",
        reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
    )
    
    email_html_message = """
    Hi {name},
    <br><br>
    You're receiving this email because you requested a password reset for your user account at {site_name}.
    <br><br>
    Please go to the following page and choose a new password:
    <a href="{url}">Reset your password</a>
    <br><br>
    Your username, in case you’ve forgotten: {username}
    <br><br>
    Thank you for using our site!
    <br>
    The {site_name} team
    """.format(
        name=reset_password_token.user.get_full_name() or "user",
        site_name="Your Website Title",
        url=reset_url,
        username=reset_password_token.user.username
    )

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
        print("Failed to send email:", e)