from django.contrib import admin
from django import forms
from .models import Product, ProductImage, validate_image
from django.core.exceptions import ValidationError


class ProductImageForm(forms.ModelForm):
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            validate_image(image)  # Keeping the custom image validation
            # scan_file_for_viruses(image)
        return image
    
    class Meta:
        model = ProductImage
        fields = '__all__'
        validators = [validate_image]

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageForm
    extra = 1  # Number of empty rows to display
    fields = ['image', 'description']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'category',
                     'price_weights', 'get_tags']
    search_fields = ['name', 'description']
    list_filter = ['category']
    inlines = [ProductImageInline]

    def get_tags(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    get_tags.short_description = 'Tags'

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        try:
            for instance in instances:
                instance.save()
            formset.save_m2m()
        except ValidationError as e:
            for form in formset.forms:
                form.errors['__all__'] = form.error_class([e.message])

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
