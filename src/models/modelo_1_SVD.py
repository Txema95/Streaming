##############################################################################################
#
#  MODELO 1: SVD (Singular Value Decomposition)
#  =============================================
#  Sistema de Recomendación basado en Filtrado Colaborativo.
#
#  ¿Qué hace?
#  ----------
#  Descompone la gigantesca matriz de "usuarios × películas" en factores latentes.
#  Cada usuario y cada película quedan representados por un vector numérico pequeño
#  (embedding) que captura sus "gustos ocultos". Para predecir si al Usuario 42
#  le gustará la Película 100, multiplicamos sus vectores y obtenemos una nota estimada.
#
#  Librería: scikit-surprise
#
##############################################################################################

import pandas as pd
import pickle
import os
import time

from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
from surprise import accuracy

##############################################################################################
#  CONFIGURACIÓN GLOBAL
##############################################################################################

# Ruta al archivo CSV con las valoraciones (userId, tmdb_id, rating)
ruta_ratings = "src/data/ready/ratings_finales_ia.csv"

# Ruta donde guardaremos el modelo ya entrenado para que el Backend lo cargue sin re-entrenar
ruta_modelo = "src/models/modelo_1_SVD.pkl"

# Mínimo de valoraciones que debe tener un usuario para incluirlo en el entrenamiento.
# Usuarios con pocas valoraciones aportan ruido y ralentizan el proceso.
# Con ≥20 ratings, reducimos de 33 millones de filas a un conjunto manejable.
min_ratings_por_usuario = 20

# Número de factores latentes (dimensiones del embedding).
# Más factores = más capacidad de aprendizaje, pero más lento y riesgo de sobreajuste.
n_factores = 100

# Número de épocas (pasadas completas sobre los datos durante el entrenamiento).
n_epocas = 20

# Tasa de aprendizaje: cuánto se ajustan los pesos en cada paso.
learning_rate = 0.005

# Regularización: penalización para evitar que el modelo memorice los datos (sobreajuste).
regularizacion = 0.02


##############################################################################################
#  PASO 1: CARGA Y FILTRADO DE DATOS
##############################################################################################


def cargar_datos():
    """
    Lee el CSV de ratings y filtra usuarios con pocas valoraciones.
    Devuelve un DataFrame limpio y reducido, listo para entrenar.
    """
    print("=" * 70)
    print("  MODELO 1: SVD — Carga de Datos")
    print("=" * 70)

    # Leemos el CSV completo (33.8M filas, pero solo 3 columnas: userId, tmdb_id, rating)
    print(f"\n  Leyendo {ruta_ratings}...")
    df = pd.read_csv(ruta_ratings)
    print(f"  -> Filas totales en bruto: {len(df):,}")
    print(f"  -> Usuarios unicos: {df['userId'].nunique():,}")
    print(f"  -> Peliculas unicas: {df['tmdb_id'].nunique():,}")

    # Contamos cuántas valoraciones tiene cada usuario
    conteo_por_usuario = df.groupby("userId").size()

    # Nos quedamos solo con los usuarios que tengan 20 o mas valoraciones
    usuarios_validos = conteo_por_usuario[
        conteo_por_usuario >= min_ratings_por_usuario
    ].index
    df_filtrado = df[df["userId"].isin(usuarios_validos)]

    print(f"\n  Filtro aplicado: Usuarios con >= {min_ratings_por_usuario} ratings")
    print(f"  -> Usuarios tras filtro: {df_filtrado['userId'].nunique():,}")
    print(f"  -> Filas tras filtro: {len(df_filtrado):,}")
    print(
        f"  -> Reducción: {100 - (len(df_filtrado) / len(df) * 100):.1f}% menos datos\n"
    )

    return df_filtrado


##############################################################################################
#  PASO 2: ENTRENAMIENTO DEL MODELO SVD
##############################################################################################


def entrenar_modelo(df):
    """
    Recibe el DataFrame filtrado, lo convierte al formato que necesita Surprise,
    entrena el modelo SVD y devuelve el modelo + las métricas de evaluación.
    """
    print("=" * 70)
    print("  MODELO 1: SVD — Entrenamiento")
    print("=" * 70)

    # Surprise necesita saber el rango de las puntuaciones (0.5 a 5.0 en MovieLens)
    reader = Reader(rating_scale=(0.5, 5.0))

    # Convertimos nuestro DataFrame de Pandas al formato interno de Surprise
    # Le decimos qué columnas son: usuario, item, rating
    datos_surprise = Dataset.load_from_df(df[["userId", "tmdb_id", "rating"]], reader)

    # Dividimos para entrenar con el 80% y test con el 20% restante
    print("\n  Dividiendo datos: 80% entrenamiento / 20% test...")

    trainset, testset = train_test_split(datos_surprise, test_size=0.2, random_state=42)

    print(f"  -> Entrenamiento: {trainset.n_ratings:,} ratings")
    print(f"  -> Test: {len(testset):,} ratings")

    # Creamos el modelo SVD con los hiperparámetros que configuramos arriba
    modelo = SVD(
        n_factors=n_factores,  # Dimensiones del embedding
        n_epochs=n_epocas,  # Número de pasadas sobre los datos
        lr_all=learning_rate,  # Tasa de aprendizaje global
        reg_all=regularizacion,  # Regularización global (anti-sobreajuste)
        verbose=True,  # Que imprima el progreso época por época
    )

    # ¡Entrenamos!
    # Surprise optimiza internamente con SGD.
    print(f"\n  Entrenando SVD con {n_factores} factores, {n_epocas} épocas...")
    inicio = time.time()
    modelo.fit(trainset)
    duracion = time.time() - inicio
    print(f"\n  Entrenamiento completado en {duracion:.1f} segundos")

    # Evaluamos la calidad del modelo
    print("\n  Evaluando sobre el conjunto de test...")
    predicciones = modelo.test(testset)

    # RMSE: Error cuadrático medio. Cuanto más bajo, mejor. Objetivo: < 0.90
    rmse = accuracy.rmse(predicciones, verbose=False)
    # MAE: Error absoluto medio. Cuanto más bajo, mejor. Objetivo: < 0.70
    mae = accuracy.mae(predicciones, verbose=False)

    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║  RESULTADOS DEL MODELO SVD           ║")
    print(f"  ╠══════════════════════════════════════╣")
    print(f"  ║  RMSE: {rmse:.4f} (Objetivo: < 0.90) ║")
    print(f"  ║  MAE:  {mae:.4f}  (Objetivo: < 0.70) ║")
    print(f"  ╚══════════════════════════════════════╝")

    return modelo, rmse, mae


# Información importante:
# El RMSE se mide en las mismas unidades que los datos originales. Como nuestros ratings
# van de 0.5 a 5.0 estrellas, el RMSE también se mide en estrellas.
# 0.0 = modelo perfecto (no se equivoca nunca)
# 4.5 = error máximo posible


##############################################################################################
#  PASO 3: GUARDAR EL MODELO ENTRENADO
##############################################################################################


def guardar_modelo(modelo):
    """
    Serializa (convierte a bytes) el modelo SVD y lo guarda como archivo .pkl
    para que el Backend (FastAPI) pueda cargarlo luego sin tener que re-entrenar.
    """
    # pickle.dump convierte cualquier objeto Python en un archivo binario
    with open(ruta_modelo, "wb") as f:
        pickle.dump(modelo, f)

    # Calculamos el tamaño del archivo para informar al usuario
    tamano_mb = os.path.getsize(ruta_modelo) / (1024 * 1024)
    print(f"\n  Modelo guardado en: {ruta_modelo} ({tamano_mb:.1f} MB)")


##############################################################################################
#  PASO 4: FUNCIÓN DE RECOMENDACIÓN
##############################################################################################


def recomendar(modelo, user_id, df_ratings, n=10):
    """
    Dado un usuario, predice la nota que le daría a TODAS las películas que NO ha visto
    y devuelve las top-N con mayor puntuación predicha.

    Parámetros:
    ----------
    modelo    : El modelo SVD ya entrenado
    user_id   : ID numérico del usuario (de la tabla users de MovieLens)
    df_ratings: DataFrame completo de ratings (para saber qué pelis YA ha visto)
    n         : Cantidad de recomendaciones a devolver (default: 10)

    Returns:
    -------
    Lista de diccionarios [{tmdb_id, predicted_rating}, ...]
    """

    # 1. Sacamos la lista de películas que este usuario ya ha valorado
    pelis_vistas = set(df_ratings[df_ratings["userId"] == user_id]["tmdb_id"].tolist())

    # 2. Sacamos la lista de todas las películas del catálogo
    todas_las_pelis = set(df_ratings["tmdb_id"].unique())

    # 3. Restamos: películas que existen menos las que ya ha visto = candidatas
    pelis_no_vistas = todas_las_pelis - pelis_vistas

    # 4. Para cada película candidata, le pedimos al modelo que prediga la nota
    predicciones = []
    for tmdb_id in pelis_no_vistas:
        # modelo.predict devuelve un objeto con el atributo .est (estimación de rating)
        pred = modelo.predict(user_id, tmdb_id)
        predicciones.append(
            {"tmdb_id": int(tmdb_id), "predicted_rating": round(pred.est, 2)}
        )

    # 5. Ordenamos de mayor a menor nota predicha y nos quedamos con las top-N
    predicciones.sort(key=lambda x: x["predicted_rating"], reverse=True)

    return predicciones[:n]


##############################################################################################
#  PASO 5: CARGAR MODELO YA ENTRENADO (para uso desde el Backend)
##############################################################################################


def cargar_modelo_guardado():
    """
    Carga el modelo SVD previamente guardado desde el archivo .pkl.
    El Backend (FastAPI) usará esta función para no tener que re-entrenar en cada arranque.
    """
    if not os.path.exists(ruta_modelo):
        print(f"  Error: No se encontró el modelo en {ruta_modelo}")
        print(f"  Ejecuta primero: python src/models/modelo_1_SVD.py")
        return None

    with open(ruta_modelo, "rb") as f:
        modelo = pickle.load(f)

    print(f"  Modelo SVD cargado desde {ruta_modelo}")
    return modelo


##############################################################################################
#  PRINCIPAL: Se ejecuta directamente

#   Comando: python src/models/modelo_1_SVD.py
##############################################################################################

if __name__ == "__main__":
    # Paso 1: Cargar y filtrar los datos
    df = cargar_datos()

    # Paso 2: Entrenar el modelo SVD
    modelo, rmse, mae = entrenar_modelo(df)

    # Paso 3: Guardar el modelo entrenado para el Backend
    guardar_modelo(modelo)

    # Paso 4: Demo rápida — Probamos recomendaciones para un usuario de ejemplo
    print("\n" + "=" * 70)
    print("  DEMO: Recomendaciones para el Usuario 1")
    print("=" * 70)

    recomendaciones = recomendar(modelo, user_id=1, df_ratings=df, n=10)

    # Intentamos cruzar con el catálogo para mostrar títulos bonitos
    try:
        df_movies = pd.read_csv(
            "src/data/ready/dataset_final_movies.csv",
            on_bad_lines="skip",
            engine="python",
        )
        print(f"\n  {'Pos':<5} {'Título':<45} {'Nota Predicha':<15}")
        print("  " + "-" * 65)
        for i, rec in enumerate(recomendaciones, 1):
            # Buscamos el título de la película en el catálogo
            match = df_movies[df_movies["tmdb_id"] == rec["tmdb_id"]]
            titulo = (
                match["titulo"].values[0]
                if not match.empty
                else f"ID: {rec['tmdb_id']}"
            )
            # Truncamos títulos largos para que queden bonitos
            if len(titulo) > 42:
                titulo = titulo[:39] + "..."
            print(f"  {i:<5} {titulo:<45} ⭐ {rec['predicted_rating']}")
    except Exception:
        # Si no tenemos el catálogo, mostramos solo los IDs
        for i, rec in enumerate(recomendaciones, 1):
            print(
                f"  {i}. tmdb_id={rec['tmdb_id']}  |  Nota predicha: {rec['predicted_rating']}"
            )

    print("\n  ¡Modelo SVD listo para producción!")
    print("=" * 70)
