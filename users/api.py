import logging
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from users.models import Address
from .serializers import UserSerializer, AddressSerializer
from .utils import send_verification_email
from .email_rate_limit import EmailResendAttempt
from django.db import IntegrityError, transaction
from django.utils.timezone import now
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.views import APIView
from django.urls import reverse_lazy
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from rest_framework.response import Response
from .tokens import custom_token_generator
from rest_framework import generics
from .tokens import email_verification_token, custom_token_generator
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from functools import wraps
import requests
from .utils import decode_user_uid

logger = logging.getLogger(__name__)

# Production-ready rate limiting decorator that respects test environment
def production_ratelimit(*args, **kwargs):
    """Rate limiting decorator that bypasses rate limiting during tests."""
    def decorator(func):
        # Bypass rate limiting during tests
        if getattr(settings, 'TESTING', False) or not getattr(settings, 'ENABLE_RATE_LIMIT', True):
            @wraps(func)
            def wrapped(request, *args, **kwargs):
                return func(request, *args, **kwargs)
            return wrapped
        else:
            # Apply production rate limiting
            return ratelimit(*args, **kwargs)(func)
    return decorator


User = get_user_model()


class UserRegisterAPIView(views.APIView):
    permission_classes = [AllowAny]  # Allow unregistered users to access this view

    @method_decorator(production_ratelimit(key='ip', rate='3/m', method='POST'))
    def post(self, request):
        with transaction.atomic():
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    user = serializer.save()
                    # make inactive + (if present) unverified
                    fields = []
                    if getattr(user, "is_active", None) is not False:
                        user.is_active = False
                        fields.append("is_active")
                    if hasattr(user, "is_email_verified"):
                        user.is_email_verified = False
                        fields.append("is_email_verified")
                    if fields:
                        user.save(update_fields=fields)
                    
                    # Attempt to send verification email
                    email_sent_successfully = send_verification_email(user)
                    
                    if not email_sent_successfully:
                        # If email delivery fails, delete the user and return error
                        user.delete()
                        logger.error(f"Registration failed for {user.email} due to email delivery failure")
                        return Response({
                            "error": "Email delivery failed. Please verify your email address is correct and try again.",
                            "email_delivery_failed": True
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Return success response with user data
                    response_data = serializer.data.copy()
                    response_data.update({
                        "message": "Registration successful. Please check your email for verification instructions.",
                        "email_sent": True,
                        "verification_required": True
                    })
                    return Response(response_data, status=status.HTTP_201_CREATED)
                    
                except IntegrityError as e:
                    # Enhanced error handling for a better user experience
                    if 'phone_number' in str(e):
                        return Response({
                            "error": "Registration failed. Phone number already exists.",
                            "field_error": "phone_number"
                        }, status=status.HTTP_409_CONFLICT)
                    elif 'email' in str(e):
                        return Response({
                            "error": "Registration failed. Email address already exists.",
                            "field_error": "email"
                        }, status=status.HTTP_409_CONFLICT)
                    elif 'username' in str(e):
                        return Response({
                            "error": "Registration failed. Username already exists.",
                            "field_error": "username"
                        }, status=status.HTTP_409_CONFLICT)
                    return Response({
                        "error": "Registration failed due to duplicate information.",
                        "details": str(e)
                    }, status=status.HTTP_409_CONFLICT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class UserLoginAPIView(views.APIView):
    permission_classes = [AllowAny]  # Allow unregistered users to access this view

    @method_decorator(production_ratelimit(key='ip', rate='5/m', method='POST'))
    def post(self, request):
        login = request.data.get('login')
        password = request.data.get('password')
        
        # Input validation
        if not login or not password:
            return Response({
                "error": "Both login and password are required",
                "isUserEmailVerified": False
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(Q(username=login) | Q(phone_number=login) | Q(email=login)).first()
        if not user or not user.check_password(password):
            # Log failed attempt with IP and timestamp
            logging.warning(f"Failed login attempt for user {login} from IP {request.META.get('REMOTE_ADDR', 'unknown')} at {now()}")
            return Response({
                "error": "Invalid credentials",
                "isUserEmailVerified": False
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if user account is active
        if not user.is_active:
            return Response({
                "error": "User account is inactive. Please contact support.",
                "isUserEmailVerified": getattr(user, 'is_email_verified', False)
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check email verification status
        is_email_verified = getattr(user, 'is_email_verified', False)
        if not is_email_verified:
            # Check if email delivery failed during registration
            if getattr(user, 'email_failed', False):
                return Response({
                    "error": f"Please verify your email at {user.email} before logging in.",
                    "isUserEmailVerified": False,
                    "stored_email_address": user.email,
                    "action_required": "resend_verification_email"
                }, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({
                    "error": f"Please verify your email at {user.email} before logging in.",
                    "isUserEmailVerified": False,
                    "stored_email_address": user.email,
                    "action_required": "check_email_for_verification"
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Update last_login on successful login
        user.last_login = now()
        user.save(update_fields=['last_login'])
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'isUserEmailVerified': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }, status=status.HTTP_200_OK)


class LogoutAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            
            if not refresh_token:
                return Response(
                    {
                        "error": "Refresh token is required",
                        "detail": "Please provide a valid refresh token to logout."
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Attempt to blacklist the given token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {
                    "success": "Logged out successfully",
                    "detail": "Your session has been terminated and tokens have been invalidated."
                }, 
                status=status.HTTP_205_RESET_CONTENT
            )
            
        except TokenError as e:
            return Response(
                {
                    "error": "Token is invalid or already blacklisted",
                    "detail": "The provided refresh token is either malformed, expired, or already blacklisted."
                }, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except InvalidToken as e:
            return Response(
                {
                    "error": "Invalid token format",
                    "detail": "The provided token is not in the correct format."
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "error": "Logout failed",
                    "detail": f"An unexpected error occurred during logout: {str(e)}"
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileAPIView(views.APIView):
    permission_classes = [IsAuthenticated]  # Ensures that the user must be logged in to access or modify their profile

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            # Prevent updating email and phone number
            serializer.validated_data.pop('email', None)
            serializer.validated_data.pop('phone_number', None)
            user = serializer.save()

            # Handle address updates
            addresses_data = request.data.get('addresses', [])
            existing_addresses = {addr.id: addr for addr in user.addresses.all()}

            for address_data in addresses_data:
                address_id = address_data.get('id')
                if address_id and address_id in existing_addresses:
                    # Update existing address
                    address = existing_addresses.pop(address_id)
                    for attr, value in address_data.items():
                        setattr(address, attr, value)
                    address.save()
                else:
                    # Create new address
                    Address.objects.create(user=user, **address_data)

            # No need to delete any addresses as we're not handling explicit deletions here

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CustomPasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(production_ratelimit(key='ip', rate='2/m', method='POST'))
    def post(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist) as e:
            return Response({"error": "Invalid link: " + str(e)}, status=400)
        
        # Check if user is active and email is verified
        if not user.is_active:
            return Response({"error": "User account is inactive"}, status=400)
        
        if not user.is_email_verified:
            return Response({"error": "Email must be verified before password reset"}, status=400)

        if user is not None and custom_token_generator.check_token(user, token):
            form = SetPasswordForm(user, request.data)
            if form.is_valid():
                form.save()
                return Response({"message": "Password has been reset successfully"}, status=200)
            return Response({"errors": form.errors}, status=400)

        return Response({"error": "Invalid token or user"}, status=400)
    

class AddressListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if self.request.user.is_staff and user_id:
            return Address.objects.filter(user_id=user_id)
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user_id = self.request.data.get('user_id')
        if self.request.user.is_staff and user_id:
            serializer.save(user_id=user_id)
        else:
            serializer.save(user=self.request.user)

class AddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if self.request.user.is_staff and user_id:
            return Address.objects.filter(user_id=user_id)
        return Address.objects.filter(user=self.request.user)

    def get_object(self):
        queryset = self.get_queryset()
        filter_kwargs = {'pk': self.kwargs['pk']}
        obj = generics.get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

class ResendVerificationEmailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(production_ratelimit(key='ip', rate='2/m', method='POST'))
    def post(self, request):
        """Resend verification email to authenticated user with enhanced security."""
        # Get authenticated user - no email parameter needed
        user = request.user
        email = user.email
        
        # Identity verification - ensure user is requesting verification for their own email
        if not email:
            return Response({
                'error': 'User account does not have an email address configured',
                'action_required': 'contact_support'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user account is active
        if not user.is_active:
            return Response({
                'error': 'User account is inactive. Please contact support.',
                'stored_email_address': email,
                'action_required': 'contact_support'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check rate limiting (5 attempts per day per email)
        can_resend, attempts_today, remaining_attempts = EmailResendAttempt.can_resend_email(email)
        
        if not can_resend:
            # Rate limit exceeded - provide support contact information
            support_phone = getattr(settings, 'SUPPORT_PHONE_NUMBER', '+91-8758503609')
            return Response({
                'error': f'Daily email resend limit exceeded ({attempts_today}/5 attempts used today). Please call support at {support_phone}',
                'rate_limit_exceeded': True,
                'attempts_today': attempts_today,
                'support_phone': support_phone,
                'reset_time': 'Limit resets at midnight UTC',
                'stored_email_address': email
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Check if user is already verified
        if user.is_email_verified:
            # Record attempt but don't send email
            EmailResendAttempt.record_attempt(
                email=email,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                success=False
            )
            return Response({
                'error': 'Email is already verified',
                'stored_email_address': email,
                'remaining_attempts': remaining_attempts - 1
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle edge case: Check if email delivery failed during registration
        if getattr(user, 'email_failed', False):
            # Reset email status flags before resending
            user.email_sent = False
            user.email_failed = False
            user.save(update_fields=['email_sent', 'email_failed'])
            
            # Send verification email
            email_sent_successfully = send_verification_email(user)
            
            # Record the attempt
            EmailResendAttempt.record_attempt(
                email=email,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                success=email_sent_successfully
            )
            
            if email_sent_successfully:
                return Response({
                    'message': f'Please verify your email at {email} before logging in.',
                    'stored_email_address': email,
                    'email_sent': True,
                    'verification_required': True,
                    'remaining_attempts': remaining_attempts - 1
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to send verification email. Please try again later or contact support.',
                    'stored_email_address': email,
                    'email_sent': False,
                    'action_required': 'contact_support',
                    'remaining_attempts': remaining_attempts - 1
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Reset email status flags before resending
        user.email_sent = False
        user.email_failed = False
        user.save(update_fields=['email_sent', 'email_failed'])
        
        # Send verification email
        email_sent_successfully = send_verification_email(user)
        
        # Record the attempt
        EmailResendAttempt.record_attempt(
            email=email,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            success=email_sent_successfully
        )
        
        if email_sent_successfully:
            logger.info(f"Verification email resent successfully to {user.email}")
            return Response({
                'message': f'Please verify your email at {email} before logging in.',
                'stored_email_address': email,
                'email_sent': True,
                'verification_required': True,
                'remaining_attempts': remaining_attempts - 1
            }, status=status.HTTP_200_OK)
        else:
            logger.error(f"Failed to resend verification email to {user.email}")
            return Response({
                'error': 'Failed to send verification email. Please try again later or contact support.',
                'stored_email_address': email,
                'email_sent': False,
                'action_required': 'contact_support',
                'remaining_attempts': remaining_attempts - 1
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyEmail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            # Decode user ID using the new decode function
            try:
                user_id = decode_user_uid(uidb64)
            except ValueError:
                # Fallback to old method for backward compatibility
                user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and email_verification_token.check_token(user, token):
            updates = []
            if not user.is_active:
                user.is_active = True
                updates.append("is_active")
            if hasattr(user, "is_email_verified") and not user.is_email_verified:
                user.is_email_verified = True
                updates.append("is_email_verified")
            if updates:
                user.save(update_fields=updates)
                # Send admin notification after successful email verification
                self._send_admin_notification(user)
            return Response({'message': 'Email verified successfully!'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid token or user ID'}, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_admin_notification(self, user):
        """Send notification to admin panel about successful email verification."""
        try:
            # Prepare notification data
            notification_data = {
                'event_type': 'email_verification',
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or 'N/A',
                'verification_timestamp': user.date_joined.isoformat() if user.date_joined else None,
                'message': f'User {user.username} ({user.email}) has successfully verified their email address.'
            }
            
            # Log the notification locally
            logger.info(f"Email verification notification: User {user.username} ({user.email}) verified their email")
            
            # If there's an admin notification endpoint configured, send POST request
            admin_notification_url = getattr(settings, 'ADMIN_NOTIFICATION_URL', None)
            if admin_notification_url:
                # Prepare secure headers with internal service token
                headers = {
                    'Content-Type': 'application/json',
                    'X-INTERNAL-TOKEN': getattr(settings, 'INTERNAL_SERVICE_TOKEN', '')
                }
                
                response = requests.post(
                    admin_notification_url,
                    json=notification_data,
                    timeout=5,
                    headers=headers
                )
                if response.status_code == 200:
                    logger.info(f"Admin notification sent successfully for user {user.username}")
                else:
                    logger.warning(f"Admin notification failed with status {response.status_code} for user {user.username}")
            
        except Exception as e:
            # Don't fail email verification if admin notification fails
            logger.error(f"Failed to send admin notification for user {user.username}: {str(e)}")