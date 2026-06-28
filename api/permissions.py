from rest_framework import permissions
from accounts.models import UserRole

class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.ADMIN)

class IsManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [UserRole.ADMIN, UserRole.MANAGER]
        )

class IsViewerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER]
        )

class IsAdminRoleOrManagerReadOnly(permissions.BasePermission):
    """
    Admin has full access.
    Manager has read-only (SAFE_METHODS) access.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role == UserRole.ADMIN:
            return True
        if request.method in permissions.SAFE_METHODS and request.user.role == UserRole.MANAGER:
            return True
        return False
