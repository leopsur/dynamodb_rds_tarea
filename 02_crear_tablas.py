import os
import pymysql
import boto3
from dotenv import load_dotenv

load_dotenv()

def obtener_endpoint_rds():
    rds_client = boto3.client(
        'rds',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION")
    )
    response = rds_client.describe_db_instances(DBInstanceIdentifier=os.getenv("DB_INSTANCE_ID"))
    return response['DBInstances'][0]['Endpoint']['Address']

def funcionalidad_2_crear_tablas(db_host=None):
    print("\n" + "="*80)
    print("EJECUTANDO FUNCIONALIDAD 2: CREACIÓN DE TABLAS E INSERCIÓN DE DATOS")
    print("Explicación: Crea las 10 tablas del diagrama ER de ActivityLeo e inserta datos iniciales.")
    print("="*80)

    if not db_host:
        db_host = obtener_endpoint_rds()

    # Tablas ordenadas por jerarquía de claves foráneas (FK)
    sql_tablas = [
        """
        CREATE TABLE IF NOT EXISTS Categorias_Interes (
            id_categoria INT AUTO_INCREMENT PRIMARY KEY,
            nombre_categoria VARCHAR(60) NOT NULL,
            descripcion VARCHAR(255)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Alumnos (
            id_alumno INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            curso VARCHAR(30) NOT NULL,
            fecha_nacimiento DATE NOT NULL,
            correo_institucional VARCHAR(150) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Vecinos (
            id_vecino INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            codigo_postal VARCHAR(10) NOT NULL,
            rango_edad VARCHAR(20) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Espacios_disponibles (
            id_espacio INT AUTO_INCREMENT PRIMARY KEY,
            nombre_espacio VARCHAR(100) NOT NULL,
            capacidad_maxima INT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Preferencias_Alumnos (
            id_preferencia INT AUTO_INCREMENT PRIMARY KEY,
            id_alumno INT NOT NULL,
            id_categoria INT NOT NULL,
            nivel_interes INT NOT NULL,
            FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
            FOREIGN KEY (id_categoria) REFERENCES Categorias_Interes(id_categoria) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Preferencias_Vecinos (
            id_preferencia_vec INT AUTO_INCREMENT PRIMARY KEY,
            id_vecino INT NOT NULL,
            id_categoria INT NOT NULL,
            frecuencia_deseada VARCHAR(20) NOT NULL,
            FOREIGN KEY (id_vecino) REFERENCES Vecinos(id_vecino) ON DELETE CASCADE,
            FOREIGN KEY (id_categoria) REFERENCES Categorias_Interes(id_categoria) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Tendencias_Redes (
            id_tendencia INT AUTO_INCREMENT PRIMARY KEY,
            id_categoria INT NOT NULL,
            palabra_clave VARCHAR(100) NOT NULL,
            volumen_busquedas INT NOT NULL,
            FOREIGN KEY (id_categoria) REFERENCES Categorias_Interes(id_categoria) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Propuestas_actividades (
            id_propuesta INT AUTO_INCREMENT PRIMARY KEY,
            id_categoria INT NOT NULL,
            titulo_propuesta VARCHAR(200) NOT NULL,
            origen VARCHAR(20) NOT NULL,
            FOREIGN KEY (id_categoria) REFERENCES Categorias_Interes(id_categoria) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Votaciones (
            id_voto INT AUTO_INCREMENT PRIMARY KEY,
            id_propuesta INT NOT NULL,
            id_alumno INT NULL,
            id_vecino INT NULL,
            FOREIGN KEY (id_propuesta) REFERENCES Propuestas_actividades(id_propuesta) ON DELETE CASCADE,
            FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
            FOREIGN KEY (id_vecino) REFERENCES Vecinos(id_vecino) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Actividades_finales (
            id_actividad INT AUTO_INCREMENT PRIMARY KEY,
            id_propuesta INT NOT NULL,
            id_espacio INT NOT NULL,
            horario_fijo DATETIME NOT NULL,
            FOREIGN KEY (id_propuesta) REFERENCES Propuestas_actividades(id_propuesta) ON DELETE CASCADE,
            FOREIGN KEY (id_espacio) REFERENCES Espacios_disponibles(id_espacio) ON DELETE CASCADE
        );
        """
    ]

    sql_datos = [
        """INSERT INTO Categorias_Interes (nombre_categoria, descripcion) VALUES
        ('Tecnología y Robótica', 'Talleres de programación, diseño 3D y electrónica creativa'),
        ('Gaming y Esports', 'Torneos de videojuegos, desarrollo indie y creación de contenido'),
        ('Deporte Urbano', 'Actividades físicas al aire libre, baloncesto 3x3 y calistenia'),
        ('Arte y Cultura', 'Teatro, música moderna, fotografía y muralismo vecinal');""",

        """INSERT INTO Alumnos (nombre, curso, fecha_nacimiento, correo_institucional) VALUES
        ('Lucas Pérez', '3º ESO A', '2011-05-14', 'lucas.perez@instituto.edu'),
        ('María Gómez', '2º Bachillerato B', '2009-09-22', 'maria.gomez@instituto.edu'),
        ('Elena Sánchez', '2º ESO C', '2012-02-10', 'elena.sanchez@instituto.edu'),
        ('Diego Morales', '4º ESO A', '2010-11-30', 'diego.morales@instituto.edu');""",

        """INSERT INTO Vecinos (nombre, codigo_postal, rango_edad) VALUES
        ('Carlos Ruiz', '41001', '30-40 años'),
        ('Javier Fernández', '41002', '25-30 años'),
        ('Ana Martínez', '41001', '40-50 años');""",

        """INSERT INTO Espacios_disponibles (nombre_espacio, capacidad_maxima) VALUES
        ('Aula de Informática 1', 25),
        ('Salón de Actos', 120),
        ('Pista Polideportiva Exterior', 60),
        ('Sala Multiusos Centro Juvenil', 40);""",

        """INSERT INTO Preferencias_Alumnos (id_alumno, id_categoria, nivel_interes) VALUES
        (1, 1, 5),
        (1, 2, 4),
        (2, 2, 5),
        (3, 1, 5),
        (4, 3, 4);""",

        """INSERT INTO Preferencias_Vecinos (id_vecino, id_categoria, frecuencia_deseada) VALUES
        (1, 3, 'Semanal'),
        (2, 1, 'Quincenal'),
        (3, 4, 'Mensual');""",

        """INSERT INTO Tendencias_Redes (id_categoria, palabra_clave, volumen_busquedas) VALUES
        (1, 'Impresión 3D', 1450),
        (2, 'Torneo Valorant', 2300),
        (3, 'Baloncesto 3x3', 980),
        (4, 'Fotografía móvil', 760);""",

        """INSERT INTO Propuestas_actividades (id_categoria, titulo_propuesta, origen) VALUES
        (1, 'Taller de Diseño e Impresión 3D', 'Encuesta Alumnos'),
        (2, 'Torneo Intercentros Gaming & Esports', 'Redes Sociales'),
        (3, 'Liga de Baloncesto Urbano 3x3', 'Buzón Vecinal'),
        (4, 'Taller de Teatro e Improvisación', 'Centro Juvenil');""",

        """INSERT INTO Votaciones (id_propuesta, id_alumno, id_vecino) VALUES
        (1, 1, NULL),
        (1, 3, NULL),
        (1, NULL, 2),
        (2, 1, NULL),
        (2, 2, NULL),
        (3, 4, NULL),
        (3, NULL, 1),
        (4, NULL, 3);""",

        """INSERT INTO Actividades_finales (id_propuesta, id_espacio, horario_fijo) VALUES
        (1, 1, '2026-11-20 17:00:00'),
        (2, 2, '2026-11-21 18:00:00'),
        (3, 3, '2026-11-22 11:00:00');"""
    ]

    connection = pymysql.connect(
        host=db_host,
        user=os.getenv("DB_ADMIN_USER"),
        password=os.getenv("DB_ADMIN_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        autocommit=True
    )

    cursor = connection.cursor()

    for query in sql_tablas:
        cursor.execute(query)
    print("[ÉXITO] Las 10 tablas del modelo ER de ActivityLeo se han creado correctamente.")

    cursor.execute("SELECT COUNT(*) FROM Categorias_Interes;")
    if cursor.fetchone()[0] == 0:
        for data_query in sql_datos:
            cursor.execute(data_query)
        print("[ÉXITO] Datos iniciales insertados correctamente en todas las tablas.")
    else:
        print("[INFO] Las tablas ya contenían datos previamente.")

    cursor.close()
    connection.close()

if __name__ == "__main__":
    funcionalidad_2_crear_tablas()