"""
Enhanced password reset confirmation view that supports encrypted tokens.

This module provides password reset endpoints that work with both
traditional Django tokens and encrypted Fernet tokens for security.
"""

from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.forms import SetPasswordForm
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from .encryption import decrypt_email_token
from .tokens import custom_token_generator
from .api import production_ratelimit

User = get_user_model()


class PasswordResetConfirmEncrypted(APIView):
    """
    Password reset confirmation endpoint that supports encrypted tokens.
    
    Accepts both traditional Django tokens and encrypted Fernet tokens
    for backward compatibility and enhanced security.
    """
    permission_classes = [AllowAny]

    @method_decorator(production_ratelimit(key='ip', rate='2/m', method='POST'))
    def post(self, request, uidb64=None, token=None):
        """Handle POST request for password reset confirmation."""
        # Extract parameters from URL or query params
        uid_param = uidb64 or request.GET.get('uid') or request.data.get('uid')
        token_param = token or request.GET.get('token') or request.data.get('token')
        
        if not uid_param or not token_param:
            return Response(
                {'error': 'Missing reset parameters'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Decode user ID using the new decode function
            from .utils import decode_user_uid
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
        
        # Check if user is active and email is verified
        if not user.is_active:
            return Response(
                {'error': 'User account is inactive'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.is_email_verified:
            return Response(
                {'error': 'Email must be verified before password reset'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try encrypted token first
        if self._verify_encrypted_token(token_param, user):
            return self._reset_password(user, request.data)
        
        # Fallback to Django token for backward compatibility
        if custom_token_generator.check_token(user, token_param):
            return self._reset_password(user, request.data)
        
        return Response(
            {'error': 'Invalid or expired reset token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    def _verify_encrypted_token(self, token, user):
        """Verify encrypted token."""
        try:
            payload = decrypt_email_token(token)
            if not payload:
                return False
                
            # Verify token is for this user and correct type
            return (
                payload.get('user_id') == user.pk and 
                payload.get('token_type') == 'password_reset'
            )
        except Exception:
            return False

    def _reset_password(self, user, data):
        """Reset user password using form validation."""
        form = SetPasswordForm(user, data)
        if form.is_valid():
            form.save()
            return Response(
                {'message': 'Password has been reset successfully'}, 
                status=status.HTTP_200_OK
            )
        return Response(
            {'errors': form.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )