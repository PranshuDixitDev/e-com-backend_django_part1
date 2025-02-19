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



class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField()
    secondary_description = models.TextField(blank=True, null=True)
    tags = TaggableManager()
    image = models.ImageField(upload_to='category_images/',
                            validators=[validate_image],
                            blank=False, 
                            null=False)
    secondary_image = models.ImageField(upload_to='category_images/',
                                        validators=[validate_image],
                                        blank=True,
                                        null=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            counter = 1
            original_slug = self.slug
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
