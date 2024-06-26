# products/serializers.py
from rest_framework import serializers
from .models import Product, PriceWeight, Category
from taggit.serializers import (TagListSerializerField, TaggitSerializer)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class PriceWeightComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceWeight
        fields = ['price', 'weight']

class ProductSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    price_weights = PriceWeightComboSerializer(many=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = ['name', 'category', 'inventory', 'tags', 'price_weights']
        depth = 1

    def create(self, validated_data):
        price_weight_combos_data = validated_data.pop('price_weights')
        category = validated_data.pop('category')
        product = Product.objects.create(category=category, **validated_data)
        for combo_data in price_weight_combos_data:
            PriceWeight.objects.create(product=product, **combo_data)
        return product
