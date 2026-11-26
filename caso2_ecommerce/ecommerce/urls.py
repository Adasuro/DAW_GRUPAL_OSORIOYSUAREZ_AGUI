"""Enrutamiento automático de ViewSets para TecnoMarket Perú."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CarritoViewSet,
    CategoriaViewSet,
    OrdenViewSet,
    PerfilUsuarioViewSet,
    ProductoViewSet,
    ResenaViewSet,
    VendedorViewSet,
)

router = DefaultRouter()
router.register(r"productos", ProductoViewSet, basename="producto")
router.register(r"categorias", CategoriaViewSet, basename="categoria")
router.register(r"vendedores", VendedorViewSet, basename="vendedor")
router.register(r"carrito", CarritoViewSet, basename="carrito")
router.register(r"ordenes", OrdenViewSet, basename="orden")
router.register(r"resenas", ResenaViewSet, basename="resena")
router.register(r"reseñas", ResenaViewSet, basename="resena-es")
router.register(r"usuarios", PerfilUsuarioViewSet, basename="usuario")

urlpatterns = [
    path("", include(router.urls)),
    # Alias con tilde para /api/productos/{id}/reseñas/
    path(
        "productos/<int:pk>/reseñas/",
        ProductoViewSet.as_view({"get": "resenas"}),
        name="producto-resenas-es",
    ),
]
