from rest_framework import serializers
from .models import Category
from products.serializers import ProductSerializer

class CategorySerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    slug = serializers.CharField(read_only=True)  # Include slug in output

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'tags', 'image', 'secondary_image', 'secondary_description']

    def get_tags(self, obj):
        # Return a list of tag names
        return list(obj.tags.names())


    def validate_name(self, value):
        if any(char.isdigit() for char in value):
            raise serializers.ValidationError("Name must not contain numbers.")
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
    