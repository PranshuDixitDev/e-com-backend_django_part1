from django.db import models
from categories.models import Category
from taggit.managers import TaggableManager
import re
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils.text import slugify
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.db import transaction
from django.db.models import F
from django.conf import settings
from django.utils import timezone
import zipfile
import os


def validate_image(image):
    """ Validates the size and format of the uploaded image. """
    file_size = image.size
    max_size = 2*1024*1024  # 2MB
    
    if file_size > max_size:
        raise ValidationError(f"Maximum file size allowed is {max_size/1024/1024}MB")
    
    allowed_formats = ['.png', '.jpg', '.jpeg', '.webp']
    if not any(image.name.lower().endswith(fmt) for fmt in allowed_formats):
        raise ValidationError(f"Image must be in {', '.join(allowed_formats)} format.")

class PriceWeight(models.Model):
    """ Stores price and weight combinations for a product, ensures uniqueness per product. """
    product = models.ForeignKey('Product', related_name='price_weights', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], default=Decimal('2000.00'))
    weight = models.CharField(max_length=50, default='100gms')
    inventory = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], db_index=True)

    class Meta:
        unique_together = ('product', 'price', 'weight')


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product availability after saving a PriceWeight instance
        self.product.update_availability()
    
    @transaction.atomic
    def decrease_inventory(self, quantity):
        updated = PriceWeight.objects.filter(pk=self.pk, inventory__gte=quantity).update(inventory=F('inventory') - quantity)
        if updated:
            self.refresh_from_db(fields=['inventory'])
            return True
        return False

    def __str__(self):
        return f"{self.product.name} - {self.weight} - ₹{self.price} (Inventory: {self.inventory})"
    
class Product(models.Model):
    """ Main product model. """
    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    tags = TaggableManager()
    is_active = models.BooleanField(default=True, help_text="Uncheck this box to deactivate the product.", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness by appending a counter if needed
            counter = 1
            original_slug = self.slug
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def update_availability(self):
        in_stock = self.price_weights.filter(inventory__gt=0).exists()
        if self.is_active != in_stock:
            self.is_active = in_stock
            self.save(update_fields=['is_active'])

    def __str__(self):
        return self.name

def product_image_path(instance, filename):
    # Files will be uploaded to MEDIA_ROOT/products/<product_id>/<filename>
    return 'products/{0}/{1}'.format(instance.product.id, filename)


class ProductImage(models.Model):
    """ Model to manage images associated with products. """
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=product_image_path, validators=[validate_image])
    description = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            self.__class__.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
            
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Image for {self.product.name}"


class BestSeller(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product.name


def validate_zip_file(file):
    """Validate uploaded zip file format and size."""
    if not file.name.endswith('.zip'):
        raise ValidationError('File must be a ZIP archive.')
    
    # Check file size (400MB limit)
    max_size = 400 * 1024 * 1024  # 400MB
    if file.size > max_size:
        raise ValidationError(f'File size cannot exceed {max_size/1024/1024}MB.')
    
    # Validate zip file structure
    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            # Basic validation - check if it's a valid zip
            zip_ref.testzip()
    except zipfile.BadZipFile:
        raise ValidationError('Invalid ZIP file format.')
    except Exception as e:
        raise ValidationError(f'Error reading ZIP file: {str(e)}')


def bulk_upload_path(instance, filename):
    """Generate upload path for bulk upload files."""
    return f'bulk_uploads/{instance.uploaded_by.username}/{timezone.now().strftime("%Y/%m/%d")}/{filename}'


class BulkUpload(models.Model):
    """Model to track bulk catalog uploads and their processing status."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    zip_file = models.FileField(
        upload_to=bulk_upload_path,
        validators=[validate_zip_file],
        help_text='Upload a ZIP file containing catalog data (max 400MB)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bulk_uploads'
    )
    
    # Processing statistics
    categories_created = models.PositiveIntegerField(default=0)
    categories_updated = models.PositiveIntegerField(default=0)
    products_created = models.PositiveIntegerField(default=0)
    products_updated = models.PositiveIntegerField(default=0)
    images_processed = models.PositiveIntegerField(default=0)
    
    # Category-wise product tracking
    category_stats = models.JSONField(
        default=dict,
        blank=True,
        help_text='Category-wise statistics: {category_name: {expected: int, uploaded: int, errors: []}}')
    empty_categories = models.JSONField(
        default=list,
        blank=True,
        help_text='List of category folders that were found empty')
    
    # Error tracking
    error_log = models.TextField(blank=True, null=True)
    processing_notes = models.TextField(blank=True, null=True)
    detailed_errors = models.JSONField(
        default=list,
        blank=True,
        help_text='Detailed error information with expected vs given data')
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Bulk Upload'
        verbose_name_plural = 'Bulk Uploads'
    
    def __str__(self):
        return f'Bulk Upload {self.id} - {self.get_status_display()}'
    
    def mark_as_processing(self):
        """Mark upload as currently being processed."""
        self.status = 'processing'
        self.save(update_fields=['status'])
    
    def mark_as_completed(self, notes=None):
        """Mark upload as successfully completed."""
        self.status = 'completed'
        self.processed_at = timezone.now()
        if notes:
            self.processing_notes = notes
        self.save(update_fields=['status', 'processed_at', 'processing_notes', 'category_stats', 'detailed_errors', 'empty_categories'])
    
    def mark_as_failed(self, error_message):
        """Mark upload as failed with error details."""
        self.status = 'failed'
        self.processed_at = timezone.now()
        self.error_log = error_message
        self.save(update_fields=['status', 'processed_at', 'error_log', 'category_stats', 'detailed_errors', 'empty_categories'])
    
    def get_file_size_display(self):
        """Return human-readable file size."""
        if self.zip_file:
            size = self.zip_file.size
            if size < 1024:
                return f'{size} bytes'
            elif size < 1024 * 1024:
                return f'{size / 1024:.1f} KB'
            else:
                return f'{size / (1024 * 1024):.1f} MB'
        return 'N/A'
    
    def delete(self, *args, **kwargs):
        """Override delete to remove associated file."""
        if self.zip_file:
            # Delete the file from storage
            if os.path.isfile(self.zip_file.path):
                os.remove(self.zip_file.path)
        super().delete(*args, **kwargs)
