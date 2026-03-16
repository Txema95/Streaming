import requests
import pandas as pd
import os
import time

# --- CONFIGURACIÓN ---
TRAKT_CLIENT_ID = "9419ec6a85b467e556fd4a83e5b42110c1af6a9ed9df092d4433e2a4f5ba96e3" 
HEADERS = {
    'Content-Type': 'application/json',
    'trakt-api-version': '2',
    'trakt-api-key': TRAKT_CLIENT_ID
}

def obtener_tendencias_trakt(tipo="movies"):
    print(f"--- Extrayendo Tendencias Activas para: {tipo.upper()} ---")
    
    # 5 páginas de trending (500) y 50 páginas de popular (5.000)
    endpoints = {"trending": 5, "popular": 50}
    catalogo = {}
    
    for endpoint, total_paginas in endpoints.items():
        print(f"\n Consultando {endpoint}...")
        
        for pagina in range(1, total_paginas + 1):
            url = f"https://api.trakt.tv/{tipo}/{endpoint}?page={pagina}&limit=100&extended=full"
            
            try:
                respuesta = requests.get(url, headers=HEADERS)
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    if not datos: break
                        
                    for item in datos:
                        if endpoint == "popular":
                            peli = item
                            espectadores = 0
                        else: 
                            peli = item.get('show') if tipo == "shows" else item.get('movie')
                            espectadores = item.get('watchers', 0)
                            
                        if not peli: continue
                        tmdb_id = peli.get('ids', {}).get('tmdb')
                            
                        if not tmdb_id: continue
                            
                        if tmdb_id not in catalogo:
                            catalogo[tmdb_id] = {
                                'tmdb_id': tmdb_id, 
                                'titulo': peli.get('title'),
                                'certificacion': peli.get('certification'), 
                                'espectadores_live': 0, 
                                'es_tendencia': False, 
                                'es_popular': False
                            }
                            
                        if endpoint == "trending":
                            catalogo[tmdb_id]['espectadores_live'] = espectadores
                            catalogo[tmdb_id]['es_tendencia'] = True
                        elif endpoint == "popular":
                            catalogo[tmdb_id]['es_popular'] = True
                            
                elif respuesta.status_code == 429:
                    espera = int(respuesta.headers.get('Retry-After', 5))
                    print(f"⏳ Límite de API. Esperando {espera} seg...")
                    time.sleep(espera)
            except Exception as e:
                pass
                
            time.sleep(0.3) # Pausa entre peticiones a la API
            
    carpeta_destino = f"src/data/raw/trakt/{tipo}"
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_archivo = os.path.join(carpeta_destino, f'trakt_{tipo}.csv')
    
    df_final = pd.DataFrame(list(catalogo.values()))
    df_final.to_csv(ruta_archivo, index=False)
    print(f" {len(df_final)} tendencias guardadas en {ruta_archivo}")

if __name__ == "__main__":
    obtener_tendencias_trakt("shows")
    obtener_tendencias_trakt("movies")