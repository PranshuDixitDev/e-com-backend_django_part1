#!/usr/bin/env python
import os
import sys
import django
import logging

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myecommerce.settings')
django.setup()

# Set up logging to see detailed processing
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

# Enable info logging for products.services
logger = logging.getLogger('products.services')
logger.setLevel(logging.INFO)

from products.services import CatalogProcessingService
from products.models import Category, Product, BulkUpload
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import CustomUser

def test_bulk_upload():
    print("Testing bulk upload functionality...")
    
    # Count before upload
    categories_before = Category.objects.count()
    products_before = Product.objects.count()
    print(f"Categories before: {categories_before}")
    print(f"Products before: {products_before}")
    
    # Test with the actual zip file
    zip_file_path = "/Users/pranshudixit/Downloads/CATALOG UPLOAD/CATALOG UPLOAD.zip"
    
    if not os.path.exists(zip_file_path):
        print(f"Error: Zip file not found at {zip_file_path}")
        return
    
    try:
        with open(zip_file_path, 'rb') as f:
            zip_content = f.read()
        
        print(f"Catalog file size: {len(zip_content) / (1024*1024):.2f} MB")
        
        # Create uploaded file object
        uploaded_file = SimpleUploadedFile(
            name="CATALOG UPLOAD.zip",
            content=zip_content,
            content_type="application/zip"
        )
        
        # Use an existing superuser for the upload
        user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            print("Error: No superuser found. Please create a superuser first.")
            return
        
        # Create BulkUpload instance
        bulk_upload = BulkUpload.objects.create(
            zip_file=uploaded_file,
            uploaded_by=user
        )
        
        # Initialize service and process upload
        service = CatalogProcessingService(bulk_upload)
        success = service.process_catalog()
        
        # Refresh bulk_upload to get updated stats
        bulk_upload.refresh_from_db()
        
        result = {
            'success': success,
            'error': bulk_upload.error_log if not success else None,
            'categories_created': service.categories_created,
            'categories_updated': service.categories_updated,
            'products_created': service.products_created,
            'products_updated': service.products_updated,
            'images_processed': service.images_processed
        }
        
        print(f"Upload result: {result}")
        
        # Print detailed error information
        if hasattr(service, 'errors') and service.errors:
            print("\n🔍 Detailed Errors:")
            for error in service.errors:
                print(f"  - {error}")
        
        if hasattr(service, 'processing_notes') and service.processing_notes:
            print("\n📝 Processing Notes:")
            for note in service.processing_notes:
                print(f"  - {note}")
        
        # Count after upload
        categories_after = Category.objects.count()
        products_after = Product.objects.count()
        
        print(f"\n" + "="*60)
        print(f"FINAL SUMMARY")
        print(f"="*60)
        print(f"Categories before: {categories_before}")
        print(f"Categories after: {categories_after} (added: {categories_after - categories_before})")
        print(f"Products before: {products_before}")
        print(f"Products after: {products_after} (added: {products_after - products_before})")
        print(f"Categories created: {result.get('categories_created', 0)}")
        print(f"Categories updated: {result.get('categories_updated', 0)}")
        print(f"Products created: {result.get('products_created', 0)}")
        print(f"Products updated: {result.get('products_updated', 0)}")
        print(f"Images processed: {result.get('images_processed', 0)}")
        
        if result.get('success'):
            print(f"\n✅ BULK UPLOAD COMPLETED SUCCESSFULLY!")
        else:
            print(f"\n❌ BULK UPLOAD FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
        print(f"="*60)
            
    except Exception as e:
        print(f"❌ Error during bulk upload test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bulk_upload()