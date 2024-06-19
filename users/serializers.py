from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.validators import RegexValidator, validate_email
from rest_framework.validators import UniqueValidator

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[validate_email, UniqueValidator(queryset=User.objects.all())])
    phone_number = serializers.CharField(validators=[RegexValidator(regex=r'^\+91\d{10}$'), UniqueValidator(queryset=User.objects.all())])

    class Meta:
        model = User
        fields = ['username','first_name', 'last_name',
                   'email', 'password', 'phone_number',
                     'address', 'postal_code', 'birthdate']
        extra_kwargs = {
            'password': {'write_only': True},
            'phone_number': {'required': True},
            'address': {'required': True},
            'postal_code': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'birthdate': {'required': True},

        }

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user
