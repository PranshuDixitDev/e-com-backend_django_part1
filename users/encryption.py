"""
Email encryption utilities for secure token generation.

This module provides encryption for email verification and password reset tokens
using Fernet symmetric encryption instead of basic encoding.
"""

import base64
import json
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def get_email_encryption_key():
    """
    Get or generate encryption key for email tokens.
    In production, this should be set in environment variables.
    """
    key = getattr(settings, 'EMAIL_LINKS_FERNET_KEY', None)
    if not key:
        # Generate a new key if not configured
        key = Fernet.generate_key()
        print(f"Warning: Generated new EMAIL_LINKS_FERNET_KEY: {key.decode()}")
        print("Add this to your environment variables for production!")
    else:
        # Handle both string and bytes input
        if isinstance(key, str):
            key = key.encode()
    return key


def encrypt_email_token(user_id, token_type='email_verification', expires_hours=24):
    """
    Encrypt email token data with expiration.
    
    Args:
        user_id: User primary key
        token_type: Type of token ('email_verification' or 'password_reset')
        expires_hours: Token expiration in hours
        
    Returns:
        str: Encrypted token
    """
    fernet = Fernet(get_email_encryption_key())
    
    # Create payload with expiration
    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
    payload = {
        'user_id': user_id,
        'token_type': token_type,
        'expires_at': expires_at.isoformat(),
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Encrypt the payload
    token_bytes = json.dumps(payload).encode()
    encrypted_token = fernet.encrypt(token_bytes)
    
    # Return URL-safe base64 encoded string
    encoded = base64.urlsafe_b64encode(encrypted_token)
    return encoded.decode() if isinstance(encoded, bytes) else encoded


def decrypt_email_token(encrypted_token):
    """
    Decrypt and validate email token.
    
    Args:
        encrypted_token: Encrypted token string
        
    Returns:
        dict: Token payload if valid, None if invalid/expired
    """
    try:
        fernet = Fernet(get_email_encryption_key())
        
        # Decode from URL-safe base64
        # Handle both string and bytes input
        if isinstance(encrypted_token, str):
            token_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
        else:
            token_bytes = base64.urlsafe_b64decode(encrypted_token)
        
        # Decrypt token
        decrypted_data = fernet.decrypt(token_bytes)
        payload = json.loads(decrypted_data.decode())
        
        # Check expiration
        expires_at = datetime.fromisoformat(payload['expires_at'])
        if datetime.utcnow() > expires_at:
            return None  # Token expired
            
        return payload
        
    except Exception:
        return None  # Invalid token


def create_encrypted_verification_link(user, frontend_url, token_type='email_verification'):
    """
    Create encrypted verification link for email.
    
    Args:
        user: User instance
        frontend_url: Frontend base URL
        token_type: Type of verification
        
    Returns:
        str: Complete verification URL
    """
    encrypted_token = encrypt_email_token(user.pk, token_type)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    if token_type == 'email_verification':
        return f"{frontend_url.rstrip('/')}/verify-email?uid={uid}&token={encrypted_token}"
    elif token_type == 'password_reset':
        return f"{frontend_url.rstrip('/')}/reset-password?uid={uid}&token={encrypted_token}"
    
    return f"{frontend_url.rstrip('/')}/verify?uid={uid}&token={encrypted_token}"