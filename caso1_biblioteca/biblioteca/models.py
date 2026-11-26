"""Modelos de datos para la Biblioteca Central UNCP."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario del sistema bibliotecario con roles universitarios."""

    TIPO_CHOICES = [
        ("administrador", "Administrador"),
        ("bibliotecario", "Bibliotecario"),
        ("estudiante", "Estudiante"),
        ("docente", "Docente/Investigador"),
        ("externo", "Sistema Externo"),
    ]

    nombre = models.CharField(max_length=150, verbose_name="Nombre completo")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="estudiante")
    carrera = models.CharField(max_length=120, blank=True, default="")
    carnet = models.CharField(max_length=30, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        ordering = ["id"]
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def save(self, *args, **kwargs):
        if not self.nombre:
            full = f"{self.first_name} {self.last_name}".strip()
            self.nombre = full or self.username
        if self.is_superuser:
            self.tipo = "administrador"
        elif self.tipo == "administrador":
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def es_admin(self) -> bool:
        return self.is_superuser or self.is_staff or self.tipo == "administrador"

    @property
    def es_bibliotecario(self) -> bool:
        return self.tipo == "bibliotecario"

    @property
    def prestamos_activos_count(self) -> int:
        return self.prestamos.filter(estado__in=["activo", "vencido"]).count()

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_tipo_display()})"


class Autor(models.Model):
    """Autor de publicaciones académicas y libros."""

    nombre = models.CharField(max_length=150)
    nacionalidad = models.CharField(max_length=80)
    biografia = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Autor"
        verbose_name_plural = "Autores"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.nacionalidad})"


class Libro(models.Model):
    """Recurso bibliográfico del catálogo de la Biblioteca Central UNCP."""

    CATEGORIA_CHOICES = [
        ("ingenieria", "Ingeniería"),
        ("ciencias", "Ciencias"),
        ("humanidades", "Humanidades"),
        ("medicina", "Medicina"),
        ("derecho", "Derecho"),
        ("economia", "Economía"),
    ]

    isbn = models.CharField(max_length=20, unique=True, db_index=True)
    titulo = models.CharField(max_length=255, db_index=True)
    autor = models.ForeignKey(Autor, on_delete=models.CASCADE, related_name="libros")
    editorial = models.CharField(max_length=150)
    anio = models.PositiveIntegerField(verbose_name="Año de publicación", db_index=True)
    categoria = models.CharField(max_length=40, choices=CATEGORIA_CHOICES, db_index=True)
    stock = models.PositiveIntegerField(default=1)
    ubicacion = models.CharField(max_length=100, help_text="Formato: Estante X / Piso Y")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-anio", "titulo"]
        verbose_name = "Libro"
        verbose_name_plural = "Libros"

    @property
    def disponible(self) -> bool:
        return self.stock > 0

    def __str__(self) -> str:
        return f"{self.titulo} ({self.isbn})"


class Prestamo(models.Model):
    """Registro de préstamo bibliotecario con cálculo de días restantes y multa."""

    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("devuelto", "Devuelto"),
        ("vencido", "Vencido"),
    ]

    MULTA_DIARIA = Decimal("2.00")

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="prestamos")
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, related_name="prestamos")
    fecha_prestamo = models.DateField(default=date.today)
    fecha_devolucion = models.DateField()
    fecha_devolucion_real = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default="activo", db_index=True)

    class Meta:
        ordering = ["-fecha_prestamo", "-id"]
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"

    def sincronizar_estado(self) -> None:
        """Actualiza el estado a vencido si superó la fecha de devolución."""
        if self.estado == "activo" and date.today() > self.fecha_devolucion:
            self.estado = "vencido"

    @property
    def dias_restantes(self) -> int:
        if self.estado == "devuelto":
            return 0
        return (self.fecha_devolucion - date.today()).days

    @property
    def multa(self) -> Decimal:
        if self.estado == "devuelto":
            if self.fecha_devolucion_real and self.fecha_devolucion_real > self.fecha_devolucion:
                dias = (self.fecha_devolucion_real - self.fecha_devolucion).days
                return self.MULTA_DIARIA * dias
            return Decimal("0.00")
        dias_retraso = (date.today() - self.fecha_devolucion).days
        if dias_retraso > 0 or self.estado == "vencido":
            return self.MULTA_DIARIA * max(dias_retraso, 0)
        return Decimal("0.00")

    def __str__(self) -> str:
        return f"Préstamo #{self.id}: {self.libro.titulo} -> {self.usuario.nombre}"
