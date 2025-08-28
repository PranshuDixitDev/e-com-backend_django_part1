# products/serializers.py
from rest_framework import serializers
from .models import Product, PriceWeight, Category, ProductImage
from taggit.serializers import (TagListSerializerField, TaggitSerializer)
import os

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class PriceWeightComboSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = PriceWeight
        fields = ['id', 'price', 'weight', 'inventory', 'status']

    def get_status(self, obj):
        return "In stock" if obj.inventory > 0 else "Out of stock"
    

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'description', 'is_primary', 'created_at']
        read_only_fields = ['image_url', 'created_at']
        extra_kwargs = {
            'image': {'write_only': True, 'required': True},
        }

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def validate_image(self, value):
        # Check file size
        if value.size > 2 * 1024 * 1024:  # 2MB limit
            raise serializers.ValidationError("Image file too large ( > 2MB )")
        
        # Check file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(f"Unsupported file extension. Use {', '.join(valid_extensions)}")
        
        return value

    def create(self, validated_data):
        # If this image is set as primary, unset other primary images
        if validated_data.get('is_primary', False):
            ProductImage.objects.filter(
                product=validated_data['product'],
                is_primary=True
            ).update(is_primary=False)
        return super().create(validated_data)

class ProductSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    price_weights = PriceWeightComboSerializer(many=True, required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField()
    slug = serializers.CharField(read_only=True)  # New field added
    status = serializers.SerializerMethodField()


    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'category', 'category_name', 'tags', 'price_weights', 'images', 'is_active', 'status']
        depth = 1

    def get_status(self, obj):
        # Check if any of the price_weight options are in stock
        in_stock = obj.price_weights.filter(inventory__gt=0).exists()
        return "In stock" if in_stock and obj.is_active else "Out of stock"

    def create(self, validated_data):
            price_weights_data = validated_data.pop('price_weights', [])
            category = validated_data.pop('category')

            product = Product.objects.create(category=category, **validated_data)
            print(f"Created product: {product}")  # Debug log
            
            # Create price-weight combinations
            if price_weights_data:
                # Use provided price-weight data
                for combo_data in price_weights_data:
                    PriceWeight.objects.create(product=product, **combo_data)
            else:
                # Create default price-weight combination when none provided
                PriceWeight.objects.create(product=product)
            
            product.update_availability()
            return product

    def update(self, instance, validated_data):
        price_weights_data = validated_data.pop('price_weights', [])
        category = validated_data.get('category')

        # Update product fields
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        if category:
            instance.category = category
        instance.save()

        # Update price_weights
        self.update_price_weights(instance, price_weights_data)
        return instance

    def update_price_weights(self, instance, price_weights_data):
        keep_price_weights = []
        for pw_data in price_weights_data:
            pw_id = pw_data.get('id', None)
            if pw_id:
                # Update existing PriceWeight
                pw_instance = PriceWeight.objects.get(id=pw_id, product=instance)
                pw_instance.price = pw_data.get('price', pw_instance.price)
                pw_instance.weight = pw_data.get('weight', pw_instance.weight)
                pw_instance.inventory = pw_data.get('inventory', pw_instance.inventory)
                pw_instance.save()
                keep_price_weights.append(pw_instance.id)
            else:
                # Create new PriceWeight
                pw_instance = PriceWeight.objects.create(product=instance, **pw_data)
                keep_price_weights.append(pw_instance.id)

        # Delete PriceWeights not included in the request
        instance.price_weights.exclude(id__in=keep_price_weights).delete()
        # Update product availability after modifying price weights
        instance.update_availability()