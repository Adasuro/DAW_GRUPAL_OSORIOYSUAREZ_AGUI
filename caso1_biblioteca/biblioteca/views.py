"""ViewSets RESTful para la Biblioteca Central UNCP."""
from datetime import date

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import LibroFilter, SpanishLibroOrderingFilter
from .models import Autor, Libro, Prestamo, Usuario
from .pagination import LibroPageNumberPagination, PrestamoLimitOffsetPagination
from .permissions import (
    EsAdminOBibliotecario,
    EsAdminParaEliminarOBibliotecarioEditar,
    EsPropietarioPrestamoOStaff,
    EsPropietarioUsuarioOAdmin,
    PuedeCrearPrestamo,
)
from .serializers import (
    AutorSerializer,
    LibroSerializer,
    PrestamoSerializer,
    UsuarioPrivadoSerializer,
    UsuarioPublicoSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="Listar autores", tags=["Autores"]),
    retrieve=extend_schema(summary="Detalle de autor", tags=["Autores"]),
    create=extend_schema(summary="Registrar autor", tags=["Autores"]),
)
class AutorViewSet(viewsets.ModelViewSet):
    """Gestión de autores del catálogo bibliográfico."""

    queryset = Autor.objects.all()
    serializer_class = AutorSerializer
    permission_classes = [EsAdminParaEliminarOBibliotecarioEditar]
    search_fields = ["nombre", "nacionalidad"]


@extend_schema_view(
    list=extend_schema(
        summary="Listar catálogo de libros",
        description="Retorna el catálogo paginado (20 libros/página) con filtros, búsqueda y ordenamiento.",
        tags=["Libros"],
        examples=[
            OpenApiExample(
                "Ejemplo de listado de libros",
                value={
                    "count": 50,
                    "next": "http://127.0.0.1:8000/api/libros/?page=2",
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "url": "http://127.0.0.1:8000/api/libros/1/",
                            "isbn": "978-0262046305",
                            "titulo": "Introduction to Algorithms",
                            "autor": {
                                "id": 1,
                                "nombre": "Thomas H. Cormen",
                                "nacionalidad": "Estadounidense",
                                "biografia": "Profesor de Ciencias de la Computación en Dartmouth.",
                            },
                            "editorial": "MIT Press",
                            "anio": 2022,
                            "categoria": "ingenieria",
                            "stock": 8,
                            "disponible": True,
                            "ubicacion": "Estante A-04 / Piso 2",
                        }
                    ],
                },
                response_only=True,
            )
        ],
    ),
    retrieve=extend_schema(summary="Detalle completo de un libro", tags=["Libros"]),
    create=extend_schema(summary="Crear libro (Admin / Bibliotecario)", tags=["Libros"]),
    update=extend_schema(summary="Actualizar libro completo (Admin / Bibliotecario)", tags=["Libros"]),
    partial_update=extend_schema(summary="Actualizar libro parcial (Admin / Bibliotecario)", tags=["Libros"]),
    destroy=extend_schema(summary="Eliminar libro (Solo Admin)", tags=["Libros"]),
)
class LibroViewSet(viewsets.ModelViewSet):
    """ViewSet completo de Libros con serialización anidada, HATEOAS y filtrado avanzado."""

    queryset = Libro.objects.select_related("autor").all()
    serializer_class = LibroSerializer
    permission_classes = [EsAdminParaEliminarOBibliotecarioEditar]
    pagination_class = LibroPageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, SpanishLibroOrderingFilter]
    filterset_class = LibroFilter
    search_fields = ["titulo", "autor__nombre", "isbn", "editorial"]
    ordering_fields = ["anio", "titulo", "stock", "id"]
    ordering = ["-anio", "titulo"]


@extend_schema_view(
    list=extend_schema(summary="Listar préstamos (propios o todos para staff)", tags=["Préstamos"]),
    retrieve=extend_schema(summary="Detalle de préstamo con multa y días restantes", tags=["Préstamos"]),
    create=extend_schema(
        summary="Registrar nuevo préstamo",
        tags=["Préstamos"],
        examples=[
            OpenApiExample(
                "Solicitud de nuevo préstamo",
                value={"usuario": 3, "libro": 1, "fecha_devolucion": "2026-12-10"},
                request_only=True,
            )
        ],
    ),
)
class PrestamoViewSet(viewsets.ModelViewSet):
    """ViewSet de Préstamos con validaciones de negocio y acciones personalizadas."""

    queryset = Prestamo.objects.select_related("usuario", "libro", "libro__autor").all()
    serializer_class = PrestamoSerializer
    pagination_class = PrestamoLimitOffsetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, SpanishLibroOrderingFilter]
    filterset_fields = ["estado", "usuario", "libro"]
    search_fields = ["libro__titulo", "usuario__nombre", "usuario__username"]
    ordering_fields = ["fecha_prestamo", "fecha_devolucion", "estado"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.es_admin or user.es_bibliotecario:
            return qs
        return qs.filter(usuario=user)

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), PuedeCrearPrestamo()]
        if self.action in ["devolver", "vencidos", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), EsAdminOBibliotecario()]
        if self.action == "retrieve":
            return [IsAuthenticated(), EsPropietarioPrestamoOStaff()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Marcar préstamo como devuelto",
        description="Cambia el estado a 'devuelto', registra la fecha real y repone 1 unidad al stock.",
        tags=["Préstamos"],
        request=None,
    )
    @action(detail=True, methods=["post"], url_path="devolver")
    def devolver(self, request, pk=None):
        prestamo = self.get_object()
        if prestamo.estado == "devuelto":
            return Response(
                {"detail": "El préstamo ya fue marcado como devuelto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prestamo.estado = "devuelto"
        prestamo.fecha_devolucion_real = date.today()
        prestamo.save(update_fields=["estado", "fecha_devolucion_real"])

        libro = prestamo.libro
        libro.stock += 1
        libro.save(update_fields=["stock"])

        serializer = self.get_serializer(prestamo)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Listar préstamos vencidos",
        description="Retorna los préstamos vencidos o cuya fecha de devolución ya expiró.",
        tags=["Préstamos"],
    )
    @action(detail=False, methods=["get"], url_path="vencidos")
    def vencidos(self, request):
        hoy = date.today()
        qs = (
            Prestamo.objects.select_related("usuario", "libro", "libro__autor")
            .filter(Q(estado="vencido") | Q(estado="activo", fecha_devolucion__lt=hoy))
            .order_by("fecha_devolucion")
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="Listar usuarios (Solo Administrador)", tags=["Usuarios"]),
    retrieve=extend_schema(summary="Detalle de usuario (Propio o Administrador)", tags=["Usuarios"]),
)
class UsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestión de usuarios con serialización diferenciada (pública vs privada)."""

    queryset = Usuario.objects.prefetch_related("prestamos__libro").all()

    def get_serializer_class(self):
        user = self.request.user
        if user.is_authenticated and (
            self.action == "perfil"
            or user.es_admin
            or (self.action == "retrieve" and str(user.pk) == str(self.kwargs.get("pk")))
        ):
            return UsuarioPrivadoSerializer
        return UsuarioPublicoSerializer

    def get_permissions(self):
        if self.action == "perfil":
            return [IsAuthenticated()]
        if self.action == "list":
            # Solo admin lista todos los usuarios
            from rest_framework.permissions import IsAdminUser
            return [IsAuthenticated(), IsAdminUser()]
        if self.action == "retrieve":
            return [IsAuthenticated(), EsPropietarioUsuarioOAdmin()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Perfil del usuario autenticado",
        description="Retorna los datos privados y el historial de préstamos del usuario actual.",
        tags=["Usuarios"],
    )
    @action(detail=False, methods=["get"], url_path="perfil")
    def perfil(self, request):
        serializer = UsuarioPrivadoSerializer(request.user, context={"request": request})
        return Response(serializer.data)
