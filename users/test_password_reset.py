# users/test_password_reset.py

from django.urls import reverse
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch
from .models import CustomUser
from .tokens import custom_token_generator
from .encryption import encrypt_email_token

User = get_user_model()


class PasswordResetConfirmEncryptedTests(APITestCase):
    """Comprehensive test suite for password reset functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.client.enforce_csrf_checks = False
        
        # Create test users with different states
        self.active_verified_user = CustomUser.objects.create_user(
            username='activeuser',
            email='active@example.com',
            password='oldpassword123',
            first_name='Active',
            last_name='User',
            phone_number='+919876543210',
            birthdate='1990-01-01',
            is_email_verified=True,
            is_active=True
        )
        
        self.inactive_user = CustomUser.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='oldpassword123',
            first_name='Inactive',
            last_name='User',
            phone_number='+919876543211',
            birthdate='1990-01-01',
            is_email_verified=True,
            is_active=False
        )
        
        self.unverified_user = CustomUser.objects.create_user(
            username='unverifieduser',
            email='unverified@example.com',
            password='oldpassword123',
            first_name='Unverified',
            last_name='User',
            phone_number='+919876543212',
            birthdate='1990-01-01',
            is_email_verified=False,
            is_active=True
        )
        
        self.password_reset_url = reverse('password_reset_confirm')
    
    def generate_valid_token_data(self, user):
        """Generate valid uid and token for password reset"""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        encrypted_token = encrypt_email_token(user.pk, 'password_reset', user_password_hash=user.password)
        return uid, encrypted_token
    
    def generate_invalid_uid(self):
        """Generate invalid uid"""
        return urlsafe_base64_encode(force_bytes(99999))  # Non-existent user ID
    
    def generate_invalid_token(self):
        """Generate invalid token"""
        return "invalid-token-string"
    
    def test_missing_parameters(self):
        """Test password reset with missing uid or token parameters"""
        # Missing both parameters
        response = self.client.post(self.password_reset_url, {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Missing reset parameters')
        self.assertEqual(response.data['action_required'], 'check_reset_link')
        
        # Missing uid parameter
        _, token = self.generate_valid_token_data(self.active_verified_user)
        response = self.client.post(f"{self.password_reset_url}?token={token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Missing reset parameters')
        
        # Missing token parameter
        uid, _ = self.generate_valid_token_data(self.active_verified_user)
        response = self.client.post(f"{self.password_reset_url}?uid={uid}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Missing reset parameters')
    
    def test_invalid_user_id(self):
        """Test password reset with invalid user ID"""
        invalid_uid = self.generate_invalid_uid()
        _, token = self.generate_valid_token_data(self.active_verified_user)
        
        response = self.client.post(f"{self.password_reset_url}?uid={invalid_uid}&token={token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid user ID')
        self.assertEqual(response.data['action_required'], 'request_new_reset_link')
    
    def test_inactive_user_account(self):
        """Test password reset for inactive user account"""
        uid, token = self.generate_valid_token_data(self.inactive_user)
        
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'User account is inactive')
        self.assertEqual(response.data['action_required'], 'contact_support')
        self.assertIn('support_phone', response.data)
    
    def test_unverified_email_account(self):
        """Test password reset for user with unverified email"""
        uid, token = self.generate_valid_token_data(self.unverified_user)
        
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Email must be verified before password reset')
        self.assertEqual(response.data['stored_email_address'], self.unverified_user.email)
        self.assertEqual(response.data['action_required'], 'verify_email_first')
    
    def test_invalid_token(self):
        """Test password reset with invalid token"""
        uid, _ = self.generate_valid_token_data(self.active_verified_user)
        invalid_token = self.generate_invalid_token()
        
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={invalid_token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid or expired reset token')
        self.assertEqual(response.data['action_required'], 'request_new_reset_link')
    
    def test_missing_password_fields(self):
        """Test password reset with missing password fields"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        # Missing both password fields
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Both password fields are required')
        self.assertEqual(response.data['action_required'], 'provide_passwords')
        self.assertIn('required_fields', response.data)
        
        # Missing new_password1
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Both password fields are required')
        
        # Missing new_password2
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Both password fields are required')
    
    def test_password_confirmation_mismatch(self):
        """Test password reset with mismatched password confirmation"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'differentpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Password confirmation does not match')
        self.assertEqual(response.data['action_required'], 'match_passwords')
    
    def test_weak_password_validation(self):
        """Test password reset with weak passwords"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        # Test too short password
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': '123',
            'new_password2': '123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Password validation failed')
        self.assertEqual(response.data['action_required'], 'strengthen_password')
        self.assertIn('validation_errors', response.data)
        self.assertIn('password_requirements', response.data)
        
        # Test numeric-only password
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': '12345678',
            'new_password2': '12345678'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Password validation failed')
        
        # Test common password
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'password',
            'new_password2': 'password'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Password validation failed')
    
    def test_successful_password_reset(self):
        """Test successful password reset"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newstrongpassword123',
            'new_password2': 'newstrongpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password has been reset successfully')
        self.assertEqual(response.data['action_required'], 'login_with_new_password')
        self.assertEqual(response.data['next_step'], 'redirect_to_login')
        
        # Verify password was actually changed
        self.active_verified_user.refresh_from_db()
        self.assertTrue(self.active_verified_user.check_password('newstrongpassword123'))
        self.assertFalse(self.active_verified_user.check_password('oldpassword123'))
    
    def test_token_reuse_prevention(self):
        """Test that tokens cannot be reused after successful password reset"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        # First password reset - should succeed
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newstrongpassword123',
            'new_password2': 'newstrongpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Second attempt with same token - should fail
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'anothernewpassword123',
            'new_password2': 'anothernewpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid or expired reset token')
    
    @override_settings(ENABLE_RATE_LIMIT=True, TESTING=False)
    def test_rate_limiting(self):
        """Test rate limiting for password reset attempts"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        # Make multiple rapid requests to trigger rate limiting
        for i in range(10):
            response = self.client.post(f"{self.password_reset_url}?uid={uid}&token=invalid-token-{i}", {
                'new_password1': 'newpassword123',
                'new_password2': 'newpassword123'
            })
            
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                self.assertIn('rate limit', response.data.get('error', '').lower())
                break
    
    def test_malformed_uid_parameter(self):
        """Test password reset with malformed uid parameter"""
        _, token = self.generate_valid_token_data(self.active_verified_user)
        
        # Test with non-base64 uid
        response = self.client.post(f"{self.password_reset_url}?uid=invalid-uid&token={token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid user ID')
    
    def test_response_format_consistency(self):
        """Test that all responses follow consistent format"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        # Test error response format
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token=invalid", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        required_error_fields = ['error', 'details', 'action_required']
        for field in required_error_fields:
            self.assertIn(field, response.data)
        
        # Test success response format
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newstrongpassword123',
            'new_password2': 'newstrongpassword123'
        })
        
        required_success_fields = ['message', 'details', 'action_required', 'next_step']
        for field in required_success_fields:
            self.assertIn(field, response.data)
    
    def test_security_headers_and_methods(self):
        """Test security aspects of the endpoint"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        # Test that only POST method is allowed
        response = self.client.get(f"{self.password_reset_url}?uid={uid}&token={token}")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test that PUT method is not allowed
        response = self.client.put(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_edge_case_empty_passwords(self):
        """Test password reset with empty password strings"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': '',
            'new_password2': ''
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Both password fields are required')
    
    def test_integration_with_login_after_reset(self):
        """Test that user can login with new password after successful reset"""
        uid, token = self.generate_valid_token_data(self.active_verified_user)
        
        # Reset password
        response = self.client.post(f"{self.password_reset_url}?uid={uid}&token={token}", {
            'new_password1': 'newstrongpassword123',
            'new_password2': 'newstrongpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test login with new password
        login_response = self.client.post(reverse('user-login'), {
            'login': self.active_verified_user.username,
            'password': 'newstrongpassword123'
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        
        # Test that old password no longer works
        old_login_response = self.client.post(reverse('user-login'), {
            'login': self.active_verified_user.username,
            'password': 'oldpassword123'
        })
        self.assertEqual(old_login_response.status_code, status.HTTP_401_UNAUTHORIZED)