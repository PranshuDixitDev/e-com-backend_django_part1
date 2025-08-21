from rest_framework import serializers
from .models import Category
from products.serializers import ProductSerializer

class CategorySerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    slug = serializers.CharField(read_only=True)  # Include slug in output
    available_display_orders = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'tags', 'image', 'secondary_image', 'secondary_description', 'display_order', 'available_display_orders']

    def get_tags(self, obj):
        # Return a list of tag names
        return list(obj.tags.names())
    
    def get_available_display_orders(self, obj):
        """Return available display order numbers for this category."""
        available = Category.get_available_display_orders()
        # If this category already has a display_order, include it in available options
        if obj.display_order and obj.display_order not in available:
            available.append(obj.display_order)
            available.sort()
        return available


    def validate_name(self, value):
        if any(char.isdigit() for char in value):
            raise serializers.ValidationError("Name must not contain numbers.")
        return value
    
    def validate_display_order(self, value):
        """Validate display_order field."""
        if value is not None:
            # Check range
            if value < 1 or value > 8:
                raise serializers.ValidationError("Display order must be between 1 and 8.")
            
            # Check if already taken by another category (excluding current instance)
            existing_category = Category.objects.filter(display_order=value)
            if self.instance:
                existing_category = existing_category.exclude(pk=self.instance.pk)
            
            if existing_category.exists():
                existing_name = existing_category.first().name
                raise serializers.ValidationError(
                    f"Display order {value} is already assigned to category '{existing_name}'."
                )
        
        return value

   
    def validate_image(self, value):
        """ Ensure image is not empty. """
        if value is None:
            raise serializers.ValidationError("Image is required.")
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
    