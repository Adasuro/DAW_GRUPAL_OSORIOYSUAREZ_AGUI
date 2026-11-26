"""Permisos personalizados por rol universitario para Biblioteca UNCP."""
from rest_framework import permissions

from .models import Prestamo, Usuario


class EsAdminParaEliminarOBibliotecarioEditar(permissions.BasePermission):
    """
    Lectura pública para catálogo.
    POST/PUT/PATCH permitido para Administrador o Bibliotecario.
    DELETE exclusivo para Administrador.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == "DELETE":
            return request.user.es_admin
        return request.user.es_admin or request.user.es_bibliotecario


class EsAdminOBibliotecario(permissions.BasePermission):
    """Permite acciones operativas solo a Administradores o Bibliotecarios."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.es_admin or request.user.es_bibliotecario)
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Solo el propietario del recurso (o admin) puede modificarlo."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "usuario", obj)
        return owner == request.user or request.user.es_admin


class PuedeCrearPrestamo(permissions.BasePermission):
    """Verifica rol autorizado y que el usuario destino no supere 5 préstamos activos."""

    message = "No autorizado o el usuario superó el límite de 5 préstamos activos."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method != "POST":
            return True
        if not (request.user.es_admin or request.user.es_bibliotecario):
            self.message = "Solo un bibliotecario o administrador puede registrar préstamos."
            return False

        usuario_id = request.data.get("usuario")
        if usuario_id:
            try:
                target = Usuario.objects.get(pk=usuario_id)
                activos = Prestamo.objects.filter(
                    usuario=target,
                    estado__in=["activo", "vencido"],
                ).count()
                if activos >= 5:
                    self.message = (
                        f"El usuario '{target.nombre}' alcanzó el límite máximo de 5 préstamos activos."
                    )
                    return False
            except Usuario.DoesNotExist:
                pass
        return True


class EsPropietarioPrestamoOStaff(permissions.BasePermission):
    """Permite consultar un préstamo a su propietario, bibliotecario o administrador."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            obj.usuario == request.user
            or request.user.es_admin
            or request.user.es_bibliotecario
        )


class EsPropietarioUsuarioOAdmin(permissions.BasePermission):
    """Permite detalle de usuario solo al propio usuario o al administrador."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj == request.user or request.user.es_admin
