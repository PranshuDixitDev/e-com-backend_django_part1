from django.db import models
from categories.models import Category
from taggit.managers import TaggableManager
import re
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils.text import slugify
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.db import transaction


def validate_image(image):
    """ Validates the size and format of the uploaded image. """
    file_size = image.size
    max_size = 2*1024*1024  # 2MB
    
    if file_size > max_size:
        raise ValidationError(f"Maximum file size allowed is {max_size/1024/1024}MB")
    
    allowed_formats = ['.png', '.jpg', '.jpeg', '.webp']
    if not any(image.name.lower().endswith(fmt) for fmt in allowed_formats):
        raise ValidationError(f"Image must be in {', '.join(allowed_formats)} format.")

class PriceWeight(models.Model):
    """ Stores price and weight combinations for a product, ensures uniqueness per product. """
    product = models.ForeignKey('Product', related_name='price_weights', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], default=Decimal('2000.00'))
    weight = models.CharField(max_length=50, default='100gms')
    inventory = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], db_index=True)

    class Meta:
        unique_together = ('product', 'price', 'weight')


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product availability after saving a PriceWeight instance
        self.product.update_availability()
    
    @transaction.atomic
    def decrease_inventory(self, quantity):
        """Safely decrease inventory with proper validation"""
        if self.inventory >= quantity:
            self.inventory -= quantity
            self.save(update_fields=['inventory'])
            return True
        return False

    def __str__(self):
        return f"{self.product.name} - {self.weight} - ₹{self.price} (Inventory: {self.inventory})"
    
class Product(models.Model):
    """ Main product model. """
    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    tags = TaggableManager()
    is_active = models.BooleanField(default=True, help_text="Uncheck this box to deactivate the product.", db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness by appending a counter if needed
            counter = 1
            original_slug = self.slug
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

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
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            self.__class__.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
            
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Image for {self.product.name}"


class BestSeller(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product.name
