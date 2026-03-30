import pandas as pd
import numpy as np
import os
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
import tensorflow as tf
from tensorflow.keras import layers, models

# Configuración de rutas
CACHE_DIR = 'src/data/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

PATH_DF_PREP = os.path.join(CACHE_DIR, 'df_prep.parquet')
PATH_USER_ENC = os.path.join(CACHE_DIR, 'user_encoder.joblib')
PATH_ITEM_ENC = os.path.join(CACHE_DIR, 'item_encoder.joblib')

def get_processed_data(force_reprocess=False):
    # Comprobar si el caché existe
    if not force_reprocess and os.path.exists(PATH_DF_PREP):
        print("Cargando datos desde el caché (Parquet)...")
        df_prep = pd.read_parquet(PATH_DF_PREP)
        user_enc = joblib.load(PATH_USER_ENC)
        item_enc = joblib.load(PATH_ITEM_ENC)
    else:
        print("Procesando datos originales...")
        # 1. Cargar Datasets originales
        df_ratings = pd.read_csv('src/data/ready/ratings_finales_ia.csv')
        
        # 2. Limpieza y Codificación
        df_ratings = df_ratings.drop_duplicates(['userId', 'tmdb_id'])
        
        user_enc = LabelEncoder()
        item_enc = LabelEncoder()
        
        df_ratings['user_idx'] = user_enc.fit_transform(df_ratings['userId'])
        df_ratings['item_idx'] = item_enc.fit_transform(df_ratings['tmdb_id'])
        
        # 3. Filtrado por relevancia (mínimo 5 reviews)
        min_ratings = 5
        counts = df_ratings['item_idx'].value_counts()
        df_prep = df_ratings[df_ratings['item_idx'].isin(counts[counts > min_ratings].index)].copy()
        
        # Optimizamos tipos de datos para ahorrar RAM
        df_prep['rating'] = df_prep['rating'].astype(np.float32)
        df_prep['user_idx'] = df_prep['user_idx'].astype(np.int32)
        df_prep['item_idx'] = df_prep['item_idx'].astype(np.int32)

        # 4. Guardar en Caché
        df_prep.to_parquet(PATH_DF_PREP)
        joblib.dump(user_enc, PATH_USER_ENC)
        joblib.dump(item_enc, PATH_ITEM_ENC)
        print("Caché generado con éxito.")

    return df_prep, user_enc, item_enc

# Ejecución rápida
df_prep, user_encoder, item_encoder = get_processed_data()

# 5. Crear la Matriz de Usuario-Ítem (Esto siempre es rápido en memoria con CSR)
user_item_matrix = csr_matrix((df_prep['rating'], (df_prep['user_idx'], df_prep['item_idx'])))

print(f"--- Estadísticas ---")
print(f"Usuarios: {df_prep['user_idx'].nunique()} | Items: {df_prep['item_idx'].nunique()}")
print(f"Densidad: {user_item_matrix.nnz / (user_item_matrix.shape[0] * user_item_matrix.shape[1]):.4%}")


###########################################################################################################################
##MATRIX FACTORIZATION 
# Configuración de rutas para el modelo
CACHE_DIR = 'src/data/cache'
PATH_MODEL_MF = os.path.join(CACHE_DIR, 'model_svd.joblib')
PATH_USER_FACTORS = os.path.join(CACHE_DIR, 'user_factors.npy')
PATH_ITEM_FACTORS = os.path.join(CACHE_DIR, 'item_factors.npy')

def train_matrix_factorization(user_item_matrix, n_components=50, force_train=False):
    """
    Entrena SVD para obtener los factores latentes (ADN) de usuarios y películas.
    n_components: Cantidad de 'temas' o factores latentes (ej. 50 dimensiones).
    """
    
    if not force_train and os.path.exists(PATH_MODEL_MF):
        print("Cargando modelo MF y factores latentes desde caché...")
        svd = joblib.load(PATH_MODEL_MF)
        user_factors = np.load(PATH_USER_FACTORS)
        item_factors = np.load(PATH_ITEM_FACTORS)
    else:
        print(f"Entrenando Matrix Factorization (SVD) con {n_components} componentes...")
        
        # Inicializar y entrenar SVD
        # random_state asegura que el 'Usuario Ideal' sea el mismo en cada prueba
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        
        # user_factors (P): Cómo se relaciona cada usuario con los 50 temas
        user_factors = svd.fit_transform(user_item_matrix)
        
        # item_factors (Q): Cómo se relaciona cada película con los 50 temas
        item_factors = svd.components_.T
        
        # Guardar en caché
        joblib.dump(svd, PATH_MODEL_MF)
        np.save(PATH_USER_FACTORS, user_factors)
        np.save(PATH_ITEM_FACTORS, item_factors)
        print("Modelo y factores guardados.")

    return svd, user_factors, item_factors

# 1. Asumiendo que ya tienes 'user_item_matrix' del paso anterior
# Ejecutamos el entrenamiento (n_components=50 es un estándar balanceado)
model_svd, P, Q = train_matrix_factorization(user_item_matrix, n_components=50)

print(f"Dimensiones de Matriz de Usuarios (P): {P.shape}")
print(f"Dimensiones de Matriz de Ítems (Q): {Q.shape}")

##################################################################################################
# paso 3 clustering de usuarios
# Configuración de rutas para el caché del clustering
CACHE_DIR = 'src/data/cache'
PATH_CLUSTER_MODEL = os.path.join(CACHE_DIR, 'model_kmeans.joblib')
PATH_USER_CLUSTERS = os.path.join(CACHE_DIR, 'user_clusters.npy')

def perform_user_clustering(user_factors, n_clusters=20, force_train=False):
    """
    Agrupa a los usuarios basándose en sus factores latentes (Matriz P).
    n_clusters: Número de 'comunidades' de usuarios (ej. 20 grupos).
    """
    
    if not force_train and os.path.exists(PATH_CLUSTER_MODEL):
        print("Cargando clustering desde caché...")
        kmeans = joblib.load(PATH_CLUSTER_MODEL)
        user_labels = np.load(PATH_USER_CLUSTERS)
    else:
        print(f"Entrenando K-Means para {n_clusters} clusters...")
        
        # Usamos los factores latentes de los usuarios (P) para agrupar
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        user_labels = kmeans.fit_predict(user_factors)
        
        # Guardar en caché
        joblib.dump(kmeans, PATH_CLUSTER_MODEL)
        np.save(PATH_USER_CLUSTERS, user_labels)
        print("Clustering completado y guardado.")

    return kmeans, user_labels

# 1. Ejecutar el clustering
model_kmeans, user_clusters = perform_user_clustering(P, n_clusters=20)

# 2. Ejemplo de uso: Encontrar usuarios similares (Cosine Similarity)
def get_similar_users_in_cluster(user_idx, user_factors, user_labels, top_n=10):
    """
    Busca usuarios similares pero SOLO dentro del mismo cluster para ser eficiente.
    """
    # Identificar el cluster del usuario objetivo
    target_cluster = user_labels[user_idx]
    
    # Filtrar usuarios que están en el mismo cluster
    in_cluster_indices = np.where(user_labels == target_cluster)[0]
    in_cluster_factors = user_factors[in_cluster_indices]
    
    # Calcular similitud de coseno solo con los miembros del cluster
    target_vector = user_factors[user_idx].reshape(1, -1)
    sims = cosine_similarity(target_vector, in_cluster_factors)[0]
    
    # Obtener los top_n más similares (excluyendo al propio usuario)
    rel_indices = np.argsort(sims)[-(top_n+1):-1][::-1]
    
    return in_cluster_indices[rel_indices], sims[rel_indices]

# Prueba rápida con el primer usuario (índice 0)
similar_users, similarity_scores = get_similar_users_in_cluster(0, P, user_clusters)

print(f"Cluster del usuario 0: {user_clusters[0]}")
print(f"Usuarios más similares en su comunidad: {similar_users}")
print(f"Scores de similitud: {similarity_scores}")


##################################################################################################
# paso 4 Neural Collaborative Filtering

PATH_MODEL_NCF = os.path.join(CACHE_DIR, 'model_ncf.h5')

def get_ncf_model(num_users, num_items, latent_dim=16):
    # Entradas
    user_input = layers.Input(shape=(1,), name='user_input')
    item_input = layers.Input(shape=(1,), name='item_input')

    # Embeddings para la parte MLP
    user_embedding_mlp = layers.Embedding(num_users, latent_dim, name='user_emb_mlp')(user_input)
    item_embedding_mlp = layers.Embedding(num_items, latent_dim, name='item_emb_mlp')(item_input)
    
    # Embeddings para la parte GMF
    user_embedding_gmf = layers.Embedding(num_users, latent_dim, name='user_emb_gmf')(user_input)
    item_embedding_gmf = layers.Embedding(num_items, latent_dim, name='item_emb_gmf')(item_input)

    # Rama 1: MLP (Concatenación + Capas Densas)
    mlp_vector = layers.Flatten()(layers.Concatenate()([user_embedding_mlp, item_embedding_mlp]))
    mlp_vector = layers.Dense(32, activation='relu')(mlp_vector)
    mlp_vector = layers.Dense(16, activation='relu')(mlp_vector)

    # Rama 2: GMF (Producto elemento a elemento)
    gmf_vector = layers.Flatten()(layers.Multiply()([user_embedding_gmf, item_embedding_gmf]))

    # Combinación de ambas ramas (NeuMF)
    combined = layers.Concatenate()([mlp_vector, gmf_vector])
    output = layers.Dense(1, activation='linear', name='prediction')(combined)

    model = models.Model(inputs=[user_input, item_input], outputs=output)
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def train_ncf(df_prep, num_users, num_items, epochs=5, batch_size=256, force_train=False):
    if not force_train and os.path.exists(PATH_MODEL_NCF):
        print("Cargando modelo NCF desde caché...")
        model = models.load_model(PATH_MODEL_NCF)
    else:
        print("Entrenando modelo Neural Collaborative Filtering...")
        model = get_ncf_model(num_users, num_items)
        
        # Preparar datos de entrenamiento
        x_user = df_prep['user_idx'].values
        x_item = df_prep['item_idx'].values
        y = df_prep['rating'].values
        
        model.fit(
            [x_user, x_item], y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.1,
            verbose=1
        )
        
        model.save(PATH_MODEL_NCF)
        print("Modelo NCF guardado en caché.")
    
    return model

# 1. Obtener dimensiones
num_users = df_prep['user_idx'].max() + 1
num_items = df_prep['item_idx'].max() + 1

# 2. Entrenar o cargar el modelo
ncf_model = train_ncf(df_prep, num_users, num_items)