from rest_framework import serializers
from .models import Category
from products.serializers import ProductSerializer

class CategorySerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()  # This line includes associated products

    class Meta:
        model = Category
        fields = ['category_id', 'name', 'description', 'tags', 'image', 'products']  # Include 'products' in fields

    def get_tags(self, obj):
        # Return a list of tag names
        return list(obj.tags.names())

    def get_products(self, obj):
        # You can optimize this query by adjusting your viewset to prefetch related products
        products = obj.products.all().filter(is_active=True)
        return ProductSerializer(products, many=True).data  # Serialize the products

    def validate_name(self, value):
        if any(char.isdigit() for char in value):
            raise serializers.ValidationError("Name must not contain numbers.")
        return value

   
    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])  # Extract tags data if provided
        instance = super().create(validated_data)
        if tags_data:
            instance.tags.set(*tags_data)  # Set tags after the instance is created
        return instance
    
    
    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)
        if tags_data is not None:
            instance.tags.set(*tags_data)
        return super().update(instance, validated_data)
    
    
    def validate_image(self, value):
        """ Ensure image is not empty. """
        if value is None:
            raise serializers.ValidationError("Image is required.")
        return value
    