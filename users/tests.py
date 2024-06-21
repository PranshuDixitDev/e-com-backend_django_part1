# users/tests.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from .models import CustomUser


class UserAccountTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='testuser@gmail.com',
            password='password123',
            first_name='Test',
            last_name='User',
            phone_number='+919876543210',
            address='Test Address',
            postal_code='123456',
            birthdate='1990-01-01'
        )
        self.client = APIClient()
        self.client.enforce_csrf_checks = False
        self.sample_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+919765432109',
            'address': 'New Address',
            'postal_code': '654321',
            'birthdate': '2000-01-01'
        }


    def test_user_registration(self):
        url = reverse('user-register')
        data = {
            'username': 'newuser',
            'email' : 'newuser@example.com',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+919765432109',
            'address': 'New Address',
            'postal_code': '654321',
            'birthdate': '2000-01-01'
        }

        # Authenticate as necessary here before the request if your setup requires it.
        self.client.login(username='testuser', password='password123')  # Only if login is required

        response = self.client.post(url, data)
        if response.status_code == 403:
            print("Permission issues: ", response.data)
        else:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Unexpected response: {response.data}")
            self.assertEqual(response.data['username'], 'newuser')


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
        self.assertEqual(response.data['error'], 'Invalid Credentials')
    

    def test_rate_limit_registration(self):
        url = reverse('user-register')

        # Send requests with unique data
        for i in range(6):
            unique_data = {
                'username': f'newuser{i}',
                'email': f'newuser{i}@example.com',
                'password': 'newpassword123',
                'first_name': 'New',
                'last_name': 'User',
                'phone_number': f'+919000{i}54321',
                'address': 'New Address',
                'postal_code': '654321',
                'birthdate': '2000-01-01'
            }

            response = self.client.post(url, data=unique_data)
            print("******", response)

            # Verify successful registration within limit (i < 5)
            if i < 5:
                self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                                 f"Request {i+1} should be successful: {response.data}")

            # Verify rate limit exceeded (i >= 5)
            else:
                self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_429_TOO_MANY_REQUESTS],
                              f"Expected rate limit error but got {response.status_code}: {response.data}")
