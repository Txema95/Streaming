import pandas as pd
import os

def analizar_catalogo(tipo="movies"):
    print(f"\n==============================================")
    print(f"ANALISIS DE DATOS FINALES: {tipo.upper()}")
    print(f"==============================================")
    
    ruta = f"src/data/ready/dataset_final_{tipo}.csv"
    
    try:
        df = pd.read_csv(ruta)
    except FileNotFoundError:
        print(f"Error: No se encontro el archivo {ruta}")
        return
        
    total = len(df)
    print(f"Total de registros: {total}")
    
    # 1. Analisis de completitud (Calidad de datos)
    sin_desc = df['overview'].isin(['Sin descripcion disponible.', 'Sin descripción disponible.']) | df['overview'].isna()
    
    # ¡AQUÍ ESTÁ LA CORRECCIÓN DE LOS PARÉNTESIS!
    sin_generos = (df['genre_ids'] == '[]') | df['genre_ids'].isna()
    
    sin_poster = df['poster_path'].isna() | (df['poster_path'] == '')
    
    print("\n[1] Calidad de los Metadatos:")
    print(f"  -> Sin descripcion: {sin_desc.sum()} ({(sin_desc.sum()/total)*100:.2f}%)")
    print(f"  -> Sin generos asignados: {sin_generos.sum()} ({(sin_generos.sum()/total)*100:.2f}%)")
    print(f"  -> Sin poster: {sin_poster.sum()} ({(sin_poster.sum()/total)*100:.2f}%)")
    
    # 2. Analisis de negocio (Popularidad y Trakt)
    if 'es_tendencia' in df.columns:
        tendencias = df['es_tendencia'].sum()
        espectadores = df['espectadores_live'].sum()
        print("\n[2] Metricas de Negocio (Integracion Trakt):")
        print(f"  -> Titulos en tendencia ahora mismo: {tendencias}")
        print(f"  -> Total de espectadores en directo en el catalogo: {espectadores}")

    # 3. Analisis del Long Tail (Catalogo profundo)
    votos_minimos = df[df['vote_count'] > 1000]
    joyas = votos_minimos[(votos_minimos['vote_average'] > 7.5) & (votos_minimos['popularity'] < 50)]
    print("\n[3] Descubrimientos de Catalogo:")
    print(f"  -> Joyas ocultas (Nota > 7.5, pero baja popularidad): {len(joyas)}")


def analizar_ratings():
    print(f"\n==============================================")
    print(f"ANALISIS DE MATRIZ IA (MOVIELENS)")
    print(f"==============================================")
    
    ruta = "src/data/ready/ratings_finales_ia.csv"
    try:
        df = pd.read_csv(ruta)
    except FileNotFoundError:
        print(f"Error: No se encontro el archivo {ruta}")
        return
        
    total_ratings = len(df)
    usuarios_unicos = df['userId'].nunique()
    peliculas_unicas = df['tmdb_id'].nunique()
    
    print(f"Total de valoraciones: {total_ratings}")
    print(f"Usuarios unicos: {usuarios_unicos}")
    print(f"Peliculas valoradas: {peliculas_unicas}")
    
    # Calcular la densidad de la matriz (Dato clave para Machine Learning)
    posibles_interacciones = usuarios_unicos * peliculas_unicas
    densidad = (total_ratings / posibles_interacciones) * 100
    
    print("\n[Metricas de Machine Learning]:")
    print(f"  -> Interacciones posibles: {posibles_interacciones}")
    print(f"  -> Densidad de la matriz: {densidad:.2f}%")
    print(f"  -> Sparsity (Vacio a predecir): {(100-densidad):.2f}%")

if __name__ == "__main__":
    analizar_catalogo("shows")
    analizar_catalogo("movies")
    analizar_ratings()