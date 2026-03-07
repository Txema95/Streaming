import pandas as pd
import os

def unificar_datos(tipo="movies"):
    print(f"Unificacion para {tipo.upper()}...")
    
    ruta_tmdb = f"src/data/clean/tmdb_{tipo}_limpio.csv"
    ruta_trakt = f"src/data/clean/trakt_{tipo}_limpio.csv"
    
    os.makedirs("src/data/ready", exist_ok=True)
    ruta_salida = f"src/data/ready/dataset_final_{tipo}.csv"
    
    try:
        df_base = pd.read_csv(ruta_tmdb)
    except FileNotFoundError:
        print(f"Falta el archivo limpio de TMDB: {ruta_tmdb}")
        return
        
    try:
        df_trakt = pd.read_csv(ruta_trakt)
        df_final = pd.merge(df_base, df_trakt, on='tmdb_id', how='left')
        
        if 'es_tendencia' in df_final.columns:
            df_final['es_tendencia'] = df_final['es_tendencia'].fillna(False).infer_objects(copy=False)
        if 'es_popular' in df_final.columns:
            df_final['es_popular'] = df_final['es_popular'].fillna(False).infer_objects(copy=False)
            
        if 'espectadores_live' in df_final.columns:
            df_final['espectadores_live'] = df_final['espectadores_live'].fillna(0).astype(int)
            
        if 'certificacion' in df_final.columns:
            df_final['certificacion'] = df_final['certificacion'].fillna('NR')
            
    except FileNotFoundError:
        print(f"No hay archivo Trakt limpio para {tipo}. Creando dataset solo con TMDB.")
        df_final = df_base
        
    if 'titulo_x' in df_final.columns:
        df_final = df_final.rename(columns={'titulo_x': 'titulo'}).drop(columns=['titulo_y'], errors='ignore')

    # --- NUEVO: FILTRO DE RATINGS (SOLO PARA PELÍCULAS) ---
    if tipo == "movies":
        try:
            df_ratings = pd.read_csv("src/data/ready/ratings_finales_ia.csv")
            peliculas_con_rating = df_ratings['tmdb_id'].unique()
            df_final = df_final[df_final['tmdb_id'].isin(peliculas_con_rating)]
            print(f"Filtro IA aplicado: Quedan {len(df_final)} peliculas validas con historial de ratings.")
        except FileNotFoundError:
            print("Aviso: No se encontro ratings_finales_ia.csv, no se pudo filtrar las peliculas.")
        
    df_final.to_csv(ruta_salida, index=False)
    print(f"Dataset unificado Guardado en: {ruta_salida}\n")

def preparar_matriz_ia():
    print("Unificando Matriz IA de MovieLens ...")
    
    ruta_links_clean = "src/data/clean/links_limpio.csv"
    ruta_ratings_clean = "src/data/clean/ratings_limpio.csv"
    ruta_salida = "src/data/ready/ratings_finales_ia.csv"
    
    try:
        df_links = pd.read_csv(ruta_links_clean)
        df_ratings = pd.read_csv(ruta_ratings_clean)
        
        df_ia = pd.merge(df_ratings, df_links[['movieId', 'tmdbId']], on='movieId', how='inner')
        df_ia = df_ia.rename(columns={'tmdbId': 'tmdb_id'})
        
        df_ia = df_ia[['userId', 'tmdb_id', 'rating']]
        
        df_ia.to_csv(ruta_salida, index=False)
        print(f"Matriz IA lista para entrenar. Guardado en: {ruta_salida}\n")
        
    except FileNotFoundError:
        print("Error: Faltan archivos limpios de MovieLens. Ejecuta data_cleaning.py primero.")

if __name__ == "__main__":
    # ¡IMPORTANTE! El orden cambia: Primero la matriz IA, luego usamos la matriz para filtrar movies
    preparar_matriz_ia()
    unificar_datos("movies")
    unificar_datos("shows")