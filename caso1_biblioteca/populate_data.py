"""Script para poblar automáticamente la base de datos de Caso 1 (Biblioteca UNCP).
Genera mínimo: 12 usuarios (roles variados), 15 autores, 55 libros y 35 préstamos.
"""
import os
import random
from datetime import date, timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from faker import Faker
from rest_framework.authtoken.models import Token

from biblioteca.models import Autor, Libro, Prestamo, Usuario

fake = Faker("es_ES")
Faker.seed(2026)
random.seed(2026)


def run():
    print("Poblando base de datos de Biblioteca Central UNCP...")
    Prestamo.objects.all().delete()
    Libro.objects.all().delete()
    Autor.objects.all().delete()
    Usuario.objects.all().delete()

    # 1. Usuarios fijos clave para pruebas y Postman
    admin_user = Usuario.objects.create_superuser(
        username="admin_biblio",
        email="admin.biblioteca@uncp.edu.pe",
        password="AdminUNCP2026!",
        nombre="Arlette Suárez Román",
        tipo="administrador",
        carrera="Ingeniería de Sistemas",
        carnet="2022200427L",
        telefono="964100200",
    )
    bibliotecario = Usuario.objects.create_user(
        username="bibliotecario1",
        email="bibliotecario@uncp.edu.pe",
        password="BiblioUNCP2026!",
        nombre="José Pablo Osorio Mallqui",
        tipo="bibliotecario",
        carrera="Ingeniería de Sistemas",
        carnet="BIB-2026-01",
        telefono="964200300",
    )
    estudiante_demo = Usuario.objects.create_user(
        username="estudiante1",
        email="estudiante1@uncp.edu.pe",
        password="EstudUNCP2026!",
        nombre="Lucía Fernández Quispe",
        tipo="estudiante",
        carrera="Ingeniería de Sistemas",
        carnet="2023100112A",
        telefono="964300400",
    )
    docente_demo = Usuario.objects.create_user(
        username="docente1",
        email="docente1@uncp.edu.pe",
        password="DocenUNCP2026!",
        nombre="Dr. Carlos Huamán Vilchez",
        tipo="docente",
        carrera="Ingeniería de Sistemas",
        carnet="DOC-2026-01",
        telefono="964400500",
    )
    externo_demo = Usuario.objects.create_user(
        username="campus_virtual",
        email="integracion@campus.uncp.edu.pe",
        password="CampusUNCP2026!",
        nombre="Campus Virtual UNCP",
        tipo="externo",
        carrera="Plataforma Institucional",
        carnet="EXT-CAMPUS-01",
        telefono="064481060",
    )

    carreras = [
        "Ingeniería de Sistemas",
        "Ingeniería Civil",
        "Ingeniería Mecánica",
        "Arquitectura",
        "Economía",
        "Medicina Humana",
        "Derecho y Ciencias Políticas",
    ]
    usuarios = [admin_user, bibliotecario, estudiante_demo, docente_demo, externo_demo]
    for i in range(1, 10):
        tipo = "docente" if i % 4 == 0 else "estudiante"
        u = Usuario.objects.create_user(
            username=f"usuario_{i}",
            email=f"usuario_{i}@uncp.edu.pe",
            password="UserUNCP2026!",
            nombre=fake.name(),
            tipo=tipo,
            carrera=random.choice(carreras),
            carnet=f"2024{100000 + i}B",
            telefono=f"964{random.randint(100000, 999999)}",
        )
        usuarios.append(u)

    for u in usuarios:
        Token.objects.get_or_create(user=u)

    # 2. Autores realistas
    autores_data = [
        ("Thomas H. Cormen", "Estadounidense", "Coautor de Introduction to Algorithms, profesor en Dartmouth College."),
        ("Robert C. Martin", "Estadounidense", "Ingeniero de software conocido como Uncle Bob, referente en Clean Code."),
        ("Martin Fowler", "Británico", "Autor especializado en arquitectura de software, refactoring y patrones empresariales."),
        ("Andrew S. Tanenbaum", "Estadounidense", "Profesor emérito de ciencias de la computación, autor de Sistemas Operativos Modernos."),
        ("Ian Sommerville", "Británico", "Catedrático de Ingeniería de Software en la Universidad de St Andrews."),
        ("Abraham Silberschatz", "Israelí-Estadounidense", "Autor de Fundamentos de Bases de Datos y Sistemas Operativos."),
        ("Eric Evans", "Estadounidense", "Creador del enfoque Domain-Driven Design (DDD)."),
        ("Aurélien Géron", "Francés", "Especialista en Machine Learning con Scikit-Learn, Keras y TensorFlow."),
        ("N. Gregory Mankiw", "Estadounidense", "Economista de Harvard, autor de Principios de Economía."),
        ("Julio César Tello", "Peruano", "Médico y antropólogo peruano, padre de la arqueología peruana."),
        ("Mario Bunge", "Argentino", "Filósofo y físico teórico reconocido por sus aportes a la epistemología."),
        ("Roger S. Pressman", "Estadounidense", "Referente internacional en Ingeniería del Software: Un enfoque práctico."),
        ("Stuart Russell", "Británico", "Profesor en UC Berkeley, coautor de Inteligencia Artificial: Un enfoque moderno."),
        ("William Stallings", "Estadounidense", "Autor de textos sobre redes de computadoras y seguridad informática."),
        ("Erich Gamma", "Suizo", "Coautor de Design Patterns (Gang of Four) y arquitecto de software."),
    ]
    autores = [
        Autor.objects.create(nombre=n, nacionalidad=nac, biografia=bio)
        for n, nac, bio in autores_data
    ]

    # 3. Libros (55 libros)
    titulos_base = [
        ("Introduction to Algorithms", "ingenieria", "MIT Press", 2022, 0),
        ("Algoritmos y Estructuras de Datos Avanzadas", "ingenieria", "Pearson", 2023, 0),
        ("Clean Code: Manual de estilo para desarrollo ágil", "ingenieria", "Anaya Multimedia", 2021, 1),
        ("Clean Architecture: Guía para la estructura de software", "ingenieria", "Anaya Multimedia", 2020, 1),
        ("Patterns of Enterprise Application Architecture", "ingenieria", "Addison-Wesley", 2019, 2),
        ("Refactoring: Improving the Design of Existing Code", "ingenieria", "Addison-Wesley", 2021, 2),
        ("Sistemas Operativos Modernos", "ingenieria", "Pearson", 2022, 3),
        ("Redes de Computadoras", "ingenieria", "Pearson", 2020, 3),
        ("Ingeniería de Software", "ingenieria", "Pearson", 2021, 4),
        ("Fundamentos de Bases de Datos", "ingenieria", "McGraw-Hill", 2023, 5),
        ("Domain-Driven Design", "ingenieria", "Addison-Wesley", 2018, 6),
        ("Hands-On Machine Learning", "ciencias", "O'Reilly Media", 2024, 7),
        ("Principios de Economía", "economia", "Cengage Learning", 2022, 8),
        ("Macroeconomía Aplicada para Latinoamérica", "economia", "Fondo Editorial", 2021, 8),
        ("Cultura y Civilización Andina", "humanidades", "UNMSM", 2019, 9),
        ("La Ciencia, su Método y su Filosofía", "ciencias", "Siglo XXI", 2020, 10),
        ("Ingeniería del Software: Un enfoque práctico", "ingenieria", "McGraw-Hill", 2023, 11),
        ("Inteligencia Artificial: Un enfoque moderno", "ingenieria", "Pearson", 2022, 12),
        ("Criptografía y Seguridad en Redes", "ingenieria", "Pearson", 2021, 13),
        ("Design Patterns: Elements of Reusable Object-Oriented Software", "ingenieria", "Addison-Wesley", 2018, 14),
    ]

    libros = []
    for idx in range(55):
        if idx < len(titulos_base):
            titulo, cat, edit, anio, aut_idx = titulos_base[idx]
            autor = autores[aut_idx]
        else:
            cat = random.choice(["ingenieria", "ciencias", "humanidades", "medicina", "derecho", "economia"])
            prefijos = {
                "ingenieria": ["Diseño de APIs RESTful", "Arquitectura Cloud", "Algoritmos Paralelos", "Microservicios con Django"],
                "ciencias": ["Física Universitaria", "Cálculo Multivariable", "Estadística Computacional", "Álgebra Lineal"],
                "humanidades": ["Historia del Perú Contemporáneo", "Ética Profesional", "Metodología de la Investigación"],
                "medicina": ["Anatomía Humana", "Fisiología Clínica", "Farmacología Básica"],
                "derecho": ["Derecho Constitucional", "Derecho Administrativo", "Legislación Informática"],
                "economia": ["Econometría Moderna", "Finanzas Corporativas", "Gestión de Proyectos"],
            }
            titulo = f"{random.choice(prefijos[cat])} - Vol. {(idx % 4) + 1} ({idx})"
            edit = random.choice(["Pearson", "McGraw-Hill", "O'Reilly Media", "Fondo Editorial UNCP", "Alfaomega"])
            anio = random.randint(2015, 2026)
            autor = random.choice(autores)

        stock = 0 if idx in (4, 15, 33) else random.randint(2, 12)
        libro = Libro.objects.create(
            isbn=f"978-612-{1000 + idx:04d}-{idx % 9}",
            titulo=titulo,
            autor=autor,
            editorial=edit,
            anio=anio,
            categoria=cat,
            stock=stock,
            ubicacion=f"Estante {chr(65 + (idx % 6))}-{10 + (idx % 20)} / Piso {(idx % 3) + 1}",
        )
        libros.append(libro)

    # 4. Préstamos (35 préstamos: activos, devueltos y vencidos)
    hoy = date.today()
    lectores = [u for u in usuarios if u.tipo in ("estudiante", "docente")]
    libros_con_stock = [l for l in libros if l.stock > 1]

    for i in range(35):
        lector = lectores[i % len(lectores)]
        libro = libros_con_stock[i % len(libros_con_stock)]
        if i < 12:
            # Préstamos activos
            fp = hoy - timedelta(days=random.randint(1, 5))
            fd = hoy + timedelta(days=random.randint(3, 14))
            Prestamo.objects.create(
                usuario=lector,
                libro=libro,
                fecha_prestamo=fp,
                fecha_devolucion=fd,
                estado="activo",
            )
        elif i < 25:
            # Préstamos devueltos
            fp = hoy - timedelta(days=random.randint(15, 40))
            fd = fp + timedelta(days=10)
            fdr = fd - timedelta(days=random.randint(0, 3))
            Prestamo.objects.create(
                usuario=lector,
                libro=libro,
                fecha_prestamo=fp,
                fecha_devolucion=fd,
                fecha_devolucion_real=fdr,
                estado="devuelto",
            )
        else:
            # Préstamos vencidos (generan multa de S/ 2.00 por día)
            retraso = random.randint(2, 9)
            fd = hoy - timedelta(days=retraso)
            fp = fd - timedelta(days=7)
            Prestamo.objects.create(
                usuario=lector,
                libro=libro,
                fecha_prestamo=fp,
                fecha_devolucion=fd,
                estado="vencido",
            )

    print(
        f"Listo: {Usuario.objects.count()} usuarios, {Autor.objects.count()} autores, "
        f"{Libro.objects.count()} libros, {Prestamo.objects.count()} préstamos."
    )


if __name__ == "__main__":
    run()
