# cart/models.py

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from products.models import Product, PriceWeight
import logging

logger = logging.getLogger('admin_actions')

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

    def clean(self):
        """Validate cart data integrity"""
        super().clean()
        
        # Ensure user exists and is active
        if self.user and not self.user.is_active:
            raise ValidationError({
                'user': 'Cannot create cart for inactive user.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to add validation and logging"""
        self.full_clean()  # Run validation
        
        # Log cart creation/modification
        if self.pk:
            logger.info(f"Cart {self.pk} updated for user {self.user.username}")
        else:
            logger.info(f"New cart created for user {self.user.username}")
        
        super().save(*args, **kwargs)

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
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
        """Validate cart item data integrity"""
        super().clean()
        
        # Ensure product is active and available
        if self.product and not getattr(self.product, 'is_active', True):
            raise ValidationError({
                'product': f'Product {self.product.name} is not available.'
            })
        
        # Check stock availability if product has stock tracking
        if self.product and hasattr(self.product, 'stock'):
            if self.product.stock < self.quantity:
                raise ValidationError({
                    'quantity': f'Only {self.product.stock} items available in stock.'
                })
        
        # Validate quantity limits
        if self.quantity > 99:  # Business rule: max 99 items per product
            raise ValidationError({
                'quantity': 'Maximum 99 items allowed per product.'
            })
        
        # Ensure cart belongs to an active user
        if self.cart and self.cart.user and not self.cart.user.is_active:
            raise ValidationError({
                'cart': 'Cannot add items to cart of inactive user.'
            })

    def save(self, *args, **kwargs):
        """Override save to add validation and logging"""
        self.full_clean()  # Run validation
        
        # Log cart item creation/modification
        if self.pk:
            logger.info(
                f"CartItem {self.pk} updated: {self.quantity}x {self.product.name} "
                f"in cart {self.cart.id} (user: {self.cart.user.username})"
            )
        else:
            logger.info(
                f"New CartItem created: {self.quantity}x {self.product.name} "
                f"in cart {self.cart.id} (user: {self.cart.user.username})"
            )
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to add logging"""
        logger.info(
            f"CartItem {self.pk} deleted: {self.quantity}x {self.product.name} "
            f"from cart {self.cart.id} (user: {self.cart.user.username})"
        )
        super().delete(*args, **kwargs)
