import pandas as pd
from io import StringIO
from rest_framework.exceptions import ValidationError
from .models import Product, Category, PriceWeight

def bulk_upload_products(file):
    # Determine file type and read data accordingly
    if file.name.endswith('.csv'):
        data_set = file.read().decode('UTF-8')
        data = pd.read_csv(StringIO(data_set))
    elif file.name.endswith(('.xls', '.xlsx')):
        data = pd.read_excel(file)
    else:
        raise ValidationError("Unsupported file format. Please upload a CSV or Excel file.")

    # Check if data is empty
    if data.empty:
        raise ValidationError("No data found in file.")

    required_columns = ['name', 'description', 'category_id', 'inventory', 'price_weights']
    if not all(column in data.columns for column in required_columns):
        raise ValidationError("File must contain the following columns: " + ", ".join(required_columns))

    errors = []

    for _, row in data.iterrows():
        name = row['name']
        description = row['description']
        category_id = row['category_id']
        inventory = row['inventory']
        price_weights = row['price_weights']
        tags = row.get('tags', '')
        image_urls = row.get('image_urls', '')

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            errors.append(f"Category with ID {category_id} does not exist.")
            continue

        if Product.objects.filter(name=name).exists():
            errors.append(f"Product with name {name} already exists.")
            continue

        try:
            product = Product.objects.create(
                name=name,
                description=description,
                category=category,
                inventory=int(inventory),
                tags=tags
            )

            for pw in price_weights.split(','):
                price, weight = pw.split('-')
                PriceWeight.objects.create(product=product, price=float(price), weight=weight)

        except Exception as e:
            errors.append(f"Error creating product {name}: {str(e)}")
            continue

    if errors:
        raise ValidationError(errors)

    return {"status": "success", "message": "Products uploaded successfully"}

# # products/utils.py
# import clamd
# from django.core.exceptions import ValidationError

# def scan_file_for_viruses(file):
#     cd = clamd.ClamdUnixSocket()
#     result = cd.scan_file(file.temporary_file_path())
#     if result.get(file.temporary_file_path())['virus'] is not None:
#         raise ValidationError("File is infected with a virus.")
