"""
Enhanced email verification view that supports encrypted tokens.

This module provides verification endpoints that work with both
traditional Django tokens and encrypted Fernet tokens for security.
"""

from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .encryption import decrypt_email_token
from .tokens import email_verification_token
import requests
from django.conf import settings
import logging
from .utils import decode_user_uid
from .token_validator import TokenValidator


logger = logging.getLogger(__name__)

User = get_user_model()


class VerifyEmailEncrypted(APIView):
    """
    Email verification endpoint that supports encrypted tokens.
    
    Accepts both traditional Django tokens and encrypted Fernet tokens
    for backward compatibility and enhanced security.
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64=None, token=None):
        """Handle GET request for email verification."""
        # Extract parameters from URL or query params
        uid_param = uidb64 or request.GET.get('uid')
        token_param = token or request.GET.get('token')
        
        if not uid_param or not token_param:
            return Response(
                {'error': 'Missing verification parameters'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Decode user ID using the new decode function
            try:
                user_id = decode_user_uid(uid_param)
            except ValueError:
                # Fallback to old method for backward compatibility
                user_id = force_str(urlsafe_base64_decode(uid_param))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid user ID'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate token using unified validator
        if TokenValidator.validate_token(token_param, user, 'email_verification'):
            return self._activate_user(user)
        
        return Response(
            {'error': 'Invalid or expired verification token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )



    def _activate_user(self, user):
        """Activate user and mark email as verified."""
        updates = []
        
        if not user.is_active:
            user.is_active = True
            updates.append("is_active")
            
        if hasattr(user, "is_email_verified") and not user.is_email_verified:
            user.is_email_verified = True
            updates.append("is_email_verified")
            
        if updates:
            user.save(update_fields=updates)
            # Send admin notification after successful email verification
            self._send_admin_notification(user)
            
        return Response(
            {
                'message': 'Email verified successfully!',
                'detail': 'Your account has been activated and email verified.'
            }, 
            status=status.HTTP_200_OK
        )
    
    def _send_admin_notification(self, user):
        """Send notification to admin panel about successful email verification."""
        try:
            # Prepare notification data
            notification_data = {
                'event_type': 'email_verification',
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or 'N/A',
                'verification_timestamp': user.date_joined.isoformat() if user.date_joined else None,
                'message': f'User {user.username} ({user.email}) has successfully verified their email address.'
            }
            
            # Log the notification locally
            logger.info(f"Email verification notification: User {user.username} ({user.email}) verified their email")
            
            # If there's an admin notification endpoint configured, send POST request
            admin_notification_url = getattr(settings, 'ADMIN_NOTIFICATION_URL', None)
            if admin_notification_url:
                # Prepare secure headers with internal service token
                headers = {
                    'Content-Type': 'application/json',
                    'X-INTERNAL-TOKEN': getattr(settings, 'INTERNAL_SERVICE_TOKEN', '')
                }
                
                response = requests.post(
                    admin_notification_url,
                    json=notification_data,
                    timeout=5,
                    headers=headers
                )
                if response.status_code == 200:
                    logger.info(f"Admin notification sent successfully for user {user.username}")
                else:
                    logger.warning(f"Admin notification failed with status {response.status_code} for user {user.username}")
            
        except Exception as e:
            # Don't fail email verification if admin notification fails
            logger.error(f"Failed to send admin notification for user {user.username}: {str(e)}")