from django.contrib import admin
from .models import OrderAnalytics, UserActivityLog, SearchAnalytics, ErrorLog

@admin.register(OrderAnalytics)
class OrderAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_orders', 'total_revenue', 'avg_order_value', 'shipping_revenue')
    list_filter = ('date',)
    date_hierarchy = 'date'
    readonly_fields = ('date', 'total_orders', 'total_revenue', 'avg_order_value', 'shipping_revenue')

    def has_add_permission(self, request):
        return False  # Analytics are generated automatically

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'timestamp', 'ip_address')
    list_filter = ('activity_type', 'timestamp', 'user')
    search_fields = ('user__username', 'user__email', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'activity_type', 'timestamp', 'ip_address', 'details')

    def has_add_permission(self, request):
        return False

@admin.register(SearchAnalytics)
class SearchAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('query', 'user', 'timestamp', 'results_count', 'category')
    list_filter = ('timestamp', 'category', 'results_count')
    search_fields = ('query', 'user__username')
    date_hierarchy = 'timestamp'
    readonly_fields = ('query', 'user', 'timestamp', 'results_count', 'category')

    def has_add_permission(self, request):
        return False

@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'endpoint', 'get_error_preview', 'user')
    list_filter = ('timestamp', 'endpoint')
    search_fields = ('error_message', 'endpoint', 'user__username')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'endpoint', 'error_message', 'stack_trace', 'user')

    def get_error_preview(self, obj):
        return obj.error_message[:100] + '...' if len(obj.error_message) > 100 else obj.error_message
    get_error_preview.short_description = 'Error Message'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete error logs
