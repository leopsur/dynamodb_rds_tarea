import os
import json
import pymysql
import boto3
from datetime import datetime, date
from decimal import Decimal
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

def funcionalidad_3_consultas_json(db_host=None):
    print("\n" + "="*80)
    print("EJECUTANDO FUNCIONALIDAD 3: CONSULTAS ANALÍTICAS Y SALIDA EN FORMATO JSON")
    print("Explicación: Ejecuta 3 consultas sobre las tablas de ActivityLeo y las muestra en JSON.")
    print("="*80)

    if not db_host:
        db_host = obtener_endpoint_rds()

    consultas = {
        "Consulta_1_Analitica_Descriptiva_Votaciones": {
            "descripcion": "Cuenta los votos totales por propuesta de actividad desglosando participación de alumnos y vecinos.",
            "sql": """
                SELECT 
                    p.titulo_propuesta,
                    c.nombre_categoria,
                    p.origen,
                    COUNT(v.id_voto) AS total_votos,
                    COUNT(v.id_alumno) AS votos_alumnos,
                    COUNT(v.id_vecino) AS votos_vecinos
                FROM Propuestas_actividades p
                JOIN Categorias_Interes c ON p.id_categoria = c.id_categoria
                LEFT JOIN Votaciones v ON p.id_propuesta = v.id_propuesta
                GROUP BY p.id_propuesta, p.titulo_propuesta, c.nombre_categoria, p.origen
                ORDER BY total_votos DESC;
            """
        },
        "Consulta_2_Analitica_Predictiva_Tendencias": {
            "descripcion": "Cruza el interés medio de los alumnos con el volumen de búsquedas en redes sociales por categoría.",
            "sql": """
                SELECT 
                    c.nombre_categoria,
                    ROUND(AVG(pa.nivel_interes), 2) AS interes_medio_alumnos,
                    tr.palabra_clave AS tendencia_destacada,
                    tr.volumen_busquedas
                FROM Categorias_Interes c
                JOIN Preferencias_Alumnos pa ON c.id_categoria = pa.id_categoria
                JOIN Tendencias_Redes tr ON c.id_categoria = tr.id_categoria
                GROUP BY c.id_categoria, c.nombre_categoria, tr.palabra_clave, tr.volumen_busquedas
                ORDER BY tr.volumen_busquedas DESC;
            """
        },
        "Consulta_3_Analitica_Prescriptiva_Espacios": {
            "descripcion": "Muestra las actividades finales confirmadas, su espacio asignado, aforo máximo y fecha programada.",
            "sql": """
                SELECT 
                    af.id_actividad,
                    p.titulo_propuesta,
                    e.nombre_espacio,
                    e.capacidad_maxima,
                    af.horario_fijo
                FROM Actividades_finales af
                JOIN Propuestas_actividades p ON af.id_propuesta = p.id_propuesta
                JOIN Espacios_disponibles e ON af.id_espacio = e.id_espacio
                ORDER BY af.horario_fijo ASC;
            """
        }
    }

    connection = pymysql.connect(
        host=db_host,
        user=os.getenv("DB_ADMIN_USER"),
        password=os.getenv("DB_ADMIN_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

    cursor = connection.cursor()

    for clave, info in consultas.items():
        print(f"\n---> Ejecutando {clave}")
        print(f"Propósito: {info['descripcion']}")

        cursor.execute(info['sql'])
        resultados = cursor.fetchall()

        for fila in resultados:
            for k, v in fila.items():
                if isinstance(v, (datetime, date)):
                    fila[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(v, Decimal):
                    fila[k] = float(v)

        json_output = json.dumps({
            "nombre_consulta": clave,
            "explicacion": info['descripcion'],
            "total_registros": len(resultados),
            "resultados": resultados
        }, indent=4, ensure_ascii=False)

        print("\n[RESULTADO EN FORMATO JSON]:")
        print(json_output)
        print("-" * 80)

    cursor.close()
    connection.close()

if __name__ == "__main__":
    funcionalidad_3_consultas_json()