# orders/admin.py

from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    """
    Inline admin display for OrderItem within the Order admin view.
    """
    model = OrderItem
    extra = 0  # No extra blank order items
    readonly_fields = ('product', 'quantity', 'selected_price_weight', 'unit_price', 'total_price')

class OrderAdmin(admin.ModelAdmin):
    """
    Admin view for Order.
    Shows key order details and includes inline OrderItems.
    """
    list_display = ('order_number', 'user', 'status', 'payment_status', 'total_price', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email')
    inlines = [OrderItemInline]
    actions = ['export_orders_csv']

    def export_orders_csv(self, request, queryset):
        """
        Exports selected orders to a CSV file with all shipping and order details.
        """
        # Define the field names you want in the CSV export.
        fieldnames = [
            'order_number', 'user', 'created_at', 'status', 'payment_status', 'total_price', 
            'shipping_name', 'shipment_id', 'tracking_number', 'shipping_method', 'carrier', 
            'estimated_delivery_date', 'shipping_cost'
        ]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=orders_export.csv'
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        for order in queryset:
            writer.writerow({
                'order_number': order.order_number,
                'user': order.user.username,
                'created_at': order.created_at,
                'status': order.status,
                'payment_status': order.payment_status,
                'total_price': order.total_price,
                'shipping_name': order.shipping_name,
                'shipment_id': order.shipment_id,
                'tracking_number': order.tracking_number,
                'shipping_method': order.shipping_method,
                'carrier': order.carrier,
                'estimated_delivery_date': order.estimated_delivery_date,
                'shipping_cost': order.shipping_cost,
            })
        return response

    export_orders_csv.short_description = "Export Selected Orders to CSV"

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)