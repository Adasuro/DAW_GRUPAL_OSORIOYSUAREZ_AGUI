"""Pruebas unitarias y de integración para Caso 1: Biblioteca Central UNCP."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Autor, Libro, Prestamo, Usuario


class BibliotecaAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_test",
            email="admin@uncp.edu.pe",
            password="pass",
            nombre="Admin Test",
            tipo="administrador",
            carrera="Sistemas",
        )
        self.biblio = Usuario.objects.create_user(
            username="biblio_test",
            email="biblio@uncp.edu.pe",
            password="pass",
            nombre="Biblio Test",
            tipo="bibliotecario",
            carrera="Sistemas",
        )
        self.estudiante = Usuario.objects.create_user(
            username="est_test",
            email="est@uncp.edu.pe",
            password="pass",
            nombre="Estudiante Test",
            tipo="estudiante",
            carrera="Ingeniería de Sistemas",
            carnet="2023100001",
        )
        self.autor = Autor.objects.create(
            nombre="Thomas Cormen",
            nacionalidad="Estadounidense",
            biografia="Autor de algoritmos.",
        )
        self.libro = Libro.objects.create(
            isbn="978-0000000001",
            titulo="Algoritmos en Python",
            autor=self.autor,
            editorial="MIT Press",
            anio=2023,
            categoria="ingenieria",
            stock=3,
            ubicacion="Estante A-1 / Piso 1",
        )
        self.libro_agotado = Libro.objects.create(
            isbn="978-0000000002",
            titulo="Libro Sin Stock",
            autor=self.autor,
            editorial="Pearson",
            anio=2018,
            categoria="ciencias",
            stock=0,
            ubicacion="Estante B-2 / Piso 2",
        )

    def test_catalogo_publico_nested_y_hateoas(self):
        resp = self.client.get("/api/libros/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)
        first = resp.data["results"][0]
        self.assertIn("url", first)
        self.assertIn("autor", first)
        self.assertEqual(first["autor"]["nombre"], "Thomas Cormen")
        self.assertTrue(first["disponible"])

    def test_filtros_busqueda_y_ordenamiento(self):
        resp = self.client.get("/api/libros/?categoria=ingenieria&año__gte=2020&disponible=true")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

        resp_search = self.client.get("/api/libros/?search=algoritmos&ordering=-año")
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_search.data["results"][0]["titulo"], "Algoritmos en Python")

    def test_permisos_crud_libros(self):
        payload = {
            "isbn": "978-0000000003",
            "titulo": "Nuevo Libro",
            "autor_id": self.autor.id,
            "editorial": "O'Reilly",
            "anio": 2024,
            "categoria": "ingenieria",
            "stock": 5,
            "ubicacion": "Estante C-1 / Piso 1",
        }
        # Estudiante no puede crear
        self.client.force_authenticate(user=self.estudiante)
        self.assertEqual(self.client.post("/api/libros/", payload).status_code, status.HTTP_403_FORBIDDEN)

        # Bibliotecario puede crear pero no eliminar
        self.client.force_authenticate(user=self.biblio)
        created = self.client.post("/api/libros/", payload)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        new_id = created.data["id"]
        self.assertEqual(self.client.delete(f"/api/libros/{new_id}/").status_code, status.HTTP_403_FORBIDDEN)

        # Admin puede eliminar
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.delete(f"/api/libros/{new_id}/").status_code, status.HTTP_204_NO_CONTENT)

    def test_prestamo_validaciones_limite_5_y_devolucion(self):
        self.client.force_authenticate(user=self.biblio)
        # Stock agotado falla
        resp_no_stock = self.client.post(
            "/api/prestamos/",
            {
                "usuario": self.estudiante.id,
                "libro": self.libro_agotado.id,
                "fecha_devolucion": (date.today() + timedelta(days=7)).isoformat(),
            },
        )
        self.assertEqual(resp_no_stock.status_code, status.HTTP_400_BAD_REQUEST)

        # Crear 5 préstamos activos directos
        for i in range(5):
            l = Libro.objects.create(
                isbn=f"978-999000000{i}",
                titulo=f"Libro Límite {i}",
                autor=self.autor,
                editorial="UNCP",
                anio=2022,
                categoria="ingenieria",
                stock=2,
                ubicacion="Estante A",
            )
            Prestamo.objects.create(
                usuario=self.estudiante,
                libro=l,
                fecha_devolucion=date.today() + timedelta(days=5),
                estado="activo",
            )

        # El sexto préstamo es rechazado por el permiso PuedeCrearPrestamo
        resp_6 = self.client.post(
            "/api/prestamos/",
            {
                "usuario": self.estudiante.id,
                "libro": self.libro.id,
                "fecha_devolucion": (date.today() + timedelta(days=7)).isoformat(),
            },
        )
        self.assertEqual(resp_6.status_code, status.HTTP_403_FORBIDDEN)

        # Devolver un préstamo repone stock
        prestamo = Prestamo.objects.filter(usuario=self.estudiante).first()
        stock_antes = prestamo.libro.stock
        resp_dev = self.client.post(f"/api/prestamos/{prestamo.id}/devolver/")
        self.assertEqual(resp_dev.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_dev.data["estado"], "devuelto")
        prestamo.libro.refresh_from_db()
        self.assertEqual(prestamo.libro.stock, stock_antes + 1)

    def test_prestamo_vencido_calcula_multa(self):
        p = Prestamo.objects.create(
            usuario=self.estudiante,
            libro=self.libro,
            fecha_prestamo=date.today() - timedelta(days=10),
            fecha_devolucion=date.today() - timedelta(days=3),
            estado="vencido",
        )
        self.assertEqual(p.multa, Decimal("6.00"))
        self.client.force_authenticate(user=self.biblio)
        resp = self.client.get("/api/prestamos/vencidos/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_usuario_perfil_y_permisos(self):
        self.client.force_authenticate(user=self.estudiante)
        resp = self.client.get("/api/usuarios/perfil/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "est_test")
        # Estudiante no puede listar todos los usuarios
        self.assertEqual(self.client.get("/api/usuarios/").status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.get("/api/usuarios/").status_code, status.HTTP_200_OK)

    def test_token_auth_y_documentacion_openapi(self):
        token_resp = self.client.post(
            "/api/auth/token/",
            {"username": "est_test", "password": "pass"},
        )
        self.assertEqual(token_resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", token_resp.data)
        self.assertEqual(self.client.get("/api/schema/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/docs/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/redoc/").status_code, status.HTTP_200_OK)

    def test_throttling_429(self):
        cache.clear()
        for _ in range(20):
            resp = self.client.get("/api/libros/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp_429 = self.client.get("/api/libros/")
        self.assertEqual(resp_429.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
