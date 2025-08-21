# orders/admin.py

from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Order, OrderItem
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.utils import timezone

class OrderItemInline(admin.TabularInline):
    """
    Inline admin display for OrderItem within the Order admin view.
    """
    model = OrderItem
    extra = 0  # No extra blank order items
    readonly_fields = ('product', 'quantity', 'selected_price_weight', 'unit_price', 'total_price')

class OrderAdmin(admin.ModelAdmin):
    """
    Admin view for Order with CSV export capabilities only.
    Shows key order details and includes inline OrderItems.
    Supports comprehensive CSV export with time-based aggregations.
    """
    list_display = ('order_number', 'user', 'status', 'payment_status', 'total_price',
                     'shipping_name', 'carrier', 'shipping_cost', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'carrier')
    search_fields = ('order_number', 'user__username', 'user__email')
    inlines = [OrderItemInline]
    actions = ['export_orders_csv', 'export_daily_aggregation', 'export_weekly_aggregation', 
               'export_monthly_aggregation', 'export_six_monthly_aggregation', 'export_yearly_aggregation']
    list_per_page = 25
    date_hierarchy = 'created_at'

    def export_orders_csv(self, request, queryset):
        """
        Exports selected orders to a comprehensive CSV file with all order, payment, shipping, and customer details.
        """
        print("---------------------------------------Export Orders CSV action triggered")  # Debug statement
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'orders_comprehensive_export_{timestamp}.csv'
        
        # Define comprehensive field names for CSV export
        fieldnames = [
            'order_number', 'created_at', 'updated_at', 'status', 'user_name', 'user_email',
            'user_phone', 'total_price', 'amount_paid', 'payment_method', 'payment_id',
            'payment_date', 'payment_status', 'razorpay_order_id', 'shipping_cost',
            'shipping_name', 'shipping_method', 'shipment_id', 'tracking_number', 'carrier',
            'estimated_delivery_date', 'shipping_address_line1', 'shipping_address_line2',
            'shipping_city', 'shipping_state', 'shipping_postal_code', 'shipping_country',
            'total_items', 'order_items_details', 'total_weight_grams'
        ]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        
        for order in queryset:
            # Get order items details
            items = order.items.all()
            items_details = []
            for item in items:
                items_details.append(f"{item.quantity}x {item.product.name} ({item.selected_price_weight.weight}) - ₹{item.unit_price}")
            
            # Calculate total weight
            try:
                total_weight = order.calculate_total_weight()
            except:
                total_weight = 0
            
            writer.writerow({
                'order_number': order.order_number,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else '',
                'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M:%S') if order.updated_at else '',
                'status': order.status,
                'user_name': order.user.username if order.user else '',
                'user_email': order.user.email if order.user else '',
                'user_phone': getattr(order.user, 'phone', '') if order.user else '',
                'total_price': order.total_price,
                'amount_paid': order.amount_paid,
                'payment_method': order.payment_method or '',
                'payment_id': order.payment_id or '',
                'payment_date': order.payment_date.strftime('%Y-%m-%d %H:%M:%S') if order.payment_date else '',
                'payment_status': order.payment_status,
                'razorpay_order_id': order.razorpay_order_id or '',
                'shipping_cost': order.shipping_cost,
                'shipping_name': order.shipping_name or '',
                'shipping_method': order.shipping_method or '',
                'shipment_id': order.shipment_id or '',
                'tracking_number': order.tracking_number or '',
                'carrier': order.carrier or '',
                'estimated_delivery_date': order.estimated_delivery_date.strftime('%Y-%m-%d') if order.estimated_delivery_date else '',
                'shipping_address_line1': order.address.address_line1 if order.address else '',
                'shipping_address_line2': getattr(order.address, 'address_line2', '') if order.address else '',
                'shipping_city': order.address.city if order.address else '',
                'shipping_state': order.address.state if order.address else '',
                'shipping_postal_code': order.address.postal_code if order.address else '',
                'shipping_country': order.address.country if order.address else '',
                'total_items': items.count(),
                'order_items_details': "; ".join(items_details),
                'total_weight_grams': total_weight,
            })
        return response

    export_orders_csv.short_description = "Export Selected Orders to CSV"

    def export_daily_aggregation(self, request, queryset):
        """
        Export daily aggregated order data as CSV
        """
        return self._export_aggregated_data('daily', queryset)
    
    def export_weekly_aggregation(self, request, queryset):
        """
        Export weekly aggregated order data as CSV
        """
        return self._export_aggregated_data('weekly', queryset)
    
    def export_monthly_aggregation(self, request, queryset):
        """
        Export monthly aggregated order data as CSV
        """
        return self._export_aggregated_data('monthly', queryset)
    
    def export_six_monthly_aggregation(self, request, queryset):
        """
        Export six-monthly aggregated order data as CSV
        """
        return self._export_aggregated_data('six_monthly', queryset)
    
    def export_yearly_aggregation(self, request, queryset):
        """
        Export yearly aggregated order data as CSV
        """
        return self._export_aggregated_data('yearly', queryset)
    
    def _export_aggregated_data(self, period, queryset):
        """
        Helper method to export aggregated order data for different time periods
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'orders_{period}_aggregation_{timestamp}.csv'
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        fieldnames = ['period', 'total_orders', 'total_revenue', 'avg_order_value', 
                     'completed_orders', 'pending_orders', 'cancelled_orders',
                     'total_items_sold', 'unique_customers']
        
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        
        # Get aggregated data based on period
        aggregated_data = self._get_aggregated_data(period, queryset)
        
        for data in aggregated_data:
            writer.writerow(data)
        
        return response
    
    def _get_aggregated_data(self, period, queryset):
        """
        Get aggregated order data for the specified period
        """
        now = timezone.now()
        data = []
        
        if period == 'daily':
            # Last 30 days
            for i in range(30):
                date = now.date() - timedelta(days=i)
                day_orders = queryset.filter(created_at__date=date)
                data.append(self._calculate_period_stats(f'{date}', day_orders))
        
        elif period == 'weekly':
            # Last 12 weeks
            for i in range(12):
                start_date = now.date() - timedelta(weeks=i+1)
                end_date = now.date() - timedelta(weeks=i)
                week_orders = queryset.filter(created_at__date__range=[start_date, end_date])
                data.append(self._calculate_period_stats(f'Week {start_date} to {end_date}', week_orders))
        
        elif period == 'monthly':
            # Last 12 months
            for i in range(12):
                month_date = now.replace(day=1) - timedelta(days=32*i)
                month_orders = queryset.filter(
                    created_at__year=month_date.year,
                    created_at__month=month_date.month
                )
                data.append(self._calculate_period_stats(f'{month_date.strftime("%Y-%m")}', month_orders))
        
        elif period == 'six_monthly':
            # Last 4 six-month periods
            for i in range(4):
                start_month = now.month - (6 * (i + 1))
                start_year = now.year
                if start_month <= 0:
                    start_month += 12
                    start_year -= 1
                
                end_month = start_month + 5
                end_year = start_year
                if end_month > 12:
                    end_month -= 12
                    end_year += 1
                
                period_orders = queryset.filter(
                    created_at__year__gte=start_year,
                    created_at__year__lte=end_year,
                    created_at__month__gte=start_month if start_year == end_year else 1,
                    created_at__month__lte=end_month if start_year == end_year else 12
                )
                data.append(self._calculate_period_stats(f'{start_year}-{start_month:02d} to {end_year}-{end_month:02d}', period_orders))
        
        elif period == 'yearly':
            # Last 5 years
            for i in range(5):
                year = now.year - i
                year_orders = queryset.filter(created_at__year=year)
                data.append(self._calculate_period_stats(f'{year}', year_orders))
        
        return data
    
    def _calculate_period_stats(self, period_name, orders):
        """
        Calculate statistics for a given period
        """
        total_orders = orders.count()
        total_revenue = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        completed_orders = orders.filter(status='DELIVERED').count()
        pending_orders = orders.filter(status__in=['PENDING', 'PROCESSING', 'SHIPPED']).count()
        cancelled_orders = orders.filter(status='CANCELLED').count()
        
        total_items = sum(order.items.aggregate(Sum('quantity'))['quantity__sum'] or 0 for order in orders)
        unique_customers = orders.values('user').distinct().count()
        
        return {
            'period': period_name,
            'total_orders': total_orders,
            'total_revenue': f'{total_revenue:.2f}',
            'avg_order_value': f'{avg_order_value:.2f}',
            'completed_orders': completed_orders,
            'pending_orders': pending_orders,
            'cancelled_orders': cancelled_orders,
            'total_items_sold': total_items,
            'unique_customers': unique_customers
        }
    
    # Set descriptions for admin actions
    export_daily_aggregation.short_description = "Export Daily Aggregation (Last 30 days)"
    export_weekly_aggregation.short_description = "Export Weekly Aggregation (Last 12 weeks)"
    export_monthly_aggregation.short_description = "Export Monthly Aggregation (Last 12 months)"
    export_six_monthly_aggregation.short_description = "Export Six-Monthly Aggregation (Last 2 years)"
    export_yearly_aggregation.short_description = "Export Yearly Aggregation (Last 5 years)"

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)