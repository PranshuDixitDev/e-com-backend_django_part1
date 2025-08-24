"""Unified token validation utilities for email verification and password reset.

This module consolidates token validation logic to support both
traditional Django tokens and encrypted Fernet tokens across different workflows.
"""

import hashlib
from django.core.cache import cache
from .encryption import decrypt_email_token
from .tokens import custom_token_generator, email_verification_token


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
        # Try encrypted token first
        if TokenValidator._verify_encrypted_token(token, user, token_type, check_reuse):
            return True
            
        # Fallback to Django token for backward compatibility
        return TokenValidator._verify_django_token(token, user, token_type)
    
    @staticmethod
    def _verify_encrypted_token(token, user, token_type, check_reuse=False):
        """Verify encrypted Fernet token."""
        try:
            # Check if token has already been used (for password reset)
            if check_reuse and token_type == 'password_reset':
                token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
                if cache.get(f"used_reset_token_{token_hash}"):
                    return False  # Token has been used
            
            payload = decrypt_email_token(token)
            if not payload:
                return False
                
            # Verify token is for this user and correct type
            if not (payload.get('user_id') == user.pk and 
                   payload.get('token_type') == token_type):
                return False
            
            # Check password hash to prevent token reuse after password reset
            if token_type == 'password_reset':
                token_password_hash = payload.get('password_hash')
                if token_password_hash:
                    current_password_hash = user.password[:10] if user.password else ''
                    if token_password_hash != current_password_hash:
                        return False  # Token was created before password change
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def _verify_django_token(token, user, token_type):
        """Verify traditional Django token."""
        try:
            if token_type == 'password_reset':
                return custom_token_generator.check_token(user, token)
            elif token_type == 'email_verification':
                return email_verification_token.check_token(user, token)
            return False
        except Exception:
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