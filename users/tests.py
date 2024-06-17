from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

class UserAccountTests(APITestCase):
    def test_user_registration(self):
        url = reverse('user-register')
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com',
            'phone_number': '+919876543210',
            'first_name': 'Test',
            'last_name': 'User',
            'address': '123 Test Ave',
            'postal_code': '123456',
            'birthdate': '1990-01-01'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_login(self):
        self.test_user_registration()  # Ensure the user is registered
        url = reverse('user-login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
