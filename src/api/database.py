import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

# Accede a ellas
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")

# Usamos un "Pool" para manejar múltiples conexiones de forma eficiente
db_config = {
    "host": "localhost",
    "user": db_user,
    "password": db_pass,
    "database": "streaming_db",
    "port": 3306
}

conexion_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **db_config)

def get_db_connection():
    return conexion_pool.get_connection()