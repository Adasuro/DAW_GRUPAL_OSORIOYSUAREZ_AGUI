# Práctica Grupal Semana 13: Diseño de APIs RESTful con Django REST Framework

**Universidad Nacional del Centro del Perú (UNCP)** — Facultad de Ingeniería de Sistemas  
**Asignatura:** Desarrollo de Aplicaciones Web (IS093A)  
**Integrantes:**
- **Suárez Román, Arlette D'alessandra** (`dev/integrante-1`)
- **Osorio Mallqui, José Pablo** (`dev/integrante-2`)

---

## Arquitectura General del Repositorio

El repositorio implementa de manera modular **ambos casos de estudio** exigidos en la guía práctica:

```text
DAW_GRUPAL_OSORIOYSUAREZ_AGUI/
├── .github/workflows/ci.yml                 # Pipeline CI con pruebas y coverage > 80%
├── .gitignore                               # Excluye venv/, db.sqlite3, logs/, __pycache__/
├── requirements.txt                         # Dependencias DRF, Spectacular, SimpleJWT, Filters, CORS
├── README.md                                # Documentación principal
├── caso1_biblioteca/                        # CASO 1: Biblioteca Central UNCP
│   ├── manage.py
│   ├── populate_data.py                     # Genera 14 usuarios, 15 autores, 55 libros, 35 préstamos
│   ├── postman_collection_biblioteca.json   # Colección Postman exportada
│   ├── config/                              # settings.py, urls.py, wsgi.py
│   └── biblioteca/                          # models, serializers, permissions, throttles, filters, pagination, views, tests
└── caso2_ecommerce/                         # CASO 2: TecnoMarket Perú E-Commerce
    ├── manage.py
    ├── populate_data.py                     # Genera 22 usuarios, 110 productos, 55 órdenes, 110 reseñas
    ├── postman_collection_ecommerce.json    # Colección Postman exportada
    ├── config/                              # settings.py, urls.py, wsgi.py
    └── ecommerce/                           # models, serializers, permissions, throttles, filters, pagination, views, tests
```

---

## Instrucciones de Instalación Paso a Paso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Adasuro/DAW_GRUPAL_OSORIOYSUAREZ_AGUI.git
   cd DAW_GRUPAL_OSORIOYSUAREZ_AGUI
   ```

2. **Crear y activar entorno virtual:**
   ```bash
   python -m venv .venv
   # En Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # En Linux/macOS:
   source .venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar Caso 1 (Biblioteca Central UNCP — puerto 8000):**
   ```bash
   cd caso1_biblioteca
   python manage.py migrate
   python populate_data.py
   python manage.py runserver 8000
   ```
   - Swagger UI: `http://127.0.0.1:8000/api/docs/`
   - ReDoc: `http://127.0.0.1:8000/api/redoc/`

5. **Ejecutar Caso 2 (TecnoMarket Perú — puerto 8001):**
   ```bash
   cd caso2_ecommerce
   python manage.py migrate
   python populate_data.py
   python manage.py runserver 8001
   ```
   - Swagger UI: `http://127.0.0.1:8001/api/docs/`
   - ReDoc: `http://127.0.0.1:8001/api/redoc/`

---

## Lista de Endpoints Principales con Ejemplos

### Caso 1: Biblioteca Central UNCP
| Método | Endpoint | Descripción | Permisos |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/token/` | Obtener token DRF | Público |
| `GET` | `/api/libros/` | Listar libros paginados (20/pág) con HATEOAS y autor anidado | Público |
| `GET` | `/api/libros/?categoria=ingenieria&año__gte=2020&disponible=true` | Filtrado avanzado | Público |
| `GET` | `/api/libros/?search=algoritmos&ordering=-año` | Búsqueda y ordenamiento dinámico | Público |
| `POST` | `/api/libros/` | Crear libro | Admin / Bibliotecario |
| `DELETE` | `/api/libros/{id}/` | Eliminar libro | Solo Admin |
| `POST` | `/api/prestamos/` | Registrar préstamo (valida stock y máx. 5 activos) | Bibliotecario / Admin |
| `POST` | `/api/prestamos/{id}/devolver/` | Marcar devolución y reponer stock (`@action`) | Bibliotecario / Admin |
| `GET` | `/api/prestamos/vencidos/` | Listar préstamos vencidos con multa S/ 2.00/día (`@action`) | Bibliotecario / Admin |
| `GET` | `/api/usuarios/perfil/` | Perfil privado del usuario autenticado (`@action`) | Autenticado |

**Ejemplo de respuesta `GET /api/libros/1/`:**
```json
{
  "id": 1,
  "url": "http://127.0.0.1:8000/api/libros/1/",
  "isbn": "978-612-1000-0",
  "titulo": "Introduction to Algorithms",
  "autor": {
    "id": 1,
    "nombre": "Thomas H. Cormen",
    "nacionalidad": "Estadounidense",
    "biografia": "Coautor de Introduction to Algorithms..."
  },
  "editorial": "MIT Press",
  "anio": 2022,
  "categoria": "ingenieria",
  "stock": 8,
  "disponible": true,
  "ubicacion": "Estante A-10 / Piso 1"
}
```

### Caso 2: TecnoMarket Perú E-Commerce
| Método | Endpoint | Descripción | Permisos |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/token/` | Token DRF estándar | Público |
| `POST` | `/api/auth/jwt/token/` | Token JWT (`access` + `refresh`) para mobile | Público |
| `GET` | `/api/productos/` | Catálogo paginado (24/pág) con categoría anidada y HATEOAS | Público |
| `GET` | `/api/productos/?categoria=laptops&marca=dell&precio_min=500&precio_max=2000` | Filtros por categoría, marca y rango | Público |
| `GET` | `/api/productos/{id}/reseñas/` | Reseñas de un producto (`@action`) | Público |
| `GET` | `/api/carrito/` | Ver carrito activo con subtotal, IGV y descuento | Cliente autenticado |
| `POST` | `/api/carrito/agregar/` | Agregar producto validando stock (`@action`) | Propietario |
| `POST` | `/api/carrito/checkout/` | Convertir carrito en orden (Throttle `10/hour`) | Propietario |
| `POST` | `/api/ordenes/{id}/cancelar/` | Cancelar orden pendiente y reponer stock (`@action`) | Propietario / Admin |
| `GET` | `/api/ordenes/mis-ordenes/` | Historial de órdenes con snapshot de precio | Autenticado |
| `POST` | `/api/reseñas/` | Publicar reseña (solo compradores verificados) | Comprador verificado |

---

## Decisiones de Diseño Documentadas

1. **Separación en dos proyectos DRF independientes (`caso1_biblioteca` y `caso2_ecommerce`):** Evita colisiones en rutas raíz (`/api/docs/`, `/api/redoc/`) y permite configurar `PAGE_SIZE` (20 vs 24), tasas de `Throttling` (`100/hour` vs `60/hour`) y orígenes `CORS` específicos para cada dominio institucional y comercial.
2. **Optimización de consultas (`select_related` / `prefetch_related` / `annotate`):** Se eliminó el problema N+1 queries al serializar autores, categorías, ítems de orden y cálculos de `rating_promedio`.
3. **Inmutabilidad de precios en órdenes (`OrdenItem` snapshot):** Al ejecutar checkout se almacena `producto_nombre_snapshot` y `precio_unitario_snapshot`, garantizando integridad contable aunque el vendedor actualice el precio posteriormente.
4. **Seguridad y Rate Limiting con auditoría:** Se implementaron `TokenAuthentication`, `JWTAuthentication`, `CORS_ALLOWED_ORIGINS`, permisos granulares (`PuedeCrearPrestamo`, `EsCompradorVerificado`, `PuedeVender`) y middleware de auditoría que registra eventos HTTP `429`.
