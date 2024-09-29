# cart/admin.py

from django.contrib import admin
from .models import Cart, CartItem

class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_username', 'get_user_email', 'get_user_full_name', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at', 'user')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('user', 'created_at', 'updated_at')
    
    # Prevent adding or deleting carts via the admin
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

    # Custom methods to display user details
    def get_user_username(self, obj):
        return obj.user.username
    get_user_username.short_description = 'Username'
    get_user_username.admin_order_field = 'user__username'

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'user__email'

    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_user_full_name.short_description = 'Full Name'
    get_user_full_name.admin_order_field = 'user__first_name'

admin.site.register(Cart, CartAdmin)

class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price')
    readonly_fields = ('cart', 'product', 'selected_price_weight', 'quantity', 'total_price')
    search_fields = ('product__name', 'cart__user__username', 'cart__user__email')
    list_filter = ('product',)

    # Prevent adding, changing, or deleting cart items via the admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(CartItem, CartItemAdmin)
