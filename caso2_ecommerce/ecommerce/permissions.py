"""Permisos personalizados para TecnoMarket Perú."""
from rest_framework import permissions

from .models import OrdenItem


class PuedeVender(permissions.BasePermission):
    """Permite crear productos a Administradores o Vendedores registrados en el marketplace."""

    message = "Solo vendedores registrados o administradores pueden gestionar productos."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == "DELETE":
            return request.user.es_admin
        return request.user.es_admin or request.user.es_vendedor

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return request.user.es_admin
        return request.user.es_admin or obj.vendedor == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permite lectura a todos y escritura solo al propietario o administrador."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "usuario", obj)
        return owner == request.user or request.user.es_admin


class EsCompradorVerificado(permissions.BasePermission):
    """Valida que el usuario haya comprado el producto antes de reseñarlo."""

    message = "Debes haber comprado el producto para poder dejar una reseña verificada."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method != "POST":
            return True
        producto_id = request.data.get("producto")
        if not producto_id:
            return True
        return OrdenItem.objects.filter(
            orden__usuario=request.user,
            producto_id=producto_id,
        ).exclude(orden__estado="cancelada").exists()


class EsPropietarioOrdenOStaff(permissions.BasePermission):
    """Permite consultar orden al propietario o admin, y actualizar estado a admin o vendedor."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(view, "action", None) == "cancelar":
            return obj.usuario == request.user or request.user.es_admin
        if request.method in permissions.SAFE_METHODS:
            return obj.usuario == request.user or request.user.es_admin or request.user.es_vendedor
        return request.user.es_admin or request.user.es_vendedor
