from django_ratelimit.decorators import ratelimit
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer
from django.db import IntegrityError, transaction
from django.utils.timezone import now
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated


User = get_user_model()

class UserRegisterAPIView(views.APIView):
    permission_classes = [AllowAny]  # Allow unregistered users to access this view

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'))
    def post(self, request):
        with transaction.atomic():
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    user = serializer.save()
                    return Response({"id": user.id, "username": user.username}, status=status.HTTP_201_CREATED)
                except IntegrityError as e:
                    # Enhanced error handling for a better user experience
                    if 'phone_number' in str(e):
                        return Response({"error": "Registration failed, possibly due to duplicate information."}, status=status.HTTP_409_CONFLICT)
                    return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginAPIView(views.APIView):
    permission_classes = [AllowAny]  # Allow unregistered users to access this view

    @method_decorator(ratelimit(key='ip', rate='10/m'))
    def post(self, request):
        login = request.data.get('login')
        password = request.data.get('password')
        user = User.objects.filter(Q(username=login) | Q(phone_number=login)).first()
        if user and user.check_password(password):
             # Update last_login on successful login
            user.last_login = now()
            user.save(update_fields=['last_login'])
             # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            # Attempt to blacklist the given token
            token.blacklist()
            # Optionally, invalidate all tokens for this user by updating a user-specific field (not shown here)
            return Response({"success": "Logged out successfully"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
