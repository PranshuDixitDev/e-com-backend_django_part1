from django.contrib import admin
from .models import ShippingLog

@admin.register(ShippingLog)
class ShippingLogAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'endpoint', 'success', 'timestamp')
    list_filter = ('success', 'timestamp')
    search_fields = ('order_number', 'endpoint', 'request_payload', 'response_payload', 'error_message')