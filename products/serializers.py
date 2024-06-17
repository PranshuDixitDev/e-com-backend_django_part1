from rest_framework import serializers
from .models import Product, PriceWeightCombo

class PriceWeightComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceWeightCombo
        fields = ['combo_description']

class ProductSerializer(serializers.ModelSerializer):
    price_weight_combos = PriceWeightComboSerializer(many=True)

    class Meta:
        model = Product
        fields = ['name', 'category', 'inventory', 'tags', 'price_weight_combos']
        depth = 1

    def create(self, validated_data):
        price_weight_combos_data = validated_data.pop('price_weight_combos')
        product = Product.objects.create(**validated_data)
        for combo_data in price_weight_combos_data:
            PriceWeightCombo.objects.create(product=product, **combo_data)
        return product
