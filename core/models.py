from django.db import models
from django.utils import timezone
from decimal import Decimal

class DailySales(models.Model):
    """Track daily sales metrics for the dashboard"""
    date = models.DateField(unique=True)
    total_sales = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    order_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Daily Sales'
        verbose_name_plural = 'Daily Sales'
        ordering = ['-date']

    def __str__(self):
        return f"Sales for {self.date}: ₹{self.total_sales}"

