import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def funcionalidad_1_crear_db():
    print("\n" + "="*80)
    print("EJECUTANDO FUNCIONALIDAD 1: CREACIÓN DE BASE DE DATOS RDS EN AWS")
    print("Explicación: Provisiona una instancia MySQL en AWS RDS utilizando boto3.")
    print("="*80)

    rds_client = boto3.client(
        'rds',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION")
    )

    db_instance_id = os.getenv("DB_INSTANCE_ID")

    instancias = rds_client.describe_db_instances().get('DBInstances', [])
    ids_existentes = [db['DBInstanceIdentifier'] for db in instancias]

    if db_instance_id in ids_existentes:
        print(f"[INFO] La base de datos '{db_instance_id}' ya existe en RDS AWS.")
    else:
        print(f"[ACCIÓN] Solicitando creación de la instancia RDS '{db_instance_id}'...")
        rds_client.create_db_instance(
            DBInstanceIdentifier=db_instance_id,
            AllocatedStorage=20,
            DBInstanceClass='db.t3.micro',
            Engine='mysql',
            MasterUsername=os.getenv("DB_ADMIN_USER"),
            MasterUserPassword=os.getenv("DB_ADMIN_PASSWORD"),
            DBName=os.getenv("DB_NAME"),
            PubliclyAccessible=True,
            StorageType='gp2'
        )
        print("[INFO] Esperando a que AWS RDS termine la creación...")

    waiter = rds_client.get_waiter('db_instance_available')
    waiter.wait(DBInstanceIdentifier=db_instance_id, WaiterConfig={'Delay': 15, 'MaxAttempts': 40})

    response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    print(f"[ÉXITO] Base de datos activa. Endpoint obtenido: {endpoint}")
    return endpoint

if __name__ == "__main__":
    funcionalidad_1_crear_db()