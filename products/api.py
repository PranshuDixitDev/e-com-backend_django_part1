# products/api.py
# import difflib
import logging
from rest_framework import viewsets
from .models import Product, BestSeller, ProductImage
from .serializers import ProductSerializer, ProductImageSerializer, PriceWeightComboSerializer
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework import permissions
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from .utils import bulk_upload_products
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.db import transaction
from rest_framework.decorators import action
import time
# from django.contrib.postgres.search import SearchVector
from rest_framework.pagination import PageNumberPagination
from categories.models import Category
from .models import PriceWeight


logger = logging.getLogger(__name__)
class ProductPagination(PageNumberPagination):
    page_size = 10 


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('tags', 'images')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    pagination_class = ProductPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'get_products_by_category', 'best_sellers']:
            permission_classes = [IsAuthenticatedOrReadOnly]
        elif self.action == 'create':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]  # Adjust for other actions (update, delete)
        return [permission() for permission in permission_classes]
    

    @action(detail=False, methods=['get'], url_path='by-category/(?P<category_id>[^/.]+)', permission_classes=[IsAuthenticatedOrReadOnly])
    def get_products_by_category(self, request, category_id=None):
        try:
            # Get category by ID
            category = Category.objects.get(pk=category_id)
            # Filter products by category
            products = Product.objects.filter(category=category, is_active=True)
            serializer = ProductSerializer(products, many=True)
            page = self.paginate_queryset(products)
            if page is not None:
                serializer = self.get_paginated_response(ProductSerializer(page, many=True).data)
            else:
                serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Category.DoesNotExist:
            logger.error(f"Category ID {category_id} not found.")
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching products for category {category_id}: {e}")
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['get'], url_path='best-sellers', permission_classes=[IsAuthenticatedOrReadOnly])
    def best_sellers(self, request):
        """Retrieve a list of best-seller products."""
        best_sellers = BestSeller.objects.all().select_related('product')
        products = [bs.product for bs in best_sellers]
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='add-image')
    def add_image(self, request, pk=None):
        """
        Add an image to a product.
        Handles primary image logic and image optimization.
        """
        product = self.get_object()
        serializer = ProductImageSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PriceWeightViewSet(viewsets.ModelViewSet):
    queryset = PriceWeight.objects.all()
    serializer_class = PriceWeightComboSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], url_path='adjust-inventory')
    def adjust_inventory(self, request, pk=None):
        new_inventory = request.data.get('new_inventory')
        try:
            new_inventory = int(new_inventory)
            if new_inventory < 0:
                return Response({"error": "Inventory cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # Lock the PriceWeight row for the duration of this transaction
                price_weight = PriceWeight.objects.select_for_update().get(pk=pk)
                price_weight.inventory = new_inventory
                price_weight.save()

                # Update product availability
                price_weight.product.update_availability()

                low_stock_warning = None
                if price_weight.inventory <= 5:
                    low_stock_warning = f"Warning: Low stock for {price_weight.product.name} - {price_weight.weight}. Only {price_weight.inventory} items left."

                response_data = {
                    "status": "Inventory updated",
                    "new_inventory": price_weight.inventory
                }
                if low_stock_warning:
                    response_data['low_stock_warning'] = low_stock_warning

                return Response(response_data, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Inventory must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        except PriceWeight.DoesNotExist:
            return Response({"error": "PriceWeight not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error adjusting inventory: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        except ValueError:
            return Response({"error": "Inventory must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error adjusting inventory: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
