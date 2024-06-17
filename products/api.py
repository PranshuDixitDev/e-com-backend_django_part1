from rest_framework import permissions, viewsets
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAdminUser]  # Ensures only admin users can access

    def get_queryset(self):
        # Optional: filter based on query params if needed
        return super().get_queryset()
