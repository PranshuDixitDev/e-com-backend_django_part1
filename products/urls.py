from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import ProductViewSet, BulkUploadProductsView, PriceWeightViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'price-weights', PriceWeightViewSet, basename='priceweight')


urlpatterns = [
    path('', include(router.urls)),
    # path('bulk-upload/', BulkUploadProductsView.as_view(), name='bulk-upload-products'),
]
