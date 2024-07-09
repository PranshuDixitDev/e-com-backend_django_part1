# users/urls.py
from django.urls import path, include
from .api import UserRegisterAPIView, UserLoginAPIView, LogoutAPIView, UserProfileAPIView, CustomPasswordResetConfirmView

urlpatterns = [
    path('register/', UserRegisterAPIView.as_view(), name='user-register'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('logout/', LogoutAPIView.as_view(), name='user-logout'),
    path('user-profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('auth/', include('django.contrib.auth.urls')),
    path('password_reset/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
