from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Category

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'display_order', 'description', 'is_ordered']
    list_filter = ['display_order']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'secondary_description')
        }),
        ('Display Settings', {
            'fields': ('display_order',),
            'description': 'Set display order (1-8) to show category in ordered frontend list. Leave blank to exclude from ordered display.'
        }),
        ('Images', {
            'fields': ('image', 'secondary_image')
        }),
        ('Tags', {
            'fields': ('tags',)
        }),
    )
    
    readonly_fields = ['slug']
    
    def is_ordered(self, obj):
        """Display whether category has display order set."""
        return obj.display_order is not None
    is_ordered.boolean = True
    is_ordered.short_description = 'Ordered'
    
    def save_model(self, request, obj, form, change):
        """Custom save with validation and user feedback."""
        try:
            super().save_model(request, obj, form, change)
            if obj.display_order:
                messages.success(request, f'Category "{obj.name}" saved with display order {obj.display_order}.')
            else:
                messages.success(request, f'Category "{obj.name}" saved without display order.')
        except ValidationError as e:
            messages.error(request, f'Error saving category: {e}')
            raise
    
    def get_queryset(self, request):
        """Order queryset by display_order first, then name."""
        return super().get_queryset(request).order_by('display_order', 'name')
    
    class Media:
        css = {
            'all': ('admin/css/category_admin.css',)
        }

admin.site.register(Category, CategoryAdmin)
