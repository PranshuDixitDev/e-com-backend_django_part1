from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from .models import Product, ProductImage

class ImageUploadTests(TestCase):
    def test_image_upload(self):
        product = Product.objects.create(name="Test Product", description="Test Description")
        image_data = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        ProductImage.objects.create(product=product, image=image_data)
        self.assertEqual(product.images.count(), 1)
