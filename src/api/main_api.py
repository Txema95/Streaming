from fastapi import FastAPI, HTTPException
from .database import get_db_connection
from .etl import ejecutar_importacion, limpiar_tablas_contenido
import csv
import pandas as pd
import numpy as np
from pydantic import BaseModel
import bcrypt

app = FastAPI()

@app.get("/status")
def check_status():
    return {"status": "Backend funcionando correctamente"}

@app.get("/usuarios")
def obtener_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # Devuelve filas como diccionarios
    cursor.execute("SELECT * FROM users")
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return usuarios
def importar_series(conn):
    print("inicio importacion series")
    # Importamos Series
    ejecutar_importacion(conn, 'src/data/clean/tmdb_shows_limpio.csv', 'tv')
    print("fin importacion series")
def importar_peliculas(conn):
    print("inicio importacion peliculas, se viene lo chungo")
    # Importamos Películas
    #ejecutar_importacion(conn, 'src/data/raw/tmdb/movies/peliculas_2020.csv', 'movie')
    ejecutar_importacion(conn, 'src/data/clean/tmdb_movies_limpio.csv', 'movie')
    print("fin importacion peliculas, al fin!")
def limpiar_csv():
    df = pd.read_csv("src/data/raw/tmdb/movies/peliculas_2020.csv")

    # 2. LIMPIEZA CRÍTICA: Convertir NaN de Pandas a None de Python (NULL en MySQL)
    # Esto evita el error de "Lost connection" por tipos de datos inválidos
    df = df.replace({np.nan: None})

    # 3. Asegurar tipos de datos (evita el Out of Range)
    df['vote_average'] = pd.to_numeric(df['vote_average']).round(2)
    df['popularity'] = pd.to_numeric(df['popularity']).round(2)
    df.to_csv("src/data/raw/tmdb/movies/peliculas_2020_clean.csv", index=False, encoding='utf-8-sig')
@app.post("/importar_datos")
def importar_datos():
    conn = get_db_connection()
    try:
        limpiar_tablas_contenido(conn)
        #limpiar_csv()
        importar_series(conn)
        importar_peliculas(conn)
        return {"status": "success", "message": "Catálogos actualizados correctamente"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


# Clase para definir qué datos esperamos en el JSON del POST
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(datos: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Buscamos al usuario solo por nombre de usuario
    query = "SELECT id_usuario, username, email, passwd FROM users WHERE username = %s"
    cursor.execute(query, (datos.username,))
    
    usuario = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if usuario:
        # Obtenemos el hash que estaba guardado en BD
        hash_guardado = usuario['passwd']
        
        # 2. Comprobamos si la contraseña coincide (Soportando tanto Hash nuevo como Texto Plano antiguo)
        es_valido = False
        if hash_guardado.startswith("$2b$") or hash_guardado.startswith("$2a$"):
            # Si es un hash de bcrypt válido
            es_valido = bcrypt.checkpw(datos.password.encode('utf-8'), hash_guardado.encode('utf-8'))
        else:
            # Si es una contraseña antigua en texto plano (ej: 'root')
            es_valido = (datos.password == hash_guardado)

        if es_valido:
            # Por seguridad, borramos la contraseña del diccionario temporal antes de mandarlo al frontend
            del usuario['passwd']
            
            return {
                "status": "success",
                "message": "Login exitoso",
                "user": usuario
            }
        else:
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    else:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")