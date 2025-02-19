from django.contrib import admin
from django import forms
from .models import BestSeller, Product, ProductImage, PriceWeight, validate_image
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError


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
        if count < 3:
            raise ValidationError('At least 3 price-weight combinations are required.')
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
    list_display = ['name', 'slug', 'description', 'category', 'get_tags', 'is_active']
    search_fields = ['name', 'description']
    list_filter = ['category', 'is_active']
    inlines = [PriceWeightInline, ProductImageInline]

    # Custom method to display tags in the admin list view
    def get_tags(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    get_tags.short_description = 'Tags'


@admin.register(BestSeller)
class BestSellerAdmin(admin.ModelAdmin):
    list_display = ('product', 'added_on')

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
