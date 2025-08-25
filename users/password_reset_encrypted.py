"""
Enhanced password reset confirmation view that supports encrypted tokens.

This module provides password reset endpoints that work with both
traditional Django tokens and encrypted Fernet tokens for security.
"""

import logging
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from .encryption import decrypt_email_token
from .tokens import custom_token_generator
from .api import production_ratelimit
from .token_validator import TokenValidator

# Configure logging for security monitoring
logger = logging.getLogger('security.password_reset')

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
        client_ip = self._get_client_ip(request)
        
        # Log password reset attempt for security monitoring
        logger.info(f"Password reset attempt from IP: {client_ip}")
        
        # Extract parameters from URL, query params, or request data
        uid_param = uidb64 or request.GET.get('uid') or request.data.get('uid')
        token_param = token or request.GET.get('token') or request.data.get('token')
        
        # For JWT tokens, we might not need uid parameter as it's embedded in the token
        if not token_param:
            logger.warning(f"Password reset attempt without token from IP: {client_ip}")
            return Response({
                'error': 'Missing reset token',
                'details': 'Token parameter is required for password reset',
                'action_required': 'check_reset_link'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to extract user from JWT token first
        user = self._get_user_from_jwt_token(token_param)
        if user:
            logger.info(f"JWT token validation attempt for user: {user.email} from IP: {client_ip}")
            return self._handle_jwt_reset(user, token_param, request.data, client_ip)
        
        # Fallback to traditional uid/token method
        if not uid_param:
            logger.warning(f"Password reset attempt without uid from IP: {client_ip}")
            return Response({
                'error': 'Missing reset parameters',
                'details': 'Either valid JWT token or both uid and token parameters are required',
                'action_required': 'check_reset_link'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Traditional token validation attempt from IP: {client_ip}")
        return self._handle_traditional_reset(uid_param, token_param, request.data, client_ip)
    
    def _get_user_from_jwt_token(self, token):
        """Extract user from JWT token if valid."""
        try:
            import jwt
            from django.conf import settings
            
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            if payload.get('token_type') == 'password_reset':
                user_id = payload.get('user_id')
                if user_id:
                    user = User.objects.get(pk=user_id)
                    logger.info(f"JWT token decoded successfully for user: {user.email}")
                    return user
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token used in password reset attempt")
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token used in password reset attempt")
        except User.DoesNotExist:
            logger.warning("JWT token contains non-existent user ID")
        except Exception as e:
            logger.error(f"Unexpected error decoding JWT token: {str(e)}")
        return None
    
    def _handle_jwt_reset(self, user, token_param, data, client_ip):
        """Handle password reset with JWT token."""
        # Check user status conditions
        eligibility_result = self._check_user_eligibility(user)
        if not eligibility_result['eligible']:
            logger.warning(f"Ineligible user {user.email} attempted password reset from IP: {client_ip}. Reason: {eligibility_result['reason']}")
            return Response({
                'error': 'Account not eligible for password reset',
                'details': eligibility_result['message'],
                'action_required': 'verify_user_status'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validate JWT token
        if TokenValidator.validate_token(token_param, user, 'password_reset', check_reuse=True):
            logger.info(f"Valid JWT token for user {user.email} from IP: {client_ip}")
            return self._reset_password(user, data, token_param, client_ip)
        
        logger.warning(f"Invalid/expired JWT token for user {user.email} from IP: {client_ip}")
        return Response({
            'error': 'Invalid or expired reset token',
            'details': 'The password reset link is invalid or has expired. Please request a new one.',
            'action_required': 'request_new_reset_link'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _handle_traditional_reset(self, uid_param, token_param, data, client_ip):
        """Handle password reset with traditional uid/token method."""
        try:
            # Decode user ID using the new decode function
            from .utils import decode_user_uid
            try:
                user_id = decode_user_uid(uid_param)
            except ValueError:
                # Fallback to old method for backward compatibility
                user_id = force_str(urlsafe_base64_decode(uid_param))
            user = User.objects.get(pk=user_id)
            logger.info(f"Traditional token validation for user {user.email} from IP: {client_ip}")
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.warning(f"Invalid user ID in password reset from IP: {client_ip}. Error: {str(e)}")
            return Response({
                'error': 'Invalid user ID',
                'details': 'The provided user identifier is invalid or user does not exist',
                'action_required': 'request_new_reset_link'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check user status conditions
        eligibility_result = self._check_user_eligibility(user)
        if not eligibility_result['eligible']:
            logger.warning(f"Ineligible user {user.email} attempted password reset from IP: {client_ip}. Reason: {eligibility_result['reason']}")
            return Response({
                'error': 'Account not eligible for password reset',
                'details': eligibility_result['message'],
                'action_required': 'verify_user_status'
            }, status=status.HTTP_403_FORBIDDEN)

        # Validate token using unified validator
        if TokenValidator.validate_token(token_param, user, 'password_reset', check_reuse=True):
            logger.info(f"Valid traditional token for user {user.email} from IP: {client_ip}")
            return self._reset_password(user, data, token_param, client_ip)
        
        logger.warning(f"Invalid/expired traditional token for user {user.email} from IP: {client_ip}")
        return Response({
            'error': 'Invalid or expired reset token',
            'details': 'The password reset link is invalid or has expired. Please request a new one.',
            'action_required': 'request_new_reset_link'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _check_user_eligibility(self, user):
        """Check if user is eligible for password reset with detailed reasons."""
        # Required conditions: email_verified=True, email_sent=True, email_failed=False, is_active=True
        email_verified = getattr(user, 'is_email_verified', False)
        email_sent = getattr(user, 'email_sent', False)
        email_failed = getattr(user, 'email_failed', False)
        is_active = user.is_active
        
        if not is_active:
            return {
                'eligible': False,
                'reason': 'account_inactive',
                'message': 'Account is inactive. Please contact support.'
            }
        
        if not email_verified:
            return {
                'eligible': False,
                'reason': 'email_not_verified',
                'message': 'Email address is not verified. Please verify your email first.'
            }
        
        if not email_sent:
            return {
                'eligible': False,
                'reason': 'email_setup_incomplete',
                'message': 'Account setup is incomplete. Please complete your registration.'
            }
        
        if email_failed:
            return {
                'eligible': False,
                'reason': 'email_delivery_issues',
                'message': 'Email delivery issues detected. Please contact support.'
            }
        
        return {
            'eligible': True,
            'reason': 'eligible',
            'message': 'User is eligible for password reset.'
        }



    def _reset_password(self, user, data, token_param=None, client_ip=None):
        """Reset user password with enhanced validation and security logging."""
        new_password = data.get('new_password')
        re_enter_password = data.get('re_enter_password')
        
        logger.info(f"Password reset attempt for user {user.email} from IP: {client_ip}")
        
        # Validate required fields
        if not new_password or not re_enter_password:
            logger.warning(f"Incomplete password reset data for user {user.email} from IP: {client_ip}")
            return Response({
                'error': 'Both password fields are required',
                'details': 'Please provide both new_password and re_enter_password fields',
                'required_fields': ['new_password', 're_enter_password'],
                'action_required': 'provide_passwords'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password confirmation matching
        if new_password != re_enter_password:
            logger.warning(f"Password mismatch for user {user.email} from IP: {client_ip}")
            return Response({
                'error': 'Password confirmation does not match',
                'details': 'The new password and re-entered password must be identical',
                'action_required': 'match_passwords'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            logger.warning(f"Weak password attempt for user {user.email} from IP: {client_ip}")
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
        # Convert new field names to Django's expected format
        form_data = {
            'new_password1': new_password,
            'new_password2': re_enter_password
        }
        form = SetPasswordForm(user, form_data)
        if form.is_valid():
            # Store old password hash for token invalidation tracking
            old_password_hash = user.password
            form.save()
            
            # Update password reset tracking fields - preserve email sent status for admin tracking
            user.password_reset_email_failed = False
            user.password_reset_attempts = 0  # Reset attempts after successful reset
            user.save(update_fields=['password_reset_email_failed', 'password_reset_attempts'])
            
            # Mark this token as used by storing it in cache or session
            # This prevents token reuse after successful password reset
            if token_param:
                TokenValidator.mark_token_as_used(token_param, 'password_reset')
            
            logger.info(f"Password reset successful for user {user.email} from IP: {client_ip}")
            
            return Response({
                'message': 'Password has been reset successfully',
                'details': 'Your password has been updated. You can now log in with your new password.',
                'action_required': 'login_with_new_password',
                'next_step': 'redirect_to_login'
            }, status=status.HTTP_200_OK)
        
        logger.error(f"Password reset form validation failed for user {user.email} from IP: {client_ip}. Errors: {form.errors}")
        return Response({
            'error': 'Password reset failed',
            'details': 'An unexpected error occurred during password reset',
            'form_errors': form.errors,
            'action_required': 'retry_password_reset'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Get client IP address from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip