from django.db import models
from categories.models import Category
from taggit.managers import TaggableManager
import re
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal


def validate_image(image):
    """ Validates the size and format of the uploaded image. """
    file_size = image.size
    if file_size > 2*1024*1024:  # Limit to 2MB
        raise ValidationError("Maximum file size that can be uploaded is 2MB")
    if not image.name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise ValidationError("Image must be in PNG, JPG, JPEG, or WEBP format.")

class PriceWeight(models.Model):
    """ Stores price and weight combinations for a product, ensures uniqueness per product. """
    product = models.ForeignKey('Product', related_name='price_weights', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], default=Decimal('2000.00'))
    weight = models.CharField(max_length=50, default='100gms')
    inventory = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('product', 'price', 'weight')


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product availability after saving a PriceWeight instance
        self.product.update_availability()
    
    def __str__(self):
        return f"{self.product.name} - {self.weight} - ₹{self.price} (Inventory: {self.inventory})"
    
class Product(models.Model):
    """ Main product model. """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    tags = TaggableManager()
    is_active = models.BooleanField(default=True, help_text="Uncheck this box to deactivate the product.")

    def update_availability(self):
        in_stock = self.price_weights.filter(inventory__gt=0).exists()
        if self.is_active != in_stock:
            self.is_active = in_stock
            self.save(update_fields=['is_active'])

    def __str__(self):
        return self.name

def product_image_path(instance, filename):
    # Files will be uploaded to MEDIA_ROOT/products/<product_id>/<filename>
    return 'products/{0}/{1}'.format(instance.product.id, filename)


class ProductImage(models.Model):
    """ Model to manage images associated with products. """
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=product_image_path, validators=[validate_image])
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"


class BestSeller(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product.name
