from django.db import models
from django.utils import timezone

class ShippingLog(models.Model):
    """
    Model to log all Shiprocket API calls (both successful and failed).
    This model captures the request payload, response payload, error message (if any),
    a success flag, and the timestamp.
    """
    order_number = models.CharField(max_length=20)
    endpoint = models.CharField(max_length=255)
    request_payload = models.TextField(null=True, blank=True)
    response_payload = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    success = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        status = "Success" if self.success else "Failure"
        return f"ShippingLog for Order {self.order_number} - {status} at {self.timestamp}"