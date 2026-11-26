"""Paginación personalizada para productos y órdenes en TecnoMarket Perú."""
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class ProductoPageNumberPagination(PageNumberPagination):
    """24 productos por página."""

    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class OrdenLimitOffsetPagination(LimitOffsetPagination):
    """LimitOffsetPagination (50 órdenes por página)."""

    default_limit = 50
    max_limit = 200
