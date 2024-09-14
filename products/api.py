# products/api.py
import difflib
from venv import logger
from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework import permissions, viewsets
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from .utils import bulk_upload_products
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from django.db import transaction
from rest_framework.decorators import action
import time
from django.contrib.postgres.search import SearchVector
import logging
from rest_framework.pagination import PageNumberPagination
from categories.models import Category


class ProductPagination(PageNumberPagination):
    page_size = 10 


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('tags', 'images')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    pagination_class = ProductPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticatedOrReadOnly]
        elif self.action == 'create':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]  # Adjust for other actions (update, delete)
        return [permission() for permission in permission_classes]
    

    

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], url_path='adjust-inventory')
    def adjust_inventory(self, request, pk=None):
        new_inventory = request.data.get('new_inventory')
        try:
            new_inventory = int(new_inventory)
            if new_inventory < 0:
                return Response({"error": "Inventory cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # Lock the product row for the duration of this transaction
                product = Product.objects.select_for_update().get(pk=pk)
                time.sleep(1)  # Simulating a delay to test transaction locking
                product.inventory = new_inventory
                product.save()

                low_stock_warning = None
                if product.inventory <= 5:
                    low_stock_warning = f"Warning: Low stock for {product.name}. Only {product.inventory} items left."

                response_data = {
                    "status": "inventory updated",
                    "new_inventory": product.inventory
                }
                if low_stock_warning:
                    response_data['low_stock_warning'] = low_stock_warning

                return Response(response_data, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Inventory must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error adjusting inventory: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    @action(detail=False, methods=['get'], url_path='by-category/(?P<category_id>[^/.]+)')
    def get_products_by_category(self, request, category_id=None):
        try:
            # Get category by ID
            category = Category.objects.get(pk=category_id)
            # Filter products by category
            products = Product.objects.filter(category=category, is_active=True)
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Category.DoesNotExist:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

class BulkUploadProductsView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        file = request.FILES['file']
        try:
            result = bulk_upload_products(file)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_201_CREATED)
    

# class ProductSearchAPIView(APIView):
#     permission_classes = [IsAuthenticatedOrReadOnly]

#     def get(self, request, *args, **kwargs):
#         logger.debug("Received query: %s", request.GET.get('q', '').strip())

#         try:
#             query = request.GET.get('q', '').strip()  # Get the search query and remove extra spaces

#             if query:
#                 # Perform partial matches on product name, tags, and description
#                 products = Product.objects.filter(
#                     name__icontains=query
#                 ) | Product.objects.filter(
#                     tags__name__icontains=query
#                 ) | Product.objects.filter(
#                     description__icontains=query
#                 )

#                 products = products.distinct('id')  # Ensure no duplicate results

#                 # If exact match or partial match, return those products
#                 if products.exists():
#                     serializer = ProductSerializer(products, many=True)
#                     return Response(serializer.data, status=status.HTTP_200_OK)

#                 # If no exact match, provide fuzzy matching suggestions
#                 product_names = list(Product.objects.values_list('name', flat=True))
#                 closest_matches = difflib.get_close_matches(query, product_names, n=3, cutoff=0.6)

#                 if closest_matches:
#                     # Return 200 OK with fuzzy match suggestions
#                     return Response({
#                         "detail": f"No exact match for '{query}', Did you mean:",
#                         "suggestions": closest_matches
#                     }, status=status.HTTP_200_OK)

#                 # If no products and no suggestions, return 404
#                 return Response({
#                     "detail": f"No Product matches '{query}' and no suggestions available."
#                 }, status=status.HTTP_404_NOT_FOUND)

#             else:
#                 return Response({"error": "Search query not provided."}, status=status.HTTP_400_BAD_REQUEST)

#         except Exception as e:
#             # Log the error for debugging purposes
#             print(f"Error: {e}")
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
