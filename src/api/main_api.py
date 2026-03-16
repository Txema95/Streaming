from fastapi import FastAPI, HTTPException
from .database import get_db_connection
from .etl import ejecutar_importacion, limpiar_tablas_contenido
import csv
import pandas as pd
import numpy as np
from pydantic import BaseModel
import bcrypt
import pickle
import os

app = FastAPI()


@app.get("/status")
def check_status():
    return {"status": "Backend funcionando correctamente"}


@app.get("/usuarios")
def obtener_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Devuelve filas como diccionarios
    cursor.execute("SELECT * FROM users")
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return usuarios


def importar_series(conn):
    print("inicio importacion series")
    # Importamos Series
    ejecutar_importacion(conn, "src/data/clean/tmdb_shows_limpio.csv", "tv")
    print("fin importacion series")


def importar_peliculas(conn):
    print("inicio importacion peliculas, se viene lo chungo")
    # Importamos Películas
    # ejecutar_importacion(conn, 'src/data/raw/tmdb/movies/peliculas_2020.csv', 'movie')
    ejecutar_importacion(conn, "src/data/clean/tmdb_movies_limpio.csv", "movie")
    print("fin importacion peliculas, al fin!")


def limpiar_csv():
    df = pd.read_csv("src/data/raw/tmdb/movies/peliculas_2020.csv")

    # 2. LIMPIEZA CRÍTICA: Convertir NaN de Pandas a None de Python (NULL en MySQL)
    # Esto evita el error de "Lost connection" por tipos de datos inválidos
    df = df.replace({np.nan: None})

    # 3. Asegurar tipos de datos (evita el Out of Range)
    df["vote_average"] = pd.to_numeric(df["vote_average"]).round(2)
    df["popularity"] = pd.to_numeric(df["popularity"]).round(2)
    df.to_csv(
        "src/data/raw/tmdb/movies/peliculas_2020_clean.csv",
        index=False,
        encoding="utf-8-sig",
    )


@app.post("/importar_datos")
def importar_datos():
    conn = get_db_connection()
    try:
        limpiar_tablas_contenido(conn)
        # limpiar_csv()
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
        hash_guardado = usuario["passwd"]

        # 2. Comprobamos si la contraseña coincide (Soportando tanto Hash nuevo como Texto Plano antiguo)
        es_valido = False
        if hash_guardado.startswith("$2b$") or hash_guardado.startswith("$2a$"):
            # Si es un hash de bcrypt válido
            es_valido = bcrypt.checkpw(
                datos.password.encode("utf-8"), hash_guardado.encode("utf-8")
            )
        else:
            # Si es una contraseña antigua en texto plano (ej: 'root')
            es_valido = datos.password == hash_guardado

        if es_valido:
            # Por seguridad, borramos la contraseña del diccionario temporal antes de mandarlo al frontend
            del usuario["passwd"]

            return {"status": "success", "message": "Login exitoso", "user": usuario}
        else:
            raise HTTPException(
                status_code=401, detail="Usuario o contraseña incorrectos"
            )
    else:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")


##############################################################################################
#  Recomendación Modelo SVD
##############################################################################################

# Ruta al modelo SVD entrenado y al CSV de ratings, para saber qué pelis ya ha visto el usuario.
ruta_modelo_svd = "src/models/modelo_1_SVD.pkl"
ruta_ratings = "src/data/ready/ratings_finales_ia.csv"
ruta_catalogo = "src/data/ready/dataset_final_movies.csv"

# Cargamos el modelo SVD una sola vez al arrancar el Backend, no en cada petición.
modelo_svd = None
df_ratings_ia = None
df_catalogo = None


@app.on_event("startup")
def cargar_modelo_al_arrancar():
    """
    Se ejecuta automáticamente cuando FastAPI arranca.
    Carga el modelo SVD y los DataFrames necesarios en memoria para no tener que
    leerlos del disco en cada petición (sería lentísimo con 33M de filas).
    """
    global modelo_svd, df_ratings_ia, df_catalogo

    # Cargar el modelo SVD entrenado
    if os.path.exists(ruta_modelo_svd):
        with open(ruta_modelo_svd, "rb") as f:
            modelo_svd = pickle.load(f)
        print("Modelo SVD cargado correctamente al arrancar el Backend.")
    else:
        print(
            f"AVISO: No se encontró el modelo SVD en {ruta_modelo_svd}. El endpoint /recomendar no funcionará."
        )

    # Cargar los ratings para saber qué películas ha visto cada usuario
    if os.path.exists(ruta_ratings):
        df_ratings_ia = pd.read_csv(ruta_ratings)
        print(f"Ratings cargados: {len(df_ratings_ia):,} filas.")
    else:
        print(f"AVISO: No se encontró {ruta_ratings}")

    # Cargar el catálogo para enriquecer las recomendaciones con títulos y posters
    if os.path.exists(ruta_catalogo):
        df_catalogo = pd.read_csv(ruta_catalogo, on_bad_lines="skip", engine="python")
        print(f"Catálogo cargado: {len(df_catalogo):,} películas.")
    else:
        print(f"AVISO: No se encontró {ruta_catalogo}")


@app.get("/recomendar/{user_id}")
def recomendar_peliculas(user_id: int, n: int = 10):
    """
    Endpoint que devuelve las top-N películas recomendadas para un usuario.
    Usa el modelo SVD entrenado para predecir ratings de películas no vistas.
    """
    # Validamos que el modelo y los datos estén cargados
    if modelo_svd is None:
        raise HTTPException(
            status_code=503, detail="El modelo SVD no está cargado. Entrénalo primero."
        )
    if df_ratings_ia is None:
        raise HTTPException(
            status_code=503, detail="Los datos de ratings no están disponibles."
        )

    # 1. Películas que este usuario YA ha visto
    pelis_vistas = set(
        df_ratings_ia[df_ratings_ia["userId"] == user_id]["tmdb_id"].tolist()
    )

    # 2. Todas las películas disponibles en el sistema
    todas_las_pelis = set(df_ratings_ia["tmdb_id"].unique())

    # 3. Candidatas = las que NO ha visto
    pelis_no_vistas = todas_las_pelis - pelis_vistas

    # Si el usuario ha visto todas (raro pero posible), avisamos
    if not pelis_no_vistas:
        return {
            "recomendaciones": [],
            "mensaje": "Este usuario ya ha valorado todas las películas disponibles.",
        }

    # 4. Predecimos la nota para cada película candidata
    predicciones = []
    for tmdb_id in pelis_no_vistas:
        pred = modelo_svd.predict(user_id, tmdb_id)
        predicciones.append(
            {"tmdb_id": int(tmdb_id), "predicted_rating": round(pred.est, 2)}
        )

    # 5. Ordenamos de mayor a menor y nos quedamos con las top-N
    predicciones.sort(key=lambda x: x["predicted_rating"], reverse=True)
    top_n = predicciones[:n]

    # 6. Enriquecemos con datos del catálogo (título, poster, sinopsis, nota real)
    if df_catalogo is not None:
        for rec in top_n:
            match = df_catalogo[df_catalogo["tmdb_id"] == rec["tmdb_id"]]
            if not match.empty:
                fila = match.iloc[0]
                rec["titulo"] = str(fila.get("titulo", "Sin Título"))
                rec["poster_path"] = str(fila.get("poster_path", ""))
                rec["overview"] = str(fila.get("overview", "Sin sinopsis disponible."))
                rec["vote_average"] = float(fila.get("vote_average", 0))
            else:
                rec["titulo"] = f"Película #{rec['tmdb_id']}"
                rec["poster_path"] = ""
                rec["overview"] = "Sin sinopsis disponible."
                rec["vote_average"] = 0.0

    return {"recomendaciones": top_n}
