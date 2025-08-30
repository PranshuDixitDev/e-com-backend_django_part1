from django.contrib import admin, messages
from django import forms
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.http import HttpResponseRedirect, JsonResponse
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from .models import BestSeller, Product, ProductImage, PriceWeight, BulkUpload, validate_image
from .services import CatalogProcessingService
from .validators import BulkUploadValidator
import threading
import json


# Custom form for ProductImage to ensure image validation is applied
class ProductImageForm(forms.ModelForm):
    def clean_image(self):
        image = self.cleaned_data.get('image')
        validate_image(image)  # Applies custom image validation
        return image
    
    class Meta:
        model = ProductImage
        fields = '__all__'

# Custom inline formset to enforce the number of price weights
class PriceWeightInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        count = sum(1 for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE', False))
        
        # Allow 1 combination (for default values) or 3-5 combinations (for manual entries)
        if count > 0 and count < 3 and count != 1:
            raise ValidationError('Either provide 1 combination (for default values) or at least 3 price-weight combinations.')
        if count > 5:
            raise ValidationError('No more than 5 price-weight combinations are allowed.')
        
        # Additional validation for inventory
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                inventory = form.cleaned_data.get('inventory')
                if inventory is None or inventory < 0:
                    raise ValidationError('Inventory must be a non-negative integer.')

# Inline admin for PriceWeight
class PriceWeightInline(admin.TabularInline):
    model = PriceWeight
    formset = PriceWeightInlineFormSet
    fields = ['price', 'weight', 'inventory', 'status']
    readonly_fields = ['status']
    extra = 3  # Start with 3 empty forms
    max_num = 5  # Limit the number of price weights to 5

    def status(self, obj):
        return "In stock" if obj.inventory > 0 else "Out of stock"
    
# Inline admin for ProductImage
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageForm
    extra = 1  # One empty form by default

# Main Product admin
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description', 'category', 'get_tags', 'is_active_toggle']
    search_fields = ['name', 'description']
    list_filter = ['category', 'is_active']
    inlines = [PriceWeightInline, ProductImageInline]
    actions = ['make_active']
    change_list_template = 'admin/products/product/change_list.html'

    # Custom method to display tags in the admin list view
    def get_tags(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    get_tags.short_description = 'Tags'
    
    # Custom method to display clickable is_active toggle
    def is_active_toggle(self, obj):
        return format_html(
            '<input type="checkbox" class="is-active-toggle" data-product-id="{}" {}/>',
            obj.id,
            'checked' if obj.is_active else ''
        )
    is_active_toggle.short_description = 'Active'
    is_active_toggle.admin_order_field = 'is_active'
    
    # Bulk action to make products active
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} product(s) were successfully marked as active.',
            messages.SUCCESS
        )
    make_active.short_description = 'Mark selected products as active'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('toggle-active/', self.admin_site.admin_view(self.toggle_active_view), name='products_product_toggle_active'),
        ]
        return custom_urls + urls
    
    @method_decorator(csrf_exempt)
    @method_decorator(require_POST)
    def toggle_active_view(self, request):
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            if not product_id:
                return JsonResponse({'success': False, 'error': 'Product ID is required'})
            
            product = Product.objects.get(id=product_id)
            product.is_active = not product.is_active
            product.save(update_fields=['is_active'])
            
            return JsonResponse({
                'success': True,
                'is_active': product.is_active,
                'message': f'Product "{product.name}" is now {"active" if product.is_active else "inactive"}'
            })
            
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@admin.register(BestSeller)
class BestSellerAdmin(admin.ModelAdmin):
    list_display = ('product', 'added_on')


class BulkUploadForm(forms.ModelForm):
    """Custom form for BulkUpload with enhanced security validation."""
    
    class Meta:
        model = BulkUpload
        fields = ['zip_file']
        widgets = {
            'zip_file': forms.FileInput(attrs={
                'accept': '.zip',
                'class': 'form-control-file'
            })
        }
    
    def clean_zip_file(self):
        zip_file = self.cleaned_data.get('zip_file')
        if zip_file:
            # Use centralized validation
            validator = BulkUploadValidator()
            validator.validate_zip_upload(zip_file)
        
        return zip_file


@admin.register(BulkUpload)
class BulkUploadAdmin(admin.ModelAdmin):
    """Admin interface for bulk catalog uploads."""
    
    form = BulkUploadForm
    change_list_template = 'admin/products/bulkupload/change_list.html'
    

    list_display = [
        'id', 'zip_file_name', 'status_badge', 'uploaded_by', 
        'uploaded_at', 'processed_at', 'processing_summary', 'category_summary', 'actions_column'
    ]
    list_filter = ['status', 'uploaded_at', 'uploaded_by']
    search_fields = ['zip_file', 'uploaded_by__username']
    readonly_fields = [
        'status', 'uploaded_at', 'processed_at', 'uploaded_by',
        'categories_created', 'categories_updated', 'products_created', 
        'products_updated', 'images_processed', 'error_log', 'processing_notes',
        'processing_results_summary', 'formatted_category_stats', 'formatted_detailed_errors', 'formatted_empty_categories'
    ]
    ordering = ['-uploaded_at']
    
    fieldsets = (
        ('Upload Information', {
            'fields': ('zip_file', 'status', 'uploaded_by', 'uploaded_at')
        }),
        ('Processing Results', {
            'fields': (
                'processed_at', 'processing_results_summary'
            ),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': ('error_log', 'processing_notes'),
            'classes': ('collapse',)
        }),
        ('Category Tracking', {
            'fields': ('formatted_category_stats', 'formatted_empty_categories', 'formatted_detailed_errors'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['process_selected_uploads', 'reprocess_failed_uploads']
    
    def get_queryset(self, request):
        """Filter uploads by user if not superuser."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(uploaded_by=request.user)
        return qs
    
    def has_add_permission(self, request):
        """Only superusers can create bulk uploads."""
        return request.user.is_superuser
    
    def has_module_permission(self, request):
        """Only superusers can access bulk upload module."""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """Set the uploaded_by field to current user."""
        if not change:  # Only for new uploads
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        
        # Auto-process the upload after saving
        if not change and obj.status == 'pending':
            self._process_upload_async(obj, request)
    
    def _process_upload_async(self, bulk_upload, request):
        """Process upload in background thread with enhanced feedback and error handling."""
        def process():
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                # Log processing start
                logger.info(f"Starting async processing for bulk upload {bulk_upload.id}")
                
                # Mark as processing
                bulk_upload.mark_as_processing()
                
                # Initialize and run the service
                service = CatalogProcessingService(bulk_upload)
                success = service.process_catalog()
                
                # Refresh the object to get updated statistics
                bulk_upload.refresh_from_db()
                
                if success:
                    # Build detailed success message
                    success_parts = []
                    if bulk_upload.categories_created:
                        success_parts.append(f'{bulk_upload.categories_created} categories created')
                    if bulk_upload.categories_updated:
                        success_parts.append(f'{bulk_upload.categories_updated} categories updated')
                    if bulk_upload.products_created:
                        success_parts.append(f'{bulk_upload.products_created} products created')
                    if bulk_upload.products_updated:
                        success_parts.append(f'{bulk_upload.products_updated} products updated')
                    if bulk_upload.images_processed:
                        success_parts.append(f'{bulk_upload.images_processed} images processed')
                    
                    success_details = ', '.join(success_parts) if success_parts else 'No items processed'
                    
                    # Check for warnings and empty folders
                    warning_parts = []
                    if hasattr(service, 'errors') and service.errors:
                        warning_count = len(service.errors)
                        warning_parts.append(f'{warning_count} processing warnings')
                    
                    # Check for empty category folders
                    if bulk_upload.empty_categories:
                        try:
                            empty_count = len(bulk_upload.empty_categories)
                            if empty_count > 0:
                                empty_folders = ', '.join(bulk_upload.empty_categories[:3])  # Show first 3
                                if empty_count > 3:
                                    empty_folders += f' and {empty_count - 3} more'
                                warning_parts.append(f'{empty_count} empty category folders found ({empty_folders})')
                        except Exception:
                            pass
                    
                    warning_msg = ''
                    if warning_parts:
                        warning_msg = f' Note: {'; '.join(warning_parts)}.'
                    
                    messages.success(
                        request, 
                        f'✅ Bulk upload #{bulk_upload.id} completed successfully! '
                        f'{success_details}.{warning_msg}'
                    )
                    
                    # Add separate warning message for empty folders if they exist
                    if bulk_upload.empty_categories:
                        try:
                            empty_count = len(bulk_upload.empty_categories)
                            if empty_count > 0:
                                messages.warning(
                                    request,
                                    f'⚠️ Found {empty_count} empty category folders that contained no products. '
                                    f'Please review the Category Tracking section for details.'
                                )
                        except Exception:
                            pass
                    
                    logger.info(f"Successfully completed processing for bulk upload {bulk_upload.id}: {success_details}")
                    
                else:
                    # Build detailed error message
                    error_details = 'Unknown error occurred'
                    if bulk_upload.error_log:
                        error_lines = [line.strip() for line in bulk_upload.error_log.split('\n') if line.strip()]
                        if error_lines:
                            error_details = f'{len(error_lines)} errors occurred'
                            if len(error_lines) <= 3:
                                error_details += f': {'; '.join(error_lines[:3])}'
                    
                    messages.error(
                        request,
                        f'❌ Bulk upload #{bulk_upload.id} failed to process. '
                        f'{error_details}. Check the upload details for complete error log.'
                    )
                    
                    logger.error(f"Failed to process bulk upload {bulk_upload.id}: {error_details}")
                    
            except Exception as e:
                logger.exception(f"Unexpected error processing bulk upload {bulk_upload.id}: {str(e)}")
                
                # Mark as failed with detailed error
                error_message = f"Processing error: {str(e)}"
                if hasattr(e, '__class__'):
                    error_message = f"{e.__class__.__name__}: {str(e)}"
                
                bulk_upload.mark_as_failed(error_message)
                
                messages.error(
                    request,
                    f'💥 Bulk upload #{bulk_upload.id} encountered a critical error: '
                    f'{str(e)}. Please check the file format and try again.'
                )
        
        # Start processing in background
        thread = threading.Thread(target=process, name=f'BulkUpload-{bulk_upload.id}')
        thread.daemon = True
        thread.start()
        
        # Provide immediate feedback
        messages.info(
            request,
            f'🚀 Bulk upload #{bulk_upload.id} has been queued for processing. '
            f'Refresh the page to see progress updates.'
        )
    
    def zip_file_name(self, obj):
        """Display just the filename of the uploaded zip."""
        if obj.zip_file:
            return obj.zip_file.name.split('/')[-1]
        return '-'
    zip_file_name.short_description = 'File Name'
    
    def status_badge(self, obj):
        """Display status with enhanced colored badge and progress information."""
        status_config = {
            'pending': {
                'color': '#ff9800',
                'bg_color': '#fff3e0',
                'icon': '●',
                'text': 'Pending'
            },
            'processing': {
                'color': '#2196f3',
                'bg_color': '#e3f2fd',
                'icon': '●',
                'text': 'Processing'
            },
            'completed': {
                'color': '#4caf50',
                'bg_color': '#e8f5e8',
                'icon': '●',
                'text': 'Completed'
            },
            'failed': {
                'color': '#f44336',
                'bg_color': '#ffebee',
                'icon': '●',
                'text': 'Failed'
            }
        }
        
        config = status_config.get(obj.status, {
            'color': '#666',
            'bg_color': '#f5f5f5',
            'icon': '●',
            'text': obj.get_status_display()
        })
        
        # Add processing time information
        time_info = ''
        if obj.status == 'processing' and obj.uploaded_at:
            from django.utils import timezone
            processing_time = timezone.now() - obj.uploaded_at
            total_seconds = processing_time.total_seconds()
            if total_seconds < 60:
                seconds = int(total_seconds)
                milliseconds = int((total_seconds - seconds) * 1000)
                time_info = f' ({seconds}s {milliseconds}ms)'
            else:
                minutes = int(total_seconds / 60)
                seconds = int(total_seconds % 60)
                time_info = f' ({minutes}m {seconds}s)'
        elif obj.status == 'completed' and obj.processed_at and obj.uploaded_at:
            processing_time = obj.processed_at - obj.uploaded_at
            total_seconds = processing_time.total_seconds()
            if total_seconds < 60:
                seconds = int(total_seconds)
                milliseconds = int((total_seconds - seconds) * 1000)
                time_info = f' ({seconds}s {milliseconds}ms)'
            else:
                minutes = int(total_seconds / 60)
                seconds = int(total_seconds % 60)
                time_info = f' ({minutes}m {seconds}s)'
        
        return format_html(
            '<span style="'
            'display: inline-block; '
            'padding: 4px 8px; '
            'border-radius: 12px; '
            'background-color: {}; '
            'color: {}; '
            'font-weight: bold; '
            'font-size: 11px; '
            'border: 1px solid {}; '
            'white-space: nowrap;'
            '">{} {}{}</span>',
            config['bg_color'],
            config['color'],
            config['color'],
            config['icon'],
            config['text'],
            time_info
        )
    status_badge.short_description = 'Status'
    
    def processing_summary(self, obj):
        """Display enhanced processing summary with detailed statistics and error information."""
        if obj.status == 'pending':
            return format_html('<span style="color: #666; font-style: italic;">Awaiting processing</span>')
        
        if obj.status == 'processing':
            return format_html('<span style="color: #2196f3; font-style: italic;">🔄 Processing in progress...</span>')
        
        # Build detailed summary
        summary_parts = []
        total_items = 0
        
        # Categories summary
        if obj.categories_created or obj.categories_updated:
            cat_total = obj.categories_created + obj.categories_updated
            total_items += cat_total
            cat_details = []
            if obj.categories_created:
                cat_details.append(f'{obj.categories_created} new')
            if obj.categories_updated:
                cat_details.append(f'{obj.categories_updated} updated')
            summary_parts.append(f'📁 {cat_total} categories ({", ".join(cat_details)})')
        
        # Products summary
        if obj.products_created or obj.products_updated:
            prod_total = obj.products_created + obj.products_updated
            total_items += prod_total
            prod_details = []
            if obj.products_created:
                prod_details.append(f'{obj.products_created} new')
            if obj.products_updated:
                prod_details.append(f'{obj.products_updated} updated')
            summary_parts.append(f'📦 {prod_total} products ({", ".join(prod_details)})')
        
        # Images summary
        if obj.images_processed:
            summary_parts.append(f'🖼️ {obj.images_processed} images')
        
        # Category tracking details
        if obj.category_stats:
            try:
                stats = obj.category_stats
                total_categories = len(stats)
                total_expected = sum(cat.get('expected', 0) for cat in stats.values())
                total_uploaded = sum(cat.get('uploaded', 0) for cat in stats.values())
                
                if total_categories > 0:
                    summary_parts.append(f'📊 {total_categories} category folders')
                
                if total_expected > 0 and total_uploaded != total_expected:
                    summary_parts.append(f'📈 {total_uploaded}/{total_expected} expected products')
            except Exception:
                pass
        
        # Empty categories
        if obj.empty_categories:
            try:
                empty_count = len(obj.empty_categories)
                if empty_count > 0:
                    summary_parts.append(f'📂 {empty_count} empty folders')
            except Exception:
                pass
        
        # Error information
        error_info = ''
        total_detailed_errors = 0
        
        # Count detailed errors from category tracking
        if obj.detailed_errors:
            try:
                total_detailed_errors = len(obj.detailed_errors)
            except Exception:
                pass
        
        if obj.status == 'failed':
            if obj.error_log:
                error_count = len([line for line in obj.error_log.split('\n') if line.strip()])
                if total_detailed_errors > 0:
                    error_info = f' | ❌ {error_count} errors ({total_detailed_errors} detailed)'
                else:
                    error_info = f' | ❌ {error_count} errors'
            else:
                if total_detailed_errors > 0:
                    error_info = f' | ❌ Processing failed ({total_detailed_errors} detailed errors)'
                else:
                    error_info = ' | ❌ Processing failed'
        elif obj.error_log or total_detailed_errors > 0:
            # Completed with some errors
            error_count = len([line for line in obj.error_log.split('\n') if line.strip()]) if obj.error_log else 0
            if error_count > 0 and total_detailed_errors > 0:
                error_info = f' | ⚠️ {error_count} warnings ({total_detailed_errors} detailed)'
            elif error_count > 0:
                error_info = f' | ⚠️ {error_count} warnings'
            elif total_detailed_errors > 0:
                error_info = f' | ⚠️ {total_detailed_errors} detailed errors'
        
        # Build final summary
        if summary_parts:
            main_summary = ' | '.join(summary_parts)
            if total_items > 0:
                main_summary = f'✅ Total: {total_items} items | {main_summary}'
        else:
            main_summary = '❌ No items processed'
        
        # Add processing time if available
        time_info = ''
        if obj.processed_at and obj.uploaded_at:
            processing_time = obj.processed_at - obj.uploaded_at
            total_seconds = processing_time.total_seconds()
            
            if total_seconds < 60:
                # Show seconds with milliseconds for times under 1 minute
                milliseconds = int((total_seconds % 1) * 1000)
                seconds = int(total_seconds)
                time_info = f' | ⏱️ {seconds}.{milliseconds:03d}s'
            else:
                # Show minutes and seconds for longer times
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                time_info = f' | ⏱️ {minutes}m {seconds}s'
        
        # Color coding based on status
        if obj.status == 'completed':
            color = '#4caf50' if not error_info or '⚠️' in error_info else '#4caf50'
        elif obj.status == 'failed':
            color = '#f44336'
        else:
            color = '#666'
        
        return format_html(
            '<span style="color: {}; font-size: 12px;">{}{}{}</span>',
            color,
            main_summary,
            error_info,
            time_info
        )
    processing_summary.short_description = 'Summary'
    
    def category_summary(self, obj):
        """Display category-wise product count summary."""
        if not obj.category_stats:
            return format_html('<span style="color: #666;">No data</span>')
        
        try:
            stats = obj.category_stats
            total_categories = len(stats)
            total_expected = sum(cat.get('expected', 0) for cat in stats.values())
            total_uploaded = sum(cat.get('uploaded', 0) for cat in stats.values())
            total_errors = sum(len(cat.get('errors', [])) for cat in stats.values())
            
            # Count empty categories
            empty_count = len(obj.empty_categories) if obj.empty_categories else 0
            
            summary_parts = []
            
            if total_categories > 0:
                summary_parts.append(f'<strong>{total_categories}</strong> categories')
            
            if total_expected > 0:
                success_rate = (total_uploaded / total_expected) * 100 if total_expected > 0 else 0
                color = '#28a745' if success_rate >= 90 else '#ffc107' if success_rate >= 70 else '#dc3545'
                summary_parts.append(
                    f'<span style="color: {color};"><strong>{total_uploaded}/{total_expected}</strong> products ({success_rate:.1f}%)</span>'
                )
            
            if total_errors > 0:
                summary_parts.append(f'<span style="color: #dc3545;"><strong>{total_errors}</strong> errors</span>')
            
            if empty_count > 0:
                summary_parts.append(f'<span style="color: #fd7e14;"><strong>{empty_count}</strong> empty folders</span>')
            
            if not summary_parts:
                return format_html('<span style="color: #666;">No data</span>')
            
            return format_html(' | '.join(summary_parts))
            
        except Exception as e:
            return format_html(f'<span style="color: #dc3545;">Error: {str(e)}</span>')
    
    category_summary.short_description = 'Category Stats'
    
    def actions_column(self, obj):
        """Display enhanced action buttons and error details for each upload."""
        actions = []
        
        if obj.status == 'pending':
            actions.append(
                format_html(
                    '<a href="{}" class="bulk-upload-btn bulk-upload-btn--process" title="Process this bulk upload">'
                    '<span class="icon">▶️</span>Process</a>',
                    reverse("admin:products_bulkupload_process") + f"?ids={obj.id}",
                )
            )
        elif obj.status == 'failed':
            actions.append(
                format_html(
                    '<a href="{}" class="bulk-upload-btn bulk-upload-btn--retry" title="Retry processing this failed upload">'
                    '<span class="icon">🔄</span>Retry</a>',
                    reverse("admin:products_bulkupload_reprocess") + f"?ids={obj.id}",
                )
            )
        
        # Add error details button for failed uploads or completed with errors
        if obj.error_log and obj.error_log.strip():
            error_count = len([line for line in obj.error_log.split('\n') if line.strip()])
            
            # Create a link to view detailed errors in the admin detail page
            detail_url = reverse('admin:products_bulkupload_change', args=[obj.id])
            actions.append(
                format_html(
                    '<a href="{}#category-tracking" class="bulk-upload-btn bulk-upload-btn--errors" '
                    'title="View detailed error analysis ({} errors)">'
                    '<span class="icon">⚠️</span>Errors<span class="error-count">{}</span></a>',
                    detail_url,
                    error_count,
                    error_count,
                )
            )
        
        # Add download link for the uploaded file
        if obj.zip_file:
            actions.append(
                format_html(
                    '<a href="{}" class="bulk-upload-btn bulk-upload-btn--download" '
                    'title="Download original ZIP file" download>'
                    '<span class="icon">📥</span>Download</a>',
                    obj.zip_file.url,
                )
            )
        
        if not actions:
            return format_html('<span style="color: #666;">-</span>')
        
        return format_html(
            '<div class="bulk-upload-actions">{}</div>',
            format_html_join(' ', '{}', ((a,) for a in actions))
        )

    actions_column.short_description = 'Actions'

    def formatted_category_stats(self, obj):
        """Display category statistics in a user-friendly format."""
        if not obj.category_stats:
            return format_html('<span style="color: #666; font-style: italic;">No category data available</span>')
        
        try:
            stats = obj.category_stats
            if not stats:
                return format_html('<span style="color: #666; font-style: italic;">No categories processed</span>')
            
            html_parts = []
            html_parts.append('<div style="font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #dee2e6;">')
            html_parts.append('<h4 style="margin: 0 0 10px 0; color: #495057;">📊 Category Processing Summary</h4>')
            
            total_expected = sum(cat.get('expected', 0) for cat in stats.values())
            total_uploaded = sum(cat.get('uploaded', 0) for cat in stats.values())
            total_errors = sum(len(cat.get('errors', [])) for cat in stats.values())
            
            # Overall summary
            html_parts.append('<div style="margin-bottom: 15px; padding: 8px; background: #e9ecef; border-radius: 3px;">')
            html_parts.append(f'<strong>Overall:</strong> {len(stats)} categories, {total_uploaded}/{total_expected} products processed')
            if total_errors > 0:
                html_parts.append(f', <span style="color: #dc3545;">{total_errors} errors</span>')
            html_parts.append('</div>')
            
            # Category details
            for category, data in stats.items():
                expected = data.get('expected', 0)
                uploaded = data.get('uploaded', 0)
                errors = data.get('errors', [])
                
                # Category header
                success_rate = (uploaded / expected * 100) if expected > 0 else 0
                color = '#28a745' if success_rate >= 90 else '#ffc107' if success_rate >= 70 else '#dc3545'
                
                html_parts.append('<div style="margin-bottom: 10px; padding: 8px; border-left: 3px solid {}; background: #ffffff;">'.format(color))
                html_parts.append(f'<strong style="color: {color};">{category.upper()}</strong>: ')
                html_parts.append(f'{uploaded}/{expected} products ({success_rate:.1f}%)')
                
                if errors:
                    html_parts.append(f' - <span style="color: #dc3545;">{len(errors)} errors</span>')
                
                html_parts.append('</div>')
            
            html_parts.append('</div>')
            
            return format_html(''.join(html_parts))
            
        except Exception as e:
            return format_html(f'<span style="color: #dc3545;">Error displaying stats: {str(e)}</span>')
    
    formatted_category_stats.short_description = 'Category Statistics'
    
    def formatted_detailed_errors(self, obj):
        """Display detailed errors in a user-friendly format with expected vs given data."""
        if not obj.detailed_errors:
            return format_html('<span style="color: #28a745; font-style: italic;">✅ No errors found</span>')
        
        try:
            errors = obj.detailed_errors
            if not errors:
                return format_html('<span style="color: #28a745; font-style: italic;">✅ No errors found</span>')
            
            html_parts = []
            html_parts.append('<div style="font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #dee2e6;">')
            html_parts.append(f'<h4 style="margin: 0 0 10px 0; color: #dc3545;">❌ Processing Errors ({len(errors)} total)</h4>')
            
            # Group errors by type
            error_groups = {}
            for error in errors:
                error_type = error.get('error_type', 'Unknown')
                if error_type not in error_groups:
                    error_groups[error_type] = []
                error_groups[error_type].append(error)
            
            for error_type, error_list in error_groups.items():
                html_parts.append(f'<div style="margin-bottom: 15px;">')
                html_parts.append(f'<h5 style="margin: 0 0 8px 0; color: #495057; border-bottom: 1px solid #dee2e6; padding-bottom: 4px;">{error_type} ({len(error_list)} errors)</h5>')
                
                for error in error_list:
                    html_parts.append('<div style="margin-bottom: 8px; padding: 8px; background: #ffffff; border-left: 3px solid #dc3545;">')
                    
                    # Product and category info
                    product = error.get('product', 'Unknown')
                    category = error.get('category', 'Unknown')
                    html_parts.append(f'<strong>Product:</strong> {product} <span style="color: #6c757d;">({category})</span><br>')
                    
                    # Expected vs Given
                    expected = error.get('expected', 'Not specified')
                    given = error.get('given', 'Not specified')
                    html_parts.append(f'<strong style="color: #28a745;">Expected:</strong> {expected}<br>')
                    html_parts.append(f'<strong style="color: #dc3545;">Given:</strong> {given}<br>')
                    
                    # Error message
                    message = error.get('message', 'No message available')
                    html_parts.append(f'<strong>Error:</strong> <span style="color: #dc3545;">{message}</span>')
                    
                    html_parts.append('</div>')
                
                html_parts.append('</div>')
            
            html_parts.append('</div>')
            
            return format_html(''.join(html_parts))
            
        except Exception as e:
            return format_html(f'<span style="color: #dc3545;">Error displaying errors: {str(e)}</span>')
    
    formatted_detailed_errors.short_description = 'Detailed Error Analysis'
    
    def formatted_empty_categories(self, obj):
        """Display empty categories in a user-friendly format."""
        if not obj.empty_categories:
            return format_html('<span style="color: #28a745; font-style: italic;">✅ No empty categories found</span>')
        
        try:
            empty_cats = obj.empty_categories
            if not empty_cats:
                return format_html('<span style="color: #28a745; font-style: italic;">✅ No empty categories found</span>')
            
            html_parts = []
            html_parts.append('<div style="font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #dee2e6;">')
            html_parts.append(f'<h4 style="margin: 0 0 10px 0; color: #fd7e14;">📂 Empty Category Folders ({len(empty_cats)} found)</h4>')
            html_parts.append('<p style="margin: 0 0 10px 0; color: #6c757d;">These category folders were found but contained no valid product data:</p>')
            
            for i, category in enumerate(empty_cats, 1):
                html_parts.append('<div style="margin-bottom: 5px; padding: 6px; background: #ffffff; border-left: 3px solid #fd7e14;">')
                html_parts.append(f'<strong>{i}.</strong> {category.upper()}')
                html_parts.append('</div>')
            
            html_parts.append('<div style="margin-top: 10px; padding: 8px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 3px;">')
            html_parts.append('<strong>💡 Tip:</strong> Check if these folders contain the required product data files or if the folder names match the expected format.')
            html_parts.append('</div>')
            
            html_parts.append('</div>')
            
            return format_html(''.join(html_parts))
            
        except Exception as e:
            return format_html(f'<span style="color: #dc3545;">Error displaying empty categories: {str(e)}</span>')
    
    formatted_empty_categories.short_description = 'Empty Categories'
    
    def processing_results_summary(self, obj):
        """Display comprehensive processing results summary."""
        if obj.status == 'pending':
            return format_html('<span style="color: #666; font-style: italic;">⏳ Processing not started yet</span>')
        
        if obj.status == 'processing':
            return format_html('<span style="color: #2196f3; font-style: italic;">🔄 Processing in progress...</span>')
        
        try:
            html_parts = []
            html_parts.append('<div style="font-family: monospace; background: #f8f9fa; padding: 15px; border-radius: 4px; border: 1px solid #dee2e6;">')
            
            # Status header
            if obj.status == 'completed':
                html_parts.append('<h4 style="margin: 0 0 15px 0; color: #28a745;">✅ Processing Completed Successfully</h4>')
            elif obj.status == 'failed':
                html_parts.append('<h4 style="margin: 0 0 15px 0; color: #dc3545;">❌ Processing Failed</h4>')
            
            # Processing statistics from category_stats
            if obj.category_stats:
                stats = obj.category_stats
                total_categories = len(stats)
                total_expected = sum(cat.get('expected', 0) for cat in stats.values())
                total_uploaded = sum(cat.get('uploaded', 0) for cat in stats.values())
                total_errors = sum(len(cat.get('errors', [])) for cat in stats.values())
                
                html_parts.append('<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 15px;">')
                
                # Categories processed
                html_parts.append('<div style="padding: 10px; background: #e3f2fd; border-radius: 3px; text-align: center;">')
                html_parts.append(f'<div style="font-size: 24px; font-weight: bold; color: #1976d2;">{total_categories}</div>')
                html_parts.append('<div style="color: #1976d2; font-weight: bold;">Categories</div>')
                html_parts.append('</div>')
                
                # Products processed
                success_rate = (total_uploaded / total_expected * 100) if total_expected > 0 else 0
                color = '#28a745' if success_rate >= 90 else '#ffc107' if success_rate >= 70 else '#dc3545'
                html_parts.append(f'<div style="padding: 10px; background: {color}20; border-radius: 3px; text-align: center;">')
                html_parts.append(f'<div style="font-size: 24px; font-weight: bold; color: {color};">{total_uploaded}/{total_expected}</div>')
                html_parts.append(f'<div style="color: {color}; font-weight: bold;">Products ({success_rate:.1f}%)</div>')
                html_parts.append('</div>')
                
                # Errors
                if total_errors > 0:
                    html_parts.append('<div style="padding: 10px; background: #ffebee; border-radius: 3px; text-align: center;">')
                    html_parts.append(f'<div style="font-size: 24px; font-weight: bold; color: #dc3545;">{total_errors}</div>')
                    html_parts.append('<div style="color: #dc3545; font-weight: bold;">Errors</div>')
                    html_parts.append('</div>')
                
                html_parts.append('</div>')
                
                # Category breakdown
                if total_categories > 0:
                    html_parts.append('<div style="margin-bottom: 15px;">')
                    html_parts.append('<h5 style="margin: 0 0 10px 0; color: #495057; border-bottom: 1px solid #dee2e6; padding-bottom: 5px;">📁 Category Breakdown</h5>')
                    
                    for category, data in stats.items():
                        expected = data.get('expected', 0)
                        uploaded = data.get('uploaded', 0)
                        errors = data.get('errors', [])
                        
                        success_rate = (uploaded / expected * 100) if expected > 0 else 0
                        color = '#28a745' if success_rate >= 90 else '#ffc107' if success_rate >= 70 else '#dc3545'
                        
                        html_parts.append('<div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 10px; margin-bottom: 5px; background: #ffffff; border-left: 3px solid {}; border-radius: 0 3px 3px 0;">'.format(color))
                        html_parts.append(f'<span style="font-weight: bold;">{category.upper()}</span>')
                        html_parts.append(f'<span style="color: {color}; font-weight: bold;">{uploaded}/{expected} ({success_rate:.0f}%)</span>')
                        html_parts.append('</div>')
                    
                    html_parts.append('</div>')
            
            # Empty categories
            if obj.empty_categories:
                empty_count = len(obj.empty_categories)
                html_parts.append('<div style="padding: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 3px; margin-bottom: 10px;">')
                html_parts.append(f'<strong style="color: #856404;">⚠️ {empty_count} Empty Categories:</strong> ')
                html_parts.append(', '.join(obj.empty_categories[:5]))
                if empty_count > 5:
                    html_parts.append(f' and {empty_count - 5} more...')
                html_parts.append('</div>')
            
            # Processing time
            if obj.processed_at and obj.uploaded_at:
                processing_time = obj.processed_at - obj.uploaded_at
                if processing_time.total_seconds() < 60:
                    seconds = int(processing_time.total_seconds())
                    milliseconds = int((processing_time.total_seconds() - seconds) * 1000)
                    time_str = f'{seconds} seconds, {milliseconds} milliseconds'
                else:
                    minutes = int(processing_time.total_seconds() / 60)
                    seconds = int(processing_time.total_seconds() % 60)
                    time_str = f'{minutes} minutes, {seconds} seconds'
                
                html_parts.append('<div style="text-align: center; padding: 8px; background: #e9ecef; border-radius: 3px; color: #495057;">')
                html_parts.append(f'⏱️ Processing completed in {time_str}')
                html_parts.append('</div>')
            
            html_parts.append('</div>')
            
            return format_html(''.join(html_parts))
            
        except Exception as e:
            return format_html(f'<span style="color: #dc3545;">Error displaying results: {str(e)}</span>')
    
    processing_results_summary.short_description = 'Processing Results'
    
    def get_urls(self):
        """Add custom URLs for processing actions."""
        urls = super().get_urls()
        custom_urls = [
            path('process/', self.admin_site.admin_view(self.process_uploads_view), 
                 name='products_bulkupload_process'),
            path('reprocess/', self.admin_site.admin_view(self.reprocess_uploads_view), 
                 name='products_bulkupload_reprocess'),
        ]
        return custom_urls + urls
    
    def process_uploads_view(self, request):
        """Custom view to process specific uploads."""
        ids = request.GET.get('ids', '').split(',')
        uploads = BulkUpload.objects.filter(id__in=ids, status='pending')
        
        for upload in uploads:
            self._process_upload_async(upload, request)
        
        messages.info(request, f'Started processing {uploads.count()} upload(s).')
        return HttpResponseRedirect(reverse('admin:products_bulkupload_changelist'))
    
    def reprocess_uploads_view(self, request):
        """Custom view to reprocess failed uploads."""
        ids = request.GET.get('ids', '').split(',')
        uploads = BulkUpload.objects.filter(id__in=ids, status='failed')
        
        for upload in uploads:
            upload.status = 'pending'
            upload.error_log = None
            upload.save()
            self._process_upload_async(upload, request)
        
        messages.info(request, f'Started reprocessing {uploads.count()} upload(s).')
        return HttpResponseRedirect(reverse('admin:products_bulkupload_changelist'))
    
    def process_selected_uploads(self, request, queryset):
        """Admin action to process selected pending uploads."""
        pending_uploads = queryset.filter(status='pending')
        
        for upload in pending_uploads:
            self._process_upload_async(upload, request)
        
        self.message_user(
            request,
            f'Started processing {pending_uploads.count()} upload(s).',
            messages.INFO
        )
    process_selected_uploads.short_description = 'Process selected pending uploads'
    
    def reprocess_failed_uploads(self, request, queryset):
        """Admin action to reprocess selected failed uploads."""
        failed_uploads = queryset.filter(status='failed')
        
        for upload in failed_uploads:
            upload.status = 'pending'
            upload.error_log = None
            upload.save()
            self._process_upload_async(upload, request)
        
        self.message_user(
            request,
            f'Started reprocessing {failed_uploads.count()} upload(s).',
            messages.INFO
        )
    reprocess_failed_uploads.short_description = 'Reprocess selected failed uploads'
    
    def has_delete_permission(self, request, obj=None):
        """Only allow deletion of completed or failed uploads."""
        if obj and obj.status in ['processing']:
            return False
        return super().has_delete_permission(request, obj)
    
    def has_change_permission(self, request, obj=None):
        """Restrict editing of uploads that are being processed."""
        if obj and obj.status == 'processing':
            return False
        return super().has_change_permission(request, obj)


admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
