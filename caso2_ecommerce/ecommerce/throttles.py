"""Throttling especializado para checkout y búsquedas en TecnoMarket Perú."""
from rest_framework.throttling import SimpleRateThrottle


class CheckoutRateThrottle(SimpleRateThrottle):
    """Previene abuso de checkout (10 requests/hour)."""

    scope = "checkout"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"checkout-user-{request.user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class SearchRateThrottle(SimpleRateThrottle):
    """Previene scraping de catálogo/precios en búsquedas (100 requests/hour)."""

    scope = "search"

    def get_cache_key(self, request, view):
        if not request.query_params.get("search"):
            return None
        if request.user and request.user.is_authenticated:
            ident = f"search-user-{request.user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
