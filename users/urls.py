# users/urls.py
from django.urls import path
from .api import UserRegisterAPIView, UserLoginAPIView, LogoutAPIView, UserProfileAPIView

urlpatterns = [
    path('register/', UserRegisterAPIView.as_view(), name='user-register'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('logout/', LogoutAPIView.as_view(), name='user-logout'),
    path('user-profile/', UserProfileAPIView.as_view(), name='user-profile'),
]
