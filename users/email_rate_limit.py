# users/email_rate_limit.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class EmailResendAttempt(models.Model):
    """
    Track email resend attempts for rate limiting.
    Allows 5 resend attempts per day per email address.
    """
    email = models.EmailField()
    attempt_date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    success = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'email_resend_attempts'
        indexes = [
            models.Index(fields=['email', 'attempt_date']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.attempt_date}"
    
    @classmethod
    def can_resend_email(cls, email):
        """
        Check if email can be resent based on daily limit.
        
        Args:
            email (str): Email address to check
            
        Returns:
            tuple: (can_resend: bool, attempts_today: int, remaining_attempts: int)
        """
        today = timezone.now().date()
        start_of_day = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        end_of_day = start_of_day + timedelta(days=1)
        
        attempts_today = cls.objects.filter(
            email=email,
            attempt_date__gte=start_of_day,
            attempt_date__lt=end_of_day
        ).count()
        
        max_attempts = 5
        can_resend = attempts_today < max_attempts
        remaining_attempts = max(0, max_attempts - attempts_today)
        
        return can_resend, attempts_today, remaining_attempts
    
    @classmethod
    def record_attempt(cls, email, ip_address=None, user_agent=None, success=False):
        """
        Record an email resend attempt.
        
        Args:
            email (str): Email address
            ip_address (str): IP address of the request
            user_agent (str): User agent string
            success (bool): Whether the email was sent successfully
            
        Returns:
            EmailResendAttempt: Created attempt record
        """
        attempt = cls.objects.create(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success
        )
        
        logger.info(
            f"Email resend attempt recorded for {email}. "
            f"Success: {success}, IP: {ip_address}"
        )
        
        return attempt
    
    @classmethod
    def cleanup_old_attempts(cls, days_to_keep=30):
        """
        Clean up old email resend attempts to prevent database bloat.
        
        Args:
            days_to_keep (int): Number of days to keep records
            
        Returns:
            int: Number of deleted records
        """
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        deleted_count, _ = cls.objects.filter(attempt_date__lt=cutoff_date).delete()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old email resend attempt records")
        
        return deleted_count