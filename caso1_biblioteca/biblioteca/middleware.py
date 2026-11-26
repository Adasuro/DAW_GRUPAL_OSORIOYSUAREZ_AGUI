"""Middleware para registrar eventos de throttling (HTTP 429) en logs de auditoría."""
import logging

logger = logging.getLogger("biblioteca.security")


class ThrottlingAuditMiddleware:
    """Registra advertencias cuando un cliente alcanza el límite de rate limiting."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 429:
            user_info = (
                request.user.username
                if getattr(request, "user", None) and request.user.is_authenticated
                else "anonimo"
            )
            ip = request.META.get("REMOTE_ADDR", "unknown")
            logger.warning(
                "THROTTLE_429 | ip=%s | user=%s | method=%s | path=%s",
                ip,
                user_info,
                request.method,
                request.path,
            )
        return response
