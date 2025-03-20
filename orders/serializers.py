from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductSerializer, PriceWeightComboSerializer
from users.serializers import AddressSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product = ProductSerializer(read_only=True)
    selected_price_weight = PriceWeightComboSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'selected_price_weight', 'quantity', 'unit_price', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    order_number = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'address', 'status', 'payment_status',
            'total_price', 'created_at', 'updated_at', 'items',
            'shipping_name', 'shipment_id', 'tracking_number', 'shipping_method',
            'carrier', 'estimated_delivery_date', 'shipping_cost'
        ]
        read_only_fields = [
            'order_number', 'total_price', 'created_at', 'updated_at', 'items',
            'shipping_name', 'shipment_id', 'tracking_number', 'shipping_method',
            'carrier', 'estimated_delivery_date', 'shipping_cost'
        ]
    
    def get_total_amount(self, obj):
        return obj.total_price

class OrderCreateSerializer(serializers.ModelSerializer):
    address_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Order
        fields = ['address_id']

    def create(self, validated_data):
        user = self.context['request'].user
        address_id = validated_data.pop('address_id')
        order = Order.objects.create(user=user, address_id=address_id)
        return order

class OrderHistorySerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = [
            'order_number', 'status', 'payment_status', 'total_price',
            'created_at', 'items'
        ]
