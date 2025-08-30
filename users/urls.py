# users/urls.py
from django.urls import path, include
from .api import (
    UserRegisterAPIView,
    UserLoginAPIView,
    LogoutAPIView,
    UserProfileAPIView,
    AddressListCreateAPIView,
    AddressDetailAPIView,
    VerifyEmail,
    ResendVerificationEmailAPIView,
)
from .verify_email_encrypted import VerifyEmailEncrypted
from .password_reset_encrypted import PasswordResetConfirmEncrypted
from .password_reset_request import PasswordResetRequestView

urlpatterns = [
    path('register/', UserRegisterAPIView.as_view(), name='user-register'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('logout/', LogoutAPIView.as_view(), name='user-logout'),
    path('user-profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('addresses/', AddressListCreateAPIView.as_view(), name='address-list-create'),
    path('addresses/<int:pk>/', AddressDetailAPIView.as_view(), name='address-detail'),
    # Removed django_rest_passwordreset - using custom implementation only
    path('auth/', include('django.contrib.auth.urls')),
    # Password reset endpoints - standardized to support query parameters
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmEncrypted.as_view(), name='password_reset_confirm'),
    path('password-reset/confirm/<uidb64>/<token>/', PasswordResetConfirmEncrypted.as_view(), name='password_reset_confirm_legacy'),
    
    # Email verification endpoints - standardized format
     path('email-verify/', VerifyEmailEncrypted.as_view(), name='email-verify'),
     path('verify-email/<uidb64>/<token>/', VerifyEmail.as_view(), name='email-verify-legacy'),
     path('resend-verification-email/', ResendVerificationEmailAPIView.as_view(), name='resend-verification-email'),
]
