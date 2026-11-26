from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Autor, Libro, Prestamo, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "nombre", "tipo", "carrera", "carnet", "is_staff")
    list_filter = ("tipo", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Información Universitaria", {"fields": ("nombre", "tipo", "carrera", "carnet", "telefono")}),
    )


@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nacionalidad")
    search_fields = ("nombre", "nacionalidad")


@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ("isbn", "titulo", "autor", "categoria", "anio", "stock", "disponible")
    list_filter = ("categoria", "anio")
    search_fields = ("isbn", "titulo", "autor__nombre")


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "libro", "fecha_prestamo", "fecha_devolucion", "estado")
    list_filter = ("estado",)
