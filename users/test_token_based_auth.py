# users/test_token_based_auth.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from .models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import override_settings
import json


class TokenBasedAuthenticationTests(APITestCase):
    """
    Test the new token-based authentication flow for unverified users.
    
    This tests the integration between:
    1. Login API returning tokens for unverified users
    2. ResendVerificationEmailAPIView using those tokens
    3. Password reset edge cases for unverified users
    """
    
    def setUp(self):
        self.client = APIClient()
        self.client.enforce_csrf_checks = False
        
        # Create unverified user
        self.unverified_user = CustomUser.objects.create_user(
            username='unverifieduser',
            email='unverified@example.com',
            password='password123',
            first_name='Unverified',
            last_name='User',
            phone_number='+919876543210',
            birthdate='1990-01-01',
            is_email_verified=False,
            email_sent=False,
            email_failed=False
        )
        
        # Create verified user for comparison
        self.verified_user = CustomUser.objects.create_user(
            username='verifieduser',
            email='verified@example.com',
            password='password123',
            first_name='Verified',
            last_name='User',
            phone_number='+919876543211',
            birthdate='1990-01-01',
            is_email_verified=True,
            email_sent=True,
            email_failed=False
        )
        
        self.login_url = reverse('user-login')
        self.resend_url = reverse('resend-verification-email')
        self.password_reset_url = reverse('password_reset_confirm')
    
    def test_login_returns_tokens_for_unverified_user(self):
        """Test that login returns JWT tokens for unverified users in 403 response."""
        data = {
            'login': 'unverifieduser',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, data)
        
        # Should return 403 for unverified user but include tokens
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('verification_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('isUserEmailVerified', response.data)
        self.assertFalse(response.data['isUserEmailVerified'])
        self.assertIn('Please verify your email', response.data['error'])
    
    def test_login_success_for_verified_user(self):
        """Test that login works normally for verified users."""
        data = {
            'login': 'verifieduser',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, data)
        
        # Should return 200 for verified user
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('isUserEmailVerified', response.data)
        self.assertTrue(response.data['isUserEmailVerified'])
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_token_based_resend_verification_flow(self):
        """Test the complete flow: login -> get tokens -> use tokens for resend."""
        # Step 1: Login with unverified user to get tokens
        login_data = {
            'login': 'unverifieduser',
            'password': 'password123'
        }
        login_response = self.client.post(self.login_url, login_data)
        self.assertEqual(login_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Extract verification token (acts as access token for unverified users)
        access_token = login_response.data['verification_token']
        
        # Step 2: Use token to call resend verification endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        resend_response = self.client.post(self.resend_url, {})
        
        # Should succeed with token-based authentication
        self.assertEqual(resend_response.status_code, status.HTTP_200_OK)
        self.assertIn('message', resend_response.data)
        self.assertEqual(resend_response.data['stored_email_address'], 'unverified@example.com')
    
    def test_resend_verification_without_token_fails(self):
        """Test that resend verification fails without authentication token."""
        response = self.client.post(self.resend_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_resend_verification_with_invalid_token_fails(self):
        """Test that resend verification fails with invalid token."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = self.client.post(self.resend_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_password_reset_edge_cases_for_unverified_users(self):
        """Test enhanced password reset responses for unverified users."""
        # Test password reset for unverified user with required uid and token parameters
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        
        uid = urlsafe_base64_encode(force_bytes(self.unverified_user.pk))
        token = default_token_generator.make_token(self.unverified_user)
        
        data = {
            'uid': uid,
            'token': token,
            'new_password': 'newpassword123'
        }
        response = self.client.post(self.password_reset_url, data)
        
        # Should return 403 with enhanced guidance
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('verification_status', response.data)
        self.assertIn('guidance', response.data)
        
        # Check verification status details
        verification_status = response.data['verification_status']
        self.assertIn('is_newly_registered', verification_status)
        self.assertIn('email_failed', verification_status)
        self.assertIn('registration_date', verification_status)
        
        # Check guidance is provided
        guidance = response.data['guidance']
        self.assertIn('message', guidance)
        self.assertIn('recommended_action', guidance)
    
    def test_verified_user_can_reset_password(self):
        """Test that verified users can reset password normally."""
        # Test with valid uid and token for verified user
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        
        uid = urlsafe_base64_encode(force_bytes(self.verified_user.pk))
        token = default_token_generator.make_token(self.verified_user)
        
        data = {
            'uid': uid,
            'token': token,
            'new_password': 'newpassword123'
        }
        response = self.client.post(self.password_reset_url, data)
        
        # Should not return 403 (forbidden for unverified), may return other status for validation
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_token_based_auth_preserves_user_context(self):
        """Test that token-based auth correctly identifies the user."""
        # Login to get token
        login_data = {
            'login': 'unverifieduser',
            'password': 'password123'
        }
        login_response = self.client.post(self.login_url, login_data)
        access_token = login_response.data['verification_token']
        
        # Use token for resend verification
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        resend_response = self.client.post(self.resend_url, {})
        
        # Verify the correct user's email is used
        self.assertEqual(resend_response.data['stored_email_address'], 'unverified@example.com')
        
        # Test with different user
        other_user = CustomUser.objects.create_user(
            username='otherunverified',
            email='other@example.com',
            password='password123',
            is_email_verified=False
        )
        
        # Login with other user
        login_data['login'] = 'otherunverified'
        login_response = self.client.post(self.login_url, login_data)
        other_access_token = login_response.data['verification_token']
        
        # Use other user's token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_access_token}')
        resend_response = self.client.post(self.resend_url, {})
        
        # Should use the other user's email
        self.assertEqual(resend_response.data['stored_email_address'], 'other@example.com')