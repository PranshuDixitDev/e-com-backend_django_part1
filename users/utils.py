"""
Utility functions for user management.

This module contains reusable functions following DRY principles.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .tokens import email_verification_token
from .encryption import create_encrypted_verification_link, encrypt_email_token


def send_verification_email(user):
    """
    Send email verification to user.
    
    This is a centralized helper function to avoid code duplication
    across serializers and API views. Generates verification tokens,
    constructs proper links, and sends HTML email.
    
    Args:
        user: User instance that needs email verification
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Generate tokens
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        
        # Backend confirm path (unchanged for compatibility)
        backend_confirm = reverse('email-verify', kwargs={'uidb64': uid, 'token': token})
        
        # Create backend API verification link that directly verifies the email
        # Use the current domain for the backend API endpoint
        from django.contrib.sites.models import Site
        current_site = Site.objects.get_current()
        backend_domain = f"http://{current_site.domain}:8001" if settings.DEBUG else f"https://{current_site.domain}"
        
        # Use encrypted verification endpoint for security
        verification_link = f"{backend_domain}/api/users/email-verify/?uid={uid}&token={encrypt_email_token(user.pk, 'email_verification')}"
        
        # Prepare email context
        context = {
            "user": user, 
            "verification_link": verification_link,
            "current_year": "2024"
        }
        html_content = render_to_string('email_verification.html', context)
        
        # Create and send email
        email = EmailMultiAlternatives(
            subject="Verify your email - Gujju Masala",
            body=f"Click to verify your account: {verification_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        # Update email_sent status on successful send
        user.email_sent = True
        user.email_failed = False
        user.save(update_fields=['email_sent', 'email_failed'])
        
        return True
        
    except Exception as e:
        # Log error if needed
        print(f"Failed to send verification email to {user.email}: {str(e)}")
        
        # Update email_failed status on failure
        user.email_sent = False
        user.email_failed = True
        user.save(update_fields=['email_sent', 'email_failed'])
        
        return False