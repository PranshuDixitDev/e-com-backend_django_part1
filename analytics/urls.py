from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import AnalyticsViewSet, AdminNotificationView

router = DefaultRouter()
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
    path('admin-notification/', AdminNotificationView.as_view(), name='admin-notification'),
]