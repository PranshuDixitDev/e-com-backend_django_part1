from django.db import models
from taggit.managers import TaggableManager

class Category(models.Model):
    category_id = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    tags = TaggableManager()

    def __str__(self):
        return self.name
