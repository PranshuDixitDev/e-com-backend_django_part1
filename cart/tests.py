# cart/tests.py

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser
from products.models import Product, PriceWeight, Category
from cart.models import Cart, CartItem
from decimal import Decimal

class CartAPITestCase(TestCase):
    def setUp(self):
        # Initialize APIClient
        self.client = APIClient()
        
        # Create a test user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpassword',
            email='testuser@example.com'
        )
        
        # Authenticate the client using JWT
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'testuser', 'password': 'testpassword'},
            format='json'
        )
        self.access_token = response.data.get('access')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        
        # Create a category
        self.category = Category.objects.create(name='Electronics')
        
        # Create a product
        self.product = Product.objects.create(
            name='Smartphone',
            category=self.category,
            is_active=True
        )
        
        # Create a PriceWeight with reduced inventory for testing
        self.price_weight = PriceWeight.objects.create(
            product=self.product,
            price=Decimal('599.99'),
            weight='200g',
            inventory=10  # Reduced inventory
        )
        
        # Create a second PriceWeight for distinct cart items
        self.price_weight_2 = PriceWeight.objects.create(
            product=self.product,
            price=Decimal('699.99'),
            weight='250g',
            inventory=30
        )
        
        # Ensure the cart exists
        self.cart, created = Cart.objects.get_or_create(user=self.user)
    
    def test_retrieve_cart_empty(self):
        """
        Test retrieving an empty cart.
        """
        url = reverse('cart-retrieve-cart')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Retrieve the cart instance
        cart = Cart.objects.get(user=self.user)
        
        self.assertEqual(response.data['cart_id'], cart.id)
        self.assertEqual(len(response.data['items']), 0)
    
    def test_add_to_cart_success(self):
        """
        Test adding a product to the cart successfully.
        """
        url = reverse('cart-add-to-cart')
        data = {
            "product_id": self.product.id,
            "quantity": 2,
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'Added to cart')
        
        # Verify in database
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        cart_item = cart.items.first()
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.selected_price_weight, self.price_weight)
    
    def test_add_to_cart_insufficient_stock(self):
        """
        Test adding a product to the cart with quantity exceeding inventory.
        """
        url = reverse('cart-add-to-cart')
        data = {
            "product_id": self.product.id,
            "quantity": 100,  # Exceeds inventory of 10
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Insufficient stock available.')
    
    def test_update_cart_item_success(self):
        """
        Test updating a cart item successfully.
        """
        # First, add to cart
        add_url = reverse('cart-add-to-cart')
        add_data = {
            "product_id": self.product.id,
            "quantity": 2,
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        self.client.post(add_url, add_data, format='json')
        
        # Get the cart item
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.first()
        
        # Update the cart item
        update_url = reverse('cart-update-cart-item', args=[cart_item.id])
        update_data = {
            "quantity": 5,  # Update quantity within inventory
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        response = self.client.put(update_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'Cart item updated')
        
        # Verify in database
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)
    
    def test_update_cart_item_insufficient_stock(self):
        """
        Test updating a cart item with quantity exceeding inventory.
        """
        # First, add to cart
        add_url = reverse('cart-add-to-cart')
        add_data = {
            "product_id": self.product.id,
            "quantity": 2,
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        self.client.post(add_url, add_data, format='json')
        
        # Get the cart item
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.first()
        
        # Attempt to update with insufficient stock
        update_url = reverse('cart-update-cart-item', args=[cart_item.id])
        update_data = {
            "quantity": 15,  # Exceeds inventory of 10
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        response = self.client.put(update_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Insufficient stock available.')
    
    def test_delete_cart_item_success(self):
        """
        Test deleting a cart item successfully.
        """
        # First, add to cart
        add_url = reverse('cart-add-to-cart')
        add_data = {
            "product_id": self.product.id,
            "quantity": 2,
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        self.client.post(add_url, add_data, format='json')
        
        # Get the cart item
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.first()
        
        # Delete the cart item
        delete_url = reverse('cart-delete-cart-item', args=[cart_item.id])
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify in database
        self.assertEqual(CartItem.objects.filter(id=cart_item.id).count(), 0)
    
    def test_delete_cart_item_not_found(self):
        """
        Test deleting a non-existent cart item.
        """
        delete_url = reverse('cart-delete-cart-item', args=[999])  # Assuming ID 999 doesn't exist
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Cart item not found.')
    
    def test_clear_cart(self):
        """
        Test clearing all items from the cart.
        """
        # Add two distinct items to cart
        add_url = reverse('cart-add-to-cart')
        data1 = {
            "product_id": self.product.id,
            "quantity": 2,
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        data2 = {
            "product_id": self.product.id,
            "quantity": 3,
            "price_weight": {
                "price": "699.99",
                "weight": "250g"
            }
        }
        self.client.post(add_url, data1, format='json')
        self.client.post(add_url, data2, format='json')
        
        # Clear the cart
        clear_url = reverse('cart-clear-cart')
        response = self.client.post(clear_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'Cart cleared')
        
        # Verify in database
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)
    
    def test_cart_summary(self):
        """
        Test retrieving the cart summary with two distinct items.
        """
        # Add two distinct items to cart
        add_url = reverse('cart-add-to-cart')
        data1 = {
            "product_id": self.product.id,
            "quantity": 2,
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        data2 = {
            "product_id": self.product.id,
            "quantity": 3,
            "price_weight": {
                "price": "699.99",
                "weight": "250g"
            }
        }
        self.client.post(add_url, data1, format='json')
        self.client.post(add_url, data2, format='json')
        
        # Get cart summary
        summary_url = reverse('cart-cart-summary')
        response = self.client.get(summary_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['total_price']), '3299.95')  # Updated expected total
        self.assertEqual(response.data['item_count'], 2)
    
    def test_validate_cart_success(self):
        """
        Test validating the cart when inventory is sufficient.
        """
        # Add items within inventory limits
        add_url = reverse('cart-add-to-cart')
        data = {
            "product_id": self.product.id,
            "quantity": 5,  # Within inventory of 10
            "price_weight": {
                "price": "599.99",
                "weight": "200g"
            }
        }
        self.client.post(add_url, data, format='json')
        
        # Validate the cart
        validate_url = reverse('cart-validate-cart')
        response = self.client.post(validate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'Cart is valid')
    
    def test_validate_cart_insufficient_stock(self):
        """
        Test validating the cart when inventory is insufficient.
        """
        # Manually create a cart item with quantity exceeding inventory
        cart = Cart.objects.get(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            selected_price_weight=self.price_weight,
            quantity=15  # Exceeds inventory of 10
        )
        
        # Validate the cart
        validate_url = reverse('cart-validate-cart')
        response = self.client.post(validate_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Not enough stock for the following items', response.data['error'])
        self.assertIn(
            'Smartphone (200g) (Requested: 15, Available: 10)',
            response.data['details']
        )
