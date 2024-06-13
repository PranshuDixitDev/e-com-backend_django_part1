from django.contrib.auth import get_user_model, authenticate
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer
from django.db import IntegrityError
from django.utils.timezone import now

User = get_user_model()

class UserRegisterAPIView(views.APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response({"id": user.id, "username": user.username}, status=status.HTTP_201_CREATED)
            except IntegrityError as e:
                # Here, parse the error message to provide a more user-friendly response
                if 'phone_number' in str(e):
                    return Response({"error": "A user with this phone number already exists."}, status=status.HTTP_409_CONFLICT)
                return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginAPIView(views.APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
             # Update last_login on successful login
            user.last_login = now()
            user.save(update_fields=['last_login'])
             # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)
