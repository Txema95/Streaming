import mysql.connector
from mysql.connector import pooling

# Usamos un "Pool" para manejar múltiples conexiones de forma eficiente
db_config = {
    "host": "localhost",
    "user": "eada_new",
    "password": "Eada2021",
    "database": "streaming_db"
}

conexion_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **db_config)

def get_db_connection():
    return conexion_pool.get_connection()