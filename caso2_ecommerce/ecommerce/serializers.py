"""Serializadores avanzados con lógica de negocio, snapshots y HATEOAS."""
from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

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


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "slug", "descripcion", "imagen"]


class VendedorResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "nombre", "tienda_nombre", "rol"]


class ProductoSerializer(serializers.ModelSerializer):
    """Serializador de Productos con nested categoria, HATEOAS y campos calculados."""

    url = serializers.HyperlinkedIdentityField(view_name="producto-detail", read_only=True)
    categoria = CategoriaSerializer(read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(), source="categoria", write_only=True
    )
    vendedor = serializers.HyperlinkedRelatedField(
        view_name="vendedor-detail", read_only=True
    )
    reseñas = serializers.HyperlinkedIdentityField(
        view_name="producto-resenas", read_only=True
    )
    precio_con_descuento = serializers.SerializerMethodField()
    rating_promedio = serializers.SerializerMethodField()
    disponible = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            "id",
            "url",
            "sku",
            "nombre",
            "descripcion",
            "marca",
            "categoria",
            "categoria_id",
            "vendedor",
            "reseñas",
            "precio",
            "descuento_porcentaje",
            "precio_con_descuento",
            "stock",
            "disponible",
            "rating_promedio",
            "imagenes",
            "especificaciones_tecnicas",
            "fecha_creacion",
        ]
        read_only_fields = ["fecha_creacion"]

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_precio_con_descuento(self, obj: Producto) -> Decimal:
        return obj.precio_con_descuento

    @extend_schema_field(serializers.FloatField())
    def get_rating_promedio(self, obj: Producto) -> float:
        return obj.rating_promedio

    @extend_schema_field(serializers.BooleanField())
    def get_disponible(self, obj: Producto) -> bool:
        return obj.disponible


class CarritoItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    producto_sku = serializers.CharField(source="producto.sku", read_only=True)
    precio_unitario = serializers.SerializerMethodField()

    class Meta:
        model = CarritoItem
        fields = ["id", "producto", "producto_sku", "producto_nombre", "precio_unitario", "cantidad"]

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_precio_unitario(self, obj: CarritoItem) -> Decimal:
        return obj.producto.precio_con_descuento


class CarritoSerializer(serializers.ModelSerializer):
    items = CarritoItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    impuestos = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    total_con_descuento = serializers.SerializerMethodField()
    cantidad_items = serializers.SerializerMethodField()
    cupon_codigo = serializers.CharField(source="cupon.codigo", read_only=True, default=None)

    class Meta:
        model = Carrito
        fields = [
            "id",
            "usuario",
            "activo",
            "cupon_codigo",
            "items",
            "cantidad_items",
            "subtotal",
            "impuestos",
            "total",
            "total_con_descuento",
        ]
        read_only_fields = ["usuario", "activo"]

    def validate(self, attrs):
        request = self.context.get("request")
        if self.instance is None and request and request.user.is_authenticated:
            if Carrito.objects.filter(usuario=request.user, activo=True).exists():
                raise serializers.ValidationError("El usuario no puede tener más de 1 carrito activo.")
        return attrs

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_subtotal(self, obj: Carrito) -> Decimal:
        return obj.subtotal

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_impuestos(self, obj: Carrito) -> Decimal:
        return obj.impuestos

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total(self, obj: Carrito) -> Decimal:
        return obj.total

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_con_descuento(self, obj: Carrito) -> Decimal:
        return obj.total_con_descuento

    @extend_schema_field(serializers.IntegerField())
    def get_cantidad_items(self, obj: Carrito) -> int:
        return obj.cantidad_items


class CarritoAccionSerializer(serializers.Serializer):
    """Payload de entrada para agregar/actualizar/eliminar en carrito."""

    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1, required=False, default=1)
    cupon = serializers.CharField(required=False, allow_blank=True)


class CheckoutSerializer(serializers.Serializer):
    """Payload para convertir carrito en orden."""

    direccion_envio = serializers.CharField(max_length=255)
    metodo_pago = serializers.ChoiceField(choices=Orden.METODO_PAGO_CHOICES, default="culqi")
    cupon = serializers.CharField(required=False, allow_blank=True)


class OrdenItemSerializer(serializers.ModelSerializer):
    """Ítem de orden con snapshot del precio al momento de compra."""

    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrdenItem
        fields = [
            "id",
            "producto",
            "producto_nombre_snapshot",
            "precio_unitario_snapshot",
            "cantidad",
            "subtotal",
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_subtotal(self, obj: OrdenItem) -> Decimal:
        return obj.subtotal


class OrdenSerializer(serializers.ModelSerializer):
    """Serializador complejo de Órdenes con snapshot de ítems y tiempo estimado de entrega."""

    items = OrdenItemSerializer(many=True, read_only=True)
    tiempo_estimado_entrega = serializers.SerializerMethodField()
    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)

    class Meta:
        model = Orden
        fields = [
            "id",
            "usuario",
            "usuario_nombre",
            "items",
            "direccion_envio",
            "metodo_pago",
            "estado",
            "total",
            "numero_seguimiento",
            "tiempo_estimado_entrega",
            "fecha_creacion",
        ]
        read_only_fields = ["usuario", "total", "numero_seguimiento", "fecha_creacion"]

    @extend_schema_field(serializers.CharField())
    def get_tiempo_estimado_entrega(self, obj: Orden) -> str:
        return obj.tiempo_estimado_entrega


class ResenaSerializer(serializers.ModelSerializer):
    """Serializador de Reseñas verificando compra previa y calificación 1-5."""

    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    es_compra_verificada = serializers.SerializerMethodField()

    class Meta:
        model = Resena
        fields = [
            "id",
            "usuario",
            "usuario_nombre",
            "producto",
            "producto_nombre",
            "calificacion",
            "titulo",
            "comentario",
            "es_compra_verificada",
            "fecha_creacion",
        ]
        read_only_fields = ["usuario", "fecha_creacion"]

    @extend_schema_field(serializers.BooleanField())
    def get_es_compra_verificada(self, obj: Resena) -> bool:
        return obj.es_compra_verificada

    def validate_calificacion(self, value: int) -> int:
        if value < 1 or value > 5:
            raise serializers.ValidationError("La calificación debe estar entre 1 y 5.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        producto = attrs.get("producto")
        if request and request.user.is_authenticated and producto:
            compro = OrdenItem.objects.filter(
                orden__usuario=request.user,
                producto=producto,
            ).exclude(orden__estado="cancelada").exists()
            if not compro:
                raise serializers.ValidationError(
                    {"producto": "Solo puedes reseñar productos que hayas comprado en TecnoMarket Perú."}
                )
        return attrs


class UsuarioPerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "nombre", "email", "rol", "tienda_nombre", "puntos_fidelidad", "telefono", "direccion"]
        read_only_fields = ["puntos_fidelidad", "rol"]
