import os
import json
from datetime import datetime, date
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr
import pymysql
from dotenv import load_dotenv

# Cargar credenciales ocultas desde .env
load_dotenv()

session_kwargs = {
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
    "region_name": os.getenv("AWS_REGION", "us-east-1"),
}

# Nombres de las tablas en DynamoDB
TABLA_DYNAMO_ESPACIOS = "ActivityLeo_Espacios"
TABLA_DYNAMO_PREFERENCIAS = "ActivityLeo_Preferencias"
TABLA_DYNAMO_PROPUESTAS = "ActivityLeo_Propuestas"

ARCHIVO_JSON_FINAL = "activityleo_datos_unificados.json"


def limpiar_tipos(obj):
    """Convierte Decimal, datetime y date a tipos estándar serializables en JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError(f"Tipo no serializable: {type(obj)}")


def obtener_endpoint_rds():
    """Obtiene el Endpoint de la instancia RDS desde .env o mediante AWS boto3."""
    if os.getenv("DB_HOST"):
        return os.getenv("DB_HOST")
    rds_client = boto3.client("rds", **session_kwargs)
    response = rds_client.describe_db_instances(
        DBInstanceIdentifier=os.getenv("DB_INSTANCE_ID")
    )
    return response["DBInstances"][0]["Endpoint"]["Address"]


# ==============================================================================
# FUNCIONALIDAD 1: EXTRAER INFORMACIÓN FILTRADA DE AWS RDS (MYSQL)
# ==============================================================================
def f1_obtener_datos_rds_filtrados():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 1: CONSULTA CON FILTROS EN AWS RDS (MYSQL)")
    print("Qué hace: Se conecta a la base de datos relacional 'activityleo_db' y extrae:")
    print("  1) Propuestas originadas en encuestas de alumnos o redes sociales.")
    print("  2) Actividades finales asignadas a espacios con capacidad >= 25 personas.")
    print("  3) Preferencias de alumnos con nivel de interés alto (>= 4).")
    print("=" * 85)

    db_host = obtener_endpoint_rds()

    connection = pymysql.connect(
        host=db_host,
        user=os.getenv("DB_ADMIN_USER"),
        password=os.getenv("DB_ADMIN_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
    )

    cursor = connection.cursor()

    # Consulta filtrada 1: Propuestas y conteo de votos según origen
    cursor.execute("""
        SELECT 
            p.id_propuesta,
            p.titulo_propuesta,
            c.nombre_categoria,
            p.origen,
            COUNT(v.id_voto) AS votos_registrados
        FROM Propuestas_actividades p
        JOIN Categorias_Interes c ON p.id_categoria = c.id_categoria
        LEFT JOIN Votaciones v ON p.id_propuesta = v.id_propuesta
        WHERE p.origen IN ('Encuesta Alumnos', 'Redes Sociales')
        GROUP BY p.id_propuesta, p.titulo_propuesta, c.nombre_categoria, p.origen
        ORDER BY votos_registrados DESC;
    """)
    propuestas_rds = cursor.fetchall()

    # Consulta filtrada 2: Actividades finales confirmadas en espacios amplios
    cursor.execute("""
        SELECT 
            af.id_actividad,
            p.titulo_propuesta,
            e.nombre_espacio,
            e.capacidad_maxima,
            af.horario_fijo
        FROM Actividades_finales af
        JOIN Propuestas_actividades p ON af.id_propuesta = p.id_propuesta
        JOIN Espacios_disponibles e ON af.id_espacio = e.id_espacio
        WHERE e.capacidad_maxima >= 25
        ORDER BY af.horario_fijo ASC;
    """)
    actividades_rds = cursor.fetchall()

    # Consulta filtrada 3: Alumnos con alto interés en categorías
    cursor.execute("""
        SELECT 
            a.nombre AS alumno,
            a.curso,
            c.nombre_categoria,
            pa.nivel_interes
        FROM Preferencias_Alumnos pa
        JOIN Alumnos a ON pa.id_alumno = a.id_alumno
        JOIN Categorias_Interes c ON pa.id_categoria = c.id_categoria
        WHERE pa.nivel_interes >= 4
        ORDER BY pa.nivel_interes DESC;
    """)
    preferencias_rds = cursor.fetchall()

    cursor.close()
    connection.close()

    resultado_rds = {
        "propuestas_filtradas": propuestas_rds,
        "actividades_espacios_amplios": actividades_rds,
        "preferencias_interes_alto": preferencias_rds,
    }

    print("\n[RESULTADO OBTENIDO DESDE RDS]:")
    print(json.dumps(resultado_rds, indent=4, ensure_ascii=False, default=limpiar_tipos))
    return resultado_rds


# ==============================================================================
# FUNCIONALIDAD 2: EXTRAER INFORMACIÓN FILTRADA DE AWS DYNAMODB
# ==============================================================================
def f2_obtener_datos_dynamodb_filtrados():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 2: CONSULTA CON FILTROS EN AWS DYNAMODB")
    print("Qué hace: Escanea las 3 tablas NoSQL de DynamoDB aplicando FilterExpression:")
    print("  1) Espacios disponibles con capacidad >= 20.")
    print("  2) Preferencias de perfil 'alumno' con nivel_interes >= 4.")
    print("  3) Propuestas en estado 'Aprobada' con total_votos >= 40.")
    print("=" * 85)

    dynamodb_resource = boto3.resource("dynamodb", **session_kwargs)

    # Filtro 1 en DynamoDB: Espacios disponibles
    espacios_dynamo = dynamodb_resource.Table(TABLA_DYNAMO_ESPACIOS).scan(
        FilterExpression=Attr("disponible").eq(True) & Attr("capacidad").gte(20)
    )["Items"]

    # Filtro 2 en DynamoDB: Preferencias de alumnos con alto interés
    preferencias_dynamo = dynamodb_resource.Table(TABLA_DYNAMO_PREFERENCIAS).scan(
        FilterExpression=Attr("perfil").eq("alumno") & Attr("nivel_interes").gte(4)
    )["Items"]

    # Filtro 3 en DynamoDB: Propuestas aprobadas con alta votación
    propuestas_dynamo = dynamodb_resource.Table(TABLA_DYNAMO_PROPUESTAS).scan(
        FilterExpression=Attr("estado").eq("Aprobada") & Attr("total_votos").gte(40)
    )["Items"]

    resultado_dynamo = {
        "espacios_disponibles": espacios_dynamo,
        "preferencias_alumnos": preferencias_dynamo,
        "propuestas_aprobadas": propuestas_dynamo,
    }

    print("\n[RESULTADO OBTENIDO DESDE DYNAMODB]:")
    print(json.dumps(resultado_dynamo, indent=4, ensure_ascii=False, default=limpiar_tipos))
    return resultado_dynamo


# ==============================================================================
# FUNCIONALIDAD 3: UNIR AMBAS FUENTES Y CREAR ARCHIVO JSON ÚNICO
# ==============================================================================
def f3_unificar_y_guardar_json(datos_rds, datos_dynamodb):
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 3: UNIFICACIÓN Y EXPORTACIÓN A ARCHIVO JSON ÚNICO")
    print(f"Qué hace: Combina los registros filtrados de RDS y DynamoDB en una estructura")
    print(f"          unificada de ActivityLeo y la guarda en '{ARCHIVO_JSON_FINAL}'.")
    print("=" * 85)

    # Normalizar tipos antes de consolidar
    rds_limpio = json.loads(json.dumps(datos_rds, default=limpiar_tipos))
    dynamo_limpio = json.loads(json.dumps(datos_dynamodb, default=limpiar_tipos))

    documento_unificado = {
        "proyecto": "ActivityLeo - Plataforma Big Data Comunitaria",
        "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resumen_integracion": {
            "total_registros_rds": (
                len(rds_limpio["propuestas_filtradas"])
                + len(rds_limpio["actividades_espacios_amplios"])
                + len(rds_limpio["preferencias_interes_alto"])
            ),
            "total_registros_dynamodb": (
                len(dynamo_limpio["espacios_disponibles"])
                + len(dynamo_limpio["preferencias_alumnos"])
                + len(dynamo_limpio["propuestas_aprobadas"])
            ),
        },
        "catalogo_unificado": {
            "propuestas_destacadas": {
                "origen_rds_relacional": rds_limpio["propuestas_filtradas"],
                "origen_dynamodb_nosql": dynamo_limpio["propuestas_aprobadas"],
            },
            "espacios_y_planificacion": {
                "calendario_confirmado_rds": rds_limpio["actividades_espacios_amplios"],
                "disponibilidad_tiempo_real_dynamodb": dynamo_limpio["espacios_disponibles"],
            },
            "segmentacion_intereses": {
                "alumnos_rds": rds_limpio["preferencias_interes_alto"],
                "interacciones_dynamodb": dynamo_limpio["preferencias_alumnos"],
            },
        },
    }

    # Escribir el archivo JSON único en disco
    with open(ARCHIVO_JSON_FINAL, "w", encoding="utf-8") as archivo:
        json.dump(documento_unificado, archivo, indent=4, ensure_ascii=False)

    print(f"\n[ÉXITO] Archivo '{ARCHIVO_JSON_FINAL}' creado correctamente en la carpeta actual.")
    print("\n[CONTENIDO DEL ARCHIVO JSON UNIFICADO]:")
    print(json.dumps(documento_unificado, indent=4, ensure_ascii=False))


# ==============================================================================
# BLOQUE PRINCIPAL DE EJECUCIÓN
# ==============================================================================
if __name__ == "__main__":
    print("=" * 85)
    print(" INICIANDO INTEGRACIÓN DE DATOS RDS + DYNAMODB - PROYECTO ACTIVITYLEO")
    print("=" * 85)

    datos_desde_rds = f1_obtener_datos_rds_filtrados()
    datos_desde_dynamodb = f2_obtener_datos_dynamodb_filtrados()
    f3_unificar_y_guardar_json(datos_desde_rds, datos_desde_dynamodb)

    print("\n" + "=" * 85)
    print(" [PROCESO COMPLETADO] TODOS LOS DATOS SE HAN UNIFICADO SIN ERRORES.")
    print("=" * 85)