"""Filtros avanzados para el catálogo de TecnoMarket Perú."""
import django_filters

from .models import Producto


class ProductoFilter(django_filters.FilterSet):
    """Soporta ?categoria=laptops, ?marca=dell, ?precio_min=500&precio_max=2000, ?disponible=true."""

    categoria = django_filters.CharFilter(field_name="categoria__slug", lookup_expr="iexact")
    marca = django_filters.CharFilter(field_name="marca", lookup_expr="iexact")
    precio_min = django_filters.NumberFilter(field_name="precio", lookup_expr="gte")
    precio_max = django_filters.NumberFilter(field_name="precio", lookup_expr="lte")
    disponible = django_filters.BooleanFilter(method="filter_disponible")

    class Meta:
        model = Producto
        fields = ["categoria", "marca", "precio_min", "precio_max", "disponible"]

    def filter_disponible(self, queryset, name, value):
        if value is True:
            return queryset.filter(stock__gt=0)
        if value is False:
            return queryset.filter(stock=0)
        return queryset
