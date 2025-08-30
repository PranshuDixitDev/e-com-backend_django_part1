import re
import zipfile
import mimetypes
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from typing import Dict, List, Any, Optional


class BulkUploadValidationConstants:
    """Constants for bulk upload validation."""
    
    # File size limits
    MAX_ZIP_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MIN_ZIP_FILE_SIZE = 1024  # 1KB
    MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_FILENAME_LENGTH = 255
    MAX_DIRECTORY_DEPTH = 15
    
    # File type limits
    MAX_TEXT_FILE_SIZE = 1024 * 1024  # 1MB
    MAX_IMAGE_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Allowed extensions
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
    ALLOWED_TEXT_EXTENSIONS = ['.txt', '.json']
    ALLOWED_ZIP_MIME_TYPES = ['application/zip', 'application/x-zip-compressed']
    
    # Security patterns
    SUSPICIOUS_PATTERNS = [
        '<script', 'javascript:', 'data:', 'vbscript:', 
        'onload=', 'onerror=', 'onclick=', 'onmouseover='
    ]
    
    # Name validation
    MIN_NAME_LENGTH = 2
    MAX_CATEGORY_NAME_LENGTH = 100
    MAX_PRODUCT_NAME_LENGTH = 200
    
    # Text content validation
    MAX_TEXT_LENGTH = 5000  # Maximum length for text content like descriptions
    
    # Data field validation
    ALLOWED_CATEGORY_FIELDS = ['slug', 'description', 'secondary_description']
    ALLOWED_PRODUCT_FIELDS = [
        'description', 'secondary_description', 'tags', 'price', 'weight',
        # Additional fields for product data JSON files
        'Description', 'Ingredients', 'Features & Benefits', 'Usage Recommendation'
    ]


class SecurityValidator:
    """Handles security-related validation for bulk uploads."""
    
    @staticmethod
    def validate_name_security(name: str, max_length: int = BulkUploadValidationConstants.MAX_CATEGORY_NAME_LENGTH) -> bool:
        """Validate name for security and format requirements."""
        if not name or not isinstance(name, str):
            return False
        
        # Check length
        name_stripped = name.strip()
        if len(name_stripped) < BulkUploadValidationConstants.MIN_NAME_LENGTH or len(name_stripped) > max_length:
            return False
        
        # Check for suspicious patterns
        name_lower = name.lower()
        if any(pattern in name_lower for pattern in BulkUploadValidationConstants.SUSPICIOUS_PATTERNS):
            return False
        
        return True
    
    @staticmethod
    def validate_file_path_security(file_path: str) -> bool:
        """Validate file path for security issues."""
        if not file_path:
            return False
        
        # Prevent directory traversal attacks
        if '..' in file_path:
            return False
        
        # Allow absolute paths from temporary directories (for bulk upload)
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        # On macOS, temp files can be in /var/folders/... which links to /tmp
        # Also check for common temporary directory patterns
        temp_patterns = [temp_dir, '/tmp', '/var/folders']
        is_temp_path = any(file_path.startswith(pattern) for pattern in temp_patterns)
        
        if file_path.startswith('/') and not is_temp_path:
            return False
        
        # Check filename length
        filename = file_path.split('/')[-1]
        if len(filename) > BulkUploadValidationConstants.MAX_FILENAME_LENGTH:
            return False
        
        return True
    
    @staticmethod
    def sanitize_text_input(text: str) -> str:
        """Sanitize text input by removing potentially harmful content."""
        if not text:
            return ''
        
        # Remove HTML tags and suspicious content
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'data:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
        
        return text.strip()


class FileValidator:
    """Handles file-related validation for bulk uploads."""
    
    @staticmethod
    def validate_zip_file(zip_file: UploadedFile) -> None:
        """Comprehensive ZIP file validation."""
        if not zip_file:
            raise ValidationError("No file provided.")
        
        # Validate file extension
        if not zip_file.name.lower().endswith('.zip'):
            raise ValidationError("Please upload a valid ZIP file.")
        
        # Check file size limits
        FileValidator._validate_file_size(
            zip_file.size,
            BulkUploadValidationConstants.MIN_ZIP_FILE_SIZE,
            BulkUploadValidationConstants.MAX_ZIP_FILE_SIZE,
            "ZIP file"
        )
        
        # Validate file content type
        FileValidator._validate_zip_mime_type(zip_file)
        
        # Validate ZIP file structure and content
        FileValidator._validate_zip_structure(zip_file)
    
    @staticmethod
    def _validate_file_size(file_size: int, min_size: int, max_size: int, file_type: str) -> None:
        """Validate file size within specified limits."""
        if file_size > max_size:
            raise ValidationError(f"{file_type} size cannot exceed {max_size/1024/1024:.0f}MB.")
        
        if file_size < min_size:
            raise ValidationError(f"{file_type} is too small to be valid.")
    
    @staticmethod
    def _validate_zip_mime_type(zip_file: UploadedFile) -> None:
        """Validate ZIP file MIME type."""
        try:
            import magic
            file_type = magic.from_buffer(zip_file.read(1024), mime=True)
            zip_file.seek(0)  # Reset file pointer
            
            if file_type not in BulkUploadValidationConstants.ALLOWED_ZIP_MIME_TYPES:
                raise ValidationError("Invalid file type. Only ZIP files are allowed.")
        except ImportError:
            # Fallback if python-magic is not available
            pass
    
    @staticmethod
    def _validate_zip_structure(zip_file: UploadedFile) -> None:
        """Validate ZIP file internal structure and security."""
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                total_size = 0
                
                for file_info in zip_ref.filelist:
                    filename = file_info.filename
                    
                    # Security checks
                    if not SecurityValidator.validate_file_path_security(filename):
                        raise ValidationError("ZIP file contains suspicious file paths.")
                    
                    # Accumulate uncompressed size
                    total_size += file_info.file_size
                
                # Check total uncompressed size to prevent zip bombs
                if total_size > BulkUploadValidationConstants.MAX_UNCOMPRESSED_SIZE:
                    raise ValidationError("ZIP file uncompressed size exceeds security limits.")
            
            zip_file.seek(0)  # Reset file pointer
        except zipfile.BadZipFile:
            raise ValidationError("Invalid or corrupted ZIP file.")
        except Exception as e:
            raise ValidationError(f"Error validating ZIP file: {str(e)}")
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """Validate file extension against allowed list."""
        if not filename:
            return False
        
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        return f'.{file_ext}' in [ext.lower() for ext in allowed_extensions]
    
    @staticmethod
    def validate_file_content(file_path: str, file_size: int) -> bool:
        """Validate file content based on type and size."""
        if not file_path:
            return False
        
        file_ext = '.' + file_path.lower().split('.')[-1] if '.' in file_path else ''
        
        # Validate image files
        if file_ext in BulkUploadValidationConstants.ALLOWED_IMAGE_EXTENSIONS:
            return file_size <= BulkUploadValidationConstants.MAX_IMAGE_FILE_SIZE
        
        # Validate text files
        if file_ext in BulkUploadValidationConstants.ALLOWED_TEXT_EXTENSIONS:
            return file_size <= BulkUploadValidationConstants.MAX_TEXT_FILE_SIZE
        
        return False


class DataValidator:
    """Handles data structure validation for bulk uploads."""
    
    @staticmethod
    def validate_category_name(name: str) -> bool:
        """Validate category name."""
        return SecurityValidator.validate_name_security(
            name, 
            BulkUploadValidationConstants.MAX_CATEGORY_NAME_LENGTH
        )
    
    @staticmethod
    def validate_product_name(name: str) -> bool:
        """Validate product name."""
        return SecurityValidator.validate_name_security(
            name, 
            BulkUploadValidationConstants.MAX_PRODUCT_NAME_LENGTH
        )
    
    @staticmethod
    def validate_category_data(data: Dict[str, Any]) -> bool:
        """Validate category data structure."""
        return DataValidator._validate_data_structure(
            data, 
            BulkUploadValidationConstants.ALLOWED_CATEGORY_FIELDS
        )
    
    @staticmethod
    def validate_product_data(data: Dict[str, Any]) -> bool:
        """Validate product data structure."""
        return DataValidator._validate_data_structure(
            data, 
            BulkUploadValidationConstants.ALLOWED_PRODUCT_FIELDS
        )
    
    @staticmethod
    def _validate_data_structure(data: Dict[str, Any], allowed_fields: List[str]) -> bool:
        """Generic data structure validation."""
        if not isinstance(data, dict):
            return False
        
        # Check for allowed fields only
        for key in data.keys():
            if key not in allowed_fields:
                return False
        
        return True
    
    @staticmethod
    def sanitize_category_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize category data."""
        return DataValidator._sanitize_data_dict(data)
    
    @staticmethod
    def sanitize_product_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize product data."""
        return DataValidator._sanitize_data_dict(data)
    
    @staticmethod
    def _sanitize_data_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic data dictionary sanitization."""
        if not isinstance(data, dict):
            return {}
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = SecurityValidator.sanitize_text_input(value)
            else:
                sanitized[key] = value
        
        return sanitized


class BulkUploadValidator:
    """Main validator class that combines all validation functionality."""
    
    def __init__(self):
        self.security_validator = SecurityValidator()
        self.file_validator = FileValidator()
        self.data_validator = DataValidator()
    
    def validate_zip_upload(self, zip_file: UploadedFile) -> None:
        """Validate uploaded ZIP file."""
        self.file_validator.validate_zip_file(zip_file)
    
    def validate_category(self, name: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Validate category name and data."""
        if not self.data_validator.validate_category_name(name):
            return False
        
        if data and not self.data_validator.validate_category_data(data):
            return False
        
        return True
    
    def validate_product(self, name: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Validate product name and data."""
        if not self.data_validator.validate_product_name(name):
            return False
        
        if data and not self.data_validator.validate_product_data(data):
            return False
        
        return True
    
    def validate_file_path(self, file_path: str) -> bool:
        """Validate file path for security."""
        return self.security_validator.validate_file_path_security(file_path)
    
    def validate_file_content(self, file_path: str, file_size: int) -> bool:
        """Validate file content."""
        return self.file_validator.validate_file_content(file_path, file_size)
    
    def sanitize_text(self, text: str) -> str:
        """Sanitize text input."""
        return self.security_validator.sanitize_text_input(text)
    
    def sanitize_category_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize category data."""
        return self.data_validator.sanitize_category_data(data)
    
    def sanitize_product_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize product data."""
        return self.data_validator.sanitize_product_data(data)
    
    def validate_category_data_structure(self, data: Dict[str, Any]) -> bool:
        """Validate category data structure."""
        if not isinstance(data, dict):
            return False
        
        # Check for allowed fields
        allowed_fields = ['slug', 'description', 'secondary_description']
        for key in data.keys():
            if key not in allowed_fields:
                return False
        
        return True
    
    def validate_product_data_structure(self, data: Dict[str, Any]) -> bool:
        """Validate product data structure."""
        if not isinstance(data, dict):
            return False
        
        # Check for required fields and validate types
        allowed_fields = BulkUploadValidationConstants.ALLOWED_PRODUCT_FIELDS
        for key in data.keys():
            if key not in allowed_fields:
                return False
        
        return True