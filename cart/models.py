# cart/models.py

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from products.models import Product, PriceWeight

class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart {self.id} for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    selected_price_weight = models.ForeignKey(
        PriceWeight,
        on_delete=models.CASCADE
    )  # Stores the selected price-weight combination

    def __str__(self):
        product = self.selected_price_weight.product
        return f"{self.quantity} x {product.name} ({self.selected_price_weight.weight})"

    @property
    def total_price(self):
        return self.quantity * self.selected_price_weight.price

    def clean(self):
        super().clean()


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
