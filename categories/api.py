from rest_framework import generics, permissions
from .models import Category
from .serializers import CategorySerializer
from users.permissions import IsSuperUser

class CategoryList(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # Define default permissions statically
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

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
