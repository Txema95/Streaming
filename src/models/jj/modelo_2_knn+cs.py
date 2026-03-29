##############################################################################################
#
#  MODELO 2: KNN + Cosine Similarity (K-Nearest Neighbors + Similitud del Coseno)
#  ================================================================================
#  Sistema de Recomendación basado en Filtrado Colaborativo (Memoria / Basado en Vecinos).
#
#  ¿Qué hace?
#  ----------
#  A diferencia de SVD (que busca factores latentes ocultos construyendo una matriz),
#  KNN basa sus recomendaciones en encontrar "vecinos" parecidos usando los datos directos.
#
#  Se puede configurar de dos formas:
#    1. User-Based (Basado en Usuarios): Encuentra otros usuarios con gustos matemáticamente
#       similares a los tuyos (han votado lo mismo que tú con notas similares), y
#       te recomienda películas que a ellos les encantaron pero que tú aún no has visto.
#    2. Item-Based (Basado en Ítems): Calcula la similitud entre las películas mismas.
#       Si votaste con 5 estrellas "Matrix", buscará las películas que estadísticamente
#       tienen el mismo patrón de votos que "Matrix" por el resto de la comunidad.
#
#  ¿Qué es la Similitud del Coseno (Cosine Similarity)?
#  ----------------------------------------------------
#  Para saber si el Usuario A y el Usuario B son "almas gemelas" en cine, imaginamos
#  todas sus notas como si fueran una flecha (vector) apuntando en el espacio multidimensional.
#  Si calculamos el ángulo entre ambas flechas:
#    - Si apuntan exactamente al mismo sitio (ángulo = 0º), el Coseno es 1: 100% Similares.
#    - Si hacen 90 grados, el Coseno es 0: No tienen relación alguna en sus gustos.
#
#  Librería: scikit-surprise (Algoritmo: KNNBasic o KNNWithZScore)
#
##############################################################################################

import pandas as pd
import pickle
import os
import time

from surprise import KNNBasic, Dataset, Reader
from surprise.model_selection import train_test_split
from surprise import accuracy

##############################################################################################
#  CONFIGURACIÓN GLOBAL
##############################################################################################

# Ruta al archivo CSV con las valoraciones (igual que en SVD para poder compararlos luego)
ruta_ratings = "src/data/ready/ratings_finales_ia.csv"

# Ruta donde guardaremos este modelo
ruta_modelo = "src/models/jj/modelo_2_knn_cs.pkl"

# Mínimos de valoraciones para evitar el desbordamiento de RAM (OOM) en KNN
min_ratings_por_usuario = 50
min_ratings_por_pelicula = 150

# --- Hiperparámetros de KNN ---
k_vecinos = 40  # Número máximo de vecinos a considerar para predecir
min_vecinos = 5  # Si no encontramos al menos 5 vecinos parecidos, no predecimos

# Opciones de similitud dictan cómo se calculará matemáticamente la distancia
opciones_similitud = {
    "name": "cosine",  # Usar la Similitud del Coseno
    "user_based": False,  # IMPORTANTE: False = Item-Based | True = User-Based
    # Nota: Item-Based suele ser más robusto porque los gustos de las películas cambian
    # menos que los gustos volátiles de las personas, y además suele haber menos películas
    # que personas, lo que requiere menos memoria (dependiendo del dataset).
}

##############################################################################################
#  PASO 1: CARGA Y FILTRADO DE DATOS
##############################################################################################


def cargar_datos():
    """
    Lee el CSV de ratings y aplica el mismo filtro de usuarios que modelo 1 (SVD).
    """
    print("=" * 70)
    print("  MODELO 2: KNN + COSINE SIMILARITY — Carga de Datos")
    print("=" * 70)

    print(f"\n  Leyendo {ruta_ratings}...")
    df = pd.read_csv(ruta_ratings)

    # 1. Filtro de películas (CRUCIAL para KNN Item-Based, reduce la matriz NxN drásticamente)
    conteo_por_pelicula = df.groupby("tmdb_id").size()
    peliculas_validas = conteo_por_pelicula[
        conteo_por_pelicula >= min_ratings_por_pelicula
    ].index
    df_filtrado = df[df["tmdb_id"].isin(peliculas_validas)]

    # 2. Filtro de usuarios
    conteo_por_usuario = df_filtrado.groupby("userId").size()
    usuarios_validos = conteo_por_usuario[
        conteo_por_usuario >= min_ratings_por_usuario
    ].index
    df_filtrado = df_filtrado[df_filtrado["userId"].isin(usuarios_validos)]

    print(
        f"  -> Películas tras filtro (>= {min_ratings_por_pelicula} ratings): {df_filtrado['tmdb_id'].nunique():,}"
    )
    print(
        f"  -> Usuarios tras filtro (>= {min_ratings_por_usuario} ratings): {df_filtrado['userId'].nunique():,}"
    )
    print(f"  -> Filas tras filtro: {len(df_filtrado):,}\n")

    return df_filtrado


##############################################################################################
#  PASO 2: ENTRENAMIENTO DEL MODELO KNN
##############################################################################################


def entrenar_modelo(df):
    """
    Prepara los datos para Surprise, usa KNNBasic con Coseno y evalúa su precisión.
    """
    print("=" * 70)
    print("  MODELO 2: KNN + CS — Entrenamiento")
    print("=" * 70)

    reader = Reader(rating_scale=(0.5, 5.0))
    datos_surprise = Dataset.load_from_df(df[["userId", "tmdb_id", "rating"]], reader)

    print("\n  Dividiendo datos: 80% entrenamiento / 20% test...")
    trainset, testset = train_test_split(datos_surprise, test_size=0.2, random_state=42)

    # Configuramos KNNBasic con Similitud del Coseno
    modelo = KNNBasic(
        k=k_vecinos, min_k=min_vecinos, sim_options=opciones_similitud, verbose=True
    )

    print(f"\n  Calculando matriz de similitudes y vecinos...")
    inicio = time.time()
    # Para KNN, el .fit(trainset) calcula y guarda en memoria toda la matriz de
    # similitudes (ítem x ítem o usuario x usuario). Esto consume RAM.
    modelo.fit(trainset)
    duracion = time.time() - inicio
    print(f"\n  Matriz construida en {duracion:.1f} segundos")

    print("\n  Evaluando sobre el conjunto de test...")
    predicciones = modelo.test(testset)

    rmse = accuracy.rmse(predicciones, verbose=False)
    mae = accuracy.mae(predicciones, verbose=False)

    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║  RESULTADOS DE KNN + COSINE            ║")
    print(f"  ╠════════════════════════════════════════╣")
    print(f"  ║  RMSE: {rmse:.4f}                      ║")
    print(f"  ║  MAE:  {mae:.4f}                       ║")
    print(f"  ╚════════════════════════════════════════╝")
    # Te servirá para comparar directamente contra SVD.
    # Por lo general, SVD sacará mejor nota en RMSE, pero el código KNN nos puede dar
    # recomendaciones más "explicables"
    # (ej: te recomiendo la Peli B porque votaste alto la Peli A).

    return modelo, rmse, mae


##############################################################################################
#  PASO 3: GUARDAR EL MODELO ENTRENADO
##############################################################################################


def guardar_modelo(modelo):
    """
    Guarda la gigantesca tabla de distancias para el Backend.
    Aviso: Los modelos KNN suelen pesar MÁS en disco/RAM que SVD porque guardan
    toda la matriz de similitudes calculada, mientras que SVD solo guarda los vectores reducidos.
    """
    with open(ruta_modelo, "wb") as f:
        pickle.dump(modelo, f)

    tamano_mb = os.path.getsize(ruta_modelo) / (1024 * 1024)
    print(f"\n  Modelo guardado en: {ruta_modelo} (Peso: {tamano_mb:.1f} MB)")


##############################################################################################
#  PASO 4: FUNCIÓN DE RECOMENDACIÓN RÁPIDA (Opcional, Demo)
##############################################################################################


def recomendar(modelo, user_id, df_ratings, df_movies=None, n=10):
    """
    Igual que en SVD: calculamos estimaciones de todas las no-vistas y nos quedamos las mejores.
    """
    pelis_vistas = set(df_ratings[df_ratings["userId"] == user_id]["tmdb_id"].tolist())
    todas_las_pelis = set(df_ratings["tmdb_id"].unique())
    pelis_no_vistas = todas_las_pelis - pelis_vistas

    predicciones = []
    for tmdb_id in pelis_no_vistas:
        pred = modelo.predict(user_id, tmdb_id)
        predicciones.append(
            {"tmdb_id": int(tmdb_id), "predicted_rating": round(pred.est, 2)}
        )

    predicciones.sort(key=lambda x: x["predicted_rating"], reverse=True)
    return predicciones[:n]


##############################################################################################
#  EJECUCIÓN DEL SCRIPT
##############################################################################################

if __name__ == "__main__":
    df = cargar_datos()
    modelo, rmse, mae = entrenar_modelo(df)
    guardar_modelo(modelo)

    print("\n" + "=" * 70)
    print("  DEMO: Recomendaciones para el Usuario 1")
    print("=" * 70)

    recomendaciones = recomendar(modelo, user_id=1, df_ratings=df)
    try:
        df_movies = pd.read_csv(
            "src/data/ready/dataset_final_movies.csv",
            on_bad_lines="skip",
            engine="python",
        )
        print(f"\n  {'Pos':<5} {'Título':<45} {'Nota Predicha':<15}")
        print("  " + "-" * 65)
        for i, rec in enumerate(recomendaciones, 1):
            match = df_movies[df_movies["tmdb_id"] == rec["tmdb_id"]]
            titulo = (
                match["titulo"].values[0]
                if not match.empty
                else f"ID: {rec['tmdb_id']}"
            )
            if len(titulo) > 42:
                titulo = titulo[:39] + "..."
            print(f"  {i:<5} {titulo:<45} estrellas {rec['predicted_rating']}")
    except:
        for i, rec in enumerate(recomendaciones, 1):
            print(f"  {i}. ID={rec['tmdb_id']} | Nota: {rec['predicted_rating']}")

    print("\n  ¡Modelo KNN+Cosine generado!")
    print("=" * 70)
