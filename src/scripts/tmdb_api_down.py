import requests
import json
import time
import os
import calendar  # Nos ayuda a saber cuántos días tiene cada mes
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

def descargar_series_por_mes(ano_inicio=1990, ano_fin=2025):
    print("Iniciando extracción masiva de series mes a mes (Tolerancia a fallos: Activada)...")
    
    carpeta_destino = "src/data/raw/tmdb/series"
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_archivo = os.path.join(carpeta_destino, 'catalogo_series_tmdb.jsonl')
    
    # 'a' (append) permite detener el script y retomarlo sin borrar lo anterior
    with open(ruta_archivo, 'a', encoding='utf-8') as archivo:
        
        for ano in range(ano_inicio, ano_fin + 1):
            for mes in range(1, 13):
                # Averiguamos el último día de este mes en concreto
                _, ultimo_dia = calendar.monthrange(ano, mes)
                
                # Formateamos las fechas a YYYY-MM-DD
                fecha_inicio = f"{ano}-{mes:02d}-01"
                fecha_fin = f"{ano}-{mes:02d}-{ultimo_dia:02d}"
                
                print(f"\n--- Descargando estrenos del {fecha_inicio} al {fecha_fin} ---")
                pagina_actual = 1
                
                while pagina_actual <= 500: # Ahora es matemáticamente imposible llegar a 500
                    url = f"{BASE_URL}/discover/tv"
                    parametros = {
                        "api_key": API_KEY, 
                        "language": "es-ES", 
                        "page": pagina_actual,
                        "sort_by": "popularity.desc",
                        "first_air_date.gte": fecha_inicio,
                        "first_air_date.lte": fecha_fin
                    }
                    
                    respuesta = requests.get(url, params=parametros)
                    
                    if respuesta.status_code == 200:
                        datos = respuesta.json()
                        resultados = datos.get("results", [])
                        
                        if not resultados:
                            # Si la página está vacía, saltamos al mes siguiente
                            break 
                            
                        for serie in resultados:
                            archivo.write(json.dumps(serie, ensure_ascii=False) + '\n')
                            
                        print(f"[{fecha_inicio[:7]}] Página {pagina_actual} guardada.")
                        pagina_actual += 1
                        time.sleep(0.25) 
                        
                    elif respuesta.status_code == 429:
                        print("Límite de API. Esperando 10 segundos para descongestionar...")
                        time.sleep(10)
                        
                    else:
                        print(f"Error HTTP {respuesta.status_code} en página {pagina_actual}. Saltando...")
                        break

def descargar_peliculas_por_mes(ano_inicio=1990, ano_fin=2025):
    print("Iniciando extracción masiva mes a mes (Tolerancia a fallos: Activada)...")
    
    carpeta_destino = "src/data/raw/tmdb/movies"
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_archivo = os.path.join(carpeta_destino, 'catalogo_movies_tmdb.jsonl')
    
    # 'a' (append) permite detener el script y retomarlo sin borrar lo anterior
    with open(ruta_archivo, 'a', encoding='utf-8') as archivo:
        
        for ano in range(ano_inicio, ano_fin + 1):
            for mes in range(1, 13):
                # Averiguamos el último día de este mes en concreto
                _, ultimo_dia = calendar.monthrange(ano, mes)
                
                # Formateamos las fechas a YYYY-MM-DD
                fecha_inicio = f"{ano}-{mes:02d}-01"
                fecha_fin = f"{ano}-{mes:02d}-{ultimo_dia:02d}"
                
                print(f"\n--- Descargando estrenos del {fecha_inicio} al {fecha_fin} ---")
                pagina_actual = 1
                
                while pagina_actual <= 500: # Ahora es matemáticamente imposible llegar a 500
                    url = f"{BASE_URL}/discover/movie"
                    parametros = {
                        "api_key": API_KEY, 
                        "language": "es-ES", 
                        "page": pagina_actual,
                        "sort_by": "popularity.desc",
                        "release_date.gte": fecha_inicio,
                        "release_date.lte": fecha_fin
                    }
                    
                    respuesta = requests.get(url, params=parametros)
                    
                    if respuesta.status_code == 200:
                        datos = respuesta.json()
                        resultados = datos.get("results", [])
                        
                        if not resultados:
                            # Si la página está vacía, saltamos al mes siguiente
                            break 
                            
                        for pelis in resultados:
                            archivo.write(json.dumps(pelis, ensure_ascii=False) + '\n')
                            
                        print(f"[{fecha_inicio[:7]}] Página {pagina_actual} guardada.")
                        pagina_actual += 1
                        time.sleep(0.25) 
                        
                    elif respuesta.status_code == 429:
                        print("Límite de API. Esperando 10 segundos para descongestionar...")
                        time.sleep(10)
                        
                    else:
                        print(f"Error HTTP {respuesta.status_code} en página {pagina_actual}. Saltando...")
                        break

# Ejecutamos la función
descargar_series_por_mes(ano_inicio=2020, ano_fin=2025)
descargar_peliculas_por_mes(ano_inicio=2020, ano_fin=2025)