"""
========================================================================================
 SCRIPT MAESTRO: ENTRENAMIENTO WIDE & DEEP
========================================================================================
 Este archivo importa nuestra arquitectura de 'rn.py' y carga los datos para entrenarla.

 ¿QUÉ ES EL MODELO WIDE & DEEP?
 Es una arquitectura híbrida de Google que combina dos formas de "pensar":

 1. LA PARTE "WIDE" (Ancha / Memoria Directa):
    - Literalmente memoriza qué usuario ha visto qué película mediante Embeddings directos.
    - Se encarga de las "excepciones" y correlaciones específicas ("A Juan le gusta Matrix").
    - Aporta precisión cruda basada en el historial exacto.

 2. LA PARTE "DEEP" (Profunda / Generalización):
    - Pasa los datos por varias capas ocultas (por ej. 64 y 32 neuronas).
    - Permite a la IA descubrir patrones ocultos y generalizar a cosas nuevas.
    - ("Si a Juan le gusta Matrix, a lo mejor le gusta Blade Runner porque comparten rasgos abstractos").

 La red suma los instintos de ambas partes para dar la predicción final.

 Importante:
 - Si se entrena con CPU se requerira de 30 a 40 horas.
 - Si se usa una GPU se reducira significativamente el tiempo de entrenamiento.
 - Nuestro caso usaremos toda la potencia de la GPU (mi caso una RTX 5060) si PyTorch+CUDA está instalado.
 - Se recomienda usar un entorno virtual con las dependencias instaladas.
========================================================================================
"""

import pandas as pd
import numpy as np
import time
import os
import pickle

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split

# Importamos nuestra Red Neuronal local

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
try:
    from src.networks.dl.rn_mlp import WideAndDeepModel
except ImportError:
    from networks.dl.rn_mlp import WideAndDeepModel

# -----------------------------------------------------------------------------------------
# CONFIGURACIÓN GLOBAL
# -----------------------------------------------------------------------------------------
ruta_ratings = "src/data/ready/ratings_finales_ia.csv"
ruta_modelo = (
    "src/models/jj/modelo_3_wnd.pth"  # Formato oficial de PyTorch para pesajes
)
ruta_mapeos = "src/models/jj/wnd_mappings.pkl"  # Necesario para recordar qué ID real es cada vector

# Parámetros del Deep Learning (Hiperparámetros)
BATCH_SIZE = (
    4096  # Cuántas valoraciones procesamos de golpe. Las GPU aman los lotes grandes.
)
EPOCHS = 10
LEARNING_RATE = 0.001

# Hacemos recomendaciones al 100% de tus usuarios.
MIN_RATINGS_USUARIO = 1
# Con 5 valoraciones por peli limpiamos un pelín el ruido de pelis raras
MIN_RATINGS_PELICULA = 5


# -----------------------------------------------------------------------------------------
# PASO 1: DATASET PERSONALIZADO DE PYTORCH
# -----------------------------------------------------------------------------------------
class RatingsDataset(Dataset):
    """
    Clase "Traductora" para PyTorch.
    PyTorch no entiende de Tablas (Pandas DataFrames), solo entiende de "Tensores" (Matrices matemáticas).
    Esta clase convierte nuestras columnas de Pandas (Usuarios, Películas y Notas) en Tensores que pueden
    inyectarse a la Tarjeta Gráfica masivamente.
    """

    def __init__(self, users, movies, ratings):
        self.users = torch.tensor(users, dtype=torch.long)
        self.movies = torch.tensor(movies, dtype=torch.long)
        self.ratings = torch.tensor(ratings, dtype=torch.float32)

    def __len__(self):
        return len(self.ratings)

    def __getitem__(self, idx):
        return self.users[idx], self.movies[idx], self.ratings[idx]


def cargar_y_preparar_datos():
    """
    Carga el CSV, aplica filtrado para hacerlo manejable en CPU,
    limpia los IDs para que sean secuenciales y los parte en Entrenamiento/Test.
    Los mappings guardados aqui son COHERENTES con el modelo entrenado.

    ¿Por qué limpiamos los IDs?
    En Deep Learning, si tienes el Usuario ID "10.000" pero solo tienes 50 usuarios,
    crear una matriz de tamaño 10.000 desperdiciaría gigas de memoria.
    Por eso "mapeamos" todo a índices consecutivos: 0, 1, 2, 3...
    """
    print("=" * 70)
    print("  MODELO 3: WIDE & DEEP (PyTorch) — Preparando Datos")
    print("=" * 70)

    print(f"\n  Leyendo {ruta_ratings}...")
    df = pd.read_csv(ruta_ratings)
    print(f"  -> Filas en bruto: {len(df):,}")

    # --- FILTRADO para CPU ---
    print(
        f"\n  Filtrando (usuario>={MIN_RATINGS_USUARIO} ratings, pelicula>={MIN_RATINGS_PELICULA} ratings)..."
    )
    conteo_u = df.groupby("userId").size()
    df = df[df["userId"].isin(conteo_u[conteo_u >= MIN_RATINGS_USUARIO].index)]
    conteo_m = df.groupby("tmdb_id").size()
    df = df[df["tmdb_id"].isin(conteo_m[conteo_m >= MIN_RATINGS_PELICULA].index)]
    print(f"  -> Filas tras filtro: {len(df):,}")

    # IMPORTANTE: nn.Embedding(N) necesita indices exactos de 0 a (N-1).
    print("\n  Creando indices continuos (Mapeos) para la Red Neuronal...")
    user_ids = df["userId"].unique()
    movie_ids = df["tmdb_id"].unique()

    user2idx = {o: i for i, o in enumerate(user_ids)}
    movie2idx = {o: i for i, o in enumerate(movie_ids)}

    df["user_idx"] = df["userId"].map(user2idx)
    df["movie_idx"] = df["tmdb_id"].map(movie2idx)

    num_users = len(user_ids)
    num_movies = len(movie_ids)

    print(f"  -> Usuarios unicos: {num_users:,}")
    print(f"  -> Peliculas unicas: {num_movies:,}")
    print(f"  -> Total puntuaciones: {len(df):,}")

    # Dividir en Entrenamiento (80%) y Test (20%) de forma robusta con Scikit-Learn
    # evitando problemas de índices duplicados de Pandas (.drop(index)) que corrompen el mapeo.
    print("\n  Aleatorizando y dividiendo 80/20...")
    df_train, df_test = train_test_split(df, test_size=0.2, random_state=42)

    # Guardamos el diccionario para predecir en el futuro desde el Backend
    with open(ruta_mapeos, "wb") as f:
        pickle.dump({"user2idx": user2idx, "movie2idx": movie2idx}, f)

    return df_train, df_test, num_users, num_movies


# -----------------------------------------------------------------------------------------
# PASO 2: ENTRENAMIENTO EN LA GRÁFICA (GPU)
# -----------------------------------------------------------------------------------------
def entrenar_modelo(df_train, df_test, num_users, num_movies):
    print("=" * 70)
    print("  MODELO 3: ENTRENAMIENTO EN GPU")
    print("=" * 70)

    # 1. Detectar hardware (¡Aquí brilla tu RTX 5060 de Anaconda!)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(
        f"\n  -> Dispositivo seleccionado: {device.type.upper()} "
        + (
            f"({torch.cuda.get_device_name(0)})"
            if device.type == "cuda"
            else "(Alerta: Estás usando CPU, será muy lento)"
        )
    )

    # 2. Instanciar y mover la red a la tarjeta gráfica
    # Aquí llamamos a la arquitectura (WideAndDeepModel) que definimos en `rn_mlp.py`.
    # - embedding_dim=32: Significa que cada usuario/película se resume en un vector de 32 números.
    # - hidden_layers=[64, 32]: La parte "Deep" pasará por dos capas neuronales reduciéndose en embudo.
    # El comando ".to(device)" coge el modelo y lo envía a la RAM de la Tarjeta Gráfica.
    model = WideAndDeepModel(
        num_users=num_users,
        num_movies=num_movies,
        embedding_dim=32,
        hidden_layers=[64, 32],
    ).to(device)

    # 3. Preparar los empaquetadores (DataLoaders) que inyectarán datos a la gráfica por bloques
    train_dataset = RatingsDataset(
        df_train["user_idx"].values,
        df_train["movie_idx"].values,
        df_train["rating"].values,
    )
    test_dataset = RatingsDataset(
        df_test["user_idx"].values,
        df_test["movie_idx"].values,
        df_test["rating"].values,
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # 4. Matemáticas de la predicción (Función de Pérdida y Optimizador)
    # MSELoss: Compara la predicción con la realidad usando Error Cuadrático Medio.
    criterio = nn.MSELoss()

    # Adam: Es el "Mecánico" que ajustará las tuercas (pesos) de la red neuronal basándose en el error.
    # El Learning Rate (0.001) define qué tan bruscos son los giros de tuerca al aprender.
    optimizador = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print(f"\n  Iniciando bucle Deep Learning de {EPOCHS} Epocas...")

    for epoch in range(EPOCHS):
        model.train()  # Poner la red en modo iterativo/aprendizaje
        total_loss = 0
        inicio_epoca = time.time()

        # Inyectar Lotes (Batches) a la máquina
        for i, (users, movies, ratings) in enumerate(train_loader):
            # Mandar datos a la gráfica
            users = users.to(device)
            movies = movies.to(device)
            ratings = ratings.to(device)

            # PASO A: Pensar la predicción (Forward Pass)
            # Pasamos los IDs a la red para que dé su opinión (nota esperada)
            predicciones = model(users, movies)

            # PASO B: Ver cuánto nos hemos equivocado (Pérdida cruzada / Loss)
            loss = criterio(predicciones, ratings)

            # PASO C: Aprender (Ajustar pesos hacia atrás / Backpropagation)
            optimizador.zero_grad()  # 1. Limpiamos la memoria de derivadas del paso anterior
            loss.backward()  # 2. Cálculo matemático de cómo deberian modificarse los pesos
            optimizador.step()  # 3. El optimizador (Adam) cambia efectivamente las redes neuronales

            # Acumulamos el error total de toda la época
            total_loss += loss.item() * len(ratings)

            # Progreso en vivo
            if i % 50 == 0 and i > 0:
                print(
                    f"    Batch {i:03d}/{len(train_loader)} | Loss actual: {loss.item():.4f}"
                )

        avg_train_loss = total_loss / len(train_dataset)
        tiempo_epoca = time.time() - inicio_epoca

        print(
            f"  Época {epoch + 1:02d}/{EPOCHS} | Train MSE: {avg_train_loss:.4f} | Tiempo: {tiempo_epoca:.1f}s"
        )

    print("\n  =======================================================")
    print("  Evaluando precision del modelo final sobre Test Set...")

    # Poner la red en modo "Congelado" (Solo predicción pura, sin aprender trampa del Test)
    model.eval()
    test_loss = 0
    test_mae = 0
    with (
        torch.no_grad()
    ):  # Apaga el Tracking de Gradientes para ahorrar el 50% de memoria vRAM
        for users, movies, ratings in test_loader:
            users, movies, ratings = (
                users.to(device),
                movies.to(device),
                ratings.to(device),
            )

            predicciones = model(users, movies)
            # Truco: Nadie puede votar fuera de 0.5 a 5.0, así que capamos la respuesta
            predicciones = torch.clamp(predicciones, 0.5, 5.0)

            test_loss += nn.MSELoss()(predicciones, ratings).item() * len(ratings)
            test_mae += nn.L1Loss()(predicciones, ratings).item() * len(ratings)

    rmse_final = (test_loss / len(test_dataset)) ** 0.5
    mae_final = test_mae / len(test_dataset)

    print(f"\n╔══════════════════════════════════════╗")
    print(f"  ║  RESULTADOS DE WIDE & DEEP           ║")
    print(f"  ╠══════════════════════════════════════╣")
    print(f"  ║  RMSE: {rmse_final:.4f}              ║")
    print(f"  ║  MAE:  {mae_final:.4f}               ║")
    print(f"  ╚══════════════════════════════════════╝")

    # 5. Guardado del cerebro entrenado (.pth para PyTorch, donde están los pesos)
    torch.save(model.state_dict(), ruta_modelo)
    tamano_mb = os.path.getsize(ruta_modelo) / (1024 * 1024)
    print(f"\n  Cerebro Wide&Deep guardado en {ruta_modelo} ({tamano_mb:.1f} MB)")
    print("=" * 70)


if __name__ == "__main__":
    df_train, df_test, num_u, num_m = cargar_y_preparar_datos()
    entrenar_modelo(df_train, df_test, num_u, num_m)
