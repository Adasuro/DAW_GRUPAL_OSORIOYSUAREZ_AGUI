from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Carrito, Categoria, Cupon, Orden, OrdenItem, Producto, Resena, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "nombre", "rol", "tienda_nombre", "puntos_fidelidad", "is_staff")
    list_filter = ("rol", "is_staff")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug")
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(Cupon)
class CuponAdmin(admin.ModelAdmin):
    list_display = ("codigo", "porcentaje_descuento", "activo")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("sku", "nombre", "marca", "categoria", "precio", "stock", "disponible")
    list_filter = ("categoria", "marca")
    search_fields = ("sku", "nombre", "marca")


class OrdenItemInline(admin.TabularInline):
    model = OrdenItem
    extra = 0


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "metodo_pago", "estado", "total", "numero_seguimiento", "fecha_creacion")
    list_filter = ("estado", "metodo_pago")
    inlines = [OrdenItemInline]


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "producto", "calificacion", "titulo", "fecha_creacion")
    list_filter = ("calificacion",)


admin.site.register(Carrito)
