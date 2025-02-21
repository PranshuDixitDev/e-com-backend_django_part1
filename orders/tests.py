from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from django.core import mail
from django.utils import timezone

from orders.models import Order, OrderItem
from cart.models import Cart, CartItem
from products.models import Product, PriceWeight, Category
from users.models import CustomUser, Address
from orders.api import (
    generate_invoice_pdf,
    send_order_confirmation_email,
    send_order_cancellation_email,
)
from orders.api import OrderViewSet
from django.db import transaction

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class TestOrderLifecycle(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpassword',
            email='testuser@example.com',
            phone_number='+911234567890',
            birthdate="1990-01-01"
        )
        self.client.force_authenticate(user=self.user)
        self.address = Address.objects.create(
            user=self.user,
            address_line1="123 Test St",
            address_line2="Apt 4",
            city="Test City",
            state="Test State",
            country="India",
            postal_code="123456"
        )
        self.category = Category.objects.create(
            name='Electronics',
            description='Test Category',
            image='dummy.jpg'
        )
        self.product = Product.objects.create(
            name='Smartphone',
            category=self.category,
            is_active=True
        )
        self.price_weight = PriceWeight.objects.create(
            product=self.product,
            price=Decimal('599.99'),
            weight='200g',
            inventory=10
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            selected_price_weight=self.price_weight,
            quantity=2
        )

    def create_sample_order(self):
        """
        Helper method to create a sample order with one order item.
        """
        order = Order.objects.create(user=self.user, address=self.address)
        OrderItem.objects.create(
            order=order,
            product=self.product,
            selected_price_weight=self.price_weight,
            quantity=1,
            unit_price=self.price_weight.price
        )
        return order

    def test_invoice_generation_function(self):
        """
        Test that the PDF invoice is generated and contains the order number.
        Instead of looking for the full "Order Number:" line (which might be hard to extract from PDF binary),
        we now check that the order number itself is present.
        """
        order = self.create_sample_order()
        invoice_pdf = generate_invoice_pdf(order)
        self.assertIsInstance(invoice_pdf, bytes)
        self.assertTrue(invoice_pdf.startswith(b'%PDF'))
        # Check that the order number appears somewhere in the PDF (either drawn or in metadata)
        expected_text = order.order_number.encode()
        self.assertIn(expected_text, invoice_pdf)

    def test_checkout_and_inventory_deduction(self):
        """Test checkout process: order creation, inventory deduction, email sending, and cart clearance."""
        checkout_url = reverse('checkout')
        data = {
            'address_id': self.address.id,
            'payment_data': {"dummy": "data"}
        }
        response = self.client.post(checkout_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_number = response.data.get('order_number')
        self.assertIsNotNone(order_number)
        order = Order.objects.get(order_number=order_number)
        self.price_weight.refresh_from_db()
        self.assertEqual(self.price_weight.inventory, 8)
        self.assertEqual(self.cart.items.count(), 0)
        self.assertGreaterEqual(len(mail.outbox), 1)
        confirmation_email = mail.outbox[0]
        self.assertIn(order_number, confirmation_email.subject)
        self.assertTrue(confirmation_email.attachments)

    def test_order_cancellation(self):
        """Test that an order can be cancelled and that a cancellation email is sent."""
        checkout_url = reverse('checkout')
        data = {
            'address_id': self.address.id,
            'payment_data': {"dummy": "data"}
        }
        checkout_response = self.client.post(checkout_url, data, format='json')
        order_number = checkout_response.data.get('order_number')
        self.assertIsNotNone(order_number)
        cancel_url = reverse('cancel_order', kwargs={'order_number': order_number})
        cancel_response = self.client.post(cancel_url)
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.data.get('status'), 'Order cancelled successfully.')
        self.assertGreaterEqual(len(mail.outbox), 2)
        cancellation_email = mail.outbox[-1]
        self.assertIn('Cancellation', cancellation_email.subject)

    def test_order_history_retrieval(self):
        """Test that order history retrieval returns at least one order."""
        checkout_url = reverse('checkout')
        data = {
            'address_id': self.address.id,
            'payment_data': {"dummy": "data"}
        }
        self.client.post(checkout_url, data, format='json')
        history_url = reverse('order_history')
        response = self.client.get(history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_order_state_transitions(self):
        """Test various state transitions of an order."""
        order = Order.objects.create(user=self.user, address=self.address)
        self.assertEqual(order.status, 'PENDING')
        order.payment_status = 'COMPLETED'
        order.status = 'PROCESSING'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, 'PROCESSING')
        order.status = 'SHIPPED'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, 'SHIPPED')
        cancel_url = reverse('cancel_order', kwargs={'order_number': order.order_number})
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_processing_failure(self):
        """Simulate a payment failure during checkout."""
        checkout_url = reverse('checkout')
        data = {
            'address_id': self.address.id,
            'payment_data': {"simulate_failure": True}
        }
        response = self.client.post(checkout_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(order_number=response.data.get('order_number'))
        self.assertEqual(order.payment_status, 'FAILED')
        self.assertEqual(order.status, 'CANCELLED')

    def test_inventory_deduction_edge_case(self):
        """Test checkout when cart quantity exceeds available inventory."""
        self.cart_item.quantity = 15
        self.cart_item.save()
        checkout_url = reverse('checkout')
        data = {
            'address_id': self.address.id,
            'payment_data': {"dummy": "data"}
        }
        response = self.client.post(checkout_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient stock', str(response.data))

    def test_email_sending_functionality(self):
        """Test that the order confirmation email is sent with the correct subject."""
        order = Order.objects.create(user=self.user, address=self.address)
        OrderItem.objects.create(
            order=order,
            product=self.product,
            selected_price_weight=self.price_weight,
            quantity=1,
            unit_price=self.price_weight.price
        )
        invoice_pdf = generate_invoice_pdf(order)
        send_order_confirmation_email(order, invoice_pdf)
        self.assertGreaterEqual(len(mail.outbox), 1)
        email = mail.outbox[-1]
        self.assertIn("Order Confirmation", email.subject)

    def test_error_handling_empty_cart(self):
        """Test that checkout returns an error when the cart is empty."""
        self.cart.items.all().delete()
        checkout_url = reverse('checkout')
        data = {
            'address_id': self.address.id,
            'payment_data': {"dummy": "data"}
        }
        response = self.client.post(checkout_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cart is empty', str(response.data))