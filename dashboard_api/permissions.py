from rest_framework.permissions import BasePermission


class IsDashboardAdmin(BasePermission):
    message = 'Only staff users can access the dashboard.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)

