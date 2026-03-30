import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from scipy.sparse import csr_matrix

# 1. Cargar Datasets
df_movies = pd.read_csv('src/data/ready/dataset_final_movies.csv')
df_ratings = pd.read_csv('src/data/ready/ratings_finales_ia.csv')
df_trakt_m = pd.read_csv('src/data/ready/trakt_movies.csv')
df_trakt_s = pd.read_csv('src/data/ready/trakt_shows.csv')

def preprocess_data(ratings, movies):
    # Eliminar duplicados si existen
    ratings = ratings.drop_duplicates(['userId', 'tmdb_id'])
    
    # --- CODIFICACIÓN DE ÍNDICES (Crucial para NCF) ---
    # Creamos encoders para transformar IDs originales en índices de 0 a N
    user_enc = LabelEncoder()
    item_enc = LabelEncoder()
    
    ratings['user_idx'] = user_enc.fit_transform(ratings['userId'])
    ratings['item_idx'] = item_enc.fit_transform(ratings['tmdb_id'])
    
    # Mapeo para recuperar info después
    item_map = ratings[['tmdb_id', 'item_idx']].drop_duplicates()
    
    # --- FILTRADO DE DATOS (Eficiencia) ---
    # Solo nos quedamos con películas que tengan un mínimo de interacciones 
    # para evitar el "ruido" en el modelo de máster.
    min_ratings = 5
    filter_items = ratings['item_idx'].value_counts() > min_ratings
    filter_items = filter_items[filter_items].index.tolist()
    ratings_filtered = ratings[ratings['item_idx'].isin(filter_items)]
    
    return ratings_filtered, user_enc, item_enc

df_prep, user_encoder, item_encoder = preprocess_data(df_ratings, df_movies)

# 2. Crear la Matriz de Usuario-Ítem (Para Matrix Factorization y Similitud)
def create_sparse_matrix(df):
    # Usamos formato CSR (Compressed Sparse Row) para eficiencia en memoria
    return csr_matrix((df['rating'], (df['user_idx'], df['item_idx'])))

user_item_matrix = create_sparse_matrix(df_prep)

print(f"Usuarios únicos: {df_prep['user_idx'].nunique()}")
print(f"Items únicos: {df_prep['item_idx'].nunique()}")
print(f"Densidad de la matriz: {user_item_matrix.nnz / (user_item_matrix.shape[0] * user_item_matrix.shape[1]):.4%}")