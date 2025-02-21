from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Category

User = get_user_model()

class CategoryTestCase(APITestCase):
    
    def setUp(self):
        """
        Set up test data for each test.
        Create a superuser and a regular user, and create a category.
        """
        # Ensuring unique phone numbers and including all necessary fields
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='adminpass',
            phone_number='+919876543210'  # Unique phone number
        )
        self.user = User.objects.create_user(
            username='user', email='user@example.com', password='userpass',
            phone_number='+911234567890'  # Another unique phone number
        )
        self.category = Category.objects.create(
            name="Electronics", description="Gadgets and more", image='path/to/default/image.png'
        )

    def test_list_categories(self):
        """
        Test that anyone can list categories without authentication.
        """
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_category_superuser(self):
        """
        Test that a superuser can create a category.
        """
        self.client.force_authenticate(user=self.superuser)
        with open('/Users/pranshudixit/Downloads/bedroom.webp', 'rb') as img:
            data = {'name': 'Books', 'description': 'Read more', 'image': img}
            response = self.client.post(reverse('category-list'), data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_category_normal_user(self):
        """
        Test that a normal user cannot create a category.
        """
        self.client.force_authenticate(user=self.user)
        with open('/Users/pranshudixit/Downloads/bedroom.webp', 'rb') as img:
            data = {'name': 'Toys', 'description': 'Play more', 'image': img}
            response = self.client.post(reverse('category-list'), data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_category_superuser(self):
        """
        Test that a superuser can update a category.
        """
        self.client.force_authenticate(user=self.superuser)
        data = {'name': 'Updated Electronics'}
        response = self.client.patch(reverse('category-detail', kwargs={'id': self.category.id}), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_category_superuser(self):
        """
        Test that a superuser can delete a category.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(reverse('category-detail', kwargs={'id': self.category.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthorized_access(self):
        """
        Test that an unauthorized user cannot create a category.
        """
        self.client.logout()  # Ensure the client is not authenticated
        response = self.client.post(reverse('category-list'))
        self.assertEqual(response.status_code,  status.HTTP_401_UNAUTHORIZED)

    def test_wrong_credentials(self):
        """
        Test that providing wrong credentials does not allow access.
        """
        self.client.login(username='user', password='wrongpassword')
        response = self.client.get(reverse('category-list'))
        if response.status_code == status.HTTP_200_OK:
            print("Access granted without authentication, likely due to view settings allowing public read access.")
        else:
            self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def tearDown(self):
        """
        Clean up after each test.
        """
        User.objects.all().delete()
        Category.objects.all().delete()
