# categories/models.py
from django.db import models
from taggit.managers import TaggableManager
from django.core.exceptions import ValidationError


def validate_image(image):
    """ Validates the size and format of the uploaded image. """
    file_size = image.size
    if file_size > 2 * 1024 * 1024:  # Limit to 2MB
        raise ValidationError("Maximum file size that can be uploaded is 2MB")
    if not image.name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise ValidationError("Image must be in PNG, JPG, JPEG, or WEBP format.")


def get_placeholder_image():
    return '/Users/pranshudixit/Downloads/bedroom.webp'

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    secondary_description = models.TextField(blank=True, null=True)
    tags = TaggableManager()
    image = models.ImageField(upload_to='category_images/', validators=[validate_image], default=get_placeholder_image)
    secondary_image = models.ImageField(upload_to='category_images/', validators=[validate_image], blank=True, null=True, default=get_placeholder_image)
    tags = TaggableManager() 


    def __str__(self):
        return self.name
