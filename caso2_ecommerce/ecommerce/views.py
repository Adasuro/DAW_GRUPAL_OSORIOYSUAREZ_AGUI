"""ViewSets RESTful para TecnoMarket Perú E-Commerce."""
from django.db import transaction
from django.db.models import Avg
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .filters import ProductoFilter
from .models import (
    Carrito,
    CarritoItem,
    Categoria,
    Cupon,
    Orden,
    OrdenItem,
    Producto,
    Resena,
    Usuario,
)
from .pagination import OrdenLimitOffsetPagination, ProductoPageNumberPagination
from .permissions import (
    EsCompradorVerificado,
    EsPropietarioOrdenOStaff,
    IsOwnerOrReadOnly,
    PuedeVender,
)
from .serializers import (
    CarritoAccionSerializer,
    CarritoSerializer,
    CategoriaSerializer,
    CheckoutSerializer,
    OrdenSerializer,
    ProductoSerializer,
    ResenaSerializer,
    UsuarioPerfilSerializer,
    VendedorResumenSerializer,
)
from .throttles import CheckoutRateThrottle, SearchRateThrottle


class ProductoOrderingFilter(OrderingFilter):
    """Mapea rating_promedio al campo anotado avg_calificacion."""

    ALIAS_MAP = {
        "rating_promedio": "avg_calificacion",
        "-rating_promedio": "-avg_calificacion",
    }

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [self.ALIAS_MAP.get(p.strip(), p.strip()) for p in params.split(",")]
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering
        return self.get_default_ordering(view)


def _crear_orden_desde_carrito(usuario, direccion_envio: str, metodo_pago: str, cupon_codigo: str = ""):
    """Convierte el carrito activo del usuario en una Orden con snapshot inmutable de precios."""
    carrito = Carrito.objects.filter(usuario=usuario, activo=True).prefetch_related("items__producto").first()
    if not carrito or not carrito.items.exists():
        return None, {"detail": "El carrito está vacío. Agrega productos antes de realizar checkout."}

    if cupon_codigo:
        cupon = Cupon.objects.filter(codigo__iexact=cupon_codigo, activo=True).first()
        if cupon:
            carrito.cupon = cupon
            carrito.save(update_fields=["cupon"])

    with transaction.atomic():
        items = list(carrito.items.select_related("producto"))
        for item in items:
            if item.cantidad > item.producto.stock:
                return None, {
                    "detail": f"Stock insuficiente para '{item.producto.nombre}'. Disponible: {item.producto.stock}."
                }

        total_final = carrito.total_con_descuento
        orden = Orden.objects.create(
            usuario=usuario,
            direccion_envio=direccion_envio,
            metodo_pago=metodo_pago,
            estado="pendiente",
            total=total_final,
        )

        for item in items:
            prod = item.producto
            OrdenItem.objects.create(
                orden=orden,
                producto=prod,
                producto_nombre_snapshot=prod.nombre,
                precio_unitario_snapshot=prod.precio_con_descuento,
                cantidad=item.cantidad,
            )
            prod.stock -= item.cantidad
            prod.save(update_fields=["stock"])

        # Otorgar puntos de fidelidad (1 punto por cada S/ 10)
        puntos = int(total_final // 10)
        if puntos > 0:
            usuario.puntos_fidelidad += puntos
            usuario.save(update_fields=["puntos_fidelidad"])

        carrito.items.all().delete()
        carrito.activo = False
        carrito.save(update_fields=["activo"])

    return orden, None


@extend_schema_view(
    list=extend_schema(summary="Listar categorías tecnológicas", tags=["Categorías"]),
    retrieve=extend_schema(summary="Detalle de categoría", tags=["Categorías"]),
)
class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(summary="Listar vendedores del marketplace", tags=["Vendedores"]),
    retrieve=extend_schema(summary="Detalle de vendedor", tags=["Vendedores"]),
)
class VendedorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Usuario.objects.filter(rol="vendedor")
    serializer_class = VendedorResumenSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="Listar catálogo de productos",
        description="Lista paginada (24/página) con filtros por categoría, marca, rango de precio, disponibilidad y búsqueda.",
        tags=["Productos"],
        examples=[
            OpenApiExample(
                "Ejemplo de producto tecnológico",
                value={
                    "id": 1,
                    "sku": "TM-LAP-0001",
                    "nombre": "Laptop Dell XPS 15 Gaming",
                    "marca": "Dell",
                    "precio": "6499.00",
                    "precio_con_descuento": "5849.10",
                    "stock": 12,
                    "disponible": True,
                    "rating_promedio": 4.8,
                },
                response_only=True,
            )
        ],
    ),
    retrieve=extend_schema(summary="Detalle completo de producto", tags=["Productos"]),
    create=extend_schema(summary="Publicar producto (Admin / Vendedor)", tags=["Productos"]),
    update=extend_schema(summary="Actualizar producto (Propio / Admin)", tags=["Productos"]),
    destroy=extend_schema(summary="Eliminar producto (Solo Admin)", tags=["Productos"]),
)
class ProductoViewSet(viewsets.ModelViewSet):
    """Catálogo principal de TecnoMarket Perú con nested categoría, HATEOAS y búsqueda."""

    queryset = (
        Producto.objects.select_related("categoria", "vendedor")
        .annotate(avg_calificacion=Avg("resenas__calificacion"))
        .all()
    )
    serializer_class = ProductoSerializer
    permission_classes = [PuedeVender]
    pagination_class = ProductoPageNumberPagination
    throttle_classes = [AnonRateThrottle, UserRateThrottle, SearchRateThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, ProductoOrderingFilter]
    filterset_class = ProductoFilter
    search_fields = ["nombre", "descripcion", "marca", "sku", "categoria__nombre"]
    ordering_fields = ["precio", "avg_calificacion", "fecha_creacion", "stock"]
    ordering = ["-fecha_creacion"]

    def perform_create(self, serializer):
        serializer.save(vendedor=self.request.user)

    @extend_schema(summary="Listar reseñas de un producto específico", tags=["Productos"])
    @action(detail=True, methods=["get"], url_path="resenas")
    def resenas(self, request, pk=None):
        producto = self.get_object()
        qs = Resena.objects.filter(producto=producto).select_related("usuario", "producto")
        serializer = ResenaSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class CarritoViewSet(viewsets.ViewSet):
    """Gestión del carrito de compras del cliente autenticado."""

    permission_classes = [IsAuthenticated]

    def _get_or_create_carrito(self, user):
        carrito = Carrito.objects.filter(usuario=user, activo=True).first()
        if not carrito:
            carrito = Carrito.objects.create(usuario=user, activo=True)
        return carrito

    def _serialize_carrito(self, carrito, request):
        refreshed = Carrito.objects.prefetch_related("items__producto").get(pk=carrito.pk)
        return CarritoSerializer(refreshed, context={"request": request}).data

    @extend_schema(summary="Ver carrito actual", tags=["Carrito"], responses=CarritoSerializer)
    def list(self, request):
        carrito = self._get_or_create_carrito(request.user)
        return Response(self._serialize_carrito(carrito, request))

    @extend_schema(
        summary="Agregar producto al carrito",
        tags=["Carrito"],
        request=CarritoAccionSerializer,
        responses=CarritoSerializer,
    )
    @action(detail=False, methods=["post"], url_path="agregar")
    def agregar(self, request):
        ser = CarritoAccionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        producto = Producto.objects.filter(pk=ser.validated_data["producto_id"]).first()
        if not producto:
            return Response({"detail": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        cantidad = ser.validated_data.get("cantidad", 1)
        carrito = self._get_or_create_carrito(request.user)
        item, created = CarritoItem.objects.get_or_create(
            carrito=carrito, producto=producto, defaults={"cantidad": cantidad}
        )
        nueva_cantidad = cantidad if created else item.cantidad + cantidad
        if nueva_cantidad > producto.stock:
            if created:
                item.delete()
            return Response(
                {"detail": f"La cantidad ({nueva_cantidad}) excede el stock disponible ({producto.stock})."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.cantidad = nueva_cantidad
        item.save()

        cupon_cod = ser.validated_data.get("cupon")
        if cupon_cod:
            cupon = Cupon.objects.filter(codigo__iexact=cupon_cod, activo=True).first()
            if cupon:
                carrito.cupon = cupon
                carrito.save(update_fields=["cupon"])

        return Response(self._serialize_carrito(carrito, request))

    @extend_schema(
        summary="Actualizar cantidad de un producto en carrito",
        tags=["Carrito"],
        request=CarritoAccionSerializer,
        responses=CarritoSerializer,
    )
    @action(detail=False, methods=["post"], url_path="actualizar")
    def actualizar(self, request):
        ser = CarritoAccionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        carrito = self._get_or_create_carrito(request.user)
        item = CarritoItem.objects.filter(carrito=carrito, producto_id=ser.validated_data["producto_id"]).first()
        if not item:
            return Response({"detail": "El producto no está en el carrito."}, status=status.HTTP_404_NOT_FOUND)
        cantidad = ser.validated_data["cantidad"]
        if cantidad > item.producto.stock:
            return Response(
                {"detail": f"Stock insuficiente. Máximo disponible: {item.producto.stock}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.cantidad = cantidad
        item.save()
        return Response(self._serialize_carrito(carrito, request))

    @extend_schema(
        summary="Eliminar un producto del carrito",
        tags=["Carrito"],
        request=CarritoAccionSerializer,
        responses=CarritoSerializer,
    )
    @action(detail=False, methods=["post"], url_path="eliminar")
    def eliminar(self, request):
        producto_id = request.data.get("producto_id")
        carrito = self._get_or_create_carrito(request.user)
        deleted, _ = CarritoItem.objects.filter(carrito=carrito, producto_id=producto_id).delete()
        if not deleted:
            return Response({"detail": "Producto no encontrado en el carrito."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self._serialize_carrito(carrito, request))

    @extend_schema(summary="Vaciar carrito completo", tags=["Carrito"], request=None, responses=CarritoSerializer)
    @action(detail=False, methods=["post"], url_path="vaciar")
    def vaciar(self, request):
        carrito = self._get_or_create_carrito(request.user)
        carrito.items.all().delete()
        carrito.cupon = None
        carrito.save(update_fields=["cupon"])
        return Response(self._serialize_carrito(carrito, request))

    @extend_schema(
        summary="Convertir carrito en orden de compra (Checkout)",
        tags=["Carrito"],
        request=CheckoutSerializer,
        responses=OrdenSerializer,
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="checkout",
        throttle_classes=[CheckoutRateThrottle, UserRateThrottle],
    )
    def checkout(self, request):
        ser = CheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        orden, error = _crear_orden_desde_carrito(
            request.user,
            ser.validated_data["direccion_envio"],
            ser.validated_data["metodo_pago"],
            ser.validated_data.get("cupon", ""),
        )
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrdenSerializer(orden, context={"request": request}).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(summary="Listar órdenes de compra (LimitOffset 50)", tags=["Órdenes"]),
    retrieve=extend_schema(summary="Detalle de orden con snapshot de precios", tags=["Órdenes"]),
    create=extend_schema(summary="Crear orden desde el carrito activo", tags=["Órdenes"], request=CheckoutSerializer),
    partial_update=extend_schema(summary="Actualizar estado de orden (Admin / Vendedor)", tags=["Órdenes"]),
)
class OrdenViewSet(viewsets.ModelViewSet):
    """Gestión de órdenes con snapshot de precios, tracking y flujo de estados."""

    queryset = Orden.objects.select_related("usuario").prefetch_related("items__producto").all()
    serializer_class = OrdenSerializer
    pagination_class = OrdenLimitOffsetPagination
    permission_classes = [IsAuthenticated, EsPropietarioOrdenOStaff]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["estado", "metodo_pago"]
    ordering_fields = ["fecha_creacion", "total"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.es_admin or user.es_vendedor:
            return qs
        return qs.filter(usuario=user)

    def create(self, request, *args, **kwargs):
        ser = CheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        orden, error = _crear_orden_desde_carrito(
            request.user,
            ser.validated_data["direccion_envio"],
            ser.validated_data["metodo_pago"],
            ser.validated_data.get("cupon", ""),
        )
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrdenSerializer(orden, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Cancelar orden pendiente y reponer stock", tags=["Órdenes"], request=None)
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        orden = self.get_object()
        if orden.usuario != request.user and not request.user.es_admin:
            return Response({"detail": "No autorizado para cancelar esta orden."}, status=status.HTTP_403_FORBIDDEN)
        if orden.estado != "pendiente":
            return Response(
                {"detail": "Solo se pueden cancelar órdenes en estado 'pendiente'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            for item in orden.items.select_related("producto"):
                item.producto.stock += item.cantidad
                item.producto.save(update_fields=["stock"])
            orden.estado = "cancelada"
            orden.save(update_fields=["estado"])
        return Response(OrdenSerializer(orden, context={"request": request}).data)

    @extend_schema(summary="Listar órdenes del usuario autenticado", tags=["Órdenes"])
    @action(detail=False, methods=["get"], url_path="mis-ordenes")
    def mis_ordenes(self, request):
        qs = Orden.objects.filter(usuario=request.user).prefetch_related("items")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(OrdenSerializer(page, many=True, context={"request": request}).data)
        return Response(OrdenSerializer(qs, many=True, context={"request": request}).data)


@extend_schema_view(
    list=extend_schema(summary="Listar reseñas (Público)", tags=["Reseñas"]),
    create=extend_schema(summary="Crear reseña verificada (Cliente comprador)", tags=["Reseñas"]),
    destroy=extend_schema(summary="Eliminar reseña (Propio o Admin)", tags=["Reseñas"]),
)
class ResenaViewSet(viewsets.ModelViewSet):
    """Gestión de reseñas y calificaciones de productos comprados."""

    queryset = Resena.objects.select_related("usuario", "producto").all()
    serializer_class = ResenaSerializer
    permission_classes = [IsOwnerOrReadOnly, EsCompradorVerificado]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["producto", "calificacion"]
    ordering_fields = ["calificacion", "fecha_creacion"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), EsCompradorVerificado()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


class PerfilUsuarioViewSet(viewsets.ViewSet):
    """Perfil del usuario autenticado y puntos de fidelidad."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Obtener perfil del usuario autenticado", tags=["Usuarios"], responses=UsuarioPerfilSerializer)
    @action(detail=False, methods=["get"], url_path="perfil")
    def perfil(self, request):
        return Response(UsuarioPerfilSerializer(request.user).data)
