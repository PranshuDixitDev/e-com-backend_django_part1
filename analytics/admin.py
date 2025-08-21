from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    OrderAnalytics, UserActivityLog, SearchAnalytics, ErrorLog,
    APIEvent, SalesMetrics, ProductAnalytics, ConversionFunnel,
    CartAbandonmentAnalytics, CustomerLifetimeValue
)

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
    list_display = ('user', 'activity_type', 'timestamp', 'ip_address', 'view_details_link')
    list_filter = ('activity_type', 'timestamp', 'user')
    search_fields = ('user__username', 'user__email', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'activity_type', 'timestamp', 'ip_address', 'details')
    ordering = ['-timestamp']
    list_per_page = 50

    def view_details_link(self, obj):
        return format_html(
            '<a href="{}" style="color: #007cba; text-decoration: none;">👁️ View</a>',
            reverse('admin:analytics_useractivitylog_change', args=[obj.pk])
        )
    view_details_link.short_description = 'Details'
    view_details_link.allow_tags = True

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True  # Allow viewing but not editing

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete logs

    def get_readonly_fields(self, request, obj=None):
        # Make all fields readonly to prevent editing
        if obj:  # Editing an existing object
            return [field.name for field in self.model._meta.fields]
        return self.readonly_fields

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


@admin.register(APIEvent)
class APIEventAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp', 'get_status_badge', 'get_user_info', 'request_method', 
        'endpoint', 'get_response_time', 'get_ip_address', 'get_performance_indicator'
    )
    list_filter = (
        'status', 'request_method', 'response_status_code', 'timestamp', 
        'endpoint', 'user'
    )
    search_fields = (
        'endpoint', 'user__username', 'user__email', 'ip_address', 
        'error_message', 'user_agent'
    )
    date_hierarchy = 'timestamp'
    readonly_fields = (
        'timestamp', 'status', 'endpoint', 'response_time', 'user', 
        'ip_address', 'user_agent', 'request_method', 'request_data',
        'response_status_code', 'error_message', 'session_id', 'referer',
        'request_size', 'response_size'
    )
    ordering = ['-timestamp']
    list_per_page = 100
    actions = ['analyze_endpoint_performance', 'analyze_user_patterns']
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('timestamp', 'status', 'endpoint', 'request_method', 'response_time')
        }),
        ('User Information', {
            'fields': ('user', 'ip_address', 'session_id', 'user_agent')
        }),
        ('Request Details', {
            'fields': ('request_data', 'request_size', 'referer')
        }),
        ('Response Details', {
            'fields': ('response_status_code', 'response_size', 'error_message')
        }),
    )

    def get_status_badge(self, obj):
        if obj.status == 'success':
            color = '#10b981'
            icon = '✅'
        else:
            color = '#ef4444'
            icon = '❌'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'

    def get_response_time(self, obj):
        if obj.response_time < 200:
            color = '#10b981'  # Green for fast
            icon = '🚀'
        elif obj.response_time < 1000:
            color = '#f59e0b'  # Yellow for moderate
            icon = '⚡'
        else:
            color = '#ef4444'  # Red for slow
            icon = '🐌'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}ms</span>',
            color, icon, obj.response_time
        )
    get_response_time.short_description = 'Response Time'
    get_response_time.admin_order_field = 'response_time'

    def get_performance_indicator(self, obj):
        if obj.status == 'success' and obj.response_time < 500:
            return format_html('<span style="color: #10b981;">🎯 Optimal</span>')
        elif obj.status == 'success' and obj.response_time < 1000:
            return format_html('<span style="color: #f59e0b;">⚠️ Slow</span>')
        elif obj.status == 'success':
            return format_html('<span style="color: #ef4444;">🚨 Very Slow</span>')
        else:
            return format_html('<span style="color: #ef4444;">💥 Failed</span>')
    get_performance_indicator.short_description = 'Performance'

    def get_user_info(self, obj):
        if obj.user:
            return format_html(
                '<span style="color: #007cba;">👤 {}</span>',
                obj.user.username
            )
        return format_html('<span style="color: #666;">🔒 Anonymous</span>')
    get_user_info.short_description = 'User'
    get_user_info.admin_order_field = 'user__username'
    
    def get_ip_address(self, obj):
        if obj.ip_address:
            return format_html(
                '<span style="color: #10b981; font-family: monospace;">{}</span>',
                obj.ip_address
            )
        return format_html('<span style="color: #666;">-</span>')
    get_ip_address.short_description = 'IP Address'
    get_ip_address.admin_order_field = 'ip_address'

    def analyze_endpoint_performance(self, request, queryset):
        # This could be expanded to show detailed analytics
        endpoints = queryset.values_list('endpoint', flat=True).distinct()
        self.message_user(request, f'Analyzed {len(endpoints)} unique endpoints from {queryset.count()} events.')
    analyze_endpoint_performance.short_description = 'Analyze selected API events'
    
    def analyze_user_patterns(self, request, queryset):
        # Analyze user patterns from selected API events
        users = queryset.exclude(user__isnull=True).values_list('user__username', flat=True).distinct()
        ips = queryset.exclude(ip_address__isnull=True).values_list('ip_address', flat=True).distinct()
        self.message_user(
            request, 
            f'Analyzed patterns: {len(users)} unique users, {len(ips)} unique IPs from {queryset.count()} events.'
        )
    analyze_user_patterns.short_description = 'Analyze user patterns'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SalesMetrics)
class SalesMetricsAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'total_visitors', 'unique_visitors', 'get_conversion_rate',
        'get_abandonment_rate', 'new_customers', 'returning_customers',
        'get_acquisition_cost'
    )
    list_filter = ('date', 'conversion_rate', 'cart_abandonment_rate')
    date_hierarchy = 'date'
    readonly_fields = (
        'date', 'total_visitors', 'unique_visitors', 'conversion_rate',
        'cart_abandonment_rate', 'new_customers', 'returning_customers',
        'customer_acquisition_cost'
    )
    ordering = ['-date']
    list_per_page = 31  # Show about a month of data

    def get_conversion_rate(self, obj):
        return f"{obj.conversion_rate:.2f}%"
    get_conversion_rate.short_description = 'Conversion Rate'
    get_conversion_rate.admin_order_field = 'conversion_rate'

    def get_abandonment_rate(self, obj):
        return f"{obj.cart_abandonment_rate:.2f}%"
    get_abandonment_rate.short_description = 'Cart Abandonment'
    get_abandonment_rate.admin_order_field = 'cart_abandonment_rate'

    def get_acquisition_cost(self, obj):
        return f"${obj.customer_acquisition_cost:.2f}"
    get_acquisition_cost.short_description = 'CAC'
    get_acquisition_cost.admin_order_field = 'customer_acquisition_cost'

    def has_add_permission(self, request):
        return False


@admin.register(ProductAnalytics)
class ProductAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'get_product_name', 'date', 'views', 'cart_additions', 'purchases',
        'get_revenue', 'get_conversion_rate', 'get_cart_conversion_rate'
    )
    list_filter = ('date', 'product__category', 'conversion_rate')
    search_fields = ('product__name', 'product__sku')
    date_hierarchy = 'date'
    readonly_fields = (
        'product', 'date', 'views', 'cart_additions', 'purchases',
        'revenue', 'conversion_rate', 'cart_to_purchase_rate'
    )
    ordering = ['-date', '-revenue']
    list_per_page = 50
    raw_id_fields = ('product',)

    def get_product_name(self, obj):
        return obj.product.name if obj.product else 'N/A'
    get_product_name.short_description = 'Product'
    get_product_name.admin_order_field = 'product__name'

    def get_revenue(self, obj):
        return f"${obj.revenue:.2f}"
    get_revenue.short_description = 'Revenue'
    get_revenue.admin_order_field = 'revenue'

    def get_conversion_rate(self, obj):
        return f"{obj.conversion_rate:.2f}%"
    get_conversion_rate.short_description = 'Conversion Rate'
    get_conversion_rate.admin_order_field = 'conversion_rate'

    def get_cart_conversion_rate(self, obj):
        return f"{obj.cart_to_purchase_rate:.2f}%"
    get_cart_conversion_rate.short_description = 'Cart→Purchase'
    get_cart_conversion_rate.admin_order_field = 'cart_to_purchase_rate'

    def has_add_permission(self, request):
        return False


@admin.register(ConversionFunnel)
class ConversionFunnelAdmin(admin.ModelAdmin):
    list_display = (
        'get_user_name', 'session_id', 'stage', 'get_product_name',
        'timestamp', 'get_stage_badge'
    )
    list_filter = ('stage', 'timestamp', 'product__category')
    search_fields = ('user__username', 'user__email', 'session_id', 'product__name')
    date_hierarchy = 'timestamp'
    readonly_fields = (
        'user', 'session_id', 'stage', 'product', 'timestamp', 'metadata'
    )
    ordering = ['-timestamp']
    list_per_page = 100
    raw_id_fields = ('user', 'product')

    def get_user_name(self, obj):
        return obj.user.username if obj.user else 'Anonymous'
    get_user_name.short_description = 'User'
    get_user_name.admin_order_field = 'user__username'

    def get_product_name(self, obj):
        return obj.product.name if obj.product else 'N/A'
    get_product_name.short_description = 'Product'
    get_product_name.admin_order_field = 'product__name'

    def get_stage_badge(self, obj):
        stage_colors = {
            'PRODUCT_VIEW': '#17a2b8',
            'CART_ADD': '#ffc107',
            'CHECKOUT_START': '#fd7e14',
            'PAYMENT_INFO': '#6f42c1',
            'ORDER_COMPLETE': '#28a745'
        }
        color = stage_colors.get(obj.stage, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_stage_display()
        )
    get_stage_badge.short_description = 'Stage'
    get_stage_badge.admin_order_field = 'stage'

    def has_add_permission(self, request):
        return False


@admin.register(CartAbandonmentAnalytics)
class CartAbandonmentAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'get_user_name', 'session_id', 'cart_created', 'cart_abandoned',
        'get_cart_value', 'items_count', 'abandonment_stage',
        'get_recovery_status', 'recovery_email_sent'
    )
    list_filter = (
        'abandonment_stage', 'recovered', 'recovery_email_sent',
        'cart_abandoned', 'cart_created'
    )
    search_fields = ('user__username', 'user__email', 'session_id')
    date_hierarchy = 'cart_abandoned'
    readonly_fields = (
        'user', 'session_id', 'cart_created', 'cart_abandoned',
        'cart_value', 'items_count', 'abandonment_stage',
        'recovery_email_sent', 'recovered', 'recovery_date'
    )
    ordering = ['-cart_abandoned']
    list_per_page = 50
    raw_id_fields = ('user',)

    def get_user_name(self, obj):
        return obj.user.username if obj.user else 'Anonymous'
    get_user_name.short_description = 'User'
    get_user_name.admin_order_field = 'user__username'

    def get_cart_value(self, obj):
        return f"${obj.cart_value:.2f}"
    get_cart_value.short_description = 'Cart Value'
    get_cart_value.admin_order_field = 'cart_value'

    def get_recovery_status(self, obj):
        if obj.recovered:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Recovered</span>'
            )
        elif obj.recovery_email_sent:
            return format_html(
                '<span style="color: orange;">📧 Email Sent</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">❌ Abandoned</span>'
            )
    get_recovery_status.short_description = 'Recovery Status'
    get_recovery_status.admin_order_field = 'recovered'

    def has_add_permission(self, request):
        return False


@admin.register(CustomerLifetimeValue)
class CustomerLifetimeValueAdmin(admin.ModelAdmin):
    list_display = (
        'get_user_name', 'total_orders', 'get_total_spent', 'get_avg_order_value',
        'get_customer_segment', 'first_order_date', 'last_order_date',
        'get_predicted_ltv', 'last_updated'
    )
    list_filter = (
        'customer_segment', 'first_order_date', 'last_order_date',
        'total_orders', 'last_updated'
    )
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    date_hierarchy = 'last_order_date'
    readonly_fields = (
        'user', 'total_orders', 'total_spent', 'avg_order_value',
        'first_order_date', 'last_order_date', 'predicted_ltv',
        'customer_segment', 'last_updated'
    )
    ordering = ['-total_spent']
    list_per_page = 50
    raw_id_fields = ('user',)

    def get_user_name(self, obj):
        return f"{obj.user.get_full_name()} ({obj.user.username})" if obj.user else 'N/A'
    get_user_name.short_description = 'Customer'
    get_user_name.admin_order_field = 'user__username'

    def get_total_spent(self, obj):
        return f"${obj.total_spent:.2f}"
    get_total_spent.short_description = 'Total Spent'
    get_total_spent.admin_order_field = 'total_spent'

    def get_avg_order_value(self, obj):
        return f"${obj.avg_order_value:.2f}"
    get_avg_order_value.short_description = 'AOV'
    get_avg_order_value.admin_order_field = 'avg_order_value'

    def get_predicted_ltv(self, obj):
        return f"${obj.predicted_ltv:.2f}"
    get_predicted_ltv.short_description = 'Predicted LTV'
    get_predicted_ltv.admin_order_field = 'predicted_ltv'

    def get_customer_segment(self, obj):
        segment_colors = {
            'new': '#17a2b8',
            'regular': '#28a745',
            'vip': '#ffc107',
            'churned': '#dc3545'
        }
        color = segment_colors.get(obj.customer_segment, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.customer_segment
        )
    get_customer_segment.short_description = 'Segment'
    get_customer_segment.admin_order_field = 'customer_segment'

    def has_add_permission(self, request):
        return False
