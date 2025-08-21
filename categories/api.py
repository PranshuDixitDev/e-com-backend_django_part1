from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Category
from .serializers import CategorySerializer
from users.permissions import IsSuperUser

class CategoryList(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    # Define default permissions statically
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        """Return categories ordered by display_order first, then name."""
        return Category.objects.all().order_by('display_order', 'name')

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        # Return the appropriate permission classes based on the method
        if self.request.method == 'POST':
            return [IsSuperUser()]
        return super().get_permissions()

class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'id'
    # Define default permissions statically
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        # Return the appropriate permission classes based on the method
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsSuperUser()]
        return super().get_permissions()


class OrderedCategoryList(generics.ListAPIView):
    """Returns only categories with display_order set, ordered by display_order."""
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    
    def get_queryset(self):
        """Return only categories with display_order set, ordered by display_order."""
        return Category.get_ordered_categories()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def available_display_orders(request):
    """Returns available display order numbers (1-8)."""
    available_orders = Category.get_available_display_orders()
    return Response({
        'available_orders': available_orders,
        'total_slots': 8,
        'used_slots': 8 - len(available_orders)
    })
