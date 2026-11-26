"""Serializadores avanzados con HATEOAS, nested serialization y validaciones."""
from datetime import date
from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Autor, Libro, Prestamo, Usuario


class AutorSerializer(serializers.ModelSerializer):
    """Serializador completo para autores (usado en nested serialization)."""

    class Meta:
        model = Autor
        fields = ["id", "nombre", "nacionalidad", "biografia"]


class LibroSerializer(serializers.ModelSerializer):
    """Serializador avanzado de Libros con campo calculado, HATEOAS y autor anidado."""

    url = serializers.HyperlinkedIdentityField(view_name="libro-detail", read_only=True)
    autor = AutorSerializer(read_only=True)
    autor_id = serializers.PrimaryKeyRelatedField(
        queryset=Autor.objects.all(),
        source="autor",
        write_only=True,
    )
    disponible = serializers.SerializerMethodField()

    class Meta:
        model = Libro
        fields = [
            "id",
            "url",
            "isbn",
            "titulo",
            "autor",
            "autor_id",
            "editorial",
            "anio",
            "categoria",
            "stock",
            "disponible",
            "ubicacion",
        ]

    @extend_schema_field(serializers.BooleanField())
    def get_disponible(self, obj: Libro) -> bool:
        return obj.stock > 0

    def validate_anio(self, value: int) -> int:
        if value < 1450 or value > date.today().year + 1:
            raise serializers.ValidationError("El año de publicación no es válido.")
        return value


class PrestamoSerializer(serializers.ModelSerializer):
    """Serializador de Préstamos con validación de stock y límite de 5 préstamos activos."""

    url = serializers.HyperlinkedIdentityField(view_name="prestamo-detail", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    libro_titulo = serializers.CharField(source="libro.titulo", read_only=True)
    dias_restantes = serializers.SerializerMethodField()
    multa = serializers.SerializerMethodField()

    class Meta:
        model = Prestamo
        fields = [
            "id",
            "url",
            "usuario",
            "usuario_nombre",
            "libro",
            "libro_titulo",
            "fecha_prestamo",
            "fecha_devolucion",
            "fecha_devolucion_real",
            "estado",
            "dias_restantes",
            "multa",
        ]
        read_only_fields = ["fecha_devolucion_real", "estado"]

    @extend_schema_field(serializers.IntegerField())
    def get_dias_restantes(self, obj: Prestamo) -> int:
        return obj.dias_restantes

    @extend_schema_field(serializers.DecimalField(max_digits=8, decimal_places=2))
    def get_multa(self, obj: Prestamo) -> Decimal:
        return obj.multa

    def validate(self, attrs):
        if self.instance is None:
            usuario = attrs.get("usuario")
            libro = attrs.get("libro")
            fecha_prestamo = attrs.get("fecha_prestamo") or date.today()
            fecha_devolucion = attrs.get("fecha_devolucion")

            if fecha_devolucion and fecha_devolucion < fecha_prestamo:
                raise serializers.ValidationError(
                    {"fecha_devolucion": "La fecha de devolución debe ser posterior al préstamo."}
                )

            activos = Prestamo.objects.filter(
                usuario=usuario,
                estado__in=["activo", "vencido"],
            ).count()
            if activos >= 5:
                raise serializers.ValidationError(
                    {
                        "usuario": (
                            f"El usuario {usuario.nombre} ya tiene {activos} préstamos activos. "
                            "El límite máximo permitido es 5."
                        )
                    }
                )

            if libro.stock <= 0:
                raise serializers.ValidationError(
                    {"libro": f"El libro '{libro.titulo}' no tiene stock disponible."}
                )
        return attrs

    def create(self, validated_data):
        libro = validated_data["libro"]
        libro.stock -= 1
        libro.save(update_fields=["stock"])
        return super().create(validated_data)


class PrestamoResumenSerializer(serializers.ModelSerializer):
    """Serializador compacto para el historial de préstamos en el perfil de usuario."""

    libro_titulo = serializers.CharField(source="libro.titulo", read_only=True)
    multa = serializers.SerializerMethodField()

    class Meta:
        model = Prestamo
        fields = ["id", "libro_titulo", "fecha_prestamo", "fecha_devolucion", "estado", "multa"]

    @extend_schema_field(serializers.DecimalField(max_digits=8, decimal_places=2))
    def get_multa(self, obj: Prestamo) -> Decimal:
        return obj.multa


class UsuarioPublicoSerializer(serializers.ModelSerializer):
    """Vista pública de usuario (solo datos básicos no sensibles)."""

    prestamos_activos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "tipo", "carrera", "prestamos_activos"]

    @extend_schema_field(serializers.IntegerField())
    def get_prestamos_activos(self, obj: Usuario) -> int:
        return obj.prestamos_activos_count


class UsuarioPrivadoSerializer(serializers.ModelSerializer):
    """Vista privada de usuario autenticado (propio o administrador)."""

    prestamos_activos = serializers.SerializerMethodField()
    historial_prestamos = PrestamoResumenSerializer(source="prestamos", many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nombre",
            "tipo",
            "carrera",
            "carnet",
            "email",
            "telefono",
            "prestamos_activos",
            "historial_prestamos",
        ]
        read_only_fields = ["prestamos_activos", "historial_prestamos"]

    @extend_schema_field(serializers.IntegerField())
    def get_prestamos_activos(self, obj: Usuario) -> int:
        return obj.prestamos_activos_count
