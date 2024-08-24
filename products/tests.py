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
from django.core.files.uploadedfile import SimpleUploadedFile
import io
import csv
from io import BytesIO
import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile

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


class BulkUploadProductsTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Setup data that is used across multiple test methods.
        cls.category = Category.objects.create(category_id="001", name="Electronics", description="Electronic items")
        cls.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass',
            phone_number='+0987654321'
        )
        cls.url_bulk_upload = reverse('bulk-upload-products')

    def get_tokens_for_user(self, user):
        # Helper method to generate JWT tokens for users.
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_bulk_upload_products_by_admin(self):
        # Test that an admin user can bulk upload products.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        
        # Create a CSV file in memory
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['name', 'description', 'category_id', 'inventory', 'price_weights'])
        writer.writerow(['Smartphone', 'Latest model', '001', '50', '2000-100gms,3000-200gms,4000-300gms'])
        writer.writerow(['Tablet', 'Portable device', '001', '30', '2000-100gms,3000-200gms,4000-300gms'])
        csv_file.seek(0)
        
        upload_file = SimpleUploadedFile("products.csv", csv_file.getvalue().encode())
        
        response = self.client.post(self.url_bulk_upload, {'file': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

    def test_bulk_upload_with_invalid_category(self):
        # Test that bulk upload fails with an invalid category.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        
        # Create a CSV file in memory
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['name', 'description', 'category_id', 'inventory', 'price_weights'])
        writer.writerow(['Smartphone', 'Latest model', '999', '50', '2000-100gms,3000-200gms,4000-300gms'])  # Invalid category_id
        csv_file.seek(0)
        
        upload_file = SimpleUploadedFile("products.csv", csv_file.getvalue().encode())
        
        response = self.client.post(self.url_bulk_upload, {'file': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Category with ID 999 does not exist.", response.data['error'])

    def test_bulk_upload_with_duplicate_product_name(self):
        # Test that bulk upload fails if a product with the same name already exists.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        
        # Create an existing product
        Product.objects.create(
            name="Smartphone",
            description="Latest model",
            category=self.category,
            inventory=50
        )
        
        # Create a CSV file in memory
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['name', 'description', 'category_id', 'inventory', 'price_weights'])
        writer.writerow(['Smartphone', 'Latest model', '001', '50', '2000-100gms,3000-200gms,4000-300gms'])  # Duplicate product name
        csv_file.seek(0)
        
        upload_file = SimpleUploadedFile("products.csv", csv_file.getvalue().encode())
        
        response = self.client.post(self.url_bulk_upload, {'file': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Product with name Smartphone already exists.", response.data['error'])

    def test_bulk_upload_by_non_admin(self):
        # Test that non-admin users cannot bulk upload products.
        user = User.objects.create_user(
            username='user', 
            password='pass',
            phone_number='+1234567890'
        )
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(user))
        
        # Create a CSV file in memory
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['name', 'description', 'category_id', 'inventory', 'price_weights'])
        writer.writerow(['Smartphone', 'Latest model', '001', '50', '2000-100gms,3000-200gms,4000-300gms'])
        csv_file.seek(0)
        
        upload_file = SimpleUploadedFile("products.csv", csv_file.getvalue().encode())
        
        response = self.client.post(self.url_bulk_upload, {'file': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

# Excel bulk upload:

    def test_bulk_upload_products_by_admin_with_excel(self):
        # Test that an admin user can bulk upload products using an Excel file.
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))

        # Create a DataFrame
        data = pd.DataFrame({
            'name': ['Smartphone', 'Tablet'],
            'description': ['Latest model', 'Portable device'],
            'category_id': ['001', '001'],
            'inventory': [50, 30],
            'price_weights': ['2000-100gms,3000-200gms,4000-300gms', '1000-50gms,1500-75gms,2500-125gms']
        })

        # Save DataFrame to an Excel file in memory
        excel_file = BytesIO()
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            data.to_excel(writer, index=False)
            writer.close()  # Correct method to finalize and save the file

        excel_file.seek(0)

        # Create an InMemoryUploadedFile
        upload_file = InMemoryUploadedFile(
            excel_file, None, "products.xlsx", 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            excel_file.getbuffer().nbytes, None
        )

        # Upload the file
        response = self.client.post(self.url_bulk_upload, {'file': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)  # Assuming you're checking the total number of products after the upload

    def test_bulk_upload_empty_file(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        
        empty_csv = io.StringIO()  # create an empty CSV file
        writer = csv.writer(empty_csv)
        writer.writerow(['name', 'description', 'category_id', 'inventory', 'price_weights'])  # only headers
        empty_csv.seek(0)
        
        upload_file = SimpleUploadedFile("empty.csv", empty_csv.getvalue().encode())
        
        response = self.client.post(self.url_bulk_upload, {'file': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No data found in file.", response.data['error'])

    def test_bulk_upload_integration(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.get_tokens_for_user(self.admin))
        
        csv_file = io.StringIO()
       
        writer = csv.writer(csv_file)
        writer.writerow(['name', 'description', 'category_id', 'inventory', 'price_weights'])
        writer.writerow(['NewProduct', 'A new product', '001', '100', '500-50gms,700-75gms,900-100gms'])
        csv_file.seek(0)
        
        upload_file = SimpleUploadedFile("integration.csv", csv_file.getvalue().encode())
        response = self.client.post(self.url_bulk_upload, {'file': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.filter(name='NewProduct').count(), 1)
       
        new_product = Product.objects.get(name='NewProduct')
        self.assertEqual(new_product.inventory, 100)
        self.assertTrue(PriceWeight.objects.filter(product=new_product).count() > 0)


class ProductInventoryAdjustmentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Gadgets")
        cls.admin = User.objects.create_superuser(username='admin', password='adminpass')
        cls.product = Product.objects.create(
            name="Gadget",
            description="High-tech gadget",
            category=cls.category,
            inventory=100
        )
        cls.url_adjust_inventory = reverse('product-adjust-inventory', kwargs={'pk': cls.product.id})
        cls.url_list = reverse('product-list')  # Correctly setting the URL for listing/creating products
        cls.admin_token = RefreshToken.for_user(cls.admin).access_token

    def test_adjust_inventory_below_threshold(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        new_inventory = 4  # Below the threshold of 5
        response = self.client.post(self.url_adjust_inventory, {'new_inventory': new_inventory}, format='json')

        # Check response status and low stock warning
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('low_stock_warning', response.data)
        self.assertEqual(response.data['low_stock_warning'], f"Warning: Low stock for Gadget. Only {new_inventory} items left.")

    def test_adjust_inventory_above_threshold(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        new_inventory = 6  # Above the threshold of 5
        response = self.client.post(self.url_adjust_inventory, {'new_inventory': new_inventory}, format='json')

        # Check response status and absence of low stock warning
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('low_stock_warning', response.data)
        self.assertEqual(Product.objects.get(id=self.product.id).inventory, new_inventory)

    def test_adjust_inventory_to_threshold(self):
        # Adjust inventory to exactly the threshold (5)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        new_inventory = 5  # Exactly at threshold
        response = self.client.post(self.url_adjust_inventory, {'new_inventory': new_inventory}, format='json')

        # Check response status and that low stock warning is given
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('low_stock_warning', response.data)
        self.assertEqual(response.data['low_stock_warning'], f"Warning: Low stock for Gadget. Only {new_inventory} items left.")


    def test_adjust_inventory_to_zero(self):
        # Ensure proper handling when inventory is set to 0
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(self.url_adjust_inventory, {'new_inventory': 0}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('low_stock_warning', response.data)
        self.assertEqual(response.data['low_stock_warning'], "Warning: Low stock for Gadget. Only 0 items left.")


    def test_invalid_inventory_input(self):
        # Test providing invalid input for inventory (negative values)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(self.url_adjust_inventory, {'new_inventory': -1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Inventory cannot be negative.")

    
    def test_existing_functionality_after_changes(self):
        # Ensure product creation works after adjusting inventory logic
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        data = {
            'name': 'Tablet',
            'description': 'A new tablet',
            'category': self.category.id,
            'tags': ['tag1', 'tag2'],  # Add required tags
            'price_weights': [
                {'price': 2000, 'weight': '100gms'},
                {'price': 3000, 'weight': '200gms'},
                {'price': 4000, 'weight': '300gms'}
            ]  # Add required price_weights
        }
        response = self.client.post(self.url_list, data, format='json')

        # Check for detailed error information if creation fails
        if response.status_code != status.HTTP_201_CREATED:
            print("Error creating product:", response.data)

        # Assert that the product was created successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_product_lifecycle(self):
        # Create product, adjust inventory, and verify low stock warning.
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        product_data = {
            'name': 'Camera',
            'description': 'Digital Camera',
            'category': self.category.id,
            'tags': ['tag1', 'tag2'],
            'price_weights': [
                {'price': 2000, 'weight': '100gms'},
                {'price': 3000, 'weight': '200gms'},
                {'price': 4000, 'weight': '300gms'}
            ]
        }

        # Attempt to create product
        response = self.client.post(self.url_list, product_data, format='json')

        # Log the full response for debugging
        print("Product creation response:", response.data)

        # Check for detailed error information if creation fails
        if response.status_code != status.HTTP_201_CREATED:
            print("Error creating product:", response.data)

        # Assert that the product was created successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Ensure the response contains the 'id' field
        self.assertIn('id', response.data)

        # If the product was successfully created, retrieve the product_id
        product_id = response.data['id']

        # Adjust inventory and check for low stock warning
        adjust_url = reverse('product-adjust-inventory', kwargs={'pk': product_id})
        response = self.client.post(adjust_url, {'new_inventory': 3}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('low_stock_warning', response.data)


class ProductCreationEdgeCaseTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Gadgets")
        cls.admin = User.objects.create_superuser(username='admin', password='adminpass')
        cls.url_list = reverse('product-list')
        cls.admin_token = str(RefreshToken.for_user(cls.admin).access_token)

    def test_create_product_without_tags(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        product_data = {
            'name': 'Camera',
            'description': 'Digital Camera',
            'category': self.category.id,
            'price_weights': [
                {'price': '2000.00', 'weight': '100gms'},
                {'price': '3000.00', 'weight': '200gms'},
                {'price': '4000.00', 'weight': '300gms'}
            ],
            # Missing tags
        }
        response = self.client.post(self.url_list, product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Tags are required, so it should fail

    def test_create_product_without_price_weights(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        product_data = {
            'name': 'Phone',
            'description': 'Smartphone',
            'category': self.category.id,
            'tags': ['tag1', 'tag2'],
            # Missing price weights
        }
        response = self.client.post(self.url_list, product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expect failure since price weights are required

    def test_create_product_with_invalid_price_weight(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        product_data = {
            'name': 'Tablet',
            'description': 'A new tablet',
            'category': self.category.id,
            'tags': ['tag1', 'tag2'],
            'price_weights': [
                {'price': '-1000.00', 'weight': '100gms'}  # Invalid price
            ]
        }
        response = self.client.post(self.url_list, product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('price', response.data['price_weights'][0])  # Adjusting to the correct nesting

