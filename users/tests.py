# users/tests.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from .models import CustomUser, Address
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import override_settings


class UserAccountTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='testuser@gmail.com',
            password='password123',
            first_name='Test',
            last_name='User',
            phone_number='+919876543210',
            birthdate='1990-01-01'
        )
        # Mark the test user as email-verified to allow login per policy
        self.user.is_email_verified = True
        self.user.save(update_fields=['is_email_verified'])
        
        # Create an address associated with the user
        self.address = Address.objects.create(
            user=self.user,
            address_line1='Test Address',
            city='Test City',
            state='Test State',
            country='India',
            postal_code='123456'
        )
        
        self.client = APIClient()
        self.client.enforce_csrf_checks = False

        # Adjust sample_data to use a nested address structure for new user registration
        self.sample_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+919765432109',
            'birthdate': '2000-01-01',
            'addresses': [{
                'address_line1': 'New Address',
                'city': 'New City',
                'state': 'New State',
                'country': 'India',
                'postal_code': '654321'
            }]
        }

    def tearDown(self):
        # Log out after each test case
        self.client.logout()

    def test_user_registration(self):
        url = reverse('user-register')
        data = {
            "username": "newuser1",
            "email": "newuser1@example.com",
            "password": "newpassword123",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "+919000000001",
            "birthdate": "2000-01-01",
            "addresses": [
                {
                    "address_line1": "123 Main St",
                    "address_line2": "",
                    "city": "Anytown",
                    "state": "Anystate",
                    "country": "India",
                    "postal_code": "123456"
                }
            ]
        }

        # Make sure to use format='json' to correctly handle the nested data structure
        response = self.client.post(url, data, format='json')
        print("8888888888888", response)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Unexpected response: {response.data}")
        self.assertEqual(response.data['username'], 'newuser1')


    def test_user_login_with_username(self):
        url = reverse('user-login')
        data = {
            'login': 'testuser',
            'password': 'password123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


    def test_user_login_with_phone_number(self):
        url = reverse('user-login')
        data = {
            'login': '+919876543210',
            'password': 'password123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


    def test_user_login_invalid_credentials(self):
        url = reverse('user-login')
        data = {
            'login': 'invaliduser',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ResendVerificationEmailAPIViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.enforce_csrf_checks = False
        
        # Create verified user
        self.verified_user = CustomUser.objects.create_user(
            username='verifieduser',
            email='verified@example.com',
            password='password123',
            first_name='Verified',
            last_name='User',
            phone_number='+919876543210',
            birthdate='1990-01-01',
            is_email_verified=True,
            email_sent=True,
            email_failed=False
        )
        
        # Create unverified user
        self.unverified_user = CustomUser.objects.create_user(
            username='unverifieduser',
            email='unverified@example.com',
            password='password123',
            first_name='Unverified',
            last_name='User',
            phone_number='+919876543211',
            birthdate='1990-01-01',
            is_email_verified=False,
            email_sent=False,
            email_failed=False
        )
        
        # Create user with failed email
        self.failed_email_user = CustomUser.objects.create_user(
            username='failedemailuser',
            email='failed@example.com',
            password='password123',
            first_name='Failed',
            last_name='User',
            phone_number='+919876543212',
            birthdate='1990-01-01',
            is_email_verified=False,
            email_sent=False,
            email_failed=True
        )
        
        # Create inactive user
        self.inactive_user = CustomUser.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='password123',
            first_name='Inactive',
            last_name='User',
            phone_number='+919876543213',
            birthdate='1990-01-01',
            is_email_verified=False,
            email_sent=False,
            email_failed=False,
            is_active=False
        )
        
        # Create user without email
        self.no_email_user = CustomUser.objects.create_user(
            username='noemailuser',
            email='',
            password='password123',
            first_name='NoEmail',
            last_name='User',
            phone_number='+919876543214',
            birthdate='1990-01-01',
            is_email_verified=False,
            email_sent=False,
            email_failed=False
        )
        
        self.resend_url = reverse('resend-verification-email')
    
    def get_auth_token(self, user):
        """Helper method to get JWT token for a user"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_authentication_required(self):
        """Test that authentication is required to access the endpoint"""
        response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Authentication credentials were not provided', str(response.data))
    
    def test_invalid_token_authentication(self):
        """Test that invalid token returns 401"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_already_verified_user(self):
        """Test resending email to already verified user returns 400"""
        token = self.get_auth_token(self.verified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.resend_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Email is already verified')
        self.assertEqual(response.data['stored_email_address'], 'verified@example.com')
        self.assertIn('remaining_attempts', response.data)
    
    def test_user_without_email(self):
        """Test user without email address returns 400"""
        token = self.get_auth_token(self.no_email_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.resend_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'User account does not have an email address configured')
        self.assertEqual(response.data['action_required'], 'contact_support')
    
    def test_inactive_user(self):
        """Test inactive user returns 401"""
        # First make the user active to get a token, then deactivate
        self.inactive_user.is_active = True
        self.inactive_user.save()
        token = self.get_auth_token(self.inactive_user)
        
        # Now deactivate the user
        self.inactive_user.is_active = False
        self.inactive_user.save()
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.resend_url)
        
        # JWT authentication returns 401 for inactive users, not 403
        self.assertEqual(response.status_code, 401)
        self.assertEqual(str(response.data.get('detail')), 'User is inactive')
        self.assertEqual(response.data.get('detail').code, 'authentication_failed')
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_successful_email_resend_unverified_user(self):
        """Test successful email resend for unverified user"""
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.resend_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Please verify your email at unverified@example.com', response.data['message'])
        self.assertEqual(response.data['stored_email_address'], 'unverified@example.com')
        self.assertTrue(response.data['email_sent'])
        self.assertTrue(response.data['verification_required'])
        self.assertIn('remaining_attempts', response.data)
        
        # Check user fields updated
        self.unverified_user.refresh_from_db()
        self.assertTrue(self.unverified_user.email_sent)
        self.assertFalse(self.unverified_user.email_failed)
    
    def test_failed_email_delivery(self):
        """Test failed email delivery scenario"""
        # Mock email sending to fail
        from unittest.mock import patch
        
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        with patch('users.api.send_verification_email', return_value=False):
            response = self.client.post(self.resend_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], 'Failed to send verification email. Please try again later or contact support.')
        self.assertEqual(response.data['stored_email_address'], 'unverified@example.com')
        self.assertFalse(response.data['email_sent'])
        self.assertEqual(response.data['action_required'], 'contact_support')
        self.assertIn('remaining_attempts', response.data)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recovery_from_failed_email_state(self):
        """Test recovery from failed email state"""
        token = self.get_auth_token(self.failed_email_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Verify initial state
        self.assertTrue(self.failed_email_user.email_failed)
        self.assertFalse(self.failed_email_user.email_sent)
        
        response = self.client.post(self.resend_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Please verify your email at failed@example.com', response.data['message'])
        self.assertEqual(response.data['stored_email_address'], 'failed@example.com')
        self.assertTrue(response.data['email_sent'])
        self.assertTrue(response.data['verification_required'])
        
        # Check user fields updated - should reset failed state and set sent
        self.failed_email_user.refresh_from_db()
        self.assertTrue(self.failed_email_user.email_sent)
        self.assertFalse(self.failed_email_user.email_failed)
    
    def test_email_verified_field_scenarios(self):
        """Test is_email_verified field in different scenarios"""
        # Test verified user
        self.assertTrue(self.verified_user.is_email_verified)
        
        # Test unverified user
        self.assertFalse(self.unverified_user.is_email_verified)
        
        # Test failed email user
        self.assertFalse(self.failed_email_user.is_email_verified)
        
        # Test that verified user gets proper error response
        token = self.get_auth_token(self.verified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Email is already verified')
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_email_sent_field_updates(self):
        """Test email_sent field updates correctly"""
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Initial state
        self.assertFalse(self.unverified_user.email_sent)
        
        response = self.client.post(self.resend_url)
        
        # Check response indicates email was sent
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['email_sent'])
        
        # Check database field updated
        self.unverified_user.refresh_from_db()
        self.assertTrue(self.unverified_user.email_sent)
        self.assertFalse(self.unverified_user.email_failed)
    
    def test_email_failed_field_updates(self):
        """Test email_failed field updates correctly"""
        from unittest.mock import patch
        
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Initial state
        self.assertFalse(self.unverified_user.email_failed)
        
        with patch('users.api.send_verification_email', return_value=False):
            response = self.client.post(self.resend_url)
        
        # Check response indicates email failed
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data['email_sent'])
    
    @override_settings(ENABLE_RATE_LIMIT=True, TESTING=False)
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        from users.email_rate_limit import EmailResendAttempt
        
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create 5 attempts to reach the limit
        for i in range(5):
            EmailResendAttempt.record_attempt(
                email=self.unverified_user.email,
                ip_address='127.0.0.1',
                success=True
            )
        
        response = self.client.post(self.resend_url)
        
        # Should be rate limited
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Daily email resend limit exceeded', response.data['error'])
        self.assertTrue(response.data['rate_limit_exceeded'])
        self.assertEqual(response.data['attempts_today'], 5)
        self.assertIn('support_phone', response.data)
        self.assertEqual(response.data['stored_email_address'], 'unverified@example.com')
    
    def test_rate_limiting_attempt_recording(self):
        """Test that attempts are properly recorded for rate limiting"""
        from users.email_rate_limit import EmailResendAttempt
        
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Clear any existing attempts
        EmailResendAttempt.objects.filter(email=self.unverified_user.email).delete()
        
        # Make a request
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.resend_url)
        
        # Check that attempt was recorded
        attempts = EmailResendAttempt.objects.filter(email=self.unverified_user.email)
        self.assertEqual(attempts.count(), 1)
        
        attempt = attempts.first()
        self.assertEqual(attempt.email, self.unverified_user.email)
        self.assertTrue(attempt.success)  # Should be successful with locmem backend
    
    def test_remaining_attempts_calculation(self):
        """Test that remaining attempts are calculated correctly"""
        from users.email_rate_limit import EmailResendAttempt
        
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Clear any existing attempts
        EmailResendAttempt.objects.filter(email=self.unverified_user.email).delete()
        
        # Create 2 attempts
        for i in range(2):
            EmailResendAttempt.record_attempt(
                email=self.unverified_user.email,
                ip_address='127.0.0.1',
                success=True
            )
        
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.resend_url)
        
        # Should have 2 remaining attempts (5 max - 2 existing - 1 current = 2)
        self.assertEqual(response.data['remaining_attempts'], 2)
    
    def test_response_format_consistency(self):
        """Test that all responses follow consistent format"""
        # Test successful response format
        token = self.get_auth_token(self.unverified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.resend_url)
        
        # Check required fields in successful response
        required_fields = ['message', 'stored_email_address', 'email_sent', 'verification_required', 'remaining_attempts']
        for field in required_fields:
            self.assertIn(field, response.data)
        
        # Test error response format for already verified user
        token = self.get_auth_token(self.verified_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.post(self.resend_url)
        
        # Check required fields in error response
        required_fields = ['error', 'stored_email_address', 'remaining_attempts']
        for field in required_fields:
            self.assertIn(field, response.data)
        self.assertEqual(response.data['error'], 'Email is already verified')


class UserAccountTestsExtended(UserAccountTests):
    """Extended tests for UserAccountTests that were misplaced"""
    
    @override_settings(ENABLE_RATE_LIMIT=True, TESTING=False)
    def test_rate_limit_registration(self):
        url = reverse('user-register')

        # Send requests with unique data
        for i in range(5):
            unique_data = {
                'username': f'newuser{i}',
                'email': f'newuser{i}@example.com',
                'password': 'newpassword123',
                'first_name': 'New',
                'last_name': 'User',
                'phone_number': f'+919000{i}54321',
                'birthdate': '2000-01-01',
                'addresses': [{
                    'address_line1': '123 Main St',
                    'address_line2': '',
                    'city': 'Anytown',
                    'state': 'Anystate',
                    'country': 'India',
                    'postal_code': '123456'
                }]
            }
            
            response = self.client.post(url, data=unique_data, format='json')
            print("test_rate_limit_registration ******", response)

            # Verify successful registration within limit (i < 3)
            if i < 3:
                self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                                 f"Request {i+1} should be successful: {response.data}")

            # Verify rate limit exceeded (i >= 3)
            else:
                self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_429_TOO_MANY_REQUESTS],
                              f"Expected rate limit error but got {response.status_code}: {response.data}")


    def test_user_logout(self):
        # Create a fresh user specifically for this test to avoid conflicts
        logout_user = CustomUser.objects.create_user(
            username='logoutuser',
            email='logoutuser@gmail.com',
            password='password123',
            first_name='Logout',
            last_name='User',
            phone_number='+919876543211',
            birthdate='1990-01-01',
            is_email_verified=True
        )
        
        # Log in to get the access and refresh tokens
        login_response = self.client.post(reverse('user-login'), {
            'login': 'logoutuser',
            'password': 'password123'
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)
        
        # Use the access token for logout attempt
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + login_response.data['access'])

        # Attempt to logout using the refresh token
        logout_response = self.client.post(reverse('user-logout'), {
            'refresh': login_response.data['refresh']
        })
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        # Try to refresh the token using the old refresh token, which should fail
        refresh_response = self.client.post(reverse('token_refresh'), {
            'refresh': login_response.data['refresh']
        })
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Clear credentials for next tests
        self.client.credentials()


    def test_token_blacklisting(self):
        # Log in to get the refresh token
        login_response = self.client.post(reverse('user-login'), {
            'login': 'testuser',
            'password': 'password123'
        })
        refresh_token = login_response.data['refresh']

        # Convert the refresh token string into a RefreshToken object
        refresh_token_obj = RefreshToken(refresh_token)

        # Blacklist the refresh token
        refresh_token_obj.blacklist()

        # Attempt to use the blacklisted refresh token to get a new access token
        refresh_response = self.client.post(reverse('token_refresh'), {
            'refresh': str(refresh_token_obj)
        })
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)



    def test_multiple_sessions_handling(self):
        # Log in multiple times to simulate multiple sessions
        tokens = []
        for _ in range(3):
            login_response = self.client.post(reverse('user-login'), {
                'login': 'testuser',
                'password': 'password123'
            })
            tokens.append(login_response.data['refresh'])

        # Invalidate one session
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + login_response.data['access'])  # Ensure you use the correct token
        logout_response = self.client.post(reverse('user-logout'), {'refresh': tokens[1]})
        print("test_multiple_sessions_handling Logout response:", logout_response.data)  # Debug output

        # Clear credentials before next request
        self.client.credentials()

        # Check if the specific session is invalidated
        refresh_response = self.client.post(reverse('token_refresh'), {'refresh': tokens[1]})
        print("test_multiple_sessions_handling Refresh response for blacklisted token:", refresh_response.data)  # Debug output
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Ensure other sessions are still valid
        for index, token in enumerate([tokens[0], tokens[2]]):
            self.client.credentials()  # Clear previous credentials
            refresh_response = self.client.post(reverse('token_refresh'), {'refresh': token})
            print(f"test_multiple_sessions_handling Refresh response for session {index}:", refresh_response.data)  # Debug output
            self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)


    def test_prevent_updating_email_and_phone(self):
        self.client.force_authenticate(user=self.user)
        original_email = self.user.email
        original_phone = self.user.phone_number
        response = self.client.put(reverse('user-profile'), {
            'email': 'newemail@example.com',  # This should not change
            'phone_number': '+919876543210',  # This should not change
            'first_name': 'UpdatedName'       # This should update
        }, format='json')
        self.user.refresh_from_db()

        # Debugging output
        print("test_prevent_updating_email_and_phone Response data:", response.data)
        print("test_prevent_updating_email_and_phone Updated email:", self.user.email)
        print("test_prevent_updating_email_and_phone Updated phone number:", self.user.phone_number)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.user.email, original_email)  # Ensure email has not changed
        self.assertEqual(self.user.phone_number, original_phone)  # Ensure phone number has not changed
        self.assertEqual(self.user.first_name, 'UpdatedName')  # Ensure first name was updated


    @override_settings(ENABLE_RATE_LIMIT=False)
    def test_user_registration_with_required_and_optional_addresses(self):
        url = reverse('user-register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+919765432109',
            'birthdate': '2000-01-01',
            'addresses': [{
                'address_line1': 'New Address',
                'city': 'New City',
                'state': 'New State',
                'country': 'India',
                'postal_code': '654321'
            }]
        }
        response = self.client.post(url, data, format='json')
        print("test_user_registration_with_required_and_optional_addresses ===", response)
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Failed to create user: {response.data}")  # Debug output to understand what went wrong.
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(CustomUser.objects.get(username='newuser'))

    def test_accessibility_of_registration_endpoint(self):
        url = reverse('user-register')
        response = self.client.get(url)  # Change this to a post if your endpoint doesn't support get.
        print("test_accessibility_of_registration_endpoint Test endpoint accessibility response data:", response.data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED])

    def test_user_registration_with_multiple_addresses(self):
        url = reverse('user-register')
        data = {
            "username": "newuser2",
            "email": "newuser2@example.com",
            "password": "newpassword123",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "+919000000002",
            "birthdate": "2000-01-01",
            "addresses": [
                {
                    "address_line1": "123 Main St",
                    "city": "Anytown",
                    "state": "Anystate",
                    "country": "India",
                    "postal_code": "123456"
                },
                {
                    "address_line1": "456 Side St",
                    "city": "Othertown",
                    "state": "Otherstate",
                    "country": "India",
                    "postal_code": "654321"
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('addresses', response.data, "Address data should be part of the response.")
        self.assertEqual(len(response.data['addresses']), 2)
        self.assertEqual(response.data['addresses'][0]['city'], 'Anytown')
        self.assertEqual(response.data['addresses'][1]['city'], 'Othertown')

    def test_logout_missing_refresh_token(self):
        # Authenticate with access token first
        login_response = self.client.post(reverse('user-login'), {
            'login': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + login_response.data['access'])

        # Missing refresh token in payload
        response = self.client.post(reverse('user-logout'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('error'), 'Refresh token is required')

        self.client.credentials()

    def test_logout_malformed_refresh_token(self):
        # Authenticate with access token first
        login_response = self.client.post(reverse('user-login'), {
            'login': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + login_response.data['access'])

        # Provide malformed token
        response = self.client.post(reverse('user-logout'), {'refresh': 'not-a-valid-jwt'}, format='json')
        # Could be 400 (Invalid token format) or 401 depending on underlying validation
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

        self.client.credentials()

    def test_logout_using_access_token_in_refresh_field(self):
        login_response = self.client.post(reverse('user-login'), {
            'login': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token)

        # Try to blacklist access token accidentally passed in refresh field
        response = self.client.post(reverse('user-logout'), {'refresh': access_token}, format='json')
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

        self.client.credentials()

    def test_logout_unauthorized_without_auth_header(self):
        # No Authorization header
        response = self.client.post(reverse('user-logout'), {'refresh': 'dummy'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)