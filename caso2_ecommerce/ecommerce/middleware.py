"""Middleware de auditoría para registrar respuestas 429 (throttling) y eventos."""
import logging

logger = logging.getLogger("ecommerce.security")


class ThrottlingAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 429:
            user_info = (
                request.user.username
                if getattr(request, "user", None) and request.user.is_authenticated
                else "invitado"
            )
            logger.warning(
                "THROTTLE_429 | ip=%s | user=%s | method=%s | path=%s",
                request.META.get("REMOTE_ADDR", "unknown"),
                user_info,
                request.method,
                request.path,
            )
        return response
