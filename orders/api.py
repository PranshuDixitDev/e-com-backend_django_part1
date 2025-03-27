"""
orders/api.py

This module contains helper functions for generating invoice PDFs and sending order confirmation
and cancellation emails, as well as the OrderViewSet which handles order-related API endpoints.
"""

from decimal import Decimal
from io import BytesIO
import logging

from django.db import transaction
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from orders.models import Order

from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

# ReportLab is used for PDF generation.
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import razorpay
from shipping.shiprocket_api import create_shipment
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

def calculate_gst(amount):
    """culate_gst(amount):
    Calculate GST at 18% for the given amount.
    Calculate GST at 18% for the given amount.
    Args:
    Args:
        amount (Decimal): The monetary amount.
    
    Returns:
        Decimal: The GST calculated to two decimal places.
    """
    gst_rate = Decimal('0.18')
    return (amount * gst_rate).quantize(Decimal('0.01'))


def generate_invoice_pdf(order):
    """
    Generate a PDF invoice for the given order using ReportLab.
    
    The invoice includes:
      - Company details (static)
      - Order details (order number, order date)
      - Shipping address (if provided)
      - A table listing each order item with product name, price/weight, quantity, unit price, and total
      - Totals, GST, and grand total calculations.
    
    Additionally, we set the PDF title (metadata) to include the order number, so that the
    order number appears in the generated PDF binary.
    
    Args:
        order (Order): The order instance for which the invoice is generated.
    
    Returns:
        bytes: The binary content of the generated PDF.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Set the document title with the order number for metadata.
    c.setTitle(f"Invoice - {order.order_number}")

    # Draw the invoice header.
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "Invoice")
    c.setFont("Helvetica", 12)
    # (Optionally, you can also print the company name here.)
    
    # Define static company details.
    company_name = "gujju_masala"
    company_address = "Ahmedabad, Gujarat, India"
    company_gstin = "27XXXXXXXXX"
    
    # Draw company details.
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 100, f"Address: {company_address}")
    c.drawString(50, height - 115, f"GSTIN: {company_gstin}")
    
    # Draw order details.
    c.drawString(50, height - 145, f"Order Number: {order.order_number}")
    c.drawString(50, height - 160, f"Order Date: {order.created_at.strftime('%b %d, %Y')}")
    
    # If an address is provided, print the shipping address.
    if order.address:
        addr = f"{order.address.address_line1}, {order.address.city}, {order.address.state}, {order.address.postal_code}, {order.address.country}"
        c.drawString(50, height - 175, f"Shipping Address: {addr}")
    
    # Draw table headers for order items.
    y = height - 220
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Product")
    c.drawString(200, y, "Price/Weight")
    c.drawString(300, y, "Quantity")
    c.drawString(370, y, "Unit Price")
    c.drawString(450, y, "Total")
    y -= 15

    # Iterate over each order item and print its details.
    for item in order.items.all():
        c.setFont("Helvetica", 10)
        c.drawString(50, y, item.product.name)
        c.drawString(200, y, item.selected_price_weight.weight)
        c.drawString(300, y, str(item.quantity))
        c.drawString(370, y, str(item.unit_price))
        c.drawString(450, y, str(item.total_price))
        y -= 15

    # Draw totals: Subtotal, GST, and Grand Total.
    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(370, y, "Subtotal:")
    c.drawString(450, y, f"₹{order.total_price}")
    y -= 15
    gst_amount = calculate_gst(order.total_price)
    grand_total = (order.total_price + gst_amount).quantize(Decimal('0.01'))
    c.drawString(370, y, "GST (18%):")
    c.drawString(450, y, f"₹{gst_amount}")
    y -= 15
    c.drawString(370, y, "Grand Total:")
    c.drawString(450, y, f"₹{grand_total}")

    # Finalize the PDF.
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def send_order_confirmation_email(order, invoice_pdf):
    """
    Send an order confirmation email with the generated PDF invoice attached.
    
    The email renders an HTML template ('order_confirmation_email.html') with context including
    the order, GST, grand total, and current timestamp.
    
    Args:
        order (Order): The order instance.
        invoice_pdf (bytes): The generated PDF invoice as bytes.
    """
    subject = f"Order Confirmation - {order.order_number}"
    context = {
         'order': order,
         'gst_amount': calculate_gst(order.total_price),
         'grand_total': (order.total_price + calculate_gst(order.total_price)).quantize(Decimal('0.01')),
         'now': timezone.now(),
    }
    # Render the email HTML content using the provided template.
    html_content = render_to_string('order_confirmation_email.html', context)
    text_content = f"Your order {order.order_number} has been confirmed. Please find the attached invoice."
    email = EmailMultiAlternatives(
         subject=subject,
         body=text_content,
         from_email=settings.DEFAULT_FROM_EMAIL,
         to=[order.user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.attach(f"invoice_{order.order_number}.pdf", invoice_pdf, "application/pdf")
    email.send()


def send_order_cancellation_email(order):
    """
    Send an order cancellation email using the 'order_cancellation_email.html' template.
    
    Args:
        order (Order): The order instance that was cancelled.
    """
    subject = f"Order Cancellation - {order.order_number}"
    context = {
         'order': order,
         'now': timezone.now(),
    }
    html_content = render_to_string('order_cancellation_email.html', context)
    text_content = f"Your order {order.order_number} has been cancelled."
    email = EmailMultiAlternatives(
         subject=subject,
         body=text_content,
         from_email=settings.DEFAULT_FROM_EMAIL,
         to=[order.user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


class OrderViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for handling order-related actions such as checkout, order history retrieval,
    order detail retrieval, and order cancellation.
    
    Methods:
      - checkout: Create an order from the user's cart, process payment, send confirmation, and clear the cart.
      - history: Retrieve the authenticated user's order history.
      - detail: Retrieve details of a specific order.
      - cancel: Cancel an order that is in a cancellable state.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_order(self, request, order_number=None):
         """
         Retrieve an order by order number for the authenticated user.
         
         Args:
             request: The HTTP request.
             order_number (str): The unique order number.
         
         Returns:
             Order instance if found; otherwise, None.
         """
         from orders.models import Order
         try:
              return Order.objects.get(order_number=order_number, user=request.user)
         except Order.DoesNotExist:
              return None

    @action(detail=False, methods=['post'])
    def checkout(self, request):
         """
         Checkout endpoint: creates an order from the user's cart, processes payment, generates a PDF invoice,
         sends a confirmation email, integrates with Shiprocket for shipment creation, and clears the cart.
         
         The request data should include:
           - address_id: integer, the ID of the shipping address.
           - payment_data: a dictionary; if it contains "simulate_failure": True, payment will be simulated as failed.
           - Optional shipping details (e.g., shipping_name, shipping_method, carrier, estimated_delivery_date, shipping_cost)
             are mapped from the request for additional information.
         
         Returns:
             JSON response with the serialized order data and HTTP status 201 if successful,
             or an error message with HTTP status 400 if there is an issue.
         """
         from orders.models import Order, OrderItem
         from orders.serializers import OrderCreateSerializer, OrderSerializer
         try:
              from cart.models import Cart
              cart = Cart.objects.get(user=request.user)
              if cart.items.count() == 0:
                  return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)
         except Exception as e:
              logger.error(f"Cart retrieval error: {e}")
              return Response({'error': 'No cart found for the user.'}, status=status.HTTP_400_BAD_REQUEST)
         
         # Validate the incoming data and create the Order.
         serializer = OrderCreateSerializer(data=request.data, context={'request': request})
         serializer.is_valid(raise_exception=True)
         
         with transaction.atomic():
              order = serializer.save()
              # Map additional shipping details if provided in request.data (exclude fields set by Shiprocket)
              shipping_fields = ['shipping_name', 'shipping_method', 'carrier', 'estimated_delivery_date', 'shipping_cost']
              for field in shipping_fields:
                  if field in request.data:
                      setattr(order, field, request.data[field])
              order.save()
              
              for cart_item in cart.items.all():
                   # Check inventory before adding item.
                   if cart_item.quantity > cart_item.selected_price_weight.inventory:
                        return Response(
                             {'error': f'Insufficient stock for product {cart_item.product.name}'},
                             status=status.HTTP_400_BAD_REQUEST
                        )
                   OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        selected_price_weight=cart_item.selected_price_weight,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.selected_price_weight.price
                   )
                   # Deduct inventory.
                   price_weight = cart_item.selected_price_weight
                   price_weight.inventory = max(0, price_weight.inventory - cart_item.quantity)
                   price_weight.save()
              # Simulate payment processing.
              payment_data = request.data.get('payment_data', {})
              if payment_data.get("simulate_failure", False):
                   payment_success = False
              else:
                    try:
                         razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                         total_in_paise = int(order.total_price * 100)
                         razorpay_order = razorpay_client.order.create({
                              'amount': total_in_paise,
                              'currency': 'INR',
                              'receipt': order.order_number
                         })
                         order.razorpay_order_id = razorpay_order['id']
                         payment_success = True
                    except Exception as e:
                         logger.error(f"Razorpay order creation failed: {e}")
                         payment_success = False
              if payment_success:
                   order.payment_status = 'COMPLETED'
                   order.status = 'PROCESSING'
              else:
                   order.payment_status = 'FAILED'
                   order.status = 'CANCELLED'
              order.save()
              
              if payment_success:
                  # --- Begin Shiprocket Integration ---
                  shipment_payload = {
                      "order_id": order.order_number,
                      "order_date": order.created_at.strftime('%Y-%m-%d'),
                      "pickup_location": {
                          "name": "Your Warehouse Name",
                          "address": "Your Warehouse Address",
                          "city": "Your City",
                          "pincode": "Your Pincode",
                          "state": "Your State",
                          "country": "Your Country"
                      },
                      "billing_customer_name": order.user.get_full_name(),
                      "billing_last_name": "",
                      "billing_address": order.address.address_line1,
                      "billing_city": order.address.city,
                      "billing_pincode": order.address.postal_code,
                      "billing_state": order.address.state,
                      "billing_country": order.address.country,
                      "shipping_is_billing": True
                      # Add any additional fields required by Shiprocket
                  }
                  try:
                      # Use the module-level imported create_shipment function
                      shipment_response = create_shipment(shipment_payload)
                      order.shipment_id = shipment_response.get('shipment_id')
                      order.save()
                  except Exception as e:
                      logger.error(f"Shiprocket shipment creation failed: {e}")
                  # --- End Shiprocket Integration ---
              
              # Generate invoice PDF and send confirmation email if payment succeeded.
              invoice_pdf = generate_invoice_pdf(order)
              if payment_success:
                   send_order_confirmation_email(order, invoice_pdf)
              # Clear the cart after checkout.
              cart.items.all().delete()
         return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def history(self, request):
         """
         Retrieve the authenticated user's order history.
         
         Returns:
             JSON response containing a list of orders.
         """
         from orders.models import Order
         from orders.serializers import OrderHistorySerializer
         orders = Order.objects.filter(user=request.user).order_by('-created_at')
         serializer = OrderHistorySerializer(orders, many=True)
         return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='detail/(?P<order_number>[^/.]+)')
    def detail(self, request, order_number=None):
         """
         Retrieve details for a specific order by order number.
         
         Args:
             order_number (str): The unique order number.
         
         Returns:
             JSON response with the order details or an error message if not found.
         """
         from orders.serializers import OrderSerializer
         order = self.get_order(request, order_number)
         if not order:
              return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
         serializer = OrderSerializer(order)
         return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='cancel/(?P<order_number>[^/.]+)')
    def cancel(self, request, order_number=None):
         """
         Cancel an order if it is in a cancellable state (PENDING or PROCESSING) and send a cancellation email.
         
         Args:
             order_number (str): The unique order number.
         
         Returns:
             JSON response confirming cancellation or an error message.
         """
         from orders.models import Order
         order = self.get_order(request, order_number)
         if not order:
              return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
         if order.status not in ['PENDING', 'PROCESSING']:
              return Response({'error': 'Order cannot be cancelled at this stage.'}, status=status.HTTP_400_BAD_REQUEST)
         order.status = 'CANCELLED'
         order.payment_status = 'FAILED'
         order.save()
         send_order_cancellation_email(order)
         return Response({'status': 'Order cancelled successfully.'}, status=status.HTTP_200_OK)

    @transaction.atomic
    def checkout_for_order_creation(self, request):
        """
        Handles the creation of an order during checkout.

        This method processes shipping data, creates an order, and integrates with the shipment API.
        """
        shipping_data = {
            'shipping_name': request.data.get('shipping_name'),
            'shipping_method': request.data.get('shipping_method'),
            'carrier': request.data.get('carrier'),
            'estimated_delivery_date': request.data.get('estimated_delivery_date'),
            'shipping_cost': request.data.get('shipping_cost', '0.00')
        }
        try:
            order = Order.objects.create(user=request.user)
            order.process_shipping(shipping_data, create_shipment_fn=create_shipment)
            return Response(self.get_serializer(order).data, status=201)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({'error': str(e)}, status=400)