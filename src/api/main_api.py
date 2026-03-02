from fastapi import FastAPI, HTTPException
from .database import get_db_connection
from .etl import ejecutar_importacion
import csv

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

@app.post("/importar_datos")
def importar_datos():
    conn = get_db_connection()
    try:
        print("inicio importacion series")
        # Importamos Series
        ejecutar_importacion(conn, 'src/data/raw/tmdb/series/catalogo_series_tmdb.csv', 'tv')
        print("fin importacion series")

        print("inicio importacion peliculas, se viene lo chungo")
        # Importamos Películas
        ejecutar_importacion(conn, 'src/data/raw/tmdb/movies/catalogo_peliculas_tmdb.csv', 'movie')
        print("fin importacion peliculas, al fin!")
        return {"status": "success", "message": "Catálogos actualizados correctamente"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()