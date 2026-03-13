import pandas as pd
import os

def unificar_datos(tipo="movies"):
    print(f"Unificacion para {tipo.upper()}...")

    # Leemos siempre de la carpeta CLEAN para asegurar la calidad de datos

    ruta_tmdb = f"src/data/clean/tmdb_{tipo}_limpio.csv"
    ruta_trakt = f"src/data/clean/trakt_{tipo}_limpio.csv"

    # Creamos la ruta de salida, el directorio "ready"
    os.makedirs("src/data/ready", exist_ok=True)
    ruta_salida = f"src/data/ready/dataset_final_{tipo}.csv"

    try:
        # Cargamos el dataset base que contiene datos exhaustivos de TMDB
        df_base = pd.read_csv(ruta_tmdb)
    except FileNotFoundError:
        print(f"Falta el archivo limpio de TMDB: {ruta_tmdb}")
        return

    try:
        # Cargamos el dataset de metadatos de tendencias desde Trakt
        df_trakt = pd.read_csv(ruta_trakt)
        # LEFT JOIN: Mantenemos todas las filas de TMDB y añadimos info de Trakt
        df_final = pd.merge(df_base, df_trakt, on='tmdb_id', how='left')

        # Imputación post-cruce para manejar valores nulos que surgen del JOIN
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
    # Limpieza de columnas duplicadas post-merge    
    if 'titulo_x' in df_final.columns:
        df_final = df_final.rename(columns={'titulo_x': 'titulo'}).drop(columns=['titulo_y'], errors='ignore')

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

    print("Unificando Matriz IA de MovieLens...")

    ruta_links_clean = "src/data/clean/links_limpio.csv"
    ruta_ratings_clean = "src/data/clean/ratings_limpio.csv"
    ruta_salida = "src/data/ready/ratings_finales_ia.csv"

    try:
        df_links = pd.read_csv(ruta_links_clean)
        df_ratings = pd.read_csv(ruta_ratings_clean)
        # INNER JOIN: Cruzamos valoraciones con los links para conseguir el tmdbId
        df_ia = pd.merge(df_ratings, df_links[['movieId', 'tmdbId']], on='movieId', how='inner')
    # Renombramos para estandarizar con el resto de la base de datos
        df_ia = df_ia.rename(columns={'tmdbId': 'tmdb_id'})
        # Reordenamos columnas (userId, tmdb_id, rating)
        df_ia = df_ia[['userId', 'tmdb_id', 'rating']]
        

        df_ia.to_csv(ruta_salida, index=False)
        print(f"Matriz IA lista para entrenar. Guardado en: {ruta_salida}\n")

    except FileNotFoundError:
        print(
            "Error: Faltan archivos limpios de MovieLens. Ejecuta data_cleaning.py primero."
        )


if __name__ == "__main__":
    preparar_matriz_ia()
    unificar_datos("movies")
    unificar_datos("shows")