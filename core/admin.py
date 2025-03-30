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
    ErrorLog
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
        api_success = api_counts.get('success', 0)
        api_failure = api_counts.get('failure', 0)

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
            'api_success': api_success,
            'api_failure': api_failure,
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

# Analytics related models
custom_admin_site.register(APIEvent)
custom_admin_site.register(OrderAnalytics)
custom_admin_site.register(UserActivityLog)
custom_admin_site.register(SearchAnalytics)
custom_admin_site.register(ErrorLog)
