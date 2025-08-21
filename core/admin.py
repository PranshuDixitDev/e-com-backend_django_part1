# core/admin.py

import json
from decimal import Decimal
from django.contrib.admin import AdminSite
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.template.response import TemplateResponse
from django.contrib.auth import get_user_model
from datetime import timedelta, date
from django.db.models.functions import TruncDate
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

# Import models from your existing apps (using the exact naming conventions)
from users.models import Address
from orders.models import Order, OrderItem
from products.models import Product
from categories.models import Category
from cart.models import Cart, CartItem
# For shipping, import ShippingLog because your shipping/models.py defines ShippingLog
from shipping.models import ShippingLog

# Import the APIEvent model from the analytics app we just created.
from analytics.models import APIEvent

from analytics.models import (
    OrderAnalytics, 
    UserActivityLog, 
    SearchAnalytics, 
    ErrorLog,
    SalesMetrics,
    ProductAnalytics,
    ConversionFunnel,
    CartAbandonmentAnalytics,
    CustomerLifetimeValue
)

from products.admin import ProductAdmin, BestSellerAdmin
from products.models import Product, ProductImage, PriceWeight, BestSeller
from orders.admin import OrderAdmin
User = get_user_model()

def daterange(start_date, end_date):
    """
    Generates a range of dates from start_date to end_date (inclusive).
    """
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

class CustomAdminSite(AdminSite):
    site_title = "Gujju Admin Portal"
    site_header = "Gujju Admin"
    index_title = "Welcome to Gujju Admin"

    def index(self, request, extra_context=None):
        # Import models at the top of the function to avoid UnboundLocalError
        from products.models import Product, PriceWeight
        from orders.models import Order, OrderItem
        from django.db.models import Sum, Avg, Count, F, Q
        
        # Add debugging
        end_date = timezone.localtime(timezone.now())
        start_date = end_date - timedelta(days=30)

        # Ensure proper handling of sales data for the chart
        sales_qs = Order.objects.filter(
            payment_status="COMPLETED",
            created_at__date__range=(start_date.date(), end_date.date())
        ).annotate(
            order_date=TruncDate('created_at')
        ).values('order_date').annotate(
            total_sales=Sum('amount_paid')
        ).order_by('order_date')

        # Generate complete date labels for the last 31 days (including both start and end)
        date_labels = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(31)]

        # Map dates to sales amounts, defaulting to zero if no orders
        sales_dict = {entry['order_date'].strftime("%Y-%m-%d"): float(entry['total_sales']) for entry in sales_qs}
        sales_data = [sales_dict.get(day, 0) for day in date_labels]

        # API Events Analytics
        api_qs = APIEvent.objects.filter(
            timestamp__range=(start_date, end_date)
        ).values('status').annotate(
            count=Count('id')
        )
        api_counts = {entry['status']: entry['count'] for entry in api_qs}
        api_success_count = api_counts.get('success', 0)
        api_failure_count = api_counts.get('failure', 0)
        total_api_calls = api_success_count + api_failure_count
        
        # Calculate success rate as percentage
        if total_api_calls > 0:
            api_success_rate = round((api_success_count / total_api_calls) * 100, 1)
        else:
            api_success_rate = 100.0  # No API calls means 100% success rate
        
        # Get recent failed API calls for detailed analysis
        recent_failures = APIEvent.objects.filter(
            status='failure',
            timestamp__range=(start_date, end_date)
        ).order_by('-timestamp')[:10]
        
        # Enhanced E-commerce Analytics
        from products.models import Product, PriceWeight
        from orders.models import Order, OrderItem
        from django.db.models import Sum, Avg, Count, F, Q
        
        # Inventory Analytics
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_items = PriceWeight.objects.filter(inventory__lte=10, inventory__gt=0).count()
        out_of_stock_items = PriceWeight.objects.filter(inventory=0).count()
        total_inventory_value = PriceWeight.objects.aggregate(
            total_value=Sum(F('price') * F('inventory'))
        )['total_value'] or 0
        
        # Order Analytics (Last 30 days)
        recent_orders = Order.objects.filter(created_at__gte=start_date)
        total_orders = recent_orders.count()
        completed_orders = recent_orders.filter(status='DELIVERED').count()
        pending_orders = recent_orders.filter(status__in=['PENDING', 'PROCESSING']).count()
        cancelled_orders = recent_orders.filter(status='CANCELLED').count()
        
        # Revenue Analytics
        total_revenue = recent_orders.filter(payment_status='COMPLETED').aggregate(
            revenue=Sum('amount_paid')
        )['revenue'] or 0
        
        avg_order_value = recent_orders.filter(payment_status='COMPLETED').aggregate(
            avg_value=Avg('amount_paid')
        )['avg_value'] or 0
        
        # Conversion Rate
        if total_orders > 0:
            conversion_rate = round((completed_orders / total_orders) * 100, 1)
        else:
            conversion_rate = 0
            
        # Top Selling Products (Last 30 days)
        top_products = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__payment_status='COMPLETED'
        ).values(
            'product__name'
        ).annotate(
            total_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('-total_sold')[:5]
        
        # Payment Analytics
        payment_methods = recent_orders.filter(
            payment_status='COMPLETED'
        ).values('payment_method').annotate(
            count=Count('id'),
            revenue=Sum('amount_paid')
        ).order_by('-count')
        
        # Shipping Analytics
        avg_shipping_cost = recent_orders.aggregate(
            avg_shipping=Avg('shipping_cost')
        )['avg_shipping'] or 0
        
        shipping_methods = recent_orders.values('shipping_method').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Enhanced Cart Analytics
        total_carts = Cart.objects.count()
        active_carts = Cart.objects.filter(
            items__isnull=False
        ).distinct().count()
        empty_carts = total_carts - active_carts
        
        # Cart value distribution
        cart_values = Cart.objects.annotate(
            cart_value=Sum(F('items__quantity') * F('items__selected_price_weight__price'))
        ).filter(cart_value__isnull=False)
        
        avg_cart_value = cart_values.aggregate(
            avg_value=Avg('cart_value')
        )['avg_value'] or 0
        
        high_value_carts = cart_values.filter(
            cart_value__gte=100  # Carts with value >= $100
        ).count()
        
        # Cart item analytics
        total_cart_items = CartItem.objects.count()
        avg_items_per_cart = CartItem.objects.values('cart').annotate(
            item_count=Count('id')
        ).aggregate(
            avg_items=Avg('item_count')
        )['avg_items'] or 0
        
        # Recent cart activity
        recent_cart_activity = Cart.objects.filter(
            updated_at__gte=start_date
        ).count()
        
        # Cart abandonment indicators
        old_active_carts = Cart.objects.filter(
            items__isnull=False,
            updated_at__lt=timezone.now() - timedelta(days=7)
        ).distinct().count()

        # Enhanced Order Analytics (unified on payment_status)
        order_stats = {
            'total_orders': Order.objects.count(),
            'pending_orders': Order.objects.filter(status='PENDING').count(),
            'processing_orders': Order.objects.filter(status='PROCESSING').count(),
            'completed_orders': Order.objects.filter(payment_status='COMPLETED').count(),
            'total_revenue': Order.objects.filter(payment_status='COMPLETED').aggregate(
                total=Sum('amount_paid')
            )['total'] or 0,
            'avg_order_value': Order.objects.filter(payment_status='COMPLETED').aggregate(
                avg=Avg('amount_paid')
            )['avg'] or 0
        }

        # Enhanced User Analytics
        user_stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'verified_users': User.objects.filter(is_email_verified=True).count(),
            'new_users': User.objects.filter(
                date_joined__range=(start_date, end_date)
            ).count()
        }

        # Search and Error Analytics
        search_stats = {
            'total_searches': SearchAnalytics.objects.count(),
            'zero_results_searches': SearchAnalytics.objects.filter(
                results_count=0
            ).count(),
            'recent_searches': SearchAnalytics.objects.order_by(
                '-timestamp'
            )[:5]
        }

        error_stats = {
            'recent_errors': ErrorLog.objects.order_by('-timestamp')[:5],
            'total_errors': ErrorLog.objects.count()
        }

        context = {
            'labels_sales': json.dumps(date_labels),
            'data_sales': json.dumps(sales_data),
            'order_stats': order_stats,
            'user_stats': user_stats,
            'search_stats': search_stats,
            'error_stats': error_stats,
            'api_success_rate': api_success_rate,
            'api_success_count': api_success_count,
            'api_failure_count': api_failure_count,
            'total_api_calls': total_api_calls,
            'recent_failures': recent_failures,
            # Enhanced E-commerce Analytics
            'inventory_stats': {
                'total_products': total_products,
                'low_stock_items': low_stock_items,
                'out_of_stock_items': out_of_stock_items,
                'total_inventory_value': float(total_inventory_value),
            },
            'ecommerce_stats': {
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'pending_orders': pending_orders,
                'cancelled_orders': cancelled_orders,
                'total_revenue': float(total_revenue),
                'avg_order_value': float(avg_order_value),
                'conversion_rate': conversion_rate,
                'avg_shipping_cost': float(avg_shipping_cost),
            },
            'top_products': list(top_products),
            'payment_methods': list(payment_methods),
            'shipping_methods': list(shipping_methods),
            'cart_analytics': {
                'total_carts': total_carts,
                'active_carts': active_carts,
                'empty_carts': empty_carts,
                'avg_cart_value': float(avg_cart_value),
                'high_value_carts': high_value_carts,
                'total_cart_items': total_cart_items,
                'avg_items_per_cart': float(avg_items_per_cart),
                'recent_cart_activity': recent_cart_activity,
                'old_active_carts': old_active_carts,
            },
        }

        if extra_context:
            context.update(extra_context)

        return TemplateResponse(request, 'admin/index.html', context)

    def get_app_list(self, request):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_dict = self._build_app_dict(request)
        app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())
        return app_list

# Instantiate the custom admin site.
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register models in proper order with their admin classes
custom_admin_site.register(User)
custom_admin_site.register(Address)
custom_admin_site.register(Category)

# Product related models
custom_admin_site.register(Product, ProductAdmin)
custom_admin_site.register(ProductImage)
custom_admin_site.register(PriceWeight)
custom_admin_site.register(BestSeller, BestSellerAdmin)

# Cart related models
custom_admin_site.register(Cart)
custom_admin_site.register(CartItem)

# Order related models
custom_admin_site.register(Order, OrderAdmin)
custom_admin_site.register(OrderItem)

# Shipping related models
custom_admin_site.register(ShippingLog)

# Register analytics models
custom_admin_site.register(APIEvent)
custom_admin_site.register(OrderAnalytics)
custom_admin_site.register(UserActivityLog)
custom_admin_site.register(SearchAnalytics)
custom_admin_site.register(ErrorLog)
custom_admin_site.register(SalesMetrics)
custom_admin_site.register(ProductAnalytics)
custom_admin_site.register(ConversionFunnel)
custom_admin_site.register(CartAbandonmentAnalytics)
custom_admin_site.register(CustomerLifetimeValue)
