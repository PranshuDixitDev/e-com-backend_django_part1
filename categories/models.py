# categories/models.py
from django.db import models
from taggit.managers import TaggableManager
from django.core.exceptions import ValidationError
from django.utils.text import slugify



def validate_image(image):
    """ Validates the size and format of the uploaded image. """
    file_size = image.size
    if file_size > 2 * 1024 * 1024:  # Limit to 2MB
        raise ValidationError("Maximum file size that can be uploaded is 2MB")
    if not image.name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise ValidationError("Image must be in PNG, JPG, JPEG, or WEBP format.")



def validate_display_order(value):
    """Validates that display_order is within allowed range and enforces 8 category limit."""
    if value is not None:
        if value < 1 or value > 8:
            raise ValidationError("Display order must be between 1 and 8.")
        
        # Check if this display_order is already taken by another category
        from categories.models import Category
        existing_category = Category.objects.filter(display_order=value).first()
        if existing_category:
            raise ValidationError(f"Display order {value} is already assigned to category '{existing_category.name}'.")


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField()
    secondary_description = models.TextField(blank=True, null=True)
    display_order = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        unique=True,
        validators=[validate_display_order],
        help_text="Display order for frontend (1-8). Leave blank for categories not shown in ordered list."
    )
    tags = TaggableManager()
    image = models.ImageField(upload_to='category_images/',
                            validators=[validate_image],
                            blank=False, 
                            null=False)
    secondary_image = models.ImageField(upload_to='category_images/',
                                        validators=[validate_image],
                                        blank=True,
                                        null=True)
    is_active = models.BooleanField(
        default=True, 
        help_text="Uncheck this box to deactivate the category.", 
        db_index=True
    )

    class Meta:
        ordering = ['display_order', 'name']

    def clean(self):
        """Custom validation for the model."""
        super().clean()
        
        if self.display_order is not None:
            # Check if this display_order is already taken by another category
            existing_category = Category.objects.filter(display_order=self.display_order).exclude(pk=self.pk).first()
            if existing_category:
                raise ValidationError({
                    'display_order': f"Display order {self.display_order} is already assigned to category '{existing_category.name}'."
                })
            
            # Validate range
            if self.display_order < 1 or self.display_order > 8:
                raise ValidationError({
                    'display_order': "Display order must be between 1 and 8."
                })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            counter = 1
            original_slug = self.slug
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Run full_clean to trigger validation
        self.full_clean()
        super().save(*args, **kwargs)
        
    @classmethod
    def get_ordered_categories(cls):
        """Returns categories with display_order set, ordered by display_order."""
        return cls.objects.filter(display_order__isnull=False).order_by('display_order')
    
    @classmethod
    def get_available_display_orders(cls):
        """Returns a list of available display order numbers (1-8)."""
        used_orders = set(cls.objects.filter(display_order__isnull=False).values_list('display_order', flat=True))
        return [i for i in range(1, 9) if i not in used_orders]

    def __str__(self):
        return self.name
