"""Pruebas unitarias y de integración para Caso 2: TecnoMarket Perú E-Commerce."""
from decimal import Decimal

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Categoria, Cupon, Orden, Producto, Usuario


class EcommerceAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_test", email="admin@tecnomarket.pe", password="pass", nombre="Admin"
        )
        self.vendedor = Usuario.objects.create_user(
            username="vendedor_test",
            email="vend@tecnomarket.pe",
            password="pass",
            nombre="Vendedor Dell",
            rol="vendedor",
            tienda_nombre="Dell Perú",
        )
        self.cliente = Usuario.objects.create_user(
            username="cliente_test",
            email="cli@gmail.com",
            password="pass",
            nombre="Cliente Test",
            rol="cliente",
        )
        self.otro_cliente = Usuario.objects.create_user(
            username="otro_test",
            email="otro@gmail.com",
            password="pass",
            nombre="Otro Cliente",
            rol="cliente",
        )
        self.cat = Categoria.objects.create(
            nombre="Laptops", slug="laptops", descripcion="Laptops", imagen="https://cdn.test/lap.png"
        )
        self.cupon = Cupon.objects.create(codigo="DESC10", porcentaje_descuento=Decimal("10.00"), activo=True)
        self.prod = Producto.objects.create(
            sku="TM-001",
            nombre="Dell Gaming Laptop",
            descripcion="Laptop potente",
            marca="Dell",
            categoria=self.cat,
            vendedor=self.vendedor,
            precio=Decimal("1500.00"),
            descuento_porcentaje=Decimal("10.00"),
            stock=10,
        )

    def test_catalogo_filtros_y_campos_calculados(self):
        resp = self.client.get("/api/productos/?categoria=laptops&marca=dell&precio_min=500&precio_max=2000&disponible=true")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        item = resp.data["results"][0]
        self.assertEqual(Decimal(item["precio_con_descuento"]), Decimal("1350.00"))
        self.assertTrue(item["disponible"])
        self.assertIn("vendedor", item)
        self.assertIn("reseñas", item)

    def test_carrito_validaciones_y_checkout_snapshot(self):
        self.client.force_authenticate(user=self.cliente)
        # Exceder stock falla
        fail_stock = self.client.post(
            "/api/carrito/agregar/", {"producto_id": self.prod.id, "cantidad": 50}
        )
        self.assertEqual(fail_stock.status_code, status.HTTP_400_BAD_REQUEST)

        # Agregar válido con cupón
        ok = self.client.post(
            "/api/carrito/agregar/",
            {"producto_id": self.prod.id, "cantidad": 2, "cupon": "DESC10"},
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(ok.data["cantidad_items"], 2)

        # Checkout crea orden con snapshot de precio
        checkout = self.client.post(
            "/api/carrito/checkout/",
            {"direccion_envio": "Av. Lima 100", "metodo_pago": "culqi"},
        )
        self.assertEqual(checkout.status_code, status.HTTP_201_CREATED)
        orden_id = checkout.data["id"]
        self.assertEqual(Decimal(checkout.data["items"][0]["precio_unitario_snapshot"]), Decimal("1350.00"))

        # Cambio de precio posterior no altera snapshot de orden
        self.prod.precio = Decimal("2000.00")
        self.prod.save()
        orden_resp = self.client.get(f"/api/ordenes/{orden_id}/")
        self.assertEqual(Decimal(orden_resp.data["items"][0]["precio_unitario_snapshot"]), Decimal("1350.00"))

        # Cliente puede reseñar producto comprado
        resena_ok = self.client.post(
            "/api/resenas/",
            {
                "producto": self.prod.id,
                "calificacion": 5,
                "titulo": "Excelente",
                "comentario": "Muy buena laptop.",
            },
        )
        self.assertEqual(resena_ok.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resena_ok.data["es_compra_verificada"])

        # Otro cliente que NO compró no puede reseñar
        self.client.force_authenticate(user=self.otro_cliente)
        resena_fail = self.client.post(
            "/api/resenas/",
            {
                "producto": self.prod.id,
                "calificacion": 4,
                "titulo": "Sin compra",
                "comentario": "Intento.",
            },
        )
        self.assertEqual(resena_fail.status_code, status.HTTP_403_FORBIDDEN)

    def test_flujo_estados_orden_y_cancelacion(self):
        self.client.force_authenticate(user=self.cliente)
        self.client.post("/api/carrito/agregar/", {"producto_id": self.prod.id, "cantidad": 1})
        orden_resp = self.client.post(
            "/api/ordenes/", {"direccion_envio": "Jr. Cusco 222", "metodo_pago": "niubiz"}
        )
        orden_id = orden_resp.data["id"]

        # Vendedor cambia a enviada -> genera numero_seguimiento
        self.client.force_authenticate(user=self.vendedor)
        patch_resp = self.client.patch(f"/api/ordenes/{orden_id}/", {"estado": "enviada"})
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_resp.data["numero_seguimiento"].startswith("TM-"))

        # No se puede cancelar si no está pendiente
        self.client.force_authenticate(user=self.cliente)
        cancel_fail = self.client.post(f"/api/ordenes/{orden_id}/cancelar/")
        self.assertEqual(cancel_fail.status_code, status.HTTP_400_BAD_REQUEST)

    def test_jwt_token_y_docs(self):
        jwt_resp = self.client.post(
            "/api/auth/jwt/token/", {"username": "cliente_test", "password": "pass"}
        )
        self.assertEqual(jwt_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", jwt_resp.data)
        self.assertEqual(self.client.get("/api/docs/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/redoc/").status_code, status.HTTP_200_OK)

    def test_checkout_throttling_429(self):
        cache.clear()
        self.client.force_authenticate(user=self.cliente)
        for _ in range(10):
            resp = self.client.post(
                "/api/carrito/checkout/", {"direccion_envio": "Lima", "metodo_pago": "culqi"}
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp_429 = self.client.post(
            "/api/carrito/checkout/", {"direccion_envio": "Lima", "metodo_pago": "culqi"}
        )
        self.assertEqual(resp_429.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
