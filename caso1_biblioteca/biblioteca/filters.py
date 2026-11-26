"""Filtros avanzados y ordenamiento compatible con parámetros en español."""
import django_filters
from rest_framework.filters import OrderingFilter

from .models import Libro


class LibroFilter(django_filters.FilterSet):
    """Soporta ?categoria=ingenieria, ?año__gte=2020, ?anio__gte=2020 y ?disponible=true."""

    categoria = django_filters.CharFilter(field_name="categoria", lookup_expr="iexact")
    anio__gte = django_filters.NumberFilter(field_name="anio", lookup_expr="gte")
    anio__lte = django_filters.NumberFilter(field_name="anio", lookup_expr="lte")
    disponible = django_filters.BooleanFilter(method="filter_disponible")

    class Meta:
        model = Libro
        fields = ["categoria", "anio", "editorial"]

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        # Mapear parámetro con ñ (?año__gte=2020) al campo anio del modelo
        if data is not None and "año__gte" in data and "anio__gte" not in data:
            mutable = data.copy()
            mutable["anio__gte"] = mutable.get("año__gte")
            data = mutable
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)

    def filter_disponible(self, queryset, name, value):
        if value is True:
            return queryset.filter(stock__gt=0)
        if value is False:
            return queryset.filter(stock=0)
        return queryset


class SpanishLibroOrderingFilter(OrderingFilter):
    """Mapea ?ordering=-año o ?ordering=título a los campos reales del modelo."""

    ALIAS_MAP = {
        "año": "anio",
        "-año": "-anio",
        "título": "titulo",
        "-título": "-titulo",
    }

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [self.ALIAS_MAP.get(p.strip(), p.strip()) for p in params.split(",")]
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering
        return self.get_default_ordering(view)
