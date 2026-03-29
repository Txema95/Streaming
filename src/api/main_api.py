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

# --- Wide & Deep: importamos PyTorch si está disponible (opcional) ---
try:
    import torch

    try:
        from networks.dl.rn_mlp import WideAndDeepModel

        print("[WnD] WideAndDeepModel importado desde 'networks.dl.rn_mlp'")
    except ImportError as e1:
        print(f"[WnD] Import 1 fallido: {e1}")
        try:
            from src.networks.dl.rn_mlp import WideAndDeepModel

            print("[WnD] WideAndDeepModel importado desde 'src.networks.dl.rn_mlp'")
        except ImportError as e2:
            print(f"[WnD] Import 2 fallido: {e2} -> WideAndDeepModel = None")
            WideAndDeepModel = None
    TORCH_DISPONIBLE = True
    print(
        f"[WnD] PyTorch {torch.__version__} disponible. WideAndDeepModel={'OK' if WideAndDeepModel else 'None'}"
    )
except ImportError as e:
    print(f"[WnD] PyTorch no instalado: {e}")
    TORCH_DISPONIBLE = False
    WideAndDeepModel = None

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
#  Recomendación Modelos
##############################################################################################

# Ruta al modelo SVD entrenado y al CSV de ratings, para saber qué pelis ya ha visto el usuario.
ruta_modelo_svd = "src/models/jj/modelo_1_SVD.pkl"
ruta_ratings = "src/data/ready/ratings_finales_ia.csv"
ruta_catalogo = "src/data/ready/dataset_final_movies.csv"

# Cargamos el modelo SVD una sola vez al arrancar el Backend, no en cada petición.
modelo_svd = None
df_ratings_ia = None
df_catalogo = None

# --- KNN + Cosine Similarity ---
ruta_modelo_knn = "src/models/jj/modelo_2_knn_cs.pkl"
modelo_knn = None

# --- Wide & Deep (PyTorch) ---
ruta_modelo_wnd = "src/models/jj/modelo_3_wnd.pth"
ruta_mapeos_wnd = "src/models/jj/wnd_mappings.pkl"
modelo_wnd = None
wnd_mappings = None


@app.on_event("startup")
def cargar_modelo_al_arrancar():
    """
    Se ejecuta automáticamente cuando FastAPI arranca.
    Carga los 3 modelos de IA y los DataFrames necesarios en memoria.
    """
    global modelo_svd, df_ratings_ia, df_catalogo
    global modelo_knn, modelo_wnd, wnd_mappings

    # --- Modelo 1: SVD ---
    if os.path.exists(ruta_modelo_svd):
        with open(ruta_modelo_svd, "rb") as f:
            modelo_svd = pickle.load(f)
        print("Modelo SVD cargado correctamente.")
    else:
        print(f"No se encontró el modelo SVD en {ruta_modelo_svd}")

    # --- Modelo 2: KNN + Cosine Similarity ---
    if os.path.exists(ruta_modelo_knn):
        with open(ruta_modelo_knn, "rb") as f:
            modelo_knn = pickle.load(f)
        print("Modelo KNN+Cosine cargado correctamente.")
    else:
        print(f"No se encontró el modelo KNN en {ruta_modelo_knn}")

    # --- Modelo 3: Wide & Deep (PyTorch) ---
    print(
        f"[WnD Startup] TORCH_DISPONIBLE={TORCH_DISPONIBLE}, WideAndDeepModel={WideAndDeepModel}"
    )
    if TORCH_DISPONIBLE and WideAndDeepModel is not None:
        if os.path.exists(ruta_modelo_wnd) and os.path.exists(ruta_mapeos_wnd):
            try:
                with open(ruta_mapeos_wnd, "rb") as f:
                    wnd_mappings = pickle.load(f)
                num_users = len(wnd_mappings["user2idx"])
                num_movies = len(wnd_mappings["movie2idx"])
                print(
                    f"[WnD Startup] Mappings: {num_users} usuarios, {num_movies} peliculas"
                )
                modelo_wnd = WideAndDeepModel(
                    num_users=num_users,
                    num_movies=num_movies,
                    embedding_dim=32,
                    hidden_layers=[64, 32],
                )
                modelo_wnd.load_state_dict(
                    torch.load(
                        ruta_modelo_wnd,
                        map_location=torch.device("cpu"),
                        weights_only=True,
                    )
                )
                modelo_wnd.eval()
                print("Modelo Wide&Deep cargado correctamente.")
            except Exception as e:
                print(f"[WnD Startup] ERROR al cargar el modelo: {e}")
                modelo_wnd = None
        else:
            print(
                f"[WnD Startup] Archivos no encontrados: .pth existe={os.path.exists(ruta_modelo_wnd)}, .pkl existe={os.path.exists(ruta_mapeos_wnd)}"
            )
    else:
        print(
            f"[WnD Startup] Saltando Wide&Deep: TORCH={TORCH_DISPONIBLE}, modelo_class={WideAndDeepModel}"
        )

    # --- Datos compartidos: Ratings y Catálogo ---
    if os.path.exists(ruta_ratings):
        df_ratings_ia = pd.read_csv(ruta_ratings)
        print(f"Ratings cargados: {len(df_ratings_ia):,} filas.")
    else:
        print(f"No se encontró {ruta_ratings}")

    if os.path.exists(ruta_catalogo):
        df_catalogo = pd.read_csv(ruta_catalogo, on_bad_lines="skip", engine="python")
        print(f"Catálogo cargado: {len(df_catalogo):,} películas.")
    else:
        print(f"No se encontró {ruta_catalogo}")


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

    # 2. Todas las películas disponibles en el sistema (aseguramos que parten del catálogo)
    if df_catalogo is not None:
        todas_las_pelis = set(df_catalogo["tmdb_id"].unique())
    else:
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


##############################################################################################
#  Helper: Enriquecer recomendaciones con datos del catálogo
##############################################################################################


def enriquecer_recomendaciones(top_n):
    """Añade título, poster, sinopsis y nota real del catálogo a cada recomendación."""
    if df_catalogo is None:
        return
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


##############################################################################################
#  Recomendación Modelo KNN + Cosine Similarity
##############################################################################################


@app.get("/recomendar/knn/{user_id}")
def recomendar_knn(user_id: int, n: int = 10):
    """Endpoint de recomendaciones usando KNN + Cosine Similarity (Modelo 2)."""
    if modelo_knn is None:
        raise HTTPException(
            status_code=503, detail="El modelo KNN no está cargado. Entrénalo primero."
        )
    if df_ratings_ia is None:
        raise HTTPException(
            status_code=503, detail="Los datos de ratings no están disponibles."
        )

    pelis_vistas = set(
        df_ratings_ia[df_ratings_ia["userId"] == user_id]["tmdb_id"].tolist()
    )
    todas = (
        set(df_catalogo["tmdb_id"].unique())
        if df_catalogo is not None
        else set(df_ratings_ia["tmdb_id"].unique())
    )
    pelis_no_vistas = todas - pelis_vistas

    if not pelis_no_vistas:
        return {
            "recomendaciones": [],
            "modelo": "KNN+Cosine",
            "mensaje": "Este usuario ya ha valorado todas las películas.",
        }

    predicciones = []
    for tmdb_id in pelis_no_vistas:
        pred = modelo_knn.predict(user_id, tmdb_id)
        predicciones.append(
            {"tmdb_id": int(tmdb_id), "predicted_rating": round(pred.est, 2)}
        )

    predicciones.sort(key=lambda x: x["predicted_rating"], reverse=True)
    top_n = predicciones[:n]
    enriquecer_recomendaciones(top_n)

    return {"recomendaciones": top_n, "modelo": "KNN+Cosine"}


##############################################################################################
#  Recomendación Modelo Wide & Deep (PyTorch)
##############################################################################################


@app.get("/recomendar/wnd/{user_id}")
def recomendar_wnd_endpoint(user_id: int, n: int = 10):
    """Endpoint de recomendaciones usando Wide & Deep Neural Network (Modelo 3)."""
    if modelo_wnd is None or wnd_mappings is None:
        raise HTTPException(
            status_code=503, detail="El modelo Wide&Deep no está cargado."
        )
    if df_ratings_ia is None:
        raise HTTPException(
            status_code=503, detail="Los datos de ratings no están disponibles."
        )

    user2idx = wnd_mappings["user2idx"]
    movie2idx = wnd_mappings["movie2idx"]

    if user_id not in user2idx:
        return {
            "recomendaciones": [],
            "modelo": "Wide&Deep",
            "mensaje": f"El usuario {user_id} no cumplió el filtro de entrenamiento (>100 valoraciones).",
        }

    u_idx = user2idx[user_id]
    pelis_vistas = set(
        df_ratings_ia[df_ratings_ia["userId"] == user_id]["tmdb_id"].tolist()
    )

    candidatas = [
        (tid, midx) for tid, midx in movie2idx.items() if tid not in pelis_vistas
    ]
    if not candidatas:
        return {
            "recomendaciones": [],
            "modelo": "Wide&Deep",
            "mensaje": "Este usuario ya ha valorado todas las películas.",
        }

    tmdb_ids, movie_indices = zip(*candidatas)
    user_tensor = torch.tensor([u_idx] * len(movie_indices), dtype=torch.long)
    movie_tensor = torch.tensor(list(movie_indices), dtype=torch.long)

    with torch.no_grad():
        preds = modelo_wnd(user_tensor, movie_tensor)
        preds = torch.clamp(preds, 0.5, 5.0)

    predicciones = [
        {"tmdb_id": int(tid), "predicted_rating": round(preds[i].item(), 2)}
        for i, tid in enumerate(tmdb_ids)
    ]

    predicciones.sort(key=lambda x: x["predicted_rating"], reverse=True)
    top_n = predicciones[:n]
    enriquecer_recomendaciones(top_n)

    return {"recomendaciones": top_n, "modelo": "Wide&Deep"}
