from django.urls import path
from .api import CategoryList, CategoryDetail

urlpatterns = [
    path('', CategoryList.as_view(), name='category-list'),
    path('<str:id>/', CategoryDetail.as_view(), name='category-detail'),
]