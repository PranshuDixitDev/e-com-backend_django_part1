# /Users/pranshudixit/code_base/e-com-backend_django_part1/search/urls.py

from django.urls import path
from .api import UnifiedSearchAPIView

urlpatterns = [
    path('search/', UnifiedSearchAPIView.as_view(), name='unified_search'),
]
