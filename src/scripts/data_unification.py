import pandas as pd
import os

def unificar_capa_oro(tipo="movies"):
    print(f" Unificación para {tipo.upper()}...")
    
    # Leemos siempre de la carpeta CLEAN
    ruta_tmdb = f"src/data/clean/tmdb_{tipo}_limpio.csv"
    ruta_trakt = f"src/data/clean/trakt_{tipo}_limpio.csv"
    
    os.makedirs("src/data/ready", exist_ok=True)
    ruta_salida = f"src/data/ready/dataset_final_{tipo}.csv"
    
    try:
        df_base = pd.read_csv(ruta_tmdb)
    except FileNotFoundError:
        print(f" Falta el archivo limpio de TMDB: {ruta_tmdb}")
        return
        
    try:
        df_trakt = pd.read_csv(ruta_trakt)
        
        # LEFT JOIN: Mantenemos todas las filas de TMDB y añadimos info de Trakt
        df_final = pd.merge(df_base, df_trakt, on='tmdb_id', how='left')
        
        # Imputación post-cruce 
        if 'es_tendencia' in df_final.columns:
            df_final['es_tendencia'] = df_final['es_tendencia'].fillna(False)
        if 'es_popular' in df_final.columns:
            df_final['es_popular'] = df_final['es_popular'].fillna(False)
            
        if 'espectadores_live' in df_final.columns:
            df_final['espectadores_live'] = df_final['espectadores_live'].fillna(0).astype(int)
            
        if 'certificacion' in df_final.columns:
            df_final['certificacion'] = df_final['certificacion'].fillna('NR')
            
    except FileNotFoundError:
        print(f" No hay archivo Trakt limpio para {tipo}. Creando dataset solo con TMDB.")
        df_final = df_base
        
    # Limpieza de columnas duplicadas post-merge
    if 'titulo_x' in df_final.columns:
        df_final = df_final.rename(columns={'titulo_x': 'titulo'}).drop(columns=['titulo_y'], errors='ignore')
        
    df_final.to_csv(ruta_salida, index=False)
    print(f"dataset unificado Guardado en: {ruta_salida}\n")


def preparar_matriz_ia():
    print(" Preparando Matriz de Interacciones (MovieLens)...")
    ruta_links = "..."
    ruta_ratings = "..."
    ruta_salida = "src/data/ready/ratings_finales.csv"
    
    try:
        df_links = pd.read_csv(ruta_links)
        df_ratings = pd.read_csv(ruta_ratings)
        
        # INNER JOIN: Cruzamos valoraciones con links para obtener tmdbId
        df_ia = pd.merge(df_ratings, df_links[['movieId', 'tmdbId']], on='movieId', how='inner')
        df_ia = df_ia.rename(columns={'tmdbId': 'tmdb_id'})
        
        # Filtramos para quedarnos solo con lo necesario para entrenar la IA
        df_ia = df_ia[['userId', 'tmdb_id', 'rating']]
        df_ia = df_ia.dropna(subset=['tmdb_id'])
        df_ia['tmdb_id'] = df_ia['tmdb_id'].astype(int)
        
        df_ia.to_csv(ruta_salida, index=False)
        print(f" Raitings de MovieLens listo en -> {ruta_salida}\n")
        
    except FileNotFoundError:
        print(" Faltan archivos crudos de MovieLens")

if __name__ == "__main__":
    unificar_capa_oro("shows")
    unificar_capa_oro("movies")
