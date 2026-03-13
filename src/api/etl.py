import csv
import json
import ast
from mysql.connector import Error
def normalizar_datos(fila, tipo):
    """
    Normaliza las diferencias entre los CSV de películas y series.
    Maneja variaciones en nombres de columnas y tipos de datos.
    """
    # 1. Manejo de géneros: de "[99, 10]" a una lista real de Python
    try:
        generos_raw = fila.get("genre_ids", "[]")
        # Algunos CSV vienen con comillas extra o formatos raros
        generos = ast.literal_eval(generos_raw)
    except:
        generos = []

    es_peli = tipo == "movie"

    # 2. Lógica para el campo 'video' (Solo en películas)
    # Si no existe (en series), por defecto es False (0)
    video_raw = fila.get("video", "False")
    video_bool = 1 if str(video_raw).lower() == "true" else 0

    # 3. Mapeo flexible de columnas y limpieza de fecha
    release_date_raw = fila.get("fecha_estreno", "").strip()
    
    # Si la fecha es "Desconocida", está vacía o no empieza por un número (año)
    # la seteamos como None para que MySQL la acepte como NULL
    if not release_date_raw or release_date_raw.lower() == "desconocida" or not release_date_raw[0].isdigit():
        release_date_final = None
    else:
        release_date_final = release_date_raw

    # 3. Mapeo flexible de columnas
    # Usamos .get() para las columnas que podrían llamarse distinto
    return {
        "tmdb_id": int(fila.get("tmdb_id", 0)) if fila.get("tmdb_id") else int(fila.get("id", 0)),
        "content_type": tipo,
        "title": fila.get("titulo") if fila.get("titulo") else fila.get("title"), # Ambos CSV parecen tener 'titulo'
        "video": video_bool,
        "original_title": fila.get("original_title") if es_peli else fila.get("original_name"),
        "overview": fila.get("overview", ""),
        "release_date": release_date_final, # Ambos CSV usan 'fecha_estreno'
        "original_language": fila.get("original_language", ""),
        "popularity": float(fila.get("popularity", 0)) if fila.get("popularity") else 0.0,
        "poster_path": fila.get("poster_path", ""),
        "backdrop_path": fila.get("backdrop_path", ""),
        "vote_average": float(fila.get("vote_average", 0)) if fila.get("vote_average") else 0.0,
        "vote_count": int(fila.get("vote_count", 0)) if fila.get("vote_count") else 0,
        "adult": 1 if str(fila.get("adult", "False")).lower() == "true" else 0,
        "generos": generos,
    }

def ejecutar_importacion(conexion, ruta_csv, tipo_contenido):
    cursor = conexion.cursor()
    
    sql_content = """
    INSERT INTO contents 
    (tmdb_id, content_type, title, video, original_title, overview, release_date, 
     original_language, popularity, poster_path, backdrop_path, vote_average, vote_count, adult, created_at)
    VALUES (%(tmdb_id)s, %(content_type)s, %(title)s, %(video)s, %(original_title)s, %(overview)s, 
            NULLIF(%(release_date)s, ''), %(original_language)s, %(popularity)s, 
            %(poster_path)s, %(backdrop_path)s, %(vote_average)s, %(vote_count)s, %(adult)s, NOW())
    ON DUPLICATE KEY UPDATE 
        title=VALUES(title), 
        video=VALUES(video),
        popularity=VALUES(popularity);
    """

    sql_genre = "INSERT IGNORE INTO content_genres (content_id, genre_id) VALUES (%s, %s)"

    batch_size = 5000  # Tamaño del lote
    datos_contents = []
    datos_relacionales = []
    total_importados = 0

    with open(ruta_csv, mode="r", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        for fila in lector:
            data = normalizar_datos(fila, tipo_contenido)
            
            # Extraer géneros
            ids_generos = data.pop("generos") 
            datos_contents.append(data)

            for g_id in ids_generos:
                datos_relacionales.append((data["tmdb_id"], g_id))

            # --- INSERTAR CUANDO LLEGAMOS AL TAMAÑO DEL LOTE ---
            if len(datos_contents) >= batch_size:
                try:
                    cursor.executemany(sql_content, datos_contents)
                    if datos_relacionales:
                        cursor.executemany(sql_genre, datos_relacionales)
                    
                    conexion.commit() # Guardamos este lote
                    total_importados += len(datos_contents)
                    print(f"Progreso: {total_importados} registros insertados...")
                    
                    # Limpiamos las listas para el siguiente lote
                    datos_contents = []
                    datos_relacionales = []
                except Error as e:
                    conexion.rollback()
                    print(f"Error en lote: {e}")
                    # Decidir si quieres continuar o detenerte aquí

        # --- INSERTAR EL ÚLTIMO RESTO (lo que no llegó a 5000) ---
        if datos_contents:
            cursor.executemany(sql_content, datos_contents)
            if datos_relacionales:
                cursor.executemany(sql_genre, datos_relacionales)
            conexion.commit()
            total_importados += len(datos_contents)

    print(f"Finalizado: {total_importados} registros totales de tipo {tipo_contenido}")
    cursor.close()

     
def limpiar_tablas_contenido(conexion):
    """
    Limpia las tablas de contenidos y relaciones de géneros 
    respetando la integridad referencial.
    """
    cursor = conexion.cursor()
    try:
        print("Iniciando limpieza de base de datos...")
        
        # 1. Desactivar temporalmente las restricciones de FK para un truncado rápido
        # (Opcional, pero recomendado si usas TRUNCATE)
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # 2. Limpiar primero la tabla de relaciones (hija)
        # TRUNCATE es más rápido que DELETE porque reinicia los contadores
        cursor.execute("TRUNCATE TABLE content_genres;")
        
        # 3. Limpiar la tabla principal (padre)
        cursor.execute("TRUNCATE TABLE contents;")

        # 4. Reactivar restricciones
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        conexion.commit()
        print("Tablas limpiadas correctamente (contents y content_genres).")

    except Error as e:
        conexion.rollback()
        print(f"Error al limpiar las tablas: {e}")
    finally:
        cursor.close()