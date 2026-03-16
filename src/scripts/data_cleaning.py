import pandas as pd
import json
import os

###########################################################################################
#  LIMPIEZA DEL CATÁLOGO TMDB
###########################################################################################
def limpiar_catalogo_puro(tipo="movies"):
    print(f"Data Cleaning TMDB para {tipo.upper()}...")
    
    # Determina la carpeta y el nombre del archivo en función de si es para series o películas
    carpeta_tmdb = "series" if tipo == "shows" else "movies"
    nombre_archivo = (
        "catalogo_series_tmdb.jsonl"
        if tipo == "shows"
        else "catalogo_peliculas_tmdb.jsonl"
    )

    # La ruta de donde se leerá el archivo JSONL
    ruta_entrada = f"src/data/raw/tmdb/{carpeta_tmdb}/{nombre_archivo}"


    # La ruta donde se guardará el archivo CSV limpio
    ruta_salida = f"src/data/clean/tmdb_{tipo}_limpio.csv"

    datos = []
    try:
        # Abre el archivo JSONL y lee cada línea
        with open(ruta_entrada, "r", encoding="utf-8") as f:
            for linea in f:
                if linea.strip():  # Ignora las líneas vacías
                    datos.append(json.loads(linea))
    except FileNotFoundError:
        # Muestra un error si el archivo no existe
        print(f"Error al buscar el archivo de TMDB en: {ruta_entrada}")
        return

    # Convierte la lista de objetos JSON en un DataFrame de Pandas
    df = pd.DataFrame(datos)

    # Determina qué columnas usar para el título y la fecha según el tipo de contenido
    col_titulo = 'name' if tipo == "shows" else 'title'
    col_fecha = 'first_air_date' if tipo == "shows" else 'release_date'
    
    print(f"\n Auditoria de datos:")

    print(f"  -> Total de filas en bruto: {len(df)}")

    # Contamos duplicados exactos (mismo ID)
    duplicados = df.duplicated(subset=["id"]).sum()
    print(f"  -> Duplicados exactos (mismo ID): {duplicados}")

    # Contamos filas sin ID y sin Titulo
    sin_id = df["id"].isna().sum()
    sin_titulo = df[col_titulo].isna().sum()
    print(
        f"  -> Filas sin ID ({sin_id}) o sin Titulo ({sin_titulo}): {sin_id + sin_titulo}"
    )

    # Contamos filas con fechas futuras
    futuro = 0
    if col_fecha in df.columns:
        fechas = pd.to_datetime(df[col_fecha], errors="coerce")
        futuro = (fechas > pd.to_datetime("2025-12-31")).sum()
        print(f"  -> Contenido del futuro (>2025): {futuro}")
        
    print(f"\n Aplicando limpieza de datos estricta...")
    
    df = df.rename(columns={'id': 'tmdb_id', col_titulo: 'titulo', col_fecha: 'fecha_estreno'})

    # Eliminamos duplicados y filas con datos nulos
    df = df.drop_duplicates(subset=['tmdb_id'])
    df = df.dropna(subset=['tmdb_id', 'titulo'])
    #eliminamos filas sin géneros asociados
    if 'genre_ids' in df.columns:
        df = df[df['genre_ids'].notna()]
        df = df[df['genre_ids'].astype(str) != '[]']
    
    # Rellenamos valores nulos con "Sin descripcion disponible." para descripciones
    if 'overview' in df.columns:
        df['overview'] = df['overview'].fillna('Sin descripcion disponible.').astype(str).str.strip()
    # Rellenamos valores nulos con "" para imágenes
    for col_img in ['poster_path', 'backdrop_path']:
        if col_img in df.columns: 
            df[col_img] = df[col_img].fillna('')
    # Rellenamos valores nulos con 0 para estadísticas numéricas        
    for col_num in ['vote_average', 'vote_count']:
        if col_num in df.columns: 
            df[col_num] = df[col_num].fillna(0)
    # Asignamos una lista vacía como cadena si no hay géneros asociados      
    if 'fecha_estreno' in df.columns:
        df['fecha_estreno'] = pd.to_datetime(df['fecha_estreno'], errors='coerce')
        df = df[(df['fecha_estreno'] <= pd.to_datetime('2025-12-31')) | (df['fecha_estreno'].isna())]
        df['fecha_estreno'] = df['fecha_estreno'].dt.strftime('%Y-%m-%d').fillna('Desconocida')
    

    df.to_csv(ruta_salida, index=False)
    print(f"TMDB limpios y filtrados: {len(df)} filas guardadas en {ruta_salida}\n")


###########################################################################################
#  LIMPIEZA DE TENDENCIAS TRAKT
###########################################################################################


def limpiar_tendencias_trakt(tipo="movies"):
    # Imprime un mensaje indicando que comienza la limpieza de datos de Trakt
    print(f"Data Cleaning TRAKT para {tipo.upper()}...")

    # La ruta de entrada para el archivo CSV crudo de Trakt
    ruta_entrada = f"src/data/raw/trakt/{tipo}/trakt_{tipo}.csv"

    # La ruta de salida para guardar los datos limpios
    ruta_salida = f"src/data/clean/trakt_{tipo}_limpio.csv"

    try:
        # Intenta cargar los datos usando Pandas
        df = pd.read_csv(ruta_entrada)
    except FileNotFoundError:
        print(f"No se encontro {ruta_entrada}. Saltando...")
        return

    filas_iniciales = len(df)

    # Remueve filas las cuales no tengan tmdb_id y elimina duplicados basados en tmdb_id
    df = df.dropna(subset=["tmdb_id"])
    df = df.drop_duplicates(subset=["tmdb_id"])
    df["tmdb_id"] = df["tmdb_id"].astype(int)

    # Imputación de nulos
    # Rellena valores nulos con False para atributos booleanos
    cols_bool = ["es_tendencia", "es_popular"]
    for col in cols_bool:
        if col in df.columns:
            df[col] = df[col].fillna(False)

    # Asume 0 espectadores en vivo por si el dato no existe
    if "espectadores_live" in df.columns:
        df["espectadores_live"] = df["espectadores_live"].fillna(0).astype(int)

    # Asigna 'NR' (Not Rated) para clasificaciones de edad no proveidas
    if "certificacion" in df.columns:
        df["certificacion"] = df["certificacion"].fillna("NR")

    # Colocamos 'Desconocido' como nombre para titulos nulos
    if "titulo" in df.columns:
        df["titulo"] = df["titulo"].fillna("Desconocido")

    # Guarda el resultado final
    df.to_csv(ruta_salida, index=False)
    print(
        f"TRAKT limpios: {filas_iniciales} brutos -> {len(df)} limpios. -> {ruta_salida}\n"
    )


###########################################################################################
#  LIMPIEZA DE RAITINGS TRAMOVILENSKT
###########################################################################################


def limpiar_movielens():
    print("Data Cleaning MOVIELENS...")

    # Define las rutas para los datos crudos
    ruta_links_raw = "src/data/raw/movielens/links.csv"
    ruta_ratings_raw = "src/data/raw/movielens/ratings.csv"

    try:
        # Carga los DataFrames
        df_links = pd.read_csv(ruta_links_raw)
        df_ratings = pd.read_csv(ruta_ratings_raw)

        # Realiza auditoría inicial para los Links
        print(f"\n Auditoria de datos (Links):")
        print(f"  -> Total de filas en bruto: {len(df_links)}")
        sin_tmdbid = df_links["tmdbId"].isna().sum()
        print(f"  -> Filas sin tmdbId: {sin_tmdbid}")
        print(f"  -> Filas esperadas tras la limpieza: {len(df_links) - sin_tmdbid}")

        # Realiza auditoría inicial para los Ratings
        print(f"\n Auditoria de datos (Ratings):")
        print(f"  -> Total de filas en bruto: {len(df_ratings)}")
        duplicados_ratings = df_ratings.duplicated(subset=["userId", "movieId"]).sum()
        print(
            f"  -> Duplicados exactos (mismo usuario y pelicula): {duplicados_ratings}"
        )
        print(
            f"  -> Filas esperadas tras la limpieza: {len(df_ratings) - duplicados_ratings}"
        )

        print(f"\n Aplicando limpieza de datos...")

        # Limpieza de Links: elimina registros sin tmdbId y asegura un tipo numérico
        df_links = df_links.dropna(subset=["tmdbId"])
        df_links["tmdbId"] = df_links["tmdbId"].astype(int)
        df_links.to_csv("src/data/clean/links_limpio.csv", index=False)

        # Limpieza de Ratings: elimina duplicados por usuario y película
        df_ratings = df_ratings.drop_duplicates(subset=["userId", "movieId"])
        df_ratings = df_ratings[
            ["userId", "movieId", "rating"]
        ]  # Selecciona las columnas clave
        df_ratings.to_csv("src/data/clean/ratings_limpio.csv", index=False)

        print(f"MOVIELENS limpios:")
        print(
            f"  -> Links: {len(df_links)} filas guardadas en src/data/clean/links_limpio.csv"
        )
        print(
            f"  -> Ratings: {len(df_ratings)} filas guardadas en src/data/clean/ratings_limpio.csv\n"
        )

    except FileNotFoundError:
        print("Error: No se encontraron los archivos crudos de MovieLens.")


if __name__ == "__main__":
    # Ejecuta el flujo cuando el script se inicia directamente
    limpiar_catalogo_puro("shows")
    limpiar_catalogo_puro("movies")
    limpiar_tendencias_trakt("shows")
    limpiar_tendencias_trakt("movies")
    limpiar_movielens()
