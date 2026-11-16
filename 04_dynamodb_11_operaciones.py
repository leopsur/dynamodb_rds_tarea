import os
import json
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeDeserializer
from dotenv import load_dotenv

# Cargar variables de entorno ocultas desde .env
load_dotenv()

# Inicializar cliente (bajo nivel / PartiQL / DDL) y recurso (alto nivel) de DynamoDB
session_kwargs = {
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
    "region_name": os.getenv("AWS_REGION", "us-east-1"),
}

dynamodb_client = boto3.client("dynamodb", **session_kwargs)
dynamodb_resource = boto3.resource("dynamodb", **session_kwargs)
deserializer = TypeDeserializer()

# Nombres de las 3 tablas del proyecto ActivityLeo
TABLA_SIN_INDICE = "ActivityLeo_Espacios"          # Tabla 1: Sin LSI ni GSI
TABLA_CON_LSI = "ActivityLeo_Preferencias"         # Tabla 2: Con Índice Local (LSI)
TABLA_CON_GSI = "ActivityLeo_Propuestas"           # Tabla 3: Con Índice Global (GSI)


def mostrar_json(datos):
    """Convierte Decimals de DynamoDB a int/float y muestra JSON formateado."""
    def convertir_decimal(obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        raise TypeError

    print(json.dumps(datos, indent=4, ensure_ascii=False, default=convertir_decimal))


# ==============================================================================
# FUNCIONALIDADES 1 Y 2: CREAR LAS 3 TABLAS CON SUS ÍNDICES (SIN ÍNDICE, LSI, GSI)
# ==============================================================================
def f1_y_f2_crear_tablas():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDADES 1 Y 2: CREACIÓN DE TABLAS E ÍNDICES EN DYNAMODB")
    print("Qué hace: Crea 3 tablas para ActivityLeo en AWS DynamoDB:")
    print(f"  1) '{TABLA_SIN_INDICE}' -> Sin índice local ni global.")
    print(f"  2) '{TABLA_CON_LSI}' -> Con Índice Secundario Local (LSI_NivelInteres).")
    print(f"  3) '{TABLA_CON_GSI}' -> Con Índice Secundario Global (GSI_CategoriaVotos).")
    print("=" * 85)

    tablas_existentes = dynamodb_client.list_tables()["TableNames"]

    # 1. Tabla sin índice local ni global
    if TABLA_SIN_INDICE not in tablas_existentes:
        dynamodb_client.create_table(
            TableName=TABLA_SIN_INDICE,
            KeySchema=[
                {"AttributeName": "id_espacio", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id_espacio", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        print(f"[ACCIÓN] Creando tabla '{TABLA_SIN_INDICE}' (sin índices)...")

    # 2. Tabla con Índice Secundario Local (LSI)
    # Nota: Un LSI requiere clave primaria compuesta (HASH + RANGE) y comparte el mismo HASH
    if TABLA_CON_LSI not in tablas_existentes:
        dynamodb_client.create_table(
            TableName=TABLA_CON_LSI,
            KeySchema=[
                {"AttributeName": "id_usuario", "KeyType": "HASH"},
                {"AttributeName": "id_categoria", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id_usuario", "AttributeType": "S"},
                {"AttributeName": "id_categoria", "AttributeType": "S"},
                {"AttributeName": "nivel_interes", "AttributeType": "N"}
            ],
            LocalSecondaryIndexes=[
                {
                    "IndexName": "LSI_NivelInteres",
                    "KeySchema": [
                        {"AttributeName": "id_usuario", "KeyType": "HASH"},
                        {"AttributeName": "nivel_interes", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        print(f"[ACCIÓN] Creando tabla '{TABLA_CON_LSI}' con LSI 'LSI_NivelInteres'...")

    # 3. Tabla con Índice Secundario Global (GSI)
    if TABLA_CON_GSI not in tablas_existentes:
        dynamodb_client.create_table(
            TableName=TABLA_CON_GSI,
            KeySchema=[
                {"AttributeName": "id_propuesta", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id_propuesta", "AttributeType": "S"},
                {"AttributeName": "categoria", "AttributeType": "S"},
                {"AttributeName": "total_votos", "AttributeType": "N"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI_CategoriaVotos",
                    "KeySchema": [
                        {"AttributeName": "categoria", "KeyType": "HASH"},
                        {"AttributeName": "total_votos", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        print(f"[ACCIÓN] Creando tabla '{TABLA_CON_GSI}' con GSI 'GSI_CategoriaVotos'...")

    # Esperar a que las 3 tablas estén en estado ACTIVE
    waiter = dynamodb_client.get_waiter("table_exists")
    for nombre_tabla in [TABLA_SIN_INDICE, TABLA_CON_LSI, TABLA_CON_GSI]:
        waiter.wait(TableName=nombre_tabla)

    resultado = {
        "tablas_activas": [TABLA_SIN_INDICE, TABLA_CON_LSI, TABLA_CON_GSI],
        "estado": "ACTIVE"
    }
    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json(resultado)


# ==============================================================================
# FUNCIONALIDAD 3: CREAR TRES REGISTROS EN CADA TABLA
# ==============================================================================
def f3_insertar_tres_registros():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 3: INSERTAR 3 REGISTROS EN CADA TABLA")
    print("Qué hace: Inserta 3 elementos en Espacios, 3 en Preferencias y 3 en Propuestas.")
    print("=" * 85)

    t_espacios = dynamodb_resource.Table(TABLA_SIN_INDICE)
    t_preferencias = dynamodb_resource.Table(TABLA_CON_LSI)
    t_propuestas = dynamodb_resource.Table(TABLA_CON_GSI)

    espacios = [
        {"id_espacio": "ESP-01", "nombre": "Aula Informática 1", "capacidad": 25, "tipo": "Tecnologia", "disponible": True},
        {"id_espacio": "ESP-02", "nombre": "Pista Polideportiva", "capacidad": 60, "tipo": "Deporte", "disponible": True},
        {"id_espacio": "ESP-03", "nombre": "Almacén Antiguo", "capacidad": 10, "tipo": "Almacen", "disponible": False}
    ]
    for item in espacios:
        t_espacios.put_item(Item=item)

    preferencias = [
        {"id_usuario": "USR-01", "id_categoria": "CAT-3D", "nivel_interes": 5, "perfil": "alumno", "zona": "Norte"},
        {"id_usuario": "USR-01", "id_categoria": "CAT-GAMING", "nivel_interes": 4, "perfil": "alumno", "zona": "Norte"},
        {"id_usuario": "USR-02", "id_categoria": "CAT-TEATRO", "nivel_interes": 2, "perfil": "vecino", "zona": "Sur"}
    ]
    for item in preferencias:
        t_preferencias.put_item(Item=item)

    propuestas = [
        {"id_propuesta": "PROP-01", "titulo": "Taller Impresión 3D", "categoria": "Tecnologia", "total_votos": 45, "estado": "Aprobada"},
        {"id_propuesta": "PROP-02", "titulo": "Torneo Esports Viernes", "categoria": "Gaming", "total_votos": 30, "estado": "En_Revision"},
        {"id_propuesta": "PROP-03", "titulo": "Club de Ajedrez", "categoria": "Cultura", "total_votos": 8, "estado": "Descartada"}
    ]
    for item in propuestas:
        t_propuestas.put_item(Item=item)

    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json({
        "insertados_Espacios": len(espacios),
        "insertados_Preferencias": len(preferencias),
        "insertados_Propuestas": len(propuestas)
    })


# ==============================================================================
# FUNCIONALIDAD 4: OBTENER UN REGISTRO DE CADA TABLA
# ==============================================================================
def f4_obtener_un_registro():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 4: OBTENER UN REGISTRO DE CADA TABLA (GET_ITEM)")
    print("Qué hace: Recupera un registro específico mediante su clave primaria en cada tabla.")
    print("=" * 85)

    r1 = dynamodb_resource.Table(TABLA_SIN_INDICE).get_item(
        Key={"id_espacio": "ESP-01"}
    ).get("Item")

    r2 = dynamodb_resource.Table(TABLA_CON_LSI).get_item(
        Key={"id_usuario": "USR-01", "id_categoria": "CAT-3D"}
    ).get("Item")

    r3 = dynamodb_resource.Table(TABLA_CON_GSI).get_item(
        Key={"id_propuesta": "PROP-01"}
    ).get("Item")

    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json({
        TABLA_SIN_INDICE: r1,
        TABLA_CON_LSI: r2,
        TABLA_CON_GSI: r3
    })


# ==============================================================================
# FUNCIONALIDAD 5: ACTUALIZAR UN REGISTRO DE CADA TABLA
# ==============================================================================
def f5_actualizar_un_registro():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 5: ACTUALIZAR UN REGISTRO DE CADA TABLA (UPDATE_ITEM)")
    print("Qué hace: Modifica un atributo en un registro de cada tabla y devuelve el nuevo valor.")
    print("=" * 85)

    u1 = dynamodb_resource.Table(TABLA_SIN_INDICE).update_item(
        Key={"id_espacio": "ESP-01"},
        UpdateExpression="SET capacidad = :nueva_cap",
        ExpressionAttributeValues={":nueva_cap": 30},
        ReturnValues="ALL_NEW"
    )["Attributes"]

    u2 = dynamodb_resource.Table(TABLA_CON_LSI).update_item(
        Key={"id_usuario": "USR-01", "id_categoria": "CAT-3D"},
        UpdateExpression="SET zona = :nueva_zona",
        ExpressionAttributeValues={":nueva_zona": "Centro"},
        ReturnValues="ALL_NEW"
    )["Attributes"]

    u3 = dynamodb_resource.Table(TABLA_CON_GSI).update_item(
        Key={"id_propuesta": "PROP-01"},
        UpdateExpression="SET total_votos = :votos",
        ExpressionAttributeValues={":votos": 50},
        ReturnValues="ALL_NEW"
    )["Attributes"]

    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json({
        TABLA_SIN_INDICE: u1,
        TABLA_CON_LSI: u2,
        TABLA_CON_GSI: u3
    })


# ==============================================================================
# FUNCIONALIDAD 6: ELIMINAR UN REGISTRO DE CADA TABLA
# ==============================================================================
def f6_eliminar_un_registro():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 6: ELIMINAR UN REGISTRO DE CADA TABLA (DELETE_ITEM)")
    print("Qué hace: Elimina el tercer registro de cada tabla ('ESP-03', 'USR-02', 'PROP-03').")
    print("=" * 85)

    d1 = dynamodb_resource.Table(TABLA_SIN_INDICE).delete_item(
        Key={"id_espacio": "ESP-03"},
        ReturnValues="ALL_OLD"
    ).get("Attributes")

    d2 = dynamodb_resource.Table(TABLA_CON_LSI).delete_item(
        Key={"id_usuario": "USR-02", "id_categoria": "CAT-TEATRO"},
        ReturnValues="ALL_OLD"
    ).get("Attributes")

    d3 = dynamodb_resource.Table(TABLA_CON_GSI).delete_item(
        Key={"id_propuesta": "PROP-03"},
        ReturnValues="ALL_OLD"
    ).get("Attributes")

    print("\n[RESULTADO OBTENIDO (REGISTROS ELIMINADOS)]:")
    mostrar_json({
        TABLA_SIN_INDICE: d1,
        TABLA_CON_LSI: d2,
        TABLA_CON_GSI: d3
    })


# ==============================================================================
# FUNCIONALIDAD 7: OBTENER TODOS LOS REGISTROS DE CADA TABLA
# ==============================================================================
def f7_obtener_todos_los_registros():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 7: OBTENER TODOS LOS REGISTROS DE CADA TABLA (SCAN)")
    print("Qué hace: Lista todos los elementos restantes (2 por tabla) en cada tabla.")
    print("=" * 85)

    s1 = dynamodb_resource.Table(TABLA_SIN_INDICE).scan()["Items"]
    s2 = dynamodb_resource.Table(TABLA_CON_LSI).scan()["Items"]
    s3 = dynamodb_resource.Table(TABLA_CON_GSI).scan()["Items"]

    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json({
        TABLA_SIN_INDICE: s1,
        TABLA_CON_LSI: s2,
        TABLA_CON_GSI: s3
    })


# ==============================================================================
# FUNCIONALIDAD 8: SCAN FILTRADO EN CADA TABLA (USANDO ÍNDICE GLOBAL EN LA 3ª)
# ==============================================================================
def f8_scan_filtrado():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 8: SCAN CON FILTRO (Y USO DE GSI EN LA TABLA GLOBAL)")
    print("Qué hace: Aplica un filtro con scan en cada tabla; en Propuestas consulta el GSI.")
    print("=" * 85)

    # Tabla 1: Scan filtrado por capacidad >= 25
    f1 = dynamodb_resource.Table(TABLA_SIN_INDICE).scan(
        FilterExpression=Attr("capacidad").gte(25)
    )["Items"]

    # Tabla 2: Scan filtrado por nivel_interes >= 4
    f2 = dynamodb_resource.Table(TABLA_CON_LSI).scan(
        FilterExpression=Attr("nivel_interes").gte(4)
    )["Items"]

    # Tabla 3 (Global): Scan utilizando el Índice Secundario Global 'GSI_CategoriaVotos'
    f3 = dynamodb_resource.Table(TABLA_CON_GSI).scan(
        IndexName="GSI_CategoriaVotos",
        FilterExpression=Attr("total_votos").gte(30)
    )["Items"]

    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json({
        f"{TABLA_SIN_INDICE} (capacidad >= 25)": f1,
        f"{TABLA_CON_LSI} (nivel_interes >= 4)": f2,
        f"{TABLA_CON_GSI} vía GSI_CategoriaVotos (total_votos >= 30)": f3
    })


# ==============================================================================
# FUNCIONALIDAD 9: ELIMINACIÓN CONDICIONAL (USANDO GSI EN LA TABLA GLOBAL)
# ==============================================================================
def f9_eliminacion_condicional():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 9: ELIMINACIÓN CONDICIONAL EN CADA TABLA")
    print("Qué hace: Elimina un registro solo si cumple una condición. En la tabla global")
    print("          consulta primero el GSI 'GSI_CategoriaVotos' para localizar la clave")
    print("          y ejecuta después el borrado condicional sobre el ítem encontrado.")
    print("=" * 85)

    # 1. Tabla sin índice: Borrar ESP-02 solo si tipo == 'Deporte' y capacidad > 50
    c1 = dynamodb_resource.Table(TABLA_SIN_INDICE).delete_item(
        Key={"id_espacio": "ESP-02"},
        ConditionExpression=Attr("tipo").eq("Deporte") & Attr("capacidad").gt(50),
        ReturnValues="ALL_OLD"
    ).get("Attributes")

    # 2. Tabla con LSI: Borrar CAT-GAMING de USR-01 solo si nivel_interes == 4
    c2 = dynamodb_resource.Table(TABLA_CON_LSI).delete_item(
        Key={"id_usuario": "USR-01", "id_categoria": "CAT-GAMING"},
        ConditionExpression=Attr("nivel_interes").eq(4),
        ReturnValues="ALL_OLD"
    ).get("Attributes")

    # 3. Tabla con GSI: Localizar vía índice global 'GSI_CategoriaVotos' y borrar condicionalmente
    t_propuestas = dynamodb_resource.Table(TABLA_CON_GSI)
    busqueda_gsi = t_propuestas.query(
        IndexName="GSI_CategoriaVotos",
        KeyConditionExpression=Key("categoria").eq("Gaming") & Key("total_votos").lte(35)
    )["Items"]

    propuesta_objetivo = busqueda_gsi[0]
    c3 = t_propuestas.delete_item(
        Key={"id_propuesta": propuesta_objetivo["id_propuesta"]},
        ConditionExpression=Attr("estado").eq("En_Revision"),
        ReturnValues="ALL_OLD"
    ).get("Attributes")

    print("\n[RESULTADO OBTENIDO (ELEMENTOS BORRADOS CONDICIONALMENTE)]:")
    mostrar_json({
        TABLA_SIN_INDICE: c1,
        TABLA_CON_LSI: c2,
        f"{TABLA_CON_GSI} (localizado por GSI_CategoriaVotos)": c3
    })


# ==============================================================================
# FUNCIONALIDAD 10: OBTENER DATOS CON MÚLTIPLES FILTROS APLICADOS
# ==============================================================================
def f10_multiples_filtros():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 10: CONSULTA CON MÚLTIPLES FILTROS EN CADA TABLA")
    print("Qué hace: Combina 3 condiciones simultáneas (AND) mediante FilterExpression.")
    print("=" * 85)

    m1 = dynamodb_resource.Table(TABLA_SIN_INDICE).scan(
        FilterExpression=Attr("tipo").eq("Tecnologia") & Attr("capacidad").gte(20) & Attr("disponible").eq(True)
    )["Items"]

    m2 = dynamodb_resource.Table(TABLA_CON_LSI).scan(
        FilterExpression=Attr("perfil").eq("alumno") & Attr("nivel_interes").eq(5) & Attr("zona").eq("Centro")
    )["Items"]

    m3 = dynamodb_resource.Table(TABLA_CON_GSI).scan(
        FilterExpression=Attr("categoria").eq("Tecnologia") & Attr("total_votos").gte(40) & Attr("estado").eq("Aprobada")
    )["Items"]

    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json({
        TABLA_SIN_INDICE: m1,
        TABLA_CON_LSI: m2,
        TABLA_CON_GSI: m3
    })


# ==============================================================================
# FUNCIONALIDAD 11: UTILIZAR SENTENCIAS PARTIQL EN CADA TABLA
# ==============================================================================
def f11_consultas_partiql():
    print("\n" + "=" * 85)
    print("EJECUTANDO FUNCIONALIDAD 11: CONSULTAS MEDIANTE PARTIQL STATEMENT")
    print("Qué hace: Ejecuta sentencias SQL-like (PartiQL) sobre cada tabla e índices.")
    print("=" * 85)

    def ejecutar_partiql(sentencia):
        respuesta = dynamodb_client.execute_statement(Statement=sentencia)
        return [
            {k: deserializer.deserialize(v) for k, v in item.items()}
            for item in respuesta["Items"]
        ]

    # PartiQL 1: Consulta directa sobre la tabla sin índices
    p1 = ejecutar_partiql(
        f"SELECT * FROM \"{TABLA_SIN_INDICE}\" WHERE id_espacio = 'ESP-01' AND disponible = true"
    )

    # PartiQL 2: Consulta sobre el Índice Secundario Local (LSI)
    p2 = ejecutar_partiql(
        f"SELECT * FROM \"{TABLA_CON_LSI}\".\"LSI_NivelInteres\" WHERE id_usuario = 'USR-01' AND nivel_interes >= 4"
    )

    # PartiQL 3: Consulta sobre el Índice Secundario Global (GSI)
    p3 = ejecutar_partiql(
        f"SELECT * FROM \"{TABLA_CON_GSI}\".\"GSI_CategoriaVotos\" WHERE categoria = 'Tecnologia' AND total_votos >= 40"
    )

    print("\n[RESULTADO OBTENIDO]:")
    mostrar_json({
        f"PartiQL_{TABLA_SIN_INDICE}": p1,
        f"PartiQL_{TABLA_CON_LSI}_LSI": p2,
        f"PartiQL_{TABLA_CON_GSI}_GSI": p3
    })


# ==============================================================================
# EJECUCIÓN PRINCIPAL DE TODAS LAS FUNCIONALIDADES
# ==============================================================================
if __name__ == "__main__":
    print("=" * 85)
    print(" INICIANDO GESTIÓN COMPLETA DE AWS DYNAMODB - PROYECTO ACTIVITYLEO")
    print("=" * 85)

    f1_y_f2_crear_tablas()
    f3_insertar_tres_registros()
    f4_obtener_un_registro()
    f5_actualizar_un_registro()
    f6_eliminar_un_registro()
    f7_obtener_todos_los_registros()
    f8_scan_filtrado()
    f9_eliminacion_condicional()
    f10_multiples_filtros()
    f11_consultas_partiql()

    print("\n" + "=" * 85)
    print(" [ÉXITO] TODAS LAS FUNCIONALIDADES DE DYNAMODB SE HAN EJECUTADO SIN ERRORES.")
    print("=" * 85)