# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import CustomUser, Address
from .utils import send_verification_email

class AddressInline(admin.StackedInline):
    model = Address
    can_delete = False
    extra = 0

class CustomUserAdmin(UserAdmin):
    inlines = (AddressInline,)
    
    # Add email verification fields to the list display
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'phone_number',
        'is_active', 'email_verification_status', 'email_sent_status', 
        'email_failed_status', 'date_joined', 'last_login'
    )
    
    # Add filters for email verification status
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'is_email_verified',
        'email_sent', 'email_failed', 'date_joined', 'last_login'
    )
    
    # Add search fields
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')
    
    # Add email verification fields to the fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Email Verification', {
            'fields': ('is_email_verified', 'email_sent', 'email_failed'),
            'description': 'Email verification status and tracking'
        }),
        ('Additional Info', {
            'fields': ('phone_number', 'birthdate'),
        }),
    )
    
    # Make email verification fields readonly in admin
    readonly_fields = ('is_email_verified', 'email_sent', 'email_failed', 'date_joined', 'last_login')
    
    # Custom methods for better display
    def email_verification_status(self, obj):
        """Display email verification status with colored indicators."""
        if obj.is_email_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Not Verified</span>'
            )
    email_verification_status.short_description = 'Email Verified'
    email_verification_status.admin_order_field = 'is_email_verified'
    
    def email_sent_status(self, obj):
        """Display email sent status with colored indicators."""
        if obj.email_sent:
            return format_html(
                '<span style="color: green;">✓ Sent</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">✗ Not Sent</span>'
            )
    email_sent_status.short_description = 'Email Sent'
    email_sent_status.admin_order_field = 'email_sent'
    
    def email_failed_status(self, obj):
        """Display email failed status with colored indicators."""
        if obj.email_failed:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Failed</span>'
            )
        else:
            return format_html(
                '<span style="color: green;">✓ No Failures</span>'
            )
    email_failed_status.short_description = 'Email Failed'
    email_failed_status.admin_order_field = 'email_failed'
    
    # Custom actions
    actions = ['resend_verification_email']
    
    def resend_verification_email(self, request, queryset):
        """Admin action to resend verification emails to selected users."""
        success_count = 0
        failure_count = 0
        
        for user in queryset:
            if not user.is_email_verified:
                if send_verification_email(user):
                    success_count += 1
                else:
                    failure_count += 1
            
        if success_count > 0:
            self.message_user(
                request,
                f'Successfully sent verification emails to {success_count} user(s).'
            )
        if failure_count > 0:
            self.message_user(
                request,
                f'Failed to send verification emails to {failure_count} user(s).',
                level='ERROR'
            )
        if success_count == 0 and failure_count == 0:
            self.message_user(
                request,
                'No unverified users selected or all users are already verified.'
            )
    
    resend_verification_email.short_description = "Resend verification email to selected users"

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Address)
