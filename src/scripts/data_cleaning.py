import pandas as pd
import json
import os

#  LIMPIEZA DEL CATÁLOGO TMDB
def limpiar_catalogo_puro(tipo="movies"):
    print(f"Data Cleaning TMDB para {tipo.upper()}...")
    
    carpeta_tmdb = "series" if tipo == "shows" else "movies"
    nombre_archivo = "catalogo_series_tmdb.jsonl" if tipo == "shows" else "catalogo_peliculas_tmdb.jsonl"
    ruta_entrada = f"src/data/raw/tmdb/{carpeta_tmdb}/{nombre_archivo}"
    
    os.makedirs("src/data/clean", exist_ok=True)
    ruta_salida = f"src/data/clean/tmdb_{tipo}_limpio.csv"
    
    datos = []
    try:
        with open(ruta_entrada, 'r', encoding='utf-8') as f:
            for linea in f:
                if linea.strip():
                    datos.append(json.loads(linea))
    except FileNotFoundError:
        print(f"Error al buscar el archivo de TMDB en: {ruta_entrada}")
        return
                
    df = pd.DataFrame(datos)
    col_titulo = 'name' if tipo == "shows" else 'title'
    col_fecha = 'first_air_date' if tipo == "shows" else 'release_date'
    
    print(f"\n Auditoria de datos:")
    print(f"  -> Total de filas en bruto: {len(df)}")
    
    duplicados = df.duplicated(subset=['id']).sum()
    print(f"  -> Duplicados exactos (mismo ID): {duplicados}")
    
    sin_id = df['id'].isna().sum()
    sin_titulo = df[col_titulo].isna().sum()
    print(f"  -> Filas sin ID ({sin_id}) o sin Titulo ({sin_titulo}): {sin_id + sin_titulo}")
    
    futuro = 0
    if col_fecha in df.columns:
        fechas = pd.to_datetime(df[col_fecha], errors='coerce')
        futuro = (fechas > pd.to_datetime('2025-12-31')).sum()
        print(f"  -> Contenido del futuro (>2025): {futuro}")
        
    filas_esperadas = len(df) - duplicados - (sin_id + sin_titulo) - futuro
    print(f"  -> Filas reales esperadas tras la limpieza: {filas_esperadas}")
    
    print(f"\n Aplicando limpieza de datos...")
    
    df = df.rename(columns={'id': 'tmdb_id', col_titulo: 'titulo', col_fecha: 'fecha_estreno'})
    
    df = df.drop_duplicates(subset=['tmdb_id'])
    df = df.dropna(subset=['tmdb_id', 'titulo'])
    
    if 'overview' in df.columns:
        df['overview'] = df['overview'].fillna('Sin descripcion disponible.').astype(str).str.strip()
    
    for col_img in ['poster_path', 'backdrop_path']:
        if col_img in df.columns: 
            df[col_img] = df[col_img].fillna('')
            
    for col_num in ['popularity', 'vote_average', 'vote_count']:
        if col_num in df.columns: 
            df[col_num] = df[col_num].fillna(0)
            
    if 'genre_ids' in df.columns:
        df['genre_ids'] = df['genre_ids'].fillna('[]')
        
    if 'fecha_estreno' in df.columns:
        df['fecha_estreno'] = pd.to_datetime(df['fecha_estreno'], errors='coerce')
        df = df[(df['fecha_estreno'] <= pd.to_datetime('2025-12-31')) | (df['fecha_estreno'].isna())]
        df['fecha_estreno'] = df['fecha_estreno'].dt.strftime('%Y-%m-%d').fillna('Desconocida')
    
    df.to_csv(ruta_salida, index=False)
    print(f"TMDB limpios: {len(df)} filas guardadas en {ruta_salida}\n")

#  LIMPIEZA DE TENDENCIAS TRAKT 
def limpiar_tendencias_trakt(tipo="movies"):
    print(f"Data Cleaning TRAKT para {tipo.upper()}...")
    
    ruta_entrada = f"src/data/raw/trakt/{tipo}/trakt_{tipo}.csv"
    ruta_salida = f"src/data/clean/trakt_{tipo}_limpio.csv"
    
    try:
        df = pd.read_csv(ruta_entrada)
    except FileNotFoundError:
        print(f"No se encontro {ruta_entrada}. Saltando...")
        return
        
    filas_iniciales = len(df)
    
    df = df.dropna(subset=['tmdb_id'])
    df = df.drop_duplicates(subset=['tmdb_id'])
    df['tmdb_id'] = df['tmdb_id'].astype(int)
    
    # Imputación de nulos
    cols_bool = ['es_tendencia', 'es_popular']
    for col in cols_bool:
        if col in df.columns:
            df[col] = df[col].fillna(False)
            
    if 'espectadores_live' in df.columns:
        df['espectadores_live'] = df['espectadores_live'].fillna(0).astype(int)
            
    if 'certificacion' in df.columns:
        df['certificacion'] = df['certificacion'].fillna('NR')
        
    if 'titulo' in df.columns:
        df['titulo'] = df['titulo'].fillna('Desconocido')
        
    df.to_csv(ruta_salida, index=False)
    print(f"TRAKT limpios: {filas_iniciales} brutos -> {len(df)} limpios. -> {ruta_salida}\n")
    
#  LIMPIEZA DE RAITINGS TRAMOVILENSKT 
def limpiar_movielens():
    print("Data Cleaning MOVIELENS...")
          
    ruta_links_raw = "src/data/raw/movielens/links.csv"
    ruta_ratings_raw = "src/data/raw/movielens/ratings.csv"
    
    try:
        df_links = pd.read_csv(ruta_links_raw)
        df_ratings = pd.read_csv(ruta_ratings_raw)
        
        print(f"\n Auditoria de datos (Links):")
        print(f"  -> Total de filas en bruto: {len(df_links)}")
        sin_tmdbid = df_links['tmdbId'].isna().sum()
        print(f"  -> Filas sin tmdbId: {sin_tmdbid}")
        print(f"  -> Filas esperadas tras la limpieza: {len(df_links) - sin_tmdbid}")
        
        print(f"\n Auditoria de datos (Ratings):")
        print(f"  -> Total de filas en bruto: {len(df_ratings)}")
        duplicados_ratings = df_ratings.duplicated(subset=['userId', 'movieId']).sum()
        print(f"  -> Duplicados exactos (mismo usuario y pelicula): {duplicados_ratings}")
        print(f"  -> Filas esperadas tras la limpieza: {len(df_ratings) - duplicados_ratings}")
        
        print(f"\n Aplicando limpieza de datos...")
        
        # Limpieza de Links
        df_links = df_links.dropna(subset=['tmdbId'])
        df_links['tmdbId'] = df_links['tmdbId'].astype(int)
        df_links.to_csv("src/data/clean/links_limpio.csv", index=False)
        
        # Limpieza de Ratings
        df_ratings = df_ratings.drop_duplicates(subset=['userId', 'movieId'])
        df_ratings = df_ratings[['userId', 'movieId', 'rating']]
        df_ratings.to_csv("src/data/clean/ratings_limpio.csv", index=False)
        
        print(f"MOVIELENS limpios:")
        print(f"  -> Links: {len(df_links)} filas guardadas en src/data/clean/links_limpio.csv")
        print(f"  -> Ratings: {len(df_ratings)} filas guardadas en src/data/clean/ratings_limpio.csv\n")
        
    except FileNotFoundError:
        print("Error: No se encontraron los archivos crudos de MovieLens.")

if __name__ == "__main__":
    limpiar_catalogo_puro("shows")
    limpiar_catalogo_puro("movies")
    limpiar_tendencias_trakt("shows")
    limpiar_tendencias_trakt("movies")
    limpiar_movielens()