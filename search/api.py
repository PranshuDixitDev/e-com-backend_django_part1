import difflib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from products.models import Product
from categories.models import Category
from products.serializers import ProductSerializer
from categories.serializers import CategorySerializer
from django.db.models import Q
from django.utils import timezone
from analytics.models import SearchAnalytics

class UnifiedSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({"error": "Search query not provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Search for products matching name, description, or tags
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(tags__name__icontains=query) | Q(description__icontains=query)
        ).distinct()
        product_data = ProductSerializer(products, many=True).data

        # Search for categories based on the query
        categories = Category.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).distinct()
        category_data = CategorySerializer(categories, many=True).data

        # For each category, calculate the product count based on the query
        for category in category_data:
            product_count = Product.objects.filter(
                Q(name__icontains=query) | Q(tags__name__icontains=query) | Q(description__icontains=query),
                category__id=category['id']
            ).count()
            category['product_count'] = product_count
            category['products'] = []  # Ensure no products are returned inside categories

        # Generate fuzzy suggestions if no exact matches
        all_product_names = list(Product.objects.values_list('name', flat=True))
        all_category_names = list(Category.objects.values_list('name', flat=True))
        product_suggestions = difflib.get_close_matches(query, all_product_names, n=3, cutoff=0.6)
        category_suggestions = difflib.get_close_matches(query, all_category_names, n=3, cutoff=0.6)

        # If there are no exact matches, return only suggestions
        if not products and not categories:
            # Log search analytics for no results
            search_analytics, created = SearchAnalytics.objects.get_or_create(
                query=query,
                date=timezone.now().date(),
                defaults={
                    'user': request.user if request.user.is_authenticated else None,
                    'results_count': 0,
                    'search_count': 1
                }
            )
            if not created:
                search_analytics.search_count += 1
                search_analytics.save()
            
            if product_suggestions or category_suggestions:
                return Response({
                    "message": "No exact match found, did you mean:",
                    "product_suggestions": product_suggestions,
                    "category_suggestions": category_suggestions
                }, status=status.HTTP_200_OK)

            return Response({"message": "No matches found."}, status=status.HTTP_404_NOT_FOUND)

        # Log search analytics
        total_results = len(products) + len(categories)
        search_analytics, created = SearchAnalytics.objects.get_or_create(
            query=query,
            date=timezone.now().date(),
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'results_count': total_results,
                'search_count': 1
            }
        )
        if not created:
            search_analytics.search_count += 1
            search_analytics.save()
        
        # If exact matches exist but you still want to show fuzzy suggestions
        return Response({
            "products": product_data,
            "categories": category_data,
            "product_suggestions": product_suggestions,  # Add product suggestions here
            "category_suggestions": category_suggestions  # Add category suggestions here
        }, status=status.HTTP_200_OK)
