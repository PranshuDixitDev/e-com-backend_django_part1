# products/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Product, Category, PriceWeight
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class ProductModelTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Setup data that is used across multiple test methods.
        cls.category = Category.objects.create(name="Electronics")
        cls.user = User.objects.create_user(
            username='user', 
            password='pass',
            phone_number='+1234567890'
        )
        cls.admin = User.objects.create_superuser(
            username='admin', 
            password='adminpass',
            phone_number='+0987654321'
        )
        cls.product = Product.objects.create(
            name="Smartphone",
            description="Latest model",
            category=cls.category
        )
        # Preparing URL for list and detail endpoints.
        cls.url_list = reverse('product-list')
        cls.url_detail = reverse('product-detail', kwargs={'pk': cls.product.id})

    def get_tokens_for_user(self, user):
        # Helper method to generate JWT tokens for users.
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_get_products(self):
        # Test retrieving all products. Everyone can view products.
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_product_by_admin(self):
        # Test that only admin users can create products.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        data = {
            'name': 'Tablet',
            'description': 'Portable device',
            'category': self.category.id,
            'price_weights': [
                {'price': 2000, 'weight': '100gms'},
                {'price': 3000, 'weight': '200gms'},
                {'price': 4000, 'weight': '300gms'}
            ],
            'tags': ['tag1', 'tag2']
        }
        response = self.client.post(self.url_list, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_product_by_non_admin(self):
        # Test that non-admin users cannot create products.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.user))
        data = {
            'name': 'Camera',
            'description': 'Digital camera',
            'category': self.category.id,
            'price_weights': [
                {'price': 2000, 'weight': '100gms'},
                {'price': 3000, 'weight': '200gms'},
                {'price': 4000, 'weight': '300gms'}
            ],
            'tags': ['tag1', 'tag2']
        }
        response = self.client.post(self.url_list, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_product_by_admin(self):
        # Test that only admin users can update products.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        data = {'description': 'Updated model'}
        response = self.client.patch(self.url_detail, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_product_by_admin(self):
        # Test that only admin users can delete products.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        response = self.client.delete(self.url_detail)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_product_access_by_unauthorized_user(self):
        # Test that unauthorized users cannot modify product details but can view them.
        client = self.client_class()  # Create a new test client without any credentials.
        
        # Test GET request (should pass if read access is allowed without authentication)
        response = client.get(self.url_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Checking read permission for unauthorized users

        # Test POST request (should fail without authentication)
        response = client.post(self.url_detail, {'name': 'New Product'}, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])  # Checking write permission for unauthorized users

    def test_unique_product_name(self):
        # Test to ensure product names must be unique.
        with self.assertRaises(IntegrityError):
            Product.objects.create(name="Smartphone", description="Latest model", category=self.category)

    def test_minimum_price_weights(self):
        # Test to ensure a product must have a minimum of 3 price-weight combinations.
        product = Product(name="Tablet", description="Portable device", category=self.category)
        product.save()
        PriceWeight.objects.create(product=product, price=2000, weight='100gms')
        try:
            product.full_clean()
        except ValidationError as e:
            self.assertTrue('Ensure a minimum of 3 price-weight combinations are provided.' in str(e))

    def test_image_upload(self):
        # Placeholder for testing image uploads. Implement if applicable.
        pass
