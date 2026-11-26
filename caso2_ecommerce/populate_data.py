"""Script para poblar automáticamente la base de datos de Caso 2 (TecnoMarket Perú).
Genera mínimo: 22 usuarios, 110 productos, 55 órdenes y 110 reseñas verificadas.
"""
import os
import random
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from faker import Faker
from rest_framework.authtoken.models import Token

from ecommerce.models import (
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

fake = Faker("es_ES")
Faker.seed(2026)
random.seed(2026)


def run():
    print("Poblando base de datos de TecnoMarket Perú E-Commerce...")
    Resena.objects.all().delete()
    OrdenItem.objects.all().delete()
    Orden.objects.all().delete()
    CarritoItem.objects.all().delete()
    Carrito.objects.all().delete()
    Producto.objects.all().delete()
    Cupon.objects.all().delete()
    Categoria.objects.all().delete()
    Usuario.objects.all().delete()

    # 1. Usuarios (22 usuarios: admin, vendedores, clientes, sistema externo)
    admin_user = Usuario.objects.create_superuser(
        username="admin_tecno",
        email="admin@tecnomarket.pe",
        password="AdminTecno2026!",
        nombre="Arlette Suárez Román",
        rol="administrador",
        telefono="999111222",
        direccion="Av. Javier Prado Este 4200, Lima",
    )
    vendedor1 = Usuario.objects.create_user(
        username="vendedor_dell",
        email="ventas@dellstore.pe",
        password="VendTecno2026!",
        nombre="José Pablo Osorio Mallqui",
        rol="vendedor",
        tienda_nombre="Dell Official Store Perú",
        telefono="999222333",
        direccion="Miraflores, Lima",
    )
    vendedor2 = Usuario.objects.create_user(
        username="vendedor_tech",
        email="marketplace@techperu.pe",
        password="VendTecno2026!",
        nombre="TechZone Marketplace SAC",
        rol="vendedor",
        tienda_nombre="TechZone Perú",
        telefono="999333444",
        direccion="San Isidro, Lima",
    )
    cliente_demo = Usuario.objects.create_user(
        username="cliente1",
        email="cliente1@gmail.com",
        password="ClienteTecno2026!",
        nombre="Valeria Mendoza Rojas",
        rol="cliente",
        puntos_fidelidad=350,
        telefono="987654321",
        direccion="Av. Arequipa 1540, Lince, Lima",
    )
    externo = Usuario.objects.create_user(
        username="webhook_culqi",
        email="webhooks@culqi.com",
        password="WebhookTecno2026!",
        nombre="Pasarela Culqi Perú",
        rol="externo",
    )

    vendedores = [vendedor1, vendedor2]
    clientes = [cliente_demo]
    for i in range(1, 18):
        c = Usuario.objects.create_user(
            username=f"cliente_{i}",
            email=f"cliente_{i}@correo.pe",
            password="ClienteTecno2026!",
            nombre=fake.name(),
            rol="cliente",
            puntos_fidelidad=random.randint(0, 800),
            telefono=f"9{random.randint(10000000, 99999999)}",
            direccion=fake.address().replace("\n", ", "),
        )
        clientes.append(c)

    for u in [admin_user, externo] + vendedores + clientes:
        Token.objects.get_or_create(user=u)

    # 2. Categorías y Cupones
    categorias_data = [
        ("Laptops", "laptops", "Laptops ultrabook, corporativas y gaming de alto rendimiento.", "https://cdn.tecnomarket.pe/cat/laptops.png"),
        ("Smartphones", "smartphones", "Teléfonos inteligentes 5G de última generación.", "https://cdn.tecnomarket.pe/cat/smartphones.png"),
        ("Componentes", "componentes", "Procesadores, tarjetas gráficas, SSD NVMe y memorias RAM.", "https://cdn.tecnomarket.pe/cat/componentes.png"),
        ("Accesorios", "accesorios", "Teclados mecánicos, mouse gamer, monitores y audio.", "https://cdn.tecnomarket.pe/cat/accesorios.png"),
    ]
    categorias = [
        Categoria.objects.create(nombre=n, slug=s, descripcion=d, imagen=img)
        for n, s, d, img in categorias_data
    ]

    Cupon.objects.create(codigo="CYBERWOW10", porcentaje_descuento=Decimal("10.00"), activo=True)
    Cupon.objects.create(codigo="TECNOVIP15", porcentaje_descuento=Decimal("15.00"), activo=True)

    # 3. Productos (110 productos)
    marcas_por_cat = {
        "laptops": ["Dell", "ASUS", "Lenovo", "HP", "Apple", "MSI"],
        "smartphones": ["Samsung", "Apple", "Xiaomi", "Motorola"],
        "componentes": ["NVIDIA", "AMD", "Kingston", "Corsair", "Intel"],
        "accesorios": ["Logitech", "Razer", "HyperX", "Sony", "Dell"],
    }
    modelos = {
        "laptops": ["XPS 15 Gaming Laptop", "ROG Strix G16 Gaming Laptop", "ThinkPad X1 Carbon", "MacBook Pro M4", "Victus 16 Gaming"],
        "smartphones": ["Galaxy S25 Ultra", "iPhone 16 Pro", "Redmi Note 14 Pro", "Edge 50 Ultra"],
        "componentes": ["GeForce RTX 4070 Ti", "Ryzen 9 7950X", "SSD NVMe 2TB PCIe 4.0", "RAM DDR5 32GB 6000MHz"],
        "accesorios": ["Mouse MX Master 3S", "Teclado Mecánico BlackWidow", "Audífonos WH-1000XM5", "Monitor UltraSharp 27 4K"],
    }

    productos = []
    for idx in range(110):
        cat = categorias[idx % len(categorias)]
        marca = "Dell" if idx < 10 and cat.slug == "laptops" else random.choice(marcas_por_cat[cat.slug])
        modelo = random.choice(modelos[cat.slug])
        if idx == 0:
            marca = "Dell"
            modelo = "Gaming Laptop Dell G15 RTX 4060"
            precio = Decimal("1850.00")
        else:
            precio = Decimal(str(round(random.uniform(120, 6800), 2)))

        desc_pct = Decimal(str(random.choice([0, 0, 5, 10, 15, 20])))
        stock = 0 if idx in (5, 25, 75) else random.randint(5, 45)
        prod = Producto.objects.create(
            sku=f"TM-{cat.slug[:3].upper()}-{1000 + idx:04d}",
            nombre=f"{marca} {modelo} Ed.{idx + 1}",
            descripcion=f"Producto original {marca} con garantía oficial en Perú y envío rápido.",
            marca=marca,
            categoria=cat,
            vendedor=vendedores[idx % len(vendedores)],
            precio=precio,
            descuento_porcentaje=desc_pct,
            stock=stock,
            imagenes=[
                f"https://cdn.tecnomarket.pe/img/{1000 + idx}_front.jpg",
                f"https://cdn.tecnomarket.pe/img/{1000 + idx}_side.jpg",
            ],
            especificaciones_tecnicas={
                "garantia": "12 meses",
                "origen": "Importado",
                "modelo_codigo": f"{marca[:3].upper()}-{2026}-{idx}",
                "ram": "16GB" if cat.slug == "laptops" else "N/A",
            },
        )
        productos.append(prod)

    # 4. Órdenes (55 órdenes con snapshot de ítems)
    estados = ["pendiente", "pagada", "enviada", "entregada", "cancelada"]
    metodos = ["culqi", "mercadopago", "niubiz", "tarjeta"]
    ordenes = []
    comprados_por_cliente = []

    for i in range(55):
        cli = clientes[i % len(clientes)]
        estado = estados[i % len(estados)] if i < 50 else "entregada"
        orden = Orden.objects.create(
            usuario=cli,
            direccion_envio=cli.direccion or "Av. Principal 123, Lima",
            metodo_pago=random.choice(metodos),
            estado=estado,
            total=Decimal("0.00"),
        )
        items_count = random.randint(1, 3)
        total_orden = Decimal("0.00")
        for j in range(items_count):
            prod = productos[(i * 2 + j) % len(productos)]
            qty = random.randint(1, 2)
            precio_snap = prod.precio_con_descuento
            OrdenItem.objects.create(
                orden=orden,
                producto=prod,
                producto_nombre_snapshot=prod.nombre,
                precio_unitario_snapshot=precio_snap,
                cantidad=qty,
            )
            total_orden += precio_snap * qty
            if estado != "cancelada":
                comprados_por_cliente.append((cli, prod))
        orden.total = (total_orden * Decimal("1.18")).quantize(Decimal("0.01"))
        orden.save()
        ordenes.append(orden)

    # Carrito demo con ítems para cliente1
    carrito_demo = Carrito.objects.create(usuario=cliente_demo, activo=True)
    CarritoItem.objects.create(carrito=carrito_demo, producto=productos[0], cantidad=1)
    CarritoItem.objects.create(carrito=carrito_demo, producto=productos[1], cantidad=2)

    # 5. Reseñas verificadas (110 reseñas)
    titulos_resena = [
        "Excelente rendimiento y envío rápido",
        "Muy buena relación calidad-precio",
        "Cumple con todas las especificaciones",
        "Empaque seguro y producto original",
        "Recomendado para trabajo y gaming",
    ]
    for i in range(110):
        cli, prod = comprados_por_cliente[i % len(comprados_por_cliente)]
        Resena.objects.create(
            usuario=cli,
            producto=prod,
            calificacion=random.randint(3, 5),
            titulo=random.choice(titulos_resena),
            comentario=fake.sentence(nb_words=14),
        )

    print(
        f"Listo: {Usuario.objects.count()} usuarios, {Categoria.objects.count()} categorías, "
        f"{Producto.objects.count()} productos, {Orden.objects.count()} órdenes, {Resena.objects.count()} reseñas."
    )


if __name__ == "__main__":
    run()
