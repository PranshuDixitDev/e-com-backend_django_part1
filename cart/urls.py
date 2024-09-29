# cart/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import CartViewSet

router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')

urlpatterns = [
    path('', include(router.urls)),
]
