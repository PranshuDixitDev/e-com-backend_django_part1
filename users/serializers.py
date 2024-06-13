from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username','first_name', 'last_name',
         'email', 'password', 'phone_number', 'surname',
           'address', 'postal_code', 'birthdate']
        extra_kwargs = {
            'password': {'write_only': True},
            'phone_number': {'required': True},
            'surname': {'required': True},
            'address': {'required': True},
            'postal_code': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'birthdate': {'required': True},
            
        }

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
