from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class CustomUser(AbstractUser):
    phone_validator = RegexValidator(regex=r'^\+91\d{10}$', message="Phone number must be entered in the format: '+919999999999'.")
    phone_number = models.CharField(validators=[phone_validator], max_length=14, unique=True)
    address = models.CharField(max_length=255, blank=False)
    address2 = models.CharField(max_length=255, blank=True, null=True)  # Optional second address
    address3 = models.CharField(max_length=255, blank=True, null=True)  # Optional third address
    postal_code = models.CharField(max_length=6)
    birthdate = models.DateField(null=True, blank=True)  # Optional for superuser

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        db_table = 'custom_user'

    def __str__(self):
        return self.username
