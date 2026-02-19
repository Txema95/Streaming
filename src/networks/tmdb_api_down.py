import requests
import json
import time

# Sustituye esto por tu clave real de TMDB
API_KEY = "TU_API_KEY_AQUI"
BASE_URL = "https://api.themoviedb.org/3"

def obtener_series(paginas=5):
    """
    Descarga el catálogo de series populares de TMDB.
    """
    todas_las_series = []
    
    print(f"Iniciando la descarga de {paginas} páginas de series...")

    for pagina in range(1, paginas + 1):
        # Endpoint para descubrir series de TV ordenadas por popularidad
        url = f"{BASE_URL}/discover/tv"
        parametros = {
            "api_key": API_KEY,
            "language": "es-ES", # Para tener sinopsis y títulos en español
            "sort_by": "popularity.desc",
            "page": pagina
        }

        respuesta = requests.get(url, params=parametros)

        if respuesta.status_code == 200:
            datos = respuesta.json()
            resultados = datos.get("results", [])
            todas_las_series.extend(resultados)
            print(f"Página {pagina} descargada con éxito ({len(resultados)} series).")
        else:
            print(f"Error en la página {pagina}: {respuesta.status_code}")
            break
            
        # Buenas prácticas: pausa de medio segundo para no saturar la API
        time.sleep(0.5) 

    return todas_las_series

# Ejecutamos la función (ejemplo: descargamos 5 páginas = 100 series)
catalogo_series = obtener_series(paginas=5)

# Guardamos los datos en un archivo JSON local
with open('catalogo_series_tmdb.json', 'w', encoding='utf-8') as archivo:
    json.dump(catalogo_series, archivo, ensure_ascii=False, indent=4)

print(f"\n¡Proceso completado! Se han guardado {len(catalogo_series)} series en 'catalogo_series_tmdb.json'.")