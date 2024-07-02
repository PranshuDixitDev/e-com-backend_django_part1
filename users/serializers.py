from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.validators import RegexValidator, validate_email
from rest_framework.validators import UniqueValidator
from rest_framework.permissions import IsAuthenticated

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[validate_email, UniqueValidator(queryset=User.objects.all())])
    phone_number = serializers.CharField(validators=[RegexValidator(regex=r'^\+91\d{10}$'), UniqueValidator(queryset=User.objects.all())])
        # Additional address fields with appropriate settings to allow them to be optional
    address2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address3 = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['username','first_name', 'last_name',
                   'email', 'password', 'phone_number',
                    'address', 'address2', 'address3',
                    'postal_code', 'birthdate']
        read_only_fields = ['email', 'phone_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'address': {'required': True},
            'postal_code': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'birthdate': {'required': True},

        }

    def create(self, validated_data):
         # Use the built-in create_user method to handle user creation securely, ensuring that passwords are hashed.
        user = User.objects.create_user(**validated_data)
        return user
        # user = User(**validated_data)
        # user.set_password(validated_data['password'])
        # user.save()
        # return user
