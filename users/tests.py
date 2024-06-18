from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from .models import CustomUser


class UserAccountTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='password123',
            first_name='Test',
            last_name='User',
            phone_number='+919876543210',
            address='Test Address',
            postal_code='123456',
            birthdate='1990-01-01'
        )
        self.client = APIClient()

    def test_user_registration(self):
        url = reverse('user-register')
        data = {
            'username': 'newuser',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+919765432109',
            'address': 'New Address',
            'postal_code': '654321',
            'birthdate': '2000-01-01'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
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
