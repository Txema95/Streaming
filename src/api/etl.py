import csv
import json
import ast
from mysql.connector import Error


def normalizar_datos(fila, tipo):
    """Normaliza las diferencias entre el CSV de películas y series"""
    # Manejo de géneros: de "[99, 10]" a una lista real de Python
    try:
        generos = ast.literal_eval(fila["genre_ids"])
    except:
        generos = []

    # Mapeo de campos según el tipo
    es_peli = tipo == "movie"

    return {
        "tmdb_id": int(fila["id"]),
        "content_type": tipo,
        "title": fila["title"] if es_peli else fila["name"],
        "original_title": fila["original_title"] if es_peli else fila["original_name"],
        "overview": fila["overview"],
        "release_date": fila["release_date"] if es_peli else fila["first_air_date"],
        "original_language": fila["original_language"],
        "popularity": float(fila["popularity"]) if fila["popularity"] else 0.0,
        "poster_path": fila["poster_path"],
        "backdrop_path": fila["backdrop_path"],
        "vote_average": float(fila["vote_average"]) if fila["vote_average"] else 0.0,
        "vote_count": int(fila["vote_count"]) if fila["vote_count"] else 0,
        "adult": 1 if fila["adult"].lower() == "true" else 0,
        "generos": generos,
    }


def ejecutar_importacion(conexion, ruta_csv, tipo_contenido):
    cursor = conexion.cursor()

    # SQL para insertar contenido (si ya existe, actualiza con ON DUPLICATE KEY)
    sql_content = """
    INSERT INTO contents 
    (tmdb_id, content_type, title, original_title, overview, release_date, 
     original_language, popularity, poster_path, backdrop_path, vote_average, vote_count, adult, created_at)
    VALUES (%(tmdb_id)s, %(content_type)s, %(title)s, %(original_title)s, %(overview)s, 
            NULLIF(%(release_date)s, ''), %(original_language)s, %(popularity)s, 
            %(poster_path)s, %(backdrop_path)s, %(vote_average)s, %(vote_count)s, %(adult)s, NOW())
    ON DUPLICATE KEY UPDATE title=VALUES(title), popularity=VALUES(popularity);
    """

    sql_genre = (
        "INSERT IGNORE INTO content_genres (content_id, genre_id) VALUES (%s, %s)"
    )

    datos_contents = []
    datos_relacionales = []

    with open(ruta_csv, mode="r", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        for fila in lector:
            data = normalizar_datos(fila, tipo_contenido)
            # 1. Extraemos los géneros para la otra tabla
            ids_generos = data.pop("generos")  # .pop() saca el elemento y lo devuelve

            datos_contents.append(data)

            # Preparar relaciones de géneros
            for g_id in ids_generos:
                datos_relacionales.append((data["tmdb_id"], g_id))

    try:
        # 1. Insertar contenidos en bloque
        cursor.executemany(sql_content, datos_contents)

        # 2. Insertar relaciones de géneros en bloque
        if datos_relacionales:
            cursor.executemany(sql_genre, datos_relacionales)

        conexion.commit()
        print(f"Importados {len(datos_contents)} registros de tipo {tipo_contenido}")

    except Error as e:
        conexion.rollback()
        print(f"Error durante la importación: {e}")
    finally:
        cursor.close()
