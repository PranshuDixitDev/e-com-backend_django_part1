# cart/serializers.py

from rest_framework import serializers
from .models import Cart, CartItem
from products.serializers import PriceWeightComboSerializer, ProductImageSerializer

class CartItemSerializer(serializers.ModelSerializer):
    cart_item_id = serializers.IntegerField(source='id')
    product = serializers.SerializerMethodField()
    selected_price_weight = PriceWeightComboSerializer()
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            'cart_item_id', 'product', 'selected_price_weight',
            'quantity', 'total_price'
        ]

    def get_product(self, obj):
        product = obj.product
        return {
            'product_id': product.id,
            'name': product.name,
            'category_id': product.category.id,
            'inventory': product.inventory,
            'images': ProductImageSerializer(
                product.images.all(), many=True
            ).data,
            'is_active': product.is_active,
            'status': "In stock" if product.inventory > 0 else "Out of stock"
        }

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)
    cart_id = serializers.IntegerField(source='id')

    class Meta:
        model = Cart
        fields = ['cart_id', 'items', 'created_at', 'updated_at']
