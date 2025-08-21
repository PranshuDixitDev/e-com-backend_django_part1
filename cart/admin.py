# cart/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import Cart, CartItem
from django.utils.html import format_html
from django.db.models import Sum, F
from decimal import Decimal
import logging

# Configure logging for admin actions
admin_logger = logging.getLogger('admin_actions')
User = get_user_model()

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin view for Cart.
    Displays user details and timestamps.
    """
    list_display = ['id', 'get_user_info', 'get_item_count', 'get_total_value', 'get_cart_status', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['user', 'created_at', 'updated_at', 'get_item_count', 'get_total_value']
    ordering = ['-updated_at']
    
    def has_add_permission(self, request):
        """Restrict cart creation - carts should only be created by users themselves"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing but restrict modifications to cart owner"""
        if obj is None:
            return True  # Allow viewing list
        # Only allow superusers to modify carts
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Restrict cart deletion to superusers only"""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """Log any cart modifications"""
        if change:
            admin_logger.warning(
                f"Cart {obj.id} modified by admin {request.user.username} "
                f"(ID: {request.user.id}) at {obj.updated_at}"
            )
            messages.warning(
                request, 
                f"Cart modification logged. Admin: {request.user.username}"
            )
        super().save_model(request, obj, form, change)

    # Custom methods to display user details
    def get_user_info(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br/>'
                '<small>Email: {}</small><br/>'
                '<small>ID: {}</small>',
                obj.user.get_full_name() or obj.user.username,
                obj.user.email,
                obj.user.id
            )
        return "No User"
    get_user_info.short_description = "Customer Info"
    
    def get_item_count(self, obj):
        return obj.items.count()
    get_item_count.short_description = "Items"
    
    def get_total_value(self, obj):
        total = obj.items.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or Decimal('0.00')
        return f"${total:.2f}"
    get_total_value.short_description = "Total Value"
    
    def get_cart_status(self, obj):
        item_count = obj.items.count()
        if item_count == 0:
            return format_html('<span style="color: #999;">Empty</span>')
        elif item_count <= 3:
            return format_html('<span style="color: #28a745;">Active</span>')
        else:
            return format_html('<span style="color: #ffc107;">Full</span>')
    get_cart_status.short_description = "Status"

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Admin view for CartItem.
    Read-only interface to prevent modifications via admin.
    """
    list_display = ['id', 'get_cart_info', 'get_product_info', 'quantity', 'get_price_details', 'get_cart_created_at']
    list_filter = ['cart__created_at', 'cart__user']
    search_fields = ['cart__user__username', 'cart__user__email', 'product__name']
    readonly_fields = ['cart', 'product', 'get_price_details', 'get_cart_created_at']
    ordering = ['-cart__created_at']

    def has_add_permission(self, request):
        """Restrict cart item creation - items should only be added by users"""
        return request.user.is_superuser  # Only superusers can add items

    def has_change_permission(self, request, obj=None):
        """Allow viewing but restrict modifications"""
        if obj is None:
            return True  # Allow viewing list
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Restrict cart item deletion to superusers only"""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """Log any cart item modifications with detailed information"""
        action = "modified" if change else "created"
        admin_logger.warning(
            f"CartItem {obj.id} {action} by admin {request.user.username} "
            f"(ID: {request.user.id}). Cart: {obj.cart.id}, Product: {obj.product.name}, "
            f"Quantity: {obj.quantity}, User: {obj.cart.user.username}"
        )
        messages.warning(
            request, 
            f"Cart item {action} logged. Admin: {request.user.username}, "
            f"Justification required for audit trail."
        )
        super().save_model(request, obj, form, change)
    
    def delete_model(self, request, obj):
        """Log cart item deletions"""
        admin_logger.warning(
            f"CartItem {obj.id} deleted by admin {request.user.username} "
            f"(ID: {request.user.id}). Cart: {obj.cart.id}, Product: {obj.product.name}"
        )
        messages.warning(
            request, 
            f"Cart item deletion logged. Admin: {request.user.username}"
        )
        super().delete_model(request, obj)
    
    # Custom display methods
    def get_cart_info(self, obj):
        return format_html(
            '<strong>Cart #{}</strong><br/>'
            '<small>User: {}</small>',
            obj.cart.id,
            obj.cart.user.username
        )
    get_cart_info.short_description = "Cart Info"
    
    def get_product_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/>'
            '<small>SKU: {}</small>',
            obj.product.name,
            getattr(obj.product, 'sku', 'N/A')
        )
    get_product_info.short_description = "Product"
    
    def get_price_details(self, obj):
        unit_price = obj.product.price
        total_price = unit_price * obj.quantity
        return format_html(
            '${:.2f} × {} = <strong>${:.2f}</strong>',
            unit_price,
            obj.quantity,
            total_price
        )
    get_price_details.short_description = "Price Details"
    
    def get_cart_created_at(self, obj):
        """Display cart creation date"""
        return obj.cart.created_at
    get_cart_created_at.short_description = 'Cart Created'
