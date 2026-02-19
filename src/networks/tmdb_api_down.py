import requests
import json
import time
import os 

API_KEY = "75a85e69010ab0deb4646e3866d31631"
BASE_URL = "https://api.themoviedb.org/3"

def descargar_series_masivo(paginas_totales=8000):
    print("Iniciando descarga masiva...")
    
    # 2. Ruta de destino y creamos las carpetas si no existen
    carpeta_destino = "src/data/raw/tmdb/series"
    os.makedirs(carpeta_destino, exist_ok=True) 
    
    # 3. Construimos la ruta completa del archivo
    ruta_archivo = os.path.join(carpeta_destino, 'catalogo_series_tmdb.jsonl')
    
    # Usamos la nueva ruta al abrir el archivo
    with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
        
        pagina_actual = 1
        
        while pagina_actual <= paginas_totales:
            url = f"{BASE_URL}/discover/tv"
            parametros = {
                "api_key": API_KEY, 
                "language": "es-ES", 
                "page": pagina_actual,
                "sort_by": "popularity.desc"
            }
            
            respuesta = requests.get(url, params=parametros)
            
            if respuesta.status_code == 200:
                datos = respuesta.json()
                resultados = datos.get("results", [])
                
                if not resultados:
                    print("No hay más series disponibles. Fin de la descarga.")
                    break
                    
                for serie in resultados:
                    archivo.write(json.dumps(serie, ensure_ascii=False) + '\n')
                    
                print(f"Página {pagina_actual} guardada correctamente en {carpeta_destino}")
                pagina_actual += 1
                
                time.sleep(0.25) 
                
            elif respuesta.status_code == 429:
                print("\n⚠️ Límite de la API alcanzado. Esperando 10 segundos...")
                time.sleep(10)
                
            else:
                print(f"\n❌ Error fatal {respuesta.status_code} en la página {pagina_actual}.")
                break

# Ejecutamos la prueba con un par de páginas para verificar que crea las carpetas
descargar_series_masivo(paginas_totales=5)