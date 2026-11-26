"""Modelos de datos para TecnoMarket Perú E-Commerce."""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg


class Usuario(AbstractUser):
    """Usuario de TecnoMarket Perú (Administrador, Vendedor, Cliente, Externo)."""

    ROL_CHOICES = [
        ("administrador", "Administrador"),
        ("vendedor", "Vendedor"),
        ("cliente", "Cliente"),
        ("externo", "Sistema Externo"),
    ]

    nombre = models.CharField(max_length=150)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default="cliente")
    tienda_nombre = models.CharField(max_length=150, blank=True, default="")
    puntos_fidelidad = models.PositiveIntegerField(default=0)
    telefono = models.CharField(max_length=20, blank=True, default="")
    direccion = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def save(self, *args, **kwargs):
        if not self.nombre:
            full = f"{self.first_name} {self.last_name}".strip()
            self.nombre = full or self.username
        if self.is_superuser:
            self.rol = "administrador"
        elif self.rol == "administrador":
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def es_admin(self) -> bool:
        return self.is_superuser or self.is_staff or self.rol == "administrador"

    @property
    def es_vendedor(self) -> bool:
        return self.rol == "vendedor"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_rol_display()})"


class Categoria(models.Model):
    """Categoría de productos tecnológicos."""

    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, default="")
    imagen = models.URLField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self) -> str:
        return self.nombre


class Cupon(models.Model):
    """Cupón de descuento aplicable al carrito de compras."""

    codigo = models.CharField(max_length=30, unique=True)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    activo = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.codigo} (-{self.porcentaje_descuento}%)"


class Producto(models.Model):
    """Producto del catálogo tecnológico de TecnoMarket Perú."""

    sku = models.CharField(max_length=40, unique=True, db_index=True)
    nombre = models.CharField(max_length=200, db_index=True)
    descripcion = models.TextField()
    marca = models.CharField(max_length=100, db_index=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="productos")
    vendedor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="productos")
    precio = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    stock = models.PositiveIntegerField(default=0)
    imagenes = models.JSONField(default=list, blank=True)
    especificaciones_tecnicas = models.JSONField(default=dict, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion", "id"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    @property
    def precio_con_descuento(self) -> Decimal:
        if self.descuento_porcentaje and self.descuento_porcentaje > 0:
            factor = Decimal("1.00") - (self.descuento_porcentaje / Decimal("100.00"))
            return (self.precio * factor).quantize(Decimal("0.01"))
        return self.precio

    @property
    def rating_promedio(self) -> float:
        agg = self.resenas.aggregate(avg=Avg("calificacion"))
        val = agg.get("avg")
        return round(float(val), 2) if val is not None else 0.0

    @property
    def disponible(self) -> bool:
        return self.stock > 0

    def __str__(self) -> str:
        return f"[{self.sku}] {self.nombre}"


class Carrito(models.Model):
    """Carrito de compras activo por usuario."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="carritos")
    activo = models.BooleanField(default=True, db_index=True)
    cupon = models.ForeignKey(Cupon, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Carrito"
        verbose_name_plural = "Carritos"

    @property
    def subtotal(self) -> Decimal:
        total = sum(
            (item.producto.precio_con_descuento * item.cantidad for item in self.items.select_related("producto")),
            Decimal("0.00"),
        )
        return total.quantize(Decimal("0.01"))

    @property
    def impuestos(self) -> Decimal:
        return (self.subtotal * Decimal("0.18")).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        return (self.subtotal + self.impuestos).quantize(Decimal("0.01"))

    @property
    def total_con_descuento(self) -> Decimal:
        if self.cupon and self.cupon.activo and self.cupon.porcentaje_descuento > 0:
            factor = Decimal("1.00") - (self.cupon.porcentaje_descuento / Decimal("100.00"))
            return (self.total * factor).quantize(Decimal("0.01"))
        return self.total

    @property
    def cantidad_items(self) -> int:
        return sum(item.cantidad for item in self.items.all())

    def __str__(self) -> str:
        return f"Carrito #{self.id} de {self.usuario.username}"


class CarritoItem(models.Model):
    """Ítem dentro de un carrito de compras."""

    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ("carrito", "producto")


class Orden(models.Model):
    """Orden de compra con flujo de estados y snapshot de precios."""

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("pagada", "Pagada"),
        ("enviada", "Enviada"),
        ("entregada", "Entregada"),
        ("cancelada", "Cancelada"),
    ]
    METODO_PAGO_CHOICES = [
        ("culqi", "Culqi"),
        ("mercadopago", "MercadoPago"),
        ("niubiz", "Niubiz"),
        ("tarjeta", "Tarjeta Crédito/Débito"),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="ordenes")
    direccion_envio = models.CharField(max_length=255)
    metodo_pago = models.CharField(max_length=30, choices=METODO_PAGO_CHOICES, default="culqi")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente", db_index=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    numero_seguimiento = models.CharField(max_length=40, blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "Orden"
        verbose_name_plural = "Órdenes"

    def save(self, *args, **kwargs):
        if self.estado == "enviada" and not self.numero_seguimiento:
            self.numero_seguimiento = f"TM-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    @property
    def tiempo_estimado_entrega(self) -> str:
        base = self.fecha_creacion.date() if self.fecha_creacion else None
        if base:
            min_f = (base + timedelta(days=3)).isoformat()
            max_f = (base + timedelta(days=5)).isoformat()
            return f"{min_f} a {max_f} (3-5 días hábiles)"
        return "3-5 días hábiles"

    def __str__(self) -> str:
        return f"Orden #{self.id} - {self.usuario.username} ({self.estado})"


class OrdenItem(models.Model):
    """Snapshot inmutable del producto y precio al momento de compra."""

    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="orden_items")
    producto_nombre_snapshot = models.CharField(max_length=200)
    precio_unitario_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self) -> Decimal:
        return (self.precio_unitario_snapshot * self.cantidad).quantize(Decimal("0.01"))


class Resena(models.Model):
    """Reseña y calificación verificada (1-5) sobre un producto comprado."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="resenas")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="resenas")
    calificacion = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    titulo = models.CharField(max_length=150)
    comentario = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "Reseña"
        verbose_name_plural = "Reseñas"

    @property
    def es_compra_verificada(self) -> bool:
        return OrdenItem.objects.filter(
            orden__usuario=self.usuario,
            producto=self.producto,
        ).exclude(orden__estado="cancelada").exists()

    def __str__(self) -> str:
        return f"Reseña {self.calificacion}/5 - {self.producto.nombre}"
