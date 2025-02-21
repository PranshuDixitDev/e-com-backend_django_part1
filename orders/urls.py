from django.urls import path
from .api import OrderViewSet

order_list = OrderViewSet.as_view({
    'post': 'checkout',
    'get': 'history'
})
order_detail = OrderViewSet.as_view({
    'get': 'detail'
})
order_cancel = OrderViewSet.as_view({
    'post': 'cancel'
})

urlpatterns = [
    path('checkout/', order_list, name='checkout'),
    path('history/', order_list, name='order_history'),
    path('detail/<str:order_number>/', order_detail, name='order_detail'),
    path('cancel/<str:order_number>/', order_cancel, name='cancel_order'),
]