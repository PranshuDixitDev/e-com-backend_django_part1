# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Address

class AddressInline(admin.StackedInline):
    model = Address
    can_delete = False

class CustomUserAdmin(UserAdmin):
    inlines = (AddressInline,)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Address)
