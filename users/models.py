# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class CustomUser(AbstractUser):
    phone_validator = RegexValidator(regex=r'^\+91\d{10}$', message="Phone number must be entered in the format: '+919999999999'.")
    phone_number = models.CharField(validators=[phone_validator], max_length=14, unique=True)
    birthdate = models.DateField(null=True, blank=False)  # Optional for superuser
    is_email_verified = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False, help_text='Indicates if verification email was successfully sent')
    email_failed = models.BooleanField(default=False, help_text='Indicates if verification email failed to send')
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        db_table = 'custom_user'

    def __str__(self):
        return self.username

class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    postal_code = models.CharField(max_length=6)

    class Meta:
        verbose_name = 'address'
        verbose_name_plural = 'addresses'

    def __str__(self):
        return f'{self.address_line1}, {self.city}, {self.state}, {self.country}'
