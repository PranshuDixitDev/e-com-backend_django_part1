from rest_framework import serializers
from .models import (
    UserActivityLog, OrderAnalytics, SearchAnalytics,
    ProductAnalytics, ConversionFunnel, CartAbandonmentAnalytics,
    CustomerLifetimeValue, SalesMetrics
)


class UserActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivityLog
        fields = [
            'id', 'user', 'user_email', 'user_name', 'activity_type', 
            'timestamp', 'ip_address', 'details'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class OrderAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAnalytics
        fields = [
            'id', 'date', 'total_orders', 'total_revenue', 
            'avg_order_value', 'shipping_revenue'
        ]
        read_only_fields = ['id']


class SearchAnalyticsSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = SearchAnalytics
        fields = [
            'id', 'query', 'user', 'user_email', 'date', 'timestamp', 
            'results_count', 'search_count', 'click_through_rate', 
            'category', 'category_name'
        ]
        read_only_fields = ['id', 'timestamp']


class ProductAnalyticsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = ProductAnalytics
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'date',
            'views', 'cart_additions', 'purchases', 'revenue',
            'conversion_rate', 'cart_to_purchase_rate'
        ]
        read_only_fields = ['id']


class ConversionFunnelSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    
    class Meta:
        model = ConversionFunnel
        fields = [
            'id', 'user', 'user_email', 'session_id', 'stage', 'stage_display',
            'product', 'product_name', 'timestamp', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']


class CartAbandonmentAnalyticsSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    abandonment_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = CartAbandonmentAnalytics
        fields = [
            'id', 'user', 'user_email', 'session_id', 'cart_created',
            'cart_abandoned', 'cart_value', 'items_count', 'abandonment_stage',
            'recovery_email_sent', 'recovered', 'recovery_date', 'abandonment_duration'
        ]
        read_only_fields = ['id', 'cart_abandoned']
    
    def get_abandonment_duration(self, obj):
        """Calculate time between cart creation and abandonment in minutes"""
        if obj.cart_created and obj.cart_abandoned:
            duration = obj.cart_abandoned - obj.cart_created
            return round(duration.total_seconds() / 60, 2)
        return None


class CustomerLifetimeValueSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    customer_age_days = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomerLifetimeValue
        fields = [
            'id', 'user', 'user_email', 'user_name', 'total_orders',
            'total_spent', 'avg_order_value', 'first_order_date',
            'last_order_date', 'predicted_ltv', 'customer_segment',
            'last_updated', 'customer_age_days'
        ]
        read_only_fields = ['id', 'last_updated']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    
    def get_customer_age_days(self, obj):
        """Calculate customer age in days since first order"""
        if obj.first_order_date:
            from django.utils import timezone
            return (timezone.now().date() - obj.first_order_date.date()).days
        return None


class SalesMetricsSerializer(serializers.ModelSerializer):
    visitor_to_customer_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = SalesMetrics
        fields = [
            'id', 'date', 'total_visitors', 'unique_visitors',
            'conversion_rate', 'cart_abandonment_rate', 'new_customers',
            'returning_customers', 'customer_acquisition_cost',
            'visitor_to_customer_rate'
        ]
        read_only_fields = ['id']
    
    def get_visitor_to_customer_rate(self, obj):
        """Calculate visitor to customer conversion rate"""
        if obj.unique_visitors > 0:
            total_customers = obj.new_customers + obj.returning_customers
            return round((total_customers / obj.unique_visitors) * 100, 2)
        return 0