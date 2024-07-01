# users/urls.py
from django.urls import path
from .api import UserRegisterAPIView, UserLoginAPIView, LogoutAPIView

urlpatterns = [
    path('register/', UserRegisterAPIView.as_view(), name='user-register'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('logout/', LogoutAPIView.as_view(), name='user-logout'),
]
