import difflib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from products.models import Product
from categories.models import Category
from products.serializers import ProductSerializer
from categories.serializers import CategorySerializer

class UnifiedSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({"error": "Search query not provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Search in Products
        products = Product.objects.filter(name__icontains=query).distinct()
        product_data = ProductSerializer(products, many=True).data

        # Search in Categories
        categories = Category.objects.filter(name__icontains=query).distinct()
        category_data = CategorySerializer(categories, many=True).data

        # Fuzzy Matching if no direct results
        if not products and not categories:
            all_product_names = list(Product.objects.values_list('name', flat=True))
            all_category_names = list(Category.objects.values_list('name', flat=True))
            product_suggestions = difflib.get_close_matches(query, all_product_names, n=3, cutoff=0.6)
            category_suggestions = difflib.get_close_matches(query, all_category_names, n=3, cutoff=0.6)

            if product_suggestions or category_suggestions:
                return Response({
                    "detail": "No exact match found, did you mean:",
                    "product_suggestions": product_suggestions,
                    "category_suggestions": category_suggestions
                }, status=status.HTTP_200_OK)

            return Response({"detail": "No matches found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "products": product_data,
            "categories": category_data
        }, status=status.HTTP_200_OK)
