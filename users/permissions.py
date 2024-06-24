from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)

class IsSuperUser(permissions.BasePermission):
    """
    Custom permission to only allow superusers to create, update, delete.
    """
    message = 'Only superusers are allowed to perform this action.'

    def has_permission(self, request, view):
        has_perm = request.user and request.user.is_superuser
        if not has_perm:
            ip_addr = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR', 'Unknown IP')
            logger.warn(f"Unauthorized access attempt by {request.user} from IP {ip_addr}.")
        return has_perm
