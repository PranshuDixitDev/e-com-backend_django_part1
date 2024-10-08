from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import ProductViewSet, BulkUploadProductsView

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    # path('bulk-upload/', BulkUploadProductsView.as_view(), name='bulk-upload-products'),
]
