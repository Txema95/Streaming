from fastapi import FastAPI, HTTPException
from .database import get_db_connection
from .etl import ejecutar_importacion
import csv
import pandas as pd
import numpy as np

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
    ejecutar_importacion(conn, 'src/data/raw/tmdb/series/catalogo_series_tmdb.csv', 'tv')
    print("fin importacion series")
def importar_peliculas(conn):
    print("inicio importacion peliculas, se viene lo chungo")
    # Importamos Películas
    ejecutar_importacion(conn, 'src/data/raw/tmdb/movies/peliculas_2020_clean.csv', 'movie')
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
        limpiar_csv()
        #importar_series(conn)
        importar_peliculas(conn)
        return {"status": "success", "message": "Catálogos actualizados correctamente"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()