"""Custom password reset request view that replaces django_rest_passwordreset.

This module provides a unified password reset request endpoint that generates
JWT-based email verification links without relying on third-party packages.
"""

from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from .api import production_ratelimit
from .token_validator import TokenValidator
import logging
import requests

User = get_user_model()


class PasswordResetRequestView(APIView):
    """
    Custom password reset request endpoint that generates JWT-based email verification links.
    
    Replaces django_rest_passwordreset functionality with our unified approach.
    """
    permission_classes = [AllowAny]

    @method_decorator(production_ratelimit(key='ip', rate='2/m', method='POST'))
    def post(self, request):
        """Handle password reset request."""
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email is required',
                'details': 'Please provide an email address for password reset',
                'action_required': 'provide_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Check user status conditions for password reset access
            email_verified = getattr(user, 'is_email_verified', False)
            email_sent = getattr(user, 'email_sent', False)
            email_failed = getattr(user, 'email_failed', False)
            is_active = user.is_active
            
            # Enforce strict user eligibility criteria for security
            if not email_verified:
                return Response({
                    'error': 'Email not verified',
                    'details': 'Please verify your email address before requesting password reset',
                    'action_required': 'verify_email'
                }, status=status.HTTP_403_FORBIDDEN)
            
            if not email_sent:
                return Response({
                    'error': 'Account setup incomplete',
                    'details': 'Account verification process not completed',
                    'action_required': 'contact_support'
                }, status=status.HTTP_403_FORBIDDEN)
            
            if email_failed:
                return Response({
                    'error': 'Email delivery issues',
                    'details': 'Previous email delivery failed. Please contact support',
                    'action_required': 'contact_support'
                }, status=status.HTTP_403_FORBIDDEN)
            
            if not is_active:
                return Response({
                    'error': 'Account inactive',
                    'details': 'Your account is currently inactive. Please contact support',
                    'action_required': 'contact_support'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check for excessive password reset attempts (security measure)
            max_attempts = getattr(settings, 'MAX_PASSWORD_RESET_ATTEMPTS', 5)
            if user.password_reset_attempts >= max_attempts:
                return Response({
                    'error': 'Too many attempts',
                    'details': f'Maximum password reset attempts ({max_attempts}) exceeded. Please contact support',
                    'action_required': 'contact_support'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Generate JWT token for password reset
            jwt_token = TokenValidator.generate_jwt_token(user, 'password_reset', expires_in_hours=1)
            
            # Create frontend reset URL with JWT token
            frontend_url = settings.FRONTEND_URL.rstrip('/')
            reset_url = f"{frontend_url}/reset-password?token={jwt_token}"
            
            # Send password reset email
            if self._send_password_reset_email(user, reset_url):
                # Update password reset tracking fields on success
                user.password_reset_email_sent = True
                user.password_reset_email_failed = False
                user.password_reset_email_sent_at = timezone.now()
                user.password_reset_attempts += 1
                user.save(update_fields=['password_reset_email_sent', 'password_reset_email_failed', 
                                       'password_reset_email_sent_at', 'password_reset_attempts'])
                
                self._send_admin_notification(user, 'PASSWORD_RESET_EMAIL_SENT', 'success')
                return Response({
                    'message': 'Password reset email sent',
                    'details': 'Check your email for password reset instructions',
                    'action_required': 'check_email'
                }, status=status.HTTP_200_OK)
            else:
                # Update password reset tracking fields on failure
                user.password_reset_email_sent = False
                user.password_reset_email_failed = True
                user.password_reset_attempts += 1
                user.save(update_fields=['password_reset_email_sent', 'password_reset_email_failed', 
                                       'password_reset_attempts'])
                
                self._send_admin_notification(user, 'PASSWORD_RESET_EMAIL_FAILED', 'error')
                return Response({
                    'error': 'Try again later',
                    'details': 'Unable to send password reset email. Please try again later.',
                    'action_required': 'retry_later'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except User.DoesNotExist:
            # Return error message when user doesn't exist
            return Response({
                'error': 'User not found',
                'details': 'No account found with this email address',
                'action_required': 'verify_email'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _send_password_reset_email(self, user, reset_url):
        """Send password reset email with encrypted link."""
        try:
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
            If you didn't request this password reset, please ignore this email.
            <br><br>
            Thank you for using our site!
            <br>
            The {site_name} team
            """.format(
                name=user.get_full_name() or "user",
                site_name="Gujju Masala",
                url=reset_url,
                username=user.username
            )

            msg = EmailMultiAlternatives(
                "Password Reset for Gujju Masala",  # Subject
                email_html_message,  # HTML content
                settings.DEFAULT_FROM_EMAIL,  # From email
                [user.email]  # To email
            )
            msg.attach_alternative(email_html_message, "text/html")
            msg.send()
            
            logging.info(f"Password reset email sent successfully to {user.email}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False
    
    def _send_admin_notification(self, user, event_type, status_type):
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
                'status': status_type,
                'timestamp': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None,
                'metadata': {
                    'user_agent': 'Custom Password Reset Service',
                    'source': 'password_reset_request'
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