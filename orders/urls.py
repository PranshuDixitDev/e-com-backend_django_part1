from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import OrderViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path('checkout/', OrderViewSet.as_view({'post': 'checkout'}), name='checkout'),
    path('history/', OrderViewSet.as_view({'get': 'history'}), name='order_history'),
    path('orders/<str:order_number>/', OrderViewSet.as_view({'get': 'detail'}), name='order_detail'),
    path('orders/<str:order_number>/cancel/', OrderViewSet.as_view({'post': 'cancel'}), name='cancel_order'),
]