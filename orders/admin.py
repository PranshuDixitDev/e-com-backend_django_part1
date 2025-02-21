# orders/admin.py

from django.contrib import admin
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

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)