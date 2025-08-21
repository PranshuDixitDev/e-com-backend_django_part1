from django.urls import path
from .api import CategoryList, CategoryDetail, OrderedCategoryList, available_display_orders

urlpatterns = [
    path('', CategoryList.as_view(), name='category-list'),
    path('ordered/', OrderedCategoryList.as_view(), name='ordered-category-list'),
    path('available-orders/', available_display_orders, name='available-display-orders'),
    path('<str:id>/', CategoryDetail.as_view(), name='category-detail'),
]