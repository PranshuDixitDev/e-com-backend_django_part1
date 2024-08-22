from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.validators import RegexValidator, validate_email
from rest_framework.validators import UniqueValidator
from .models import Address
from .tokens import email_verification_token
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

User = get_user_model()

class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed address information.
    """
    id = serializers.IntegerField(required=False)  # Include ID field for updates
    address_line1 = serializers.CharField(max_length=255, help_text="Primary address line")
    address_line2 = serializers.CharField(max_length=255, allow_blank=True, required=False, help_text="Secondary address line (optional)")
    city = serializers.CharField(max_length=100, help_text="City")
    state = serializers.CharField(max_length=100, help_text="State")
    country = serializers.CharField(max_length=100, default='India', help_text="Country")
    postal_code = serializers.CharField(max_length=6, help_text="Postal code")

    class Meta:
        model = Address
        fields = ['id', 'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code']

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user information including nested address handling.
    """
    email = serializers.EmailField(validators=[validate_email, UniqueValidator(queryset=User.objects.all())])
    phone_number = serializers.CharField(validators=[RegexValidator(regex=r'^\+91\d{10}$'), UniqueValidator(queryset=User.objects.all())])
    addresses = AddressSerializer(many=True, required=False)  # Handle multiple addresses
    is_email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name',
                   'email', 'password', 'phone_number',
                    'addresses', 'birthdate', 'is_email_verified']
        read_only_fields = ['email', 'phone_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'birthdate': {'required': True},

        }

    def create(self, validated_data):
        addresses_data = validated_data.pop('addresses', [])
        user = User.objects.create_user(**validated_data)
        for address_data in addresses_data:
            Address.objects.create(user=user, **address_data)
        return user

    def update(self, instance, validated_data):
        addresses_data = validated_data.pop('addresses', None)
        instance = super().update(instance, validated_data)
        if addresses_data is not None:
            existing_addresses = {addr.id: addr for addr in instance.addresses.all()}
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
                    Address.objects.create(user=instance, **address_data)
        return instance


    def send_verification_email(self, user):
        token = email_verification_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = reverse('email-verify', kwargs={'uidb64': uid, 'token': token})
        # Construct absolute URL using request
        verification_link = f"http://127.0.0.1:8000{verification_url}"

        # Load HTML content
        html_content = render_to_string('email_verification.html', {'user': user, 'verification_link': verification_link})

        email = EmailMultiAlternatives(
            subject='Email Verification',
            body=f'Please verify your email by clicking on the following link: {verification_link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
