# orders/models.py

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging
from django.db import transaction
from shipping.shiprocket_api import create_shipment

logger = logging.getLogger(__name__)

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
    shipping_name = models.CharField(max_length=255, null=True, blank=True)      # The name associated with the shipment
    shipment_id = models.CharField(max_length=100, null=True, blank=True)        # The shipment ID provided by Porter
    tracking_number = models.CharField(max_length=100, null=True, blank=True)      # Tracking number for the shipment
    shipping_method = models.CharField(max_length=50, default='Standard')       # E.g., Standard, Express
    carrier = models.CharField(max_length=100, null=True, blank=True)             # E.g., Porter
    estimated_delivery_date = models.DateField(blank=True, null=True)            # Expected delivery date
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Cost of shipping

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

    def process_shipping(self, shipping_data, create_shipment_fn=None):
        """Process shipping information and create shipment"""
        # Update basic shipping info
        self.shipping_name = shipping_data.get('shipping_name')
        self.shipping_method = shipping_data.get('shipping_method', 'Standard')
        self.carrier = shipping_data.get('carrier')
        self.shipping_cost = Decimal(shipping_data.get('shipping_cost', '0.00'))
        self.estimated_delivery_date = shipping_data.get('estimated_delivery_date')

        if create_shipment_fn:
            try:
                shipment_payload = self._prepare_shipment_payload()
                shipment_response = create_shipment_fn(shipment_payload)
                self.shipment_id = shipment_response.get('shipment_id')
                self.tracking_number = shipment_response.get('tracking_number')
            except Exception as e:
                logger.error(f"Shiprocket shipment creation failed: {e}")
                raise

        self.save()

    def _prepare_shipment_payload(self):
        """Prepare payload for Shiprocket API"""
        return {
            "order_id": self.order_number,
            "order_date": self.created_at.strftime('%Y-%m-%d'),
            "billing_customer_name": self.shipping_name or self.user.get_full_name(),
            "billing_address": self.address.address_line1,
            "billing_city": self.address.city,
            "billing_pincode": self.address.postal_code,
            "billing_state": self.address.state,
            "billing_country": self.address.country,
            "shipping_is_billing": True
        }

    @transaction.atomic
    def process_order(self, shipping_data=None):
        """
        Process order with inventory check and shipping integration
        Maintains existing shipping integration while adding safety checks
        """
        try:
            # 1. Validate inventory first
            for item in self.items.all():
                if not item.selected_price_weight.decrease_inventory(item.quantity):
                    raise ValidationError(f"Insufficient inventory for {item.product.name}")

            # 2. Process shipping (keeping existing Shiprocket integration)
            if shipping_data:
                # Keep existing shipping logic
                self.shipping_name = shipping_data.get('shipping_name')
                self.shipping_method = shipping_data.get('shipping_method', 'Standard')
                self.carrier = shipping_data.get('carrier')
                self.shipping_cost = Decimal(shipping_data.get('shipping_cost', '0.00'))
                
                # Maintain Shiprocket integration
                try:
                    shipment_payload = self._prepare_shipment_payload()
                    shipment_response = create_shipment(shipment_payload)
                    self.shipment_id = shipment_response.get('shipment_id')
                    self.tracking_number = shipment_response.get('tracking_number')
                except Exception as e:
                    logger.error(f"Shipping API error: {str(e)}")
                    # Don't fail the order, but log the error
                    
            # 3. Update order status
            self.status = 'PROCESSING'
            self.save()
            
            return True, None

        except Exception as e:
            logger.error(f"Order processing failed: {str(e)}")
            # Rollback happens automatically due to @transaction.atomic
            return False, str(e)

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
