from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from .tokens import custom_token_generator
from .encryption import create_encrypted_verification_link
import logging
import requests


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    uidb64 = urlsafe_base64_encode(force_bytes(reset_password_token.user.pk))
    token = custom_token_generator.make_token(reset_password_token.user)
    
    # Backend confirm path (unchanged for compatibility)
    backend_confirm = reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
    
    # Frontend encrypted link for user interaction
    frontend_url = settings.FRONTEND_URL.rstrip('/')
    reset_url = create_encrypted_verification_link(
        reset_password_token.user, 
        frontend_url, 
        token_type='password_reset'
    )
    
    email_html_message = """
    Hi {name},
    <br><br>
    You're receiving this email because you requested a password reset for your user account at {site_name}.
    <br><br>
    Please go to the following page and choose a new password:
    <a href="{url}">Reset your password</a>
    <br><br>
    Your username, in case you've forgotten: {username}
    <br><br>
    Thank you for using our site!
    <br>
    The {site_name} team
    """.format(
        name=reset_password_token.user.get_full_name() or "user",
        site_name="Gujju Masala",
        url=reset_url,
        username=reset_password_token.user.username
    )

    msg = EmailMultiAlternatives(
        "Password Reset for Gujju Masala",  # Subject
        email_html_message,  # HTML content
        settings.DEFAULT_FROM_EMAIL,  # From email (no-reply@gujjumasala.in)
        [reset_password_token.user.email]  # To email
    )
    msg.attach_alternative(email_html_message, "text/html")
    
    try:
        msg.send()
        # Send admin notification for successful password reset email
        _send_admin_notification(reset_password_token.user, 'PASSWORD_RESET_EMAIL_SENT', 'success')
        logging.info(f"Password reset email sent successfully to {reset_password_token.user.email}")
    except Exception as e:
        # Send admin notification for failed password reset email
        _send_admin_notification(reset_password_token.user, 'PASSWORD_RESET_EMAIL_FAILED', 'error')
        logging.error(f"Failed to send password reset email to {reset_password_token.user.email}: {str(e)}")
        

def _send_admin_notification(user, event_type, status):
    """Send admin notification for password reset events."""
    try:
        notification_url = settings.ADMIN_NOTIFICATION_URL
        headers = {
            'Content-Type': 'application/json',
            'X-INTERNAL-TOKEN': settings.INTERNAL_SERVICE_TOKEN
        }
        
        payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'event_type': event_type,
            'status': status,
            'timestamp': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None,
            'metadata': {
                'user_agent': 'Password Reset Service',
                'source': 'password_reset_signal'
            }
        }
        
        response = requests.post(
            notification_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logging.info(f"Admin notification sent successfully for {event_type}")
        else:
            logging.warning(f"Admin notification failed with status {response.status_code}")
            
    except Exception as e:
        logging.error(f"Failed to send admin notification for {event_type}: {str(e)}")