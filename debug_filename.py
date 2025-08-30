#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append('/Users/pranshudixit/code_base/e-com-backend_django_part1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myecommerce.settings')
django.setup()

from products.models import BulkUpload
from products.services import CatalogProcessingService

# Debug the filename matching
bulk_upload = BulkUpload.objects.get(id=36)
service = CatalogProcessingService(bulk_upload)
product_dir_path = '/Users/pranshudixit/Downloads/CATALOG UPLOAD/4_MUK_mukhwas/MUK_products/MUK_fennel seeds salted variyali'
product_dir_name = 'MUK_fennel seeds salted variyali'

print('Directory contents:')
print(os.listdir(product_dir_path))
print('\nTesting filename patterns:')
possible_filenames = [
    f'{product_dir_name}.txt',  # Exact match
    f'{product_dir_name.replace("_", "_ ")}.txt',  # With space after underscore
    f'{product_dir_name.replace("_", " ")}.txt',  # Replace underscore with space
]
print('Possible filenames:', possible_filenames)

txt_files = [f for f in os.listdir(product_dir_path) if f.endswith('.txt')]
print('Actual txt files:', txt_files)

for filename in possible_filenames + txt_files:
    potential_file = os.path.join(product_dir_path, filename)
    print(f'Checking: {filename} - Exists: {os.path.exists(potential_file)}')

# Test the actual method
print('\nTesting _read_product_data method:')
result = service._read_product_data(product_dir_path, product_dir_name)
print(f'Result: {result}')