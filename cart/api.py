# cart/api.py

from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Cart, CartItem
from .serializers import CartSerializer
from products.models import Product, PriceWeight
from django.utils import timezone
from django.core.exceptions import ValidationError

class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_cart(self, request):
        """
        Retrieve or create a cart for the authenticated user.
        Clears cart items if the cart is older than 30 days.
        """
        user = request.user
        cart, created = Cart.objects.get_or_create(user=user)
        # Optionally clear cart items if older than 30 days
        if not created and (timezone.now() - cart.updated_at).days > 30:
            cart.items.all().delete()
            cart.save()
        return cart

    @action(detail=False, methods=['get'])
    def retrieve_cart(self, request):
        """
        Retrieves the current user's cart.
        """
        cart = self.get_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def add_to_cart(self, request):
        """
        Adds a product to the authenticated user's cart.
        """
        cart = self.get_cart(request)
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        price_data = request.data.get('price_weight')

        # Input validation
        if not product_id or not price_data:
            return Response({'error': 'Product ID and price-weight data must be provided.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'Quantity must be a positive integer.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({'error': 'Product does not exist or is inactive.'},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            price_weight = PriceWeight.objects.get(
                product=product,
                price=price_data['price'],
                weight=price_data['weight']
            )
        except PriceWeight.DoesNotExist:
            return Response({'error': 'Selected price-weight combination does not exist.'},
                            status=status.HTTP_404_NOT_FOUND)

        if price_weight.inventory < quantity:
            return Response({'error': 'Insufficient stock available.'},
                            status=status.HTTP_400_BAD_REQUEST)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            selected_price_weight=price_weight
        )
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity

        try:
            cart_item.save()
        except ValidationError as e:
            return Response({'error': e.message_dict},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'Added to cart'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put'])
    def update_cart_item(self, request, pk=None):
        """
        Updates the quantity or price-weight combination of an item in the user's cart.
        """
        cart = self.get_cart(request)

        try:
            cart_item = CartItem.objects.get(pk=pk, cart=cart)
        except CartItem.DoesNotExist:
            return Response({'error': 'Cart item not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        quantity = request.data.get('quantity', cart_item.quantity)
        price_data = request.data.get('price_weight')

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'Quantity must be a positive integer.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if price_data:
            try:
                price_weight = PriceWeight.objects.get(
                    product=cart_item.product,
                    price=price_data['price'],
                    weight=price_data['weight']
                )
                cart_item.selected_price_weight = price_weight
            except PriceWeight.DoesNotExist:
                return Response({'error': 'Selected price-weight combination does not exist.'},
                                status=status.HTTP_404_NOT_FOUND)

        cart_item.quantity = quantity

        # Check inventory for the updated cart item
        if cart_item.selected_price_weight.inventory < cart_item.quantity:
            return Response({'error': 'Insufficient stock available.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            cart_item.save()
        except ValidationError as e:
            return Response({'error': e.message_dict},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'Cart item updated'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def delete_cart_item(self, request, pk=None):
        """
        Removes an item from the user's cart.
        """
        cart = self.get_cart(request)

        try:
            cart_item = CartItem.objects.get(pk=pk, cart=cart)
            cart_item.delete()
            return Response({'status': 'Cart item removed'},
                            status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response({'error': 'Cart item not found.'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def clear_cart(self, request):
        """
        Clears all items from the authenticated user's cart.
        """
        cart = self.get_cart(request)
        cart.items.all().delete()
        return Response({'status': 'Cart cleared'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def cart_summary(self, request):
        """
        Returns a summary of the cart.
        """
        cart = self.get_cart(request)
        total_price = sum(item.total_price for item in cart.items.all())
        item_count = cart.items.count()

        return Response({
            'total_price': total_price,
            'item_count': item_count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def validate_cart(self, request):
        """
        Validates the cart's inventory levels before proceeding to checkout.
        """
        cart = self.get_cart(request)
        insufficient_stock = []

        for item in cart.items.select_related('selected_price_weight', 'product'):
            if item.quantity > item.selected_price_weight.inventory:
                insufficient_stock.append(
                    f"{item.product.name} ({item.selected_price_weight.weight}) "
                    f"(Requested: {item.quantity}, Available: {item.selected_price_weight.inventory})"
                )

        if insufficient_stock:
            return Response({
                'error': 'Not enough stock for the following items',
                'details': insufficient_stock
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'Cart is valid'}, status=status.HTTP_200_OK)
