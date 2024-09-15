from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import ProductViewSet, BulkUploadProductsView, BestSellerList

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    path('best-sellers/', BestSellerList.as_view(), name='best-sellers-list'),
    # path('bulk-upload/', BulkUploadProductsView.as_view(), name='bulk-upload-products'),
]
