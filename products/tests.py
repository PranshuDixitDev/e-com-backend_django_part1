from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Product, Category, PriceWeight
from django.db import IntegrityError

class ProductModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Electronics")

    def test_unique_product_name(self):
        # Ensuring that product names are unique
        Product.objects.create(name="Smartphone", description="Latest model", category=self.category)
        with self.assertRaises(IntegrityError):
            Product.objects.create(name="Smartphone", description="Old model", category=self.category)

    def test_minimum_price_weights(self):
        # Testing minimum price-weight requirements
        product = Product(name="Tablet", description="Portable device", category=self.category)
        product.save()
        # Simulating fewer than 3 price-weight combinations
        PriceWeight.objects.create(product=product, price=2000, weight='100gms')  # Only one combination provided
        try:
            product.full_clean()
        except ValidationError as e:
            self.assertTrue('Ensure a minimum of 3 price-weight combinations are provided.' in str(e))

    def test_image_upload(self):
        # Implement actual image upload tests here if applicable
        pass
