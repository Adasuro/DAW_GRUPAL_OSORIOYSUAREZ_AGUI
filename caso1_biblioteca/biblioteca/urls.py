"""Enrutamiento automático de ViewSets para Biblioteca UNCP."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AutorViewSet, LibroViewSet, PrestamoViewSet, UsuarioViewSet

router = DefaultRouter()
router.register(r"libros", LibroViewSet, basename="libro")
router.register(r"autores", AutorViewSet, basename="autor")
router.register(r"prestamos", PrestamoViewSet, basename="prestamo")
router.register(r"usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("", include(router.urls)),
]
