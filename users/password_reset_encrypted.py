"""
Enhanced password reset confirmation view that supports encrypted tokens.

This module provides password reset endpoints that work with both
traditional Django tokens and encrypted Fernet tokens for security.
"""

from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from .encryption import decrypt_email_token
from .tokens import custom_token_generator
from .api import production_ratelimit
from .token_validator import TokenValidator

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
            return Response({
                'error': 'Missing reset parameters',
                'details': 'Both uid and token parameters are required for password reset',
                'action_required': 'check_reset_link'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
            return Response({
                'error': 'Invalid user ID',
                'details': 'The provided user identifier is invalid or user does not exist',
                'action_required': 'request_new_reset_link'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is active and email is verified
        if not user.is_active:
            return Response({
                'error': 'User account is inactive',
                'details': 'This account has been deactivated. Please contact support for assistance.',
                'action_required': 'contact_support',
                'support_phone': getattr(settings, 'SUPPORT_PHONE_NUMBER', '+91-8758503609')
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not user.is_email_verified:
            # Enhanced handling for newly registered users with unverified emails
            # Check if this is a recently registered user (within last 24 hours)
            from django.utils import timezone
            from datetime import timedelta
            
            is_newly_registered = (
                user.date_joined and 
                timezone.now() - user.date_joined < timedelta(hours=24)
            )
            
            # Check if email delivery failed during registration
            email_failed = getattr(user, 'email_failed', False)
            
            response_data = {
                'error': 'Email must be verified before password reset',
                'details': f'Please verify your email at {user.email} before resetting your password',
                'stored_email_address': user.email,
                'action_required': 'verify_email_first',
                'verification_status': {
                    'is_newly_registered': is_newly_registered,
                    'email_failed': email_failed,
                    'registration_date': user.date_joined.isoformat() if user.date_joined else None
                }
            }
            
            # Provide specific guidance based on user status
            if is_newly_registered:
                if email_failed:
                    response_data['guidance'] = {
                        'message': 'Email delivery failed during registration. Please resend verification email.',
                        'recommended_action': 'resend_verification_email',
                        'login_hint': 'Try logging in first to get a verification token, then use the resend endpoint'
                    }
                else:
                    response_data['guidance'] = {
                        'message': 'Please check your email for the verification link sent during registration.',
                        'recommended_action': 'check_email_inbox',
                        'fallback_action': 'resend_verification_email_if_needed'
                    }
            else:
                response_data['guidance'] = {
                    'message': 'Your account requires email verification before password reset.',
                    'recommended_action': 'login_and_resend_verification',
                    'security_note': 'This protects your account from unauthorized password changes'
                }
            
            # Add support contact for edge cases
            response_data['support'] = {
                'phone': getattr(settings, 'SUPPORT_PHONE_NUMBER', '+91-8758503609'),
                'note': 'Contact support if you continue to experience issues'
            }
            
            return Response(response_data, status=status.HTTP_403_FORBIDDEN)

        # Validate token using unified validator
        if TokenValidator.validate_token(token_param, user, 'password_reset', check_reuse=True):
            return self._reset_password(user, request.data, token_param)
        
        return Response({
            'error': 'Invalid or expired reset token',
            'details': 'The password reset link is invalid or has expired. Please request a new one.',
            'action_required': 'request_new_reset_link'
        }, status=status.HTTP_400_BAD_REQUEST)



    def _reset_password(self, user, data, token_param=None):
        """Reset user password with enhanced validation."""
        new_password1 = data.get('new_password1')
        new_password2 = data.get('new_password2')
        
        # Validate required fields
        if not new_password1 or not new_password2:
            return Response({
                'error': 'Both password fields are required',
                'details': 'Please provide both new_password1 and new_password2 fields',
                'required_fields': ['new_password1', 'new_password2'],
                'action_required': 'provide_passwords'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password confirmation matching
        if new_password1 != new_password2:
            return Response({
                'error': 'Password confirmation does not match',
                'details': 'The password and confirmation password must be identical',
                'action_required': 'match_passwords'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        try:
            validate_password(new_password1, user)
        except ValidationError as e:
            return Response({
                'error': 'Password validation failed',
                'details': 'The password does not meet security requirements',
                'validation_errors': list(e.messages),
                'action_required': 'strengthen_password',
                'password_requirements': [
                    'At least 8 characters long',
                    'Cannot be too similar to your personal information',
                    'Cannot be a commonly used password',
                    'Cannot be entirely numeric'
                ]
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use Django's SetPasswordForm for final validation and saving
        form = SetPasswordForm(user, data)
        if form.is_valid():
            # Store old password hash for token invalidation tracking
            old_password_hash = user.password
            form.save()
            
            # Mark this token as used by storing it in cache or session
            # This prevents token reuse after successful password reset
            if token_param:
                TokenValidator.mark_token_as_used(token_param, 'password_reset')
            
            return Response({
                'message': 'Password has been reset successfully',
                'details': 'Your password has been updated. You can now log in with your new password.',
                'action_required': 'login_with_new_password',
                'next_step': 'redirect_to_login'
            }, status=status.HTTP_200_OK)
        return Response({
            'error': 'Password reset failed',
            'details': 'An unexpected error occurred during password reset',
            'form_errors': form.errors,
            'action_required': 'retry_password_reset'
        }, status=status.HTTP_400_BAD_REQUEST)