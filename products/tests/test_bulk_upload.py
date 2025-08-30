import os
import tempfile
from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest
from unittest.mock import patch, MagicMock

from products.models import BulkUpload, Product
from products.admin import BulkUploadAdmin
from products.services import CatalogProcessingService
from categories.models import Category

User = get_user_model()


class BulkUploadModelTest(TestCase):
    """Test cases for BulkUpload model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_bulk_upload_creation(self):
        """Test BulkUpload model creation with valid data."""
        zip_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"  # Simple ZIP header
        zip_file = SimpleUploadedFile(
            "test_products.zip",
            zip_content,
            content_type="application/zip"
        )
        
        bulk_upload = BulkUpload.objects.create(
            uploaded_by=self.user,
            zip_file=zip_file,
            status='pending'
        )
        
        self.assertEqual(bulk_upload.uploaded_by, self.user)
        self.assertEqual(bulk_upload.status, 'pending')
        self.assertIsNotNone(bulk_upload.uploaded_at)
        self.assertIsNone(bulk_upload.processed_at)
        self.assertEqual(bulk_upload.categories_created, 0)
        self.assertEqual(bulk_upload.products_created, 0)
        
    def test_bulk_upload_str_representation(self):
        """Test string representation of BulkUpload model."""
        zip_file = SimpleUploadedFile(
            "test.zip",
            b"test content",
            content_type="application/zip"
        )
        
        bulk_upload = BulkUpload.objects.create(
            uploaded_by=self.user,
            zip_file=zip_file
        )
        
        expected_str = f"Bulk Upload #{bulk_upload.id} by {self.user.username}"
        self.assertEqual(str(bulk_upload), expected_str)
        
    def test_bulk_upload_status_choices(self):
        """Test BulkUpload status field choices."""
        zip_file = SimpleUploadedFile(
            "test.zip",
            b"test content",
            content_type="application/zip"
        )
        
        # Test all valid status choices
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        
        for status in valid_statuses:
            bulk_upload = BulkUpload.objects.create(
                uploaded_by=self.user,
                zip_file=zip_file,
                status=status
            )
            self.assertEqual(bulk_upload.status, status)


class CatalogProcessingServiceTest(TestCase):
    """Test cases for CatalogProcessingService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
    def test_service_initialization(self):
        """Test CatalogProcessingService initialization."""
        zip_file = SimpleUploadedFile(
            "test.zip",
            b"test content",
            content_type="application/zip"
        )
        
        bulk_upload = BulkUpload.objects.create(
            uploaded_by=self.user,
            zip_file=zip_file,
            status='pending'
        )
        
        service = CatalogProcessingService(bulk_upload)
        self.assertEqual(service.bulk_upload, bulk_upload)
        
    def test_service_exists(self):
        """Test that CatalogProcessingService class exists and can be imported."""
        self.assertTrue(hasattr(CatalogProcessingService, 'process_catalog'))


class BulkUploadAdminTest(TestCase):
    """Test cases for BulkUploadAdmin."""
    
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.site = AdminSite()
        self.admin = BulkUploadAdmin(BulkUpload, self.site)
        
    def test_admin_list_display(self):
        """Test admin list display configuration."""
        expected_fields = [
            'id', 'zip_file_name', 'status_badge', 'uploaded_by', 
            'uploaded_at', 'processed_at', 'processing_summary', 'actions_column'
        ]
        self.assertEqual(list(self.admin.list_display), expected_fields)
        
    def test_admin_list_filter(self):
        """Test admin list filter configuration."""
        expected_filters = ['status', 'uploaded_at', 'uploaded_by']
        self.assertEqual(list(self.admin.list_filter), expected_filters)
        
    def test_admin_search_fields(self):
        """Test admin search fields configuration."""
        expected_fields = ['zip_file', 'uploaded_by__username']
        self.assertEqual(list(self.admin.search_fields), expected_fields)
        
    def test_admin_readonly_fields(self):
        """Test admin readonly fields configuration."""
        expected_fields = [
            'status', 'uploaded_at', 'processed_at', 'uploaded_by',
            'categories_created', 'categories_updated', 'products_created', 
            'products_updated', 'images_processed', 'error_log', 'processing_notes'
        ]
        self.assertEqual(list(self.admin.readonly_fields), expected_fields)
        
    def test_admin_fieldsets(self):
        """Test admin fieldsets configuration."""
        fieldsets = self.admin.fieldsets
        self.assertEqual(len(fieldsets), 3)
        
        # Check Upload Information section
        upload_info = fieldsets[0]
        self.assertEqual(upload_info[0], 'Upload Information')
        self.assertIn('uploaded_by', upload_info[1]['fields'])
        self.assertIn('zip_file', upload_info[1]['fields'])
        
        # Check Processing Results section
        processing_results = fieldsets[1]
        self.assertEqual(processing_results[0], 'Processing Results')
        self.assertIn('processed_at', processing_results[1]['fields'])
        
        # Check Error Details section
        error_details = fieldsets[2]
        self.assertEqual(error_details[0], 'Error Details')
        self.assertIn('error_log', error_details[1]['fields'])
        
    def test_admin_ordering(self):
        """Test admin ordering configuration."""
        expected_ordering = ['-uploaded_at']
        self.assertEqual(list(self.admin.ordering), expected_ordering)
        
    def test_admin_actions(self):
        """Test admin actions configuration."""
        self.assertIn('process_selected_uploads', self.admin.actions)
        self.assertIn('reprocess_failed_uploads', self.admin.actions)
        
    def test_process_selected_uploads_action(self):
        """Test process selected uploads admin action."""
        # Create test bulk uploads
        zip_file = SimpleUploadedFile(
            "test.zip",
            b"test content",
            content_type="application/zip"
        )
        
        bulk_upload = BulkUpload.objects.create(
            uploaded_by=self.user,
            zip_file=zip_file,
            status='pending'
        )
        
        # Create mock request
        request = HttpRequest()
        request.user = self.user
        
        # Create queryset
        queryset = BulkUpload.objects.filter(id=bulk_upload.id)
        
        # Execute action
        result = self.admin.process_selected_uploads(request, queryset)
        self.assertIsNone(result)  # Action should complete without returning a response
            
    def test_has_add_permission(self):
        """Test add permission for BulkUpload admin."""
        request = HttpRequest()
        request.user = self.user
        
        # Should allow adding new bulk uploads
        self.assertTrue(self.admin.has_add_permission(request))
        
    def test_has_change_permission(self):
        """Test change permission for BulkUpload admin."""
        request = HttpRequest()
        request.user = self.user
        
        # Should allow changing for superusers
        self.assertTrue(self.admin.has_change_permission(request))
        
    def test_has_delete_permission(self):
        """Test delete permission for BulkUpload admin."""
        request = HttpRequest()
        request.user = self.user
        
        # Should allow deleting bulk uploads
        self.assertTrue(self.admin.has_delete_permission(request))


class BulkUploadIntegrationTest(TestCase):
    """Integration tests for bulk upload functionality."""
    
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
    def test_bulk_upload_model_integration(self):
        """Test BulkUpload model integration with admin."""
        zip_file = SimpleUploadedFile(
            "test_catalog.zip",
            b"test zip content",
            content_type="application/zip"
        )
        
        # Create bulk upload
        bulk_upload = BulkUpload.objects.create(
            uploaded_by=self.user,
            zip_file=zip_file,
            status='pending'
        )
        
        # Verify creation
        self.assertEqual(bulk_upload.uploaded_by, self.user)
        self.assertEqual(bulk_upload.status, 'pending')
        self.assertIsNotNone(bulk_upload.uploaded_at)
        
        # Test status update
        bulk_upload.status = 'completed'
        bulk_upload.save()
        
        bulk_upload.refresh_from_db()
        self.assertEqual(bulk_upload.status, 'completed')
        
    def test_bulk_upload_admin_integration(self):
        """Test BulkUpload admin interface integration."""
        from django.contrib.admin.sites import AdminSite
        from products.admin import BulkUploadAdmin
        
        site = AdminSite()
        admin = BulkUploadAdmin(BulkUpload, site)
        
        # Test admin configuration
        self.assertIsNotNone(admin.list_display)
        self.assertIsNotNone(admin.list_filter)
        self.assertIsNotNone(admin.search_fields)
        self.assertIsNotNone(admin.readonly_fields)
        
        # Test admin actions
        self.assertIn('process_selected_uploads', admin.actions)
        self.assertIn('reprocess_failed_uploads', admin.actions)