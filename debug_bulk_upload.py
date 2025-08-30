#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/pranshudixit/code_base/e-com-backend_django_part1')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myecommerce.settings')
django.setup()

from products.services import CatalogProcessingService
from products.validators import BulkUploadValidator
from products.models import BulkUpload
import json

def debug_bulk_upload():
    print("=== Debugging Bulk Upload Process ===")
    
    # Get the latest bulk upload for testing
    try:
        bulk_upload = BulkUpload.objects.latest('uploaded_at')
        print(f"Using bulk upload ID: {bulk_upload.id}")
    except BulkUpload.DoesNotExist:
        print("No bulk upload found in database")
        return
    
    # Initialize service
    service = CatalogProcessingService(bulk_upload)
    validator = BulkUploadValidator()
    
    # Test directory path
    product_dir = '/Users/pranshudixit/code_base/e-com-backend_django_part1/media/bulk_uploads/extracted/CATALOG_UPLOAD_Aasanji.zip/PICKLES/MUK_fennel seeds salted variyali'
    
    print(f"\n1. Testing directory: {product_dir}")
    print(f"Directory exists: {os.path.exists(product_dir)}")
    
    if os.path.exists(product_dir):
        print(f"Directory contents: {os.listdir(product_dir)}")
        
        # Test extract product name
        product_name = service._extract_product_name('MUK_fennel seeds salted variyali')
        print(f"\n2. Extracted product name: '{product_name}'")
        
        # Test read product data with debug
        print(f"\n3. Testing _read_product_data with directory name: 'MUK_fennel seeds salted variyali'")
        product_data = service._read_product_data(product_dir, 'MUK_fennel seeds salted variyali')
        print(f"Product data result: {product_data}")
        
        if product_data:
            print(f"Product data type: {type(product_data)}")
            print(f"Product data keys: {list(product_data.keys()) if isinstance(product_data, dict) else 'Not a dict'}")
            
            # Test validation
            print(f"\n4. Testing validation:")
            is_valid = validator.validate_product_data_structure(product_data)
            print(f"Validation result: {is_valid}")
            
            if not is_valid:
                print("Validation failed - checking why:")
                if not isinstance(product_data, dict):
                    print(f"  - Data is not a dict, it's: {type(product_data)}")
                else:
                    allowed_fields = ['description', 'secondary_description', 'tags', 'price', 'weight']
                    for key in product_data.keys():
                        if key not in allowed_fields:
                            print(f"  - Invalid field found: '{key}'")
        
        # Test with extracted product name
        print(f"\n5. Testing _read_product_data with extracted name: '{product_name}'")
        product_data2 = service._read_product_data(product_dir, product_name)
        print(f"Product data result: {product_data2}")
        
        # Test the actual process_product_directory method
        print(f"\n6. Testing _process_product_directory:")
        try:
            result = service._process_product_directory(product_dir, 'MUK_fennel seeds salted variyali')
            print(f"Process result: {result}")
        except Exception as e:
            print(f"Process error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_bulk_upload()