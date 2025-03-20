# orders/models.py

import uuid
from decimal import Decimal  # <<-- Add this line
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

# Choices for order status and payment status.
ORDER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('PROCESSING', 'Processing'),
    ('SHIPPED', 'Shipped'),
    ('DELIVERED', 'Delivered'),
    ('CANCELLED', 'Cancelled'),
]

PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('COMPLETED', 'Completed'),
    ('FAILED', 'Failed'),
]

def generate_order_number():
    """
    Generates a unique and meaningful order number.
    Format: "RP-YYYYMMDD-<unique 6-digit hex>"
    """
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    unique_part = uuid.uuid4().hex[:6].upper()
    return f"RP-{date_str}-{unique_part}"

class Order(models.Model):
    """
    The Order model stores overall order information.
    - 'user': The user who placed the order.
    - 'address': Shipping address (assumed to be from the users app).
    - 'order_number': Unique identifier for the order (auto-generated).
    - 'status': Current order status.
    - 'payment_status': Payment status for the order.
    - 'total_price': Total cost calculated from order items.
    - 'created_at' & 'updated_at': Timestamps for order creation and last update.
    - **Shipping Fields Added Below:**
      - shipping_name, shipment_id, tracking_number, shipping_method,
        carrier, estimated_delivery_date, shipping_cost.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.ForeignKey('users.Address', on_delete=models.SET_NULL, null=True, blank=True)
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    # total_price is stored in the database column named 'total_amount'
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, db_column='total_amount')
    razorpay_order_id = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    razorpay_order_id = models.CharField(max_length=50, blank=True, null=True)
    # NEW SHIPPING FIELDS:
    shipping_name = models.CharField(max_length=100, blank=True, null=True)      # The name associated with the shipment
    shipment_id = models.CharField(max_length=100, blank=True, null=True)        # The shipment ID provided by Porter
    tracking_number = models.CharField(max_length=100, blank=True, null=True)      # Tracking number for the shipment
    shipping_method = models.CharField(max_length=50, blank=True, null=True)       # E.g., Standard, Express
    carrier = models.CharField(max_length=50, blank=True, null=True)             # E.g., Porter
    estimated_delivery_date = models.DateField(blank=True, null=True)            # Expected delivery date
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Cost of shipping

    def clean(self):
        if self.pk and self.status == 'CANCELLED':
            if self.payment_status == 'COMPLETED' and self.status in ['SHIPPED', 'DELIVERED']:
                raise ValidationError("Cannot cancel an order that has been shipped or delivered.")
        super().clean()

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        # Always save to update any field changes.
        super().save(*args, **kwargs)
        total = self.items.aggregate(
            total=models.Sum(models.F('quantity') * models.F('selected_price_weight__price'))
        )['total'] or Decimal('0.00')
        self.total_price = total
        # Save the state fields along with total_price.
        super().save(update_fields=['total_price', 'status', 'payment_status'])

    def __str__(self):
        return f"Order {self.order_number} by {self.user.username}"

class OrderItem(models.Model):
    """
    The OrderItem model stores individual product entries within an order.
    - 'order': The associated order.
    - 'product': The product ordered.
    - 'quantity': How many units of the product were ordered.
    - 'selected_price_weight': The chosen price/weight combination from the product.
    - 'unit_price': The price per unit at the time of order.
    """
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    selected_price_weight = models.ForeignKey('products.PriceWeight', on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be a positive integer.")
        super().clean()

    def save(self, *args, **kwargs):
        self.unit_price = self.selected_price_weight.price
        super().save(*args, **kwargs)
        self.order.save()

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.selected_price_weight.weight})"
    