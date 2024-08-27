# products/serializers.py
from rest_framework import serializers
from .models import Product, PriceWeight, Category, ProductImage
from taggit.serializers import (TagListSerializerField, TaggitSerializer)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class PriceWeightComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceWeight
        fields = ['price', 'weight']

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['image_url', 'description']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

class ProductSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    price_weights = PriceWeightComboSerializer(many=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'inventory', 'tags', 'price_weights', 'images']
        depth = 1

    def create(self, validated_data):
        price_weight_combos_data = validated_data.pop('price_weights')
        category = validated_data.pop('category')

        try:
            # Create the product
            product = Product.objects.create(category=category, **validated_data)
            print(f"Created product: {product}")  # Debug log

            # Create price-weight combinations
            for combo_data in price_weight_combos_data:
                PriceWeight.objects.create(product=product, **combo_data)
            return product

        except Exception as e:
            # Log the error and raise a validation error
            print(f"Error creating product: {str(e)}")
            raise serializers.ValidationError(f"Failed to create product: {str(e)}")

