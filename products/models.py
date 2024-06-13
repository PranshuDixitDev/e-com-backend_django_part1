from django.db import models
from categories.models import Category
from taggit.managers import TaggableManager

class Product(models.Model):
    name = models.CharField(max_length=255)
    price_weight = models.CharField(max_length=50)  # Example: '2000rs-100gm'
    description = models.TextField()
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    tags = TaggableManager()

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"
