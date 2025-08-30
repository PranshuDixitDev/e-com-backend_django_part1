import os
import zipfile
import json
import tempfile
import re
import mimetypes
import traceback
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify
from django.db import transaction, IntegrityError, DatabaseError
from django.core.exceptions import ValidationError, PermissionDenied
from categories.models import Category
from .models import Product, ProductImage, PriceWeight
from .validators import BulkUploadValidator, BulkUploadValidationConstants
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class CatalogProcessingError(Exception):
    """Custom exception for catalog processing errors."""
    pass


class FileValidationError(CatalogProcessingError):
    """Exception for file validation errors."""
    pass


class DirectoryStructureError(CatalogProcessingError):
    """Exception for directory structure errors."""
    pass


class DataProcessingError(CatalogProcessingError):
    """Exception for data processing errors."""
    pass


class CatalogProcessingService:
    """Service for processing catalog uploads with enhanced security and error handling."""
    
    # Allowed image file extensions
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    def __init__(self, bulk_upload):
        self.bulk_upload = bulk_upload
        self.temp_dir = None
        self.processing_notes = []
        self.errors = []
        
        # Statistics
        self.categories_created = 0
        self.categories_updated = 0
        self.products_created = 0
        self.products_updated = 0
        self.images_processed = 0
        
        # Category tracking for admin panel
        self.category_stats = {}
        self.empty_categories = []
        self.detailed_errors = []
        
        # Security tracking
        self.files_processed = 0
        self.max_files_limit = 10000  # Prevent processing too many files
        
        # Centralized validator
        self.validator = BulkUploadValidator()
    
    def _validate_file_path(self, file_path):
        """Validate file path for security issues."""
        # Normalize path to prevent directory traversal
        normalized_path = os.path.normpath(file_path)
        
        # Use centralized validation
        if not self.validator.validate_file_path(normalized_path):
            raise ValidationError(f"Suspicious file path detected: {file_path}")
        
        # Check directory depth
        depth = len(normalized_path.split(os.sep))
        if depth > BulkUploadValidationConstants.MAX_DIRECTORY_DEPTH:
            raise ValidationError(f"Directory structure too deep: {file_path}")
        
        return normalized_path
    
    def _validate_file_content(self, file_path):
        """Validate file content and type."""
        if not os.path.exists(file_path):
            return False
        
        # Check file size
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path).lower()
        
        # Use centralized validation for basic checks
        try:
            self.validator.validate_file_content(file_path, file_size)
        except ValidationError as e:
            self.errors.append(str(e))
            return False
        
        # Additional image validation
        if any(filename.endswith(ext) for ext in BulkUploadValidationConstants.ALLOWED_IMAGE_EXTENSIONS):
            try:
                with Image.open(file_path) as img:
                    img.verify()  # Verify it's a valid image
                return True
            except Exception:
                self.errors.append(f"Invalid image file: {filename}")
                return False
        
        return True
    
    def _sanitize_text_input(self, text):
        """Sanitize text input to prevent injection attacks."""
        if not text:
            return ''
        
        # Use centralized sanitization
        sanitized_text = self.validator.sanitize_text(text)
        
        # Limit text length using centralized constant
        max_length = BulkUploadValidationConstants.MAX_TEXT_LENGTH
        if len(sanitized_text) > max_length:
            sanitized_text = sanitized_text[:max_length]
            self.processing_notes.append("Text content truncated due to length limit")
        
        return sanitized_text.strip()
    
    def _handle_database_operation(self, operation_func, item_name, item_type="item"):
        """Centralized error handling for database operations."""
        try:
            return operation_func()
        except ValidationError as e:
            raise DataProcessingError(f"Validation failed for {item_type} '{item_name}': {str(e)}")
        except IntegrityError as e:
            raise DataProcessingError(f"Database integrity error for {item_type} '{item_name}': {str(e)}")
        except Exception as e:
            raise DataProcessingError(f"Failed to save {item_type} '{item_name}': {str(e)}")
    
    def process_catalog(self):
        """Main method to process the uploaded catalog ZIP file with comprehensive error handling."""
        start_time = logger.info(f"Starting catalog processing for bulk upload ID: {self.bulk_upload.id}")
        processing_context = {
            'bulk_upload_id': self.bulk_upload.id,
            'zip_file': str(self.bulk_upload.zip_file),
            'user': self.bulk_upload.uploaded_by.username if self.bulk_upload.uploaded_by else 'Unknown'
        }
        
        try:
            # Validate ZIP file exists and is accessible
            if not self.bulk_upload.zip_file or not self.bulk_upload.zip_file.name:
                raise FileValidationError("No ZIP file provided for processing")
            
            logger.info(f"Processing ZIP file: {self.bulk_upload.zip_file.name}", extra=processing_context)
            
            self.bulk_upload.mark_as_processing()
            logger.info(f"Marked bulk upload {self.bulk_upload.id} as processing", extra=processing_context)
            
            # Extract ZIP file with detailed error handling
            try:
                if not self._extract_zip():
                    raise FileValidationError("Failed to extract ZIP file - file may be corrupted or invalid")
                logger.info(f"Successfully extracted ZIP file, processing {self.files_processed} files", extra=processing_context)
            except zipfile.BadZipFile as e:
                raise FileValidationError(f"Invalid ZIP file format: {str(e)}")
            except PermissionError as e:
                raise FileValidationError(f"Permission denied accessing ZIP file: {str(e)}")
            except OSError as e:
                raise FileValidationError(f"File system error extracting ZIP: {str(e)}")
            
            # Process categories and products with detailed tracking
            try:
                success = self._process_catalog_structure()
                if not success:
                    raise DirectoryStructureError("Failed to process catalog directory structure")
            except DirectoryStructureError:
                raise
            except Exception as e:
                raise DataProcessingError(f"Error processing catalog data: {str(e)}")
            
            # Evaluate processing results
            if self.errors:
                error_summary = self._generate_error_summary()
                logger.warning(f"Processing completed with {len(self.errors)} errors", extra={**processing_context, 'error_summary': error_summary})
                self._finalize_failure()
                return False
            else:
                success_summary = {
                    'categories_created': self.categories_created,
                    'categories_updated': self.categories_updated,
                    'products_created': self.products_created,
                    'products_updated': self.products_updated,
                    'images_processed': self.images_processed
                }
                logger.info(f"Processing completed successfully", extra={**processing_context, 'results': success_summary})
                self._finalize_success()
                return True
                
        except FileValidationError as e:
            error_msg = f"File validation error: {str(e)}"
            logger.error(error_msg, extra={**processing_context, 'error_type': 'FileValidationError'})
            self.bulk_upload.mark_as_failed(f"File Error: {str(e)}")
            return False
            
        except DirectoryStructureError as e:
            error_msg = f"Directory structure error: {str(e)}"
            logger.error(error_msg, extra={**processing_context, 'error_type': 'DirectoryStructureError'})
            self.bulk_upload.mark_as_failed(f"Structure Error: {str(e)}")
            return False
            
        except DataProcessingError as e:
            error_msg = f"Data processing error: {str(e)}"
            logger.error(error_msg, extra={**processing_context, 'error_type': 'DataProcessingError'})
            self.bulk_upload.mark_as_failed(f"Data Error: {str(e)}")
            return False
            
        except ValidationError as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(error_msg, extra={**processing_context, 'error_type': 'ValidationError'})
            self.bulk_upload.mark_as_failed(f"Validation Error: {str(e)}")
            return False
            
        except DatabaseError as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(error_msg, extra={**processing_context, 'error_type': 'DatabaseError', 'traceback': traceback.format_exc()})
            self.bulk_upload.mark_as_failed(f"Database Error: Unable to save data. Please try again later.")
            return False
            
        except PermissionDenied as e:
            error_msg = f"Permission denied: {str(e)}"
            logger.error(error_msg, extra={**processing_context, 'error_type': 'PermissionDenied'})
            self.bulk_upload.mark_as_failed(f"Permission Error: {str(e)}")
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg, extra={**processing_context, 'error_type': 'UnexpectedError', 'traceback': traceback.format_exc()})
            self.bulk_upload.mark_as_failed(f"System Error: An unexpected error occurred. Please contact support if this persists.")
            return False
            
        finally:
            try:
                self._cleanup_temp_files()
                logger.info(f"Cleanup completed for bulk upload {self.bulk_upload.id}", extra=processing_context)
            except Exception as e:
                logger.warning(f"Cleanup failed: {str(e)}", extra={**processing_context, 'cleanup_error': str(e)})
    
    def _extract_zip(self):
        """Extract the ZIP file to a temporary directory with security validation."""
        try:
            self.temp_dir = tempfile.mkdtemp()
            
            with zipfile.ZipFile(self.bulk_upload.zip_file.path, 'r') as zip_ref:
                # Validate each file before extraction
                for file_info in zip_ref.filelist:
                    # Validate file path
                    try:
                        self._validate_file_path(file_info.filename)
                    except ValidationError as e:
                        self.errors.append(str(e))
                        continue
                    
                    # Check files processed limit
                    self.files_processed += 1
                    if self.files_processed > self.max_files_limit:
                        self.errors.append(f"Too many files in ZIP archive (limit: {self.max_files_limit})")
                        return False
                
                # Extract all files if validation passed
                zip_ref.extractall(self.temp_dir)
                
                # Validate extracted file contents
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if not self._validate_file_content(file_path):
                            # Remove invalid files
                            try:
                                os.remove(file_path)
                                self.processing_notes.append(f"Removed invalid file: {file}")
                            except Exception:
                                pass
            
            self.processing_notes.append(f"ZIP file extracted and validated in temporary directory")
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to extract ZIP file: {str(e)}")
            return False
    
    def _process_catalog_structure(self):
        """Process the catalog directory structure with proper naming pattern validation."""
        processing_stats = {'directories_found': 0, 'valid_directories': 0, 'processed_directories': 0}
        
        try:
            # Find the main catalog directory
            all_items = os.listdir(self.temp_dir)
            catalog_dirs = [d for d in all_items if os.path.isdir(os.path.join(self.temp_dir, d))]
            processing_stats['directories_found'] = len(catalog_dirs)
            
            logger.info(f"Found {len(catalog_dirs)} directories in ZIP file", extra={'directories': catalog_dirs})
            
            if not catalog_dirs:
                raise DirectoryStructureError("No catalog directories found in ZIP file. Please ensure your ZIP contains category directories.")
            
            # Process each category directory with proper validation
            for dir_name in catalog_dirs:
                if dir_name.startswith('.'):
                    logger.debug(f"Skipping hidden directory: {dir_name}")
                    continue
                    
                if not self._is_valid_category_directory(dir_name):
                    logger.warning(f"Skipping invalid category directory: {dir_name}. Expected format: number_CODE_name")
                    self.processing_notes.append(f"Skipped invalid directory: {dir_name} (expected format: number_CODE_name)")
                    continue
                
                processing_stats['valid_directories'] += 1
                dir_path = os.path.join(self.temp_dir, dir_name)
                
                try:
                    self._process_category_directory(dir_name, dir_path)
                    processing_stats['processed_directories'] += 1
                    logger.debug(f"Successfully processed category directory: {dir_name}")
                except Exception as e:
                    logger.error(f"Failed to process category directory {dir_name}: {str(e)}")
                    self.errors.append(f"Failed to process category '{dir_name}': {str(e)}")
            
            logger.info(f"Catalog structure processing completed", extra={'stats': processing_stats})
            
            if processing_stats['processed_directories'] == 0:
                raise DirectoryStructureError("No valid category directories were processed successfully")
            
            return True
            
        except DirectoryStructureError:
            raise
        except OSError as e:
            raise DirectoryStructureError(f"File system error accessing catalog structure: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error processing catalog structure: {str(e)}")
            raise DataProcessingError(f"Error processing catalog structure: {str(e)}")
    
    def _process_category_directory(self, dir_name, dir_path):
        """Process a single category directory with comprehensive error handling."""
        category_context = {'directory': dir_name, 'path': dir_path}
        
        try:
            logger.info(f"Processing category directory: {dir_name}", extra=category_context)
            
            # Extract category name from directory name (e.g., "1_SPH_spices and herbs" -> "spices and herbs")
            try:
                category_name = self._extract_category_name(dir_name)
                if not category_name:
                    raise DataProcessingError(f"Could not extract category name from directory: {dir_name}")
                category_context['category_name'] = category_name
            except Exception as e:
                raise DataProcessingError(f"Failed to parse category name from '{dir_name}': {str(e)}")
            
            # Extract display order
            display_order = self._extract_display_order(dir_name)
            category_context['display_order'] = display_order
            
            # Read category description files
            try:
                category_code = self._extract_category_code(dir_name)
                category_data = self._read_category_files(dir_path, category_code)
                category_context['category_code'] = category_code
            except FileNotFoundError as e:
                logger.warning(f"Category description files not found for {dir_name}: {str(e)}", extra=category_context)
                category_data = {'short_description': '', 'long_description': ''}
            except Exception as e:
                raise DataProcessingError(f"Failed to read category files for '{dir_name}': {str(e)}")
            
            # Process category images first to get primary and secondary images
            primary_image = None
            secondary_image = None
            try:
                image_files = [f for f in os.listdir(dir_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
                if image_files:
                    # Identify primary image (contains 'main' in filename) and secondary image
                    primary_image_file = None
                    secondary_image_file = None
                    
                    for image_file in image_files:
                        if 'main' in image_file.lower():
                            primary_image_file = image_file
                        else:
                            secondary_image_file = image_file
                    
                    # Process primary image
                    if primary_image_file:
                        primary_image_path = os.path.join(dir_path, primary_image_file)
                        primary_image = self._process_image_file(primary_image_path)
                        logger.info(f"Processed primary image: {primary_image_file}", extra=category_context)
                    
                    # Process secondary image
                    if secondary_image_file:
                        secondary_image_path = os.path.join(dir_path, secondary_image_file)
                        secondary_image = self._process_image_file(secondary_image_path)
                        logger.info(f"Processed secondary image: {secondary_image_file}", extra=category_context)
                        
            except Exception as e:
                logger.warning(f"Failed to process category images for {dir_name}: {str(e)}", extra=category_context)
            
            # Create or update category with display_order and images
            def create_category():
                category = self._create_or_update_category(
                    category_name, 
                    category_data, 
                    display_order=display_order,
                    primary_image=primary_image,
                    secondary_image=secondary_image
                )
                if not category:
                    raise DataProcessingError(f"Failed to create or update category: {category_name}")
                return category
            
            category = self._handle_database_operation(create_category, category_name, "category")
            category_context['category_id'] = category.id
            logger.info(f"Successfully processed category: {category_name}", extra=category_context)
            
            # Process products in this category using the proper naming pattern
            try:
                products_dir = os.path.join(dir_path, f'{category_code}_products')
                if os.path.exists(products_dir):
                    self._process_products_directory(category, products_dir)
                    logger.debug(f"Processed products directory for category: {category_name}", extra=category_context)
                else:
                    logger.info(f"No products directory found for category: {category_name} (expected: {category_code}_products)", extra=category_context)
                    self.processing_notes.append(f"No products directory found for category: {category_name} (expected: {category_code}_products)")
            except Exception as e:
                logger.error(f"Failed to process products for category {category_name}: {str(e)}", extra=category_context)
                self.errors.append(f"Failed to process products for category '{category_name}': {str(e)}")
            
        except DataProcessingError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error processing category directory {dir_name}: {str(e)}", extra=category_context)
            raise DataProcessingError(f"Unexpected error processing category directory {dir_name}: {str(e)}")
    
    def _is_valid_category_directory(self, dir_name):
        """Check if directory follows the expected category naming pattern."""
        # Expected pattern: number_CODE_name (e.g., "1_SPH_spices and herbs")
        parts = dir_name.split('_')
        return len(parts) >= 3 and parts[0].isdigit() and len(parts[1]) > 0
    
    def _extract_category_code(self, dir_name):
        """Extract category code from directory name."""
        # Handle formats like "1_SPH_spices and herbs" -> "SPH"
        parts = dir_name.split('_')
        if len(parts) >= 2:
            return parts[1]
    
    def _extract_display_order(self, dir_name):
        """Extract display order from directory name."""
        # Extract number from formats like "1_SPH_spices and herbs" -> 1
        if '_' in dir_name and dir_name.split('_')[0].isdigit():
            return int(dir_name.split('_')[0])
        return None
        return "SPH"  # Default fallback
    
    def _extract_category_name(self, dir_name):
        """Extract category name from directory name."""
        # Handle formats like "1_SPH_spices and herbs" -> "spices and herbs"
        if '_' in dir_name:
            parts = dir_name.split('_')
            if len(parts) >= 3:
                # Join all parts after the code (parts[2:]) to handle multi-word names
                category_name = ' '.join(parts[2:]).strip()
                return category_name if category_name else parts[1]  # Fallback to code if no name
            elif len(parts) == 2:
                return parts[1].strip()  # Just code_name format
        return dir_name.strip()
    
    def _read_category_files(self, dir_path, category_code):
        """Read category description files with security validation and flexible naming patterns."""
        category_data = {
            'secondary_description': '',
            'description': ''
        }
        
        # First, try the legacy format with separate short/long files
        short_file = os.path.join(dir_path, f'{category_code}_txt_short.txt')
        long_file = os.path.join(dir_path, f'{category_code}_txt_long.txt')
        
        if os.path.exists(short_file):
            try:
                with open(short_file, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                    category_data['secondary_description'] = self._sanitize_text_input(raw_content)
            except Exception as e:
                self.errors.append(f"Error reading short description file for {category_code}: {str(e)}")
        
        if os.path.exists(long_file):
            try:
                with open(long_file, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                    category_data['description'] = self._sanitize_text_input(raw_content)
            except Exception as e:
                self.errors.append(f"Error reading long description file for {category_code}: {str(e)}")
        
        # If legacy files don't exist, look for a single .txt file with all metadata
        if not category_data['secondary_description'] and not category_data['description']:
            # Look for any .txt file in the directory
            txt_files = [f for f in os.listdir(dir_path) if f.endswith('.txt')]
            
            if txt_files:
                # Use the first .txt file found
                txt_file_path = os.path.join(dir_path, txt_files[0])
                try:
                    with open(txt_file_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read().strip()
                        
                        # Parse the content - look for key-value pairs or use entire content as description
                        lines = [line.strip() for line in raw_content.split('\n') if line.strip()]
                        
                        # Try to extract structured data
                        parsed_data = self._parse_metadata_content(lines)
                        
                        # Use parsed data or fallback to using content as description
                        category_data['slug'] = parsed_data.get('slug', '')
                        category_data['description'] = parsed_data.get('description', raw_content)
                        
                        logger.debug(f"Successfully read metadata from {txt_files[0]} for category {category_code}")
                        
                except Exception as e:
                    self.errors.append(f"Error reading metadata file {txt_files[0]} for {category_code}: {str(e)}")
                    logger.warning(f"Failed to read metadata file {txt_files[0]}: {str(e)}")
        
        return category_data
    
    def _parse_metadata_content(self, lines):
        """Parse metadata content from a single text file with flexible format support."""
        parsed_data = {'slug': '', 'description': ''}
        
        if not lines:
            return parsed_data
        
        # Try to detect key-value pairs (e.g., "slug: value" or "description: value")
        key_value_pairs = {}
        description_lines = []
        
        for line in lines:
            # Check for key-value pattern
            if ':' in line and len(line.split(':', 1)) == 2:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key in ['slug', 'short', 'short_description']:
                    key_value_pairs['slug'] = value
                elif key in ['description', 'long', 'long_description', 'details']:
                    key_value_pairs['description'] = value
                else:
                    # If it's not a recognized key, treat as description content
                    description_lines.append(line)
            else:
                # Regular content line
                description_lines.append(line)
        
        # Set parsed values
        parsed_data['slug'] = key_value_pairs.get('slug', '')
        parsed_data['description'] = key_value_pairs.get('description', '')
        
        # If no structured description found, use all content as description
        if not parsed_data['description'] and description_lines:
            parsed_data['description'] = '\n'.join(description_lines)
        
        # If no slug found but we have description, create a basic slug from first line
        if not parsed_data['slug'] and description_lines:
            first_line = description_lines[0]
            # Take first 50 characters as slug
            parsed_data['slug'] = first_line[:50] if len(first_line) > 50 else first_line
        
        return parsed_data
    
    def _validate_category_name(self, name):
        """Validate category name for security and format requirements."""
        return self.validator.validate_category(name)
    
    def _validate_category_data(self, data):
        """Validate category data structure."""
        return self.validator.validate_category_data_structure(data)
    
    def _sanitize_category_data(self, data):
        """Sanitize category data dictionary."""
        return self.validator.sanitize_category_data(data)
    
    @transaction.atomic
    def _create_or_update_category(self, name, category_data, display_order=None, primary_image=None, secondary_image=None):
        """Create or update a category with comprehensive input validation."""
        try:
            # Validate and sanitize category name
            if not self._validate_category_name(name):
                self.errors.append(f"Invalid category name: {name}")
                return None
            
            sanitized_name = self._sanitize_text_input(name)
            if not sanitized_name:
                self.errors.append(f"Category name became empty after sanitization: {name}")
                return None
            
            # Validate category data structure
            if not self._validate_category_data(category_data):
                self.errors.append(f"Invalid category data structure for: {name}")
                return None
            
            # Sanitize category data
            sanitized_data = self._sanitize_category_data(category_data)
            
            # Check if category already exists
            try:
                category = Category.objects.get(name=sanitized_name)
                created = False
                self.processing_notes.append(f"Updated existing category: {sanitized_name}")
            except Category.DoesNotExist:
                # Create new category with required fields
                if not primary_image:
                    self.errors.append(f"Primary image is required for category: {sanitized_name}")
                    return None
                
                # Generate a proper slug from the category name
                category_slug = slugify(sanitized_name)
                if not category_slug:
                    category_slug = slugify(f"category-{sanitized_name}")
                
                category = Category(
                    name=sanitized_name,
                    slug=category_slug,
                    description=sanitized_data.get('description', ''),
                    secondary_description=sanitized_data.get('secondary_description', ''),
                    display_order=display_order,
                    image=primary_image,
                    is_active=True
                )
                
                if secondary_image:
                    category.secondary_image = secondary_image
                
                category.save()
                created = True
                self.categories_created += 1
                self.processing_notes.append(f"Created category: {sanitized_name}")
            
            if created:
                self.categories_created += 1
                self.processing_notes.append(f"Created category: {sanitized_name}")
            else:
                # Update existing category with validation
                updated = False
                if sanitized_data.get('description') and category.description != sanitized_data['description']:
                    category.description = sanitized_data['description']
                    updated = True
                
                if updated:
                    category.save()
                    self.categories_updated += 1
                    self.processing_notes.append(f"Updated category: {sanitized_name}")
            
            return category
            
        except ValidationError as e:
            self.errors.append(f"Validation error for category {name}: {str(e)}")
            return None
        except Exception as e:
            self.errors.append(f"Error creating/updating category {name}: {str(e)}")
            return None
    
    def _process_category_images(self, category, dir_path):
        """Process category images with security validation."""
        try:
            for filename in os.listdir(dir_path):
                if any(filename.lower().endswith(ext) for ext in self.ALLOWED_IMAGE_EXTENSIONS):
                    image_path = os.path.join(dir_path, filename)
                    
                    # Validate file path and content
                    try:
                        self._validate_file_path(image_path)
                        if self._validate_file_content(image_path):
                            self._process_image_file(image_path, category=category)
                    except ValidationError as e:
                        self.errors.append(f"Invalid category image {filename}: {str(e)}")
            
        except Exception as e:
            self.errors.append(f"Error processing category images: {str(e)}")
    
    def _process_products_directory(self, category, products_dir):
        """Process all products in a category's products directory with comprehensive error handling."""
        products_context = {
            'products_dir': products_dir,
            'category_id': category.id,
            'category_name': category.name
        }
        
        # Initialize category stats
        category_name = category.name
        if category_name not in self.category_stats:
            self.category_stats[category_name] = {
                'expected': 0,
                'uploaded': 0,
                'errors': []
            }
        
        try:
            if not os.path.exists(products_dir):
                logger.warning(f"Products directory not found: {products_dir}", extra=products_context)
                self.empty_categories.append(category_name)
                return
            
            logger.debug(f"Processing products directory: {products_dir}", extra=products_context)
            
            # Get list of product directories
            try:
                product_dirs = [d for d in os.listdir(products_dir) 
                              if os.path.isdir(os.path.join(products_dir, d))]
                logger.debug(f"Found {len(product_dirs)} product directories", extra=products_context)
            except OSError as e:
                raise DirectoryStructureError(f"Cannot read products directory {products_dir}: {str(e)}")
            
            # Count expected products (excluding hidden directories)
            expected_products = len([d for d in product_dirs if not d.startswith('.')])
            self.category_stats[category_name]['expected'] = expected_products
            
            # Check for empty category
            if expected_products == 0:
                self.empty_categories.append(category_name)
                logger.warning(f"Empty category found: {category_name}", extra=products_context)
                return
            
            products_processed = 0
            products_skipped = 0
            
            for product_dir_name in product_dirs:
                product_dir_path = os.path.join(products_dir, product_dir_name)
                product_context = {
                    **products_context,
                    'product_dir': product_dir_name,
                    'product_path': product_dir_path
                }
                
                try:
                    # Skip hidden directories
                    if product_dir_name.startswith('.'):
                        logger.debug(f"Skipping hidden directory: {product_dir_name}", extra=product_context)
                        products_skipped += 1
                        continue
                    
                    # Validate product directory name
                    if not self._is_valid_product_directory(product_dir_name):
                        error_msg = f"Invalid product directory name: {product_dir_name}. Expected format: PRODUCT_name"
                        logger.warning(error_msg, extra=product_context)
                        self.category_stats[category_name]['errors'].append({
                            'product': product_dir_name,
                            'error': 'Invalid directory name format',
                            'expected': 'PRODUCT_name format',
                            'given': product_dir_name
                        })
                        self.detailed_errors.append({
                            'category': category_name,
                            'product': product_dir_name,
                            'error_type': 'Invalid directory name',
                            'expected': 'PRODUCT_name format',
                            'given': product_dir_name,
                            'message': error_msg
                        })
                        products_skipped += 1
                        continue
                    
                    logger.debug(f"Processing product directory: {product_dir_name}", extra=product_context)
                    
                    # Process the product directory
                    success = self._process_product_directory(category, product_dir_name, product_dir_path)
                    if success:
                        products_processed += 1
                        self.category_stats[category_name]['uploaded'] += 1
                    else:
                        products_skipped += 1
                        # Capture the last error for this product
                        last_error = self.errors[-1] if self.errors else "Unknown error"
                        self.category_stats[category_name]['errors'].append({
                            'product': product_dir_name,
                            'error': last_error,
                            'expected': 'Valid product data file',
                            'given': 'Missing or invalid product data'
                        })
                        self.detailed_errors.append({
                            'category': category_name,
                            'product': product_dir_name,
                            'error_type': 'Product processing failed',
                            'expected': 'Valid product data file',
                            'given': 'Missing or invalid product data',
                            'message': last_error
                        })
                    
                except Exception as e:
                    error_msg = f"Error processing product directory {product_dir_name}: {str(e)}"
                    logger.error(error_msg, extra=product_context)
                    self.errors.append(f"Product processing failed for {product_dir_name}: {str(e)}")
                    self.category_stats[category_name]['errors'].append({
                        'product': product_dir_name,
                        'error': str(e),
                        'expected': 'Valid product data and structure',
                        'given': 'Invalid or corrupted data'
                    })
                    self.detailed_errors.append({
                        'category': category_name,
                        'product': product_dir_name,
                        'error_type': 'Processing error',
                        'expected': 'Valid product data and structure',
                        'given': 'Invalid or corrupted data',
                        'message': str(e)
                    })
                    continue
            
            # Log processing summary
            logger.info(f"Products processing complete. Processed: {products_processed}, Skipped: {products_skipped}", extra=products_context)
            
        except DirectoryStructureError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in products directory processing: {str(e)}", extra=products_context)
            raise DataProcessingError(f"Failed to process products directory: {str(e)}")
    
    def _process_product_directory(self, category, product_dir_name, product_dir_path):
        """Process a single product directory with comprehensive error handling."""
        product_context = {
            'category_id': category.id,
            'product_dir_name': product_dir_name,
            'product_dir_path': product_dir_path
        }
        
        try:
            logger.debug(f"Processing product directory: {product_dir_name}", extra=product_context)
            
            # Extract product name from directory name
            try:
                product_name = self._extract_product_name(product_dir_name)
                product_context['product_name'] = product_name
                logger.debug(f"Extracted product name: {product_name}", extra=product_context)
            except Exception as e:
                raise DataProcessingError(f"Failed to extract product name from {product_dir_name}: {str(e)}")
            
            # Read product data file
            try:
                product_data = self._read_product_data(product_dir_path, product_dir_name)
                if not product_data:
                    raise DataProcessingError(f"No valid product data found for: {product_dir_name}")
                logger.debug(f"Read product data for: {product_name}", extra=product_context)
            except DataProcessingError:
                raise
            except Exception as e:
                raise DataProcessingError(f"Failed to read product data for {product_dir_name}: {str(e)}")
            
            # Create or update product
            def create_product():
                product = self._create_or_update_product(category, product_name, product_data)
                if not product:
                    raise DataProcessingError(f"Failed to create or update product: {product_name}")
                return product
            
            product = self._handle_database_operation(create_product, product_name, "product")
            product_context['product_id'] = product.id
            logger.debug(f"Created/updated product: {product.name} (ID: {product.id})", extra=product_context)
            
            # Process product images
            try:
                images_before = self.images_processed
                self._process_product_images(product, product_dir_path)
                images_added = self.images_processed - images_before
                logger.debug(f"Processed {images_added} images for product: {product.name}", extra=product_context)
            except Exception as e:
                # Log error but don't fail the entire product processing
                logger.error(f"Failed to process images for product {product.name}: {str(e)}", extra=product_context)
                self.errors.append(f"Image processing failed for product {product.name}: {str(e)}")
            
            # Create default price-weight if none exist
            try:
                self._ensure_default_price_weight(product)
                logger.debug(f"Ensured default price-weight for product: {product.name}", extra=product_context)
            except Exception as e:
                # Log error but don't fail the entire product processing
                logger.warning(f"Failed to create default price-weight for product {product.name}: {str(e)}", extra=product_context)
                self.errors.append(f"Default price-weight creation failed for product {product.name}: {str(e)}")
            
            logger.debug(f"Successfully processed product: {product.name}", extra=product_context)
            return True
            
        except (DataProcessingError, ValidationError) as e:
            logger.error(f"Error processing product {product_dir_name}: {str(e)}", extra=product_context)
            self.errors.append(f"Error processing product directory {product_dir_name}: {str(e)}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error processing product {product_dir_name}: {str(e)}", extra=product_context)
            self.errors.append(f"Unexpected error processing product directory {product_dir_name}: {str(e)}")
            return False
    
    def _is_valid_product_directory(self, dir_name):
        """Check if directory follows the expected product naming pattern."""
        # Expected pattern: CODE_product_name (e.g., "SPH_ajwain ajmo", "BLS_chai masala tea")
        # Valid codes: SPH, BLS, PKL, MUK, FRP, IFP
        valid_codes = ['SPH', 'BLS', 'PKL', 'MUK', 'FRP', 'IFP']
        if '_' not in dir_name:
            return False
        
        code = dir_name.split('_')[0]
        return code in valid_codes and len(dir_name) > len(code) + 1
    
    def _extract_product_name(self, product_dir_name):
        """Extract product name from directory name."""
        # Handle formats like "SPH_ajwain ajmo" -> "ajwain ajmo"
        if '_' in product_dir_name:
            parts = product_dir_name.split('_', 1)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
        return product_dir_name.replace('_', ' ').strip()
    
    def _read_product_data(self, product_dir_path, product_dir_name):
        """Read product data from text file with security validation."""
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
        
        data_file = None
        for filename in possible_filenames:
            potential_file = os.path.join(product_dir_path, filename)
            print(f"DEBUG: Checking for data file: {potential_file}")
            if os.path.exists(potential_file):
                data_file = potential_file
                print(f"DEBUG: Found data file: {data_file}")
                break
        
        if not data_file:
            print(f"DEBUG: No data file found in {product_dir_path}. Tried: {possible_filenames}")
            return None
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                content = self._sanitize_text_input(raw_content)
            
            if not content:
                print(f"DEBUG: Empty content in file: {data_file}")
                return None
            
            # Try to parse as JSON first
            try:
                # Fix common JSON syntax errors before parsing
                fixed_content = content
                # Fix unescaped backslashes in JSON strings
                fixed_content = re.sub(r'(?<!\\)\\(?!["\\nrtbf/])', r'\\', fixed_content)
                # Fix unescaped quotes in JSON values
                fixed_content = re.sub(r'(?<!\\)"(?=\w)', r'\\"', fixed_content)
                # Fix malformed JSON where Description field is missing comma and Ingredients field name
                fixed_content = re.sub(r'("Description"\s*:\s*"[^"]*")\s*:\s*("[^"]*")', r'\1, "Ingredients": \2', fixed_content)
                
                data = json.loads(fixed_content)
                
                # Handle double-encoded JSON (string containing JSON)
                if isinstance(data, str):
                    try:
                        # Fix malformed inner JSON before parsing
                        inner_fixed = re.sub(r'("Description"\s*:\s*"[^"]*")\s*:\s*("[^"]*")', r'\1, "Ingredients": \2', data)
                        data = json.loads(inner_fixed)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse double-encoded JSON for {product_dir_name}: {e}")
                        return None
                # Map JSON fields to product data structure
                if isinstance(data, dict):
                    # Map JSON fields to expected product fields
                    description = self._sanitize_text_input(data.get('Description', ''))
                    # Convert periods to commas in description
                    description = description.replace('.', ',')
                    
                    mapped_data = {
                        'description': description,
                        'secondary_description': self._sanitize_text_input(data.get('Ingredients', '')),
                        'tags': [],
                        'price': 0.0,  # Default price
                        'weight': 0.0   # Default weight
                    }
                    
                    # Create tags from various fields
                    tag_sources = [
                        data.get('Ingredients', ''),
                        data.get('Features & Benefits', ''),
                        data.get('Usage Recommendation', '')
                    ]
                    
                    # Extract meaningful tags from the content
                    tags = set()
                    for source in tag_sources:
                        if source:
                            # Convert periods to commas in tag sources
                            source = str(source).replace('.', ',')
                            # Split by common delimiters and extract meaningful words
                            words = re.split(r'[,;\n]+', source)
                            for word in words:
                                word = word.strip().lower()
                                if len(word) > 2 and word not in ['and', 'the', 'for', 'with', 'helps', 'aids']:
                                    tags.add(word)
                    
                    mapped_data['tags'] = list(tags)[:10]  # Limit to 10 tags
                    return mapped_data
                # If data is not a dict with expected structure, return None
                print(f"DEBUG: Unexpected JSON data structure for {product_dir_name}: {data}")
                return None
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract data manually
                try:
                    # Extract Description field manually
                    desc_match = re.search(r'"Description"\s*:\s*"([^"]+)"', content)
                    ingredients_match = re.search(r'"Ingredients"\s*:\s*"([^"]+)"', content)
                    
                    if desc_match:
                        description = self._sanitize_text_input(desc_match.group(1))
                        description = description.replace('.', ',')
                        
                        ingredients = ''
                        if ingredients_match:
                            ingredients = self._sanitize_text_input(ingredients_match.group(1))
                        
                        manual_data = {
                            'description': description,
                            'secondary_description': ingredients,
                            'tags': [],
                            'price': 0.0,  # Default price
                            'weight': 0.0   # Default weight
                        }
                        print(f"DEBUG: Manual extraction data for {product_dir_name}: {manual_data}")
                        return manual_data
                except Exception:
                    pass
                
                # If all parsing fails, treat as plain text description
                # Convert periods to commas in description
                description = content.replace('.', ',')
                plain_text_data = {
                    'description': description,
                    'secondary_description': '',
                    'tags': [],
                    'price': 0.0,  # Default price
                    'weight': 0.0   # Default weight
                }
                print(f"DEBUG: Plain text data for {product_dir_name}: {plain_text_data}")
                return plain_text_data
        
        except Exception as e:
            self.errors.append(f"Error reading product data file {data_file}: {str(e)}")
            return None
    
    def _validate_product_name(self, name):
        """Validate product name for security and format requirements."""
        return self.validator.validate_product(name)
    
    def _validate_product_data(self, data):
        """Validate product data structure."""
        print(f"DEBUG: Validating product data: {data}")
        print(f"DEBUG: Data type: {type(data)}")
        print(f"DEBUG: Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        result = self.validator.validate_product_data_structure(data)
        print(f"DEBUG: Validation result: {result}")
        return result
    
    def _sanitize_product_data(self, data):
        """Sanitize product data dictionary."""
        return self.validator.sanitize_product_data(data)
    
    @transaction.atomic
    def _create_or_update_product(self, category, name, product_data):
        """Create or update a product with comprehensive input validation."""
        try:
            # Validate and sanitize product name
            if not self._validate_product_name(name):
                self.errors.append(f"Invalid product name: {name}")
                return None
            
            sanitized_name = self._sanitize_text_input(name)
            if not sanitized_name:
                self.errors.append(f"Product name became empty after sanitization: {name}")
                return None
            
            # Validate product data structure
            if not self._validate_product_data(product_data):
                self.errors.append(f"Invalid product data structure for: {name}")
                return None
            
            # Sanitize product data
            sanitized_data = self._sanitize_product_data(product_data)
            
            product, created = Product.objects.get_or_create(
                name=sanitized_name,
                defaults={
                    'category': category,
                    'description': sanitized_data.get('description', ''),
                    'is_active': True
                }
            )
            
            if created:
                self.products_created += 1
                self.processing_notes.append(f"Created product: {sanitized_name}")
                
                # Ensure default price and weight
                self._ensure_default_price_weight(product)
                
                # Add tags if provided
                tags = sanitized_data.get('tags', [])
                if tags:
                    # Filter out empty tags and limit to valid ones
                    valid_tags = [tag for tag in tags if tag and len(tag.strip()) > 0]
                    if valid_tags:
                        product.tags.add(*valid_tags[:10])  # Limit to 10 tags
            else:
                # Update existing product
                updated = False
                if sanitized_data.get('description') and product.description != sanitized_data['description']:
                    product.description = sanitized_data['description']
                    updated = True
                
                if updated:
                    product.save()
                    self.products_updated += 1
                    self.processing_notes.append(f"Updated product: {sanitized_name}")
            
            return product
            
        except ValidationError as e:
            self.errors.append(f"Validation error for product {name}: {str(e)}")
            return None
        except Exception as e:
            self.errors.append(f"Error creating/updating product {name}: {str(e)}")
            return None
    
    def _process_product_images(self, product, product_dir_path):
        """Process product images with security validation."""
        try:
            for filename in os.listdir(product_dir_path):
                if any(filename.lower().endswith(ext) for ext in self.ALLOWED_IMAGE_EXTENSIONS):
                    image_path = os.path.join(product_dir_path, filename)
                    
                    # Validate file path and content
                    try:
                        self._validate_file_path(image_path)
                        if self._validate_file_content(image_path):
                            self._process_image_file(image_path, product=product)
                    except ValidationError as e:
                        self.errors.append(f"Invalid product image {filename}: {str(e)}")
            
        except Exception as e:
            self.errors.append(f"Error processing product images: {str(e)}")
    
    def _process_image_file(self, image_path, category=None, product=None):
        """Process and save an image file with comprehensive error handling and security validation."""
        image_context = {
            'image_path': image_path,
            'category_id': category.id if category else None,
            'product_id': product.id if product else None
        }
        
        try:
            logger.debug(f"Processing image file: {image_path}", extra=image_context)
            
            # Validate file path and content
            try:
                self._validate_file_path(image_path)
                self._validate_file_content(image_path)
            except ValidationError as e:
                raise FileValidationError(f"Image validation failed for {os.path.basename(image_path)}: {str(e)}")
            
            # Open and process the image
            try:
                with Image.open(image_path) as img:
                    # Log original image properties
                    logger.debug(f"Original image: {img.size}, mode: {img.mode}, format: {img.format}", extra=image_context)
                    
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                        logger.debug(f"Converted image mode to RGB", extra=image_context)
                    
                    # Resize if too large (max 1920x1920)
                    max_size = (1920, 1920)
                    original_size = img.size
                    if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        logger.debug(f"Resized image from {original_size} to {img.size}", extra=image_context)
                    
                    # Save to BytesIO
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    output.seek(0)
                    
                    # Validate processed image size
                    processed_size = len(output.getvalue())
                    if processed_size > BulkUploadValidationConstants.MAX_IMAGE_FILE_SIZE:
                        raise FileValidationError(f"Processed image too large: {processed_size} bytes")
                    
                    logger.debug(f"Processed image size: {processed_size} bytes", extra=image_context)
                    
            except UnidentifiedImageError as e:
                raise FileValidationError(f"Invalid or corrupted image file: {os.path.basename(image_path)}")
            except OSError as e:
                raise FileValidationError(f"Cannot process image file {os.path.basename(image_path)}: {str(e)}")
            except Exception as e:
                raise DataProcessingError(f"Image processing failed for {os.path.basename(image_path)}: {str(e)}")
            
            # Generate filename
            try:
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                new_filename = f"{slugify(name)}.jpg"
                image_context['target_filename'] = new_filename
                
            except Exception as e:
                raise DataProcessingError(f"Failed to generate filename for image: {str(e)}")
            
            # Save image
            try:
                if product:
                    # Check if image already exists for this product
                    if not ProductImage.objects.filter(product=product, image__icontains=new_filename).exists():
                        product_image = ProductImage(
                            product=product,
                            description=f"Image for {product.name}"
                        )
                        product_image.image.save(
                            new_filename,
                            ContentFile(output.getvalue()),
                            save=True
                        )
                        
                        # Set as primary if it's the first image
                        if not ProductImage.objects.filter(product=product, is_primary=True).exists():
                            product_image.is_primary = True
                            product_image.save()
                        
                        self.images_processed += 1
                        logger.debug(f"Created ProductImage record for {product.name}", extra=image_context)
                elif category:
                    # For category images, return ContentFile for use in category creation
                    self.images_processed += 1
                    logger.debug(f"Processed category image: {new_filename}", extra=image_context)
                    return ContentFile(output.getvalue(), name=new_filename)
                else:
                    # For standalone image processing (category images), return ContentFile
                    self.images_processed += 1
                    logger.debug(f"Processed standalone image: {new_filename}", extra=image_context)
                    return ContentFile(output.getvalue(), name=new_filename)
                
            except IntegrityError as e:
                raise DataProcessingError(f"Database error creating image record: {str(e)}")
            except Exception as e:
                raise DataProcessingError(f"Failed to create image database record: {str(e)}")
                
        except (FileValidationError, DataProcessingError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error processing image {image_path}: {str(e)}", extra=image_context)
            raise DataProcessingError(f"Unexpected error processing image {os.path.basename(image_path)}: {str(e)}")
    
    def _ensure_default_price_weight(self, product):
        """Ensure product has at least one price-weight combination."""
        try:
            if not product.price_weights.exists():
                PriceWeight.objects.create(
                    product=product,
                    price=2000.00,  # Default price
                    weight='100gms',  # Default weight
                    inventory=0  # Default inventory
                )
                self.processing_notes.append(f"Created default price-weight for product: {product.name}")
        
        except Exception as e:
            self.errors.append(f"Error creating default price-weight for {product.name}: {str(e)}")
    
    def _finalize_success(self):
        """Finalize successful processing."""
        # Update bulk upload statistics
        self.bulk_upload.categories_created = self.categories_created
        self.bulk_upload.categories_updated = self.categories_updated
        self.bulk_upload.products_created = self.products_created
        self.bulk_upload.products_updated = self.products_updated
        self.bulk_upload.images_processed = self.images_processed
        
        # Save tracking data
        self.bulk_upload.category_stats = self.category_stats
        self.bulk_upload.detailed_errors = self.detailed_errors
        self.bulk_upload.empty_categories = self.empty_categories
        
        notes = '\n'.join(self.processing_notes)
        self.bulk_upload.mark_as_completed(notes)
    
    def _finalize_failure(self):
        """Finalize failed processing."""
        # Save tracking data even on failure
        self.bulk_upload.category_stats = self.category_stats
        self.bulk_upload.detailed_errors = self.detailed_errors
        self.bulk_upload.empty_categories = self.empty_categories
        
        error_message = '\n'.join(self.errors)
        self.bulk_upload.mark_as_failed(error_message)
    
    def _generate_error_summary(self):
        """Generate a summary of errors for logging and reporting."""
        if not self.errors:
            return "No errors"
        
        error_types = {}
        for error in self.errors:
            if "validation" in error.lower():
                error_types["validation"] = error_types.get("validation", 0) + 1
            elif "file" in error.lower():
                error_types["file"] = error_types.get("file", 0) + 1
            elif "image" in error.lower():
                error_types["image"] = error_types.get("image", 0) + 1
            elif "database" in error.lower():
                error_types["database"] = error_types.get("database", 0) + 1
            else:
                error_types["other"] = error_types.get("other", 0) + 1
        
        summary = f"Total errors: {len(self.errors)}. "
        summary += ", ".join([f"{error_type}: {count}" for error_type, count in error_types.items()])
        return summary
    
    def _cleanup_temp_files(self):
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {self.temp_dir}: {str(e)}")