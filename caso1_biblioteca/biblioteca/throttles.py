"""Throttling personalizado para prevenir scraping y abuso de endpoints."""
from rest_framework.throttling import SimpleRateThrottle


class BurstRateThrottle(SimpleRateThrottle):
    """Limita ráfagas rápidas de peticiones (20 requests/minute)."""

    scope = "burst"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user-{request.user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
