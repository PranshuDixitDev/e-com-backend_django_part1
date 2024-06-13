from django.db import models
from categories.models import Category
from taggit.managers import TaggableManager
import re
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions


def validate_image(image):
    file_size = image.file.size
    if file_size > 2*1024*1024:  # limit to 2MB
        raise ValidationError("Maximum file size that can be uploaded is 2MB")
    if not image.name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise ValidationError("Image must be '.png', '.webp','.jpg', or '.jpeg' format")


class PriceWeight(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.CharField(max_length=50)  # Example: '100gms'

    class Meta:
        unique_together = ('price', 'weight')

    def __str__(self):
        return f"{self.price}rs for {self.weight}"

def validate_price_weight(value):
    pattern = re.compile(r'^\d+rs for \d+gms$')
    if not pattern.match(value):
        raise ValidationError('Enter price and weight in the correct format (e.g., "2000rs for 100gms").')


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, related_name='products',
                                  on_delete=models.CASCADE)
    price_weights = models.CharField(max_length=100,
     default='2000rs for 100gms',
       help_text="Enter price and weight in format '2000rs for 100gms'")

    tags = TaggableManager()

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', validators=[validate_image])
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"
