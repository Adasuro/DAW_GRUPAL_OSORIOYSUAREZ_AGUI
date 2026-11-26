"""Clases de paginación configuradas para la API de Biblioteca."""
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class LibroPageNumberPagination(PageNumberPagination):
    """Paginación por número de página (20 elementos por página)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PrestamoLimitOffsetPagination(LimitOffsetPagination):
    """Paginación Limit/Offset para el historial de préstamos."""

    default_limit = 20
    max_limit = 100
