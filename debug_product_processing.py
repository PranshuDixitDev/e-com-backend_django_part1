#!/usr/bin/env python
"""
Debug script to test product processing logic for MUK_fennel seeds salted variyali
"""

import os
import json

def extract_product_name(product_dir_name):
    """Extract product name from directory name."""
    # Handle formats like "SPH_ajwain ajmo" -> "ajwain ajmo"
    if '_' in product_dir_name:
        parts = product_dir_name.split('_', 1)
        if len(parts) > 1 and parts[1].strip():
            return parts[1].strip()
    return product_dir_name.replace('_', ' ').strip()

def test_file_lookup(product_dir_path, product_dir_name):
    """Test file lookup logic for product data."""
    # Look for product data file with multiple naming patterns
    possible_filenames = [
        f"{product_dir_name}.txt",  # Exact match
        f"{product_dir_name.replace('_', '_ ')}.txt",  # With space after underscore
        f"{product_dir_name.replace('_', ' ')}.txt",  # Replace underscore with space
    ]
    
    # Also check for any .txt file in the directory as fallback
    try:
        txt_files = [f for f in os.listdir(product_dir_path) if f.endswith('.txt')]
        for txt_file in txt_files:
            if txt_file not in possible_filenames:
                possible_filenames.append(txt_file)
    except OSError:
        pass
    
    print(f"Directory name: {product_dir_name}")
    print(f"Extracted product name: {extract_product_name(product_dir_name)}")
    print(f"Looking for files: {possible_filenames}")
    
    data_file = None
    for filename in possible_filenames:
        potential_file = os.path.join(product_dir_path, filename)
        print(f"Checking: {potential_file} - Exists: {os.path.exists(potential_file)}")
        if os.path.exists(potential_file):
            data_file = potential_file
            print(f"Found data file: {data_file}")
            break
    
    if data_file:
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"File content: {content}")
                
                # Try to parse as JSON
                try:
                    data = json.loads(content)
                    print(f"JSON parsed successfully: {data}")
                    return True
                except json.JSONDecodeError as e:
                    print(f"JSON parsing failed: {e}")
                    return False
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
    else:
        print("No data file found!")
        return False

if __name__ == "__main__":
    # Test with the problematic directory
    test_dir = "/Users/pranshudixit/Downloads/CATALOG UPLOAD/4_MUK_mukhwas/MUK_products/MUK_fennel seeds salted variyali"
    test_dir_name = "MUK_fennel seeds salted variyali"
    
    print("=== Testing MUK_fennel seeds salted variyali processing ===")
    test_file_lookup(test_dir, test_dir_name)