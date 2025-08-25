# Removed django_rest_passwordreset signal handler
# Password reset functionality is now handled by custom PasswordResetRequestView
# This file can be used for other signal handlers if needed in the future

from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.conf import settings
import logging
import requests


# Signal handler removed - using custom password reset implementation
# def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
#     Password reset logic moved to PasswordResetRequestView
#     This ensures unified handling without third-party dependencies
        

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