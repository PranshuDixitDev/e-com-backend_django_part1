"""Unified token validation utilities for email verification and password reset.

This module consolidates token validation logic to support both
traditional Django tokens, encrypted Fernet tokens, and JWT tokens across different workflows.
"""

import hashlib
import jwt
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from .encryption import decrypt_email_token
from .tokens import custom_token_generator, email_verification_token

# Configure logging for security monitoring
logger = logging.getLogger('security.token_validator')


class TokenValidator:
    """Unified token validator for different token types and workflows."""
    
    @staticmethod
    def validate_token(token, user, token_type, check_reuse=False):
        """
        Validate token for a specific user and token type.
        
        Args:
            token (str): The token to validate
            user: User instance
            token_type (str): Type of token ('email_verification' or 'password_reset')
            check_reuse (bool): Whether to check for token reuse (for password reset)
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        logger.info(f"Token validation attempt for user {user.email}, type: {token_type}")
        
        # Try JWT token first
        if TokenValidator._verify_jwt_token(token, user, token_type, check_reuse):
            logger.info(f"JWT token validation successful for user {user.email}")
            return True
            
        # Try encrypted token
        if TokenValidator._verify_encrypted_token(token, user, token_type, check_reuse):
            logger.info(f"Encrypted token validation successful for user {user.email}")
            return True
            
        # Fallback to Django token for backward compatibility
        result = TokenValidator._verify_django_token(token, user, token_type)
        if result:
            logger.info(f"Django token validation successful for user {user.email}")
        else:
            logger.warning(f"All token validation methods failed for user {user.email}, type: {token_type}")
        return result
    
    @staticmethod
    def _verify_encrypted_token(token, user, token_type, check_reuse=False):
        """Verify encrypted Fernet token."""
        try:
            # Check if token has already been used (for password reset)
            if check_reuse and token_type == 'password_reset':
                token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
                if cache.get(f"used_reset_token_{token_hash}"):
                    logger.warning(f"Attempted reuse of used encrypted token for user {user.email}")
                    return False  # Token has been used
            
            payload = decrypt_email_token(token)
            if not payload:
                logger.warning(f"Failed to decrypt token for user {user.email}")
                return False
                
            # Verify token is for this user and correct type
            if not (payload.get('user_id') == user.pk and 
                   payload.get('token_type') == token_type):
                logger.warning(f"Token user/type mismatch for user {user.email}. Expected: {user.pk}/{token_type}, Got: {payload.get('user_id')}/{payload.get('token_type')}")
                return False
            
            # Check password hash to prevent token reuse after password reset
            if token_type == 'password_reset':
                token_password_hash = payload.get('password_hash')
                if token_password_hash:
                    current_password_hash = user.password[:10] if user.password else ''
                    if token_password_hash != current_password_hash:
                        logger.warning(f"Token created before password change for user {user.email}")
                        return False  # Token was created before password change
            
            return True
        except Exception as e:
            logger.error(f"Error verifying encrypted token for user {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def _verify_django_token(token, user, token_type):
        """Verify traditional Django token."""
        try:
            if token_type == 'password_reset':
                result = custom_token_generator.check_token(user, token)
                if not result:
                    logger.warning(f"Django password reset token validation failed for user {user.email}")
                return result
            elif token_type == 'email_verification':
                result = email_verification_token.check_token(user, token)
                if not result:
                    logger.warning(f"Django email verification token validation failed for user {user.email}")
                return result
            logger.warning(f"Unknown token type: {token_type} for user {user.email}")
            return False
        except Exception as e:
            logger.error(f"Error verifying Django token for user {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def generate_jwt_token(user, token_type='password_reset', expires_in_hours=1):
        """
        Generate a JWT token for password reset or email verification.
        
        Args:
            user: User instance
            token_type (str): Type of token ('password_reset' or 'email_verification')
            expires_in_hours (int): Token expiration time in hours
            
        Returns:
            str: JWT token
        """
        logger.info(f"Generating JWT token for user {user.email}, type: {token_type}, expires in: {expires_in_hours}h")
        
        payload = {
            'user_id': user.pk,
            'email': user.email,
            'token_type': token_type,
            'password_hash': user.password[:10] if user.password else '',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours)
        }
        
        secret_key = getattr(settings, 'SECRET_KEY', 'default-secret')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        logger.info(f"JWT token generated successfully for user {user.email}")
        return token
    
    @staticmethod
    def _verify_jwt_token(token, user, token_type, check_reuse=False):
        """
        Verify JWT token.
        
        Args:
            token (str): JWT token to verify
            user: User instance
            token_type (str): Expected token type
            check_reuse (bool): Whether to check for token reuse
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            # Check if token has already been used (for password reset)
            if check_reuse and token_type == 'password_reset':
                token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
                if cache.get(f"used_reset_token_{token_hash}"):
                    logger.warning(f"Attempted reuse of used JWT token for user {user.email}")
                    return False  # Token has been used
            
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Verify token is for this user and correct type
            if not (payload.get('user_id') == user.pk and 
                   payload.get('token_type') == token_type):
                logger.warning(f"JWT token user/type mismatch for user {user.email}. Expected: {user.pk}/{token_type}, Got: {payload.get('user_id')}/{payload.get('token_type')}")
                return False
            
            # Check password hash to prevent token reuse after password reset
            if token_type == 'password_reset':
                token_password_hash = payload.get('password_hash')
                if token_password_hash:
                    current_password_hash = user.password[:10] if user.password else ''
                    if token_password_hash != current_password_hash:
                        logger.warning(f"JWT token created before password change for user {user.email}")
                        return False  # Token was created before password change
            
            return True
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired JWT token used for user {user.email}")
            return False
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid JWT token used for user {user.email}")
            return False
        except Exception as e:
            logger.error(f"Error verifying JWT token for user {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def mark_token_as_used(token, token_type='password_reset', timeout=86400):
        """
        Mark a token as used to prevent reuse.
        
        Args:
            token (str): The token to mark as used
            token_type (str): Type of token
            timeout (int): Cache timeout in seconds (default: 24 hours)
        """
        if token_type == 'password_reset':
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
            cache.set(f"used_reset_token_{token_hash}", True, timeout)
            logger.info(f"Token marked as used for type: {token_type}, hash: {token_hash[:8]}...")
    
    @staticmethod
    def cleanup_expired_tokens():
        """
        Cleanup expired tokens from cache.
        This method can be called periodically to maintain cache hygiene.
        """
        logger.info("Token cleanup initiated")
        # Note: Django cache doesn't provide a direct way to list all keys
        # This is a placeholder for potential future implementation
        # In production, consider using a more sophisticated cache backend
        # or implementing a database-based token blacklist
        pass
    
    @staticmethod
    def get_token_usage_stats():
        """
        Get statistics about token usage for monitoring purposes.
        
        Returns:
            dict: Token usage statistics
        """
        # This is a placeholder for monitoring implementation
        # In production, you might want to track token generation/validation rates
        return {
            'message': 'Token usage statistics not implemented',
            'note': 'Consider implementing with proper monitoring tools'
        }