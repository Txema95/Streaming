import requests
import pandas as pd
import os
import time

# --- CONFIGURACIÓN ---
TRAKT_CLIENT_ID = "9419ec6a85b467e556fd4a83e5b42110c1af6a9ed9df092d4433e2a4f5ba96e3"
HEADERS = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
}


def obtener_datos_unificados(tipo="movies"):
    """
    Descarga trending, popular y played, y los unifica en un solo DataFrame.
    """
    print(f"--- Creando dataset UNIFICADO para: {tipo.upper()} ---")

    # ímites para cada tipo
    endpoints = {"trending": 100, "popular": 200, "played": 200}

    catalogo_unificado = {}

    for endpoint, limite in endpoints.items():
        print(f"Consultando {endpoint}...")
        url = f"https://api.trakt.tv/{tipo}/{endpoint}?limit={limite}&extended=full"

        try:
            respuesta = requests.get(url, headers=HEADERS)

            if respuesta.status_code == 200:
                datos = respuesta.json()

                for item in datos:
                    clave_item = "show" if tipo == "shows" else "movie"

                    if clave_item in item:
                        media = item[clave_item]
                        espectadores = item.get("watchers", 0)
                        reproducciones = item.get("play_count", 0)
                    else:
                        media = item
                        espectadores = 0
                        reproducciones = 0

                    tmdb_id = media.get("ids", {}).get("tmdb")

                    if not tmdb_id:
                        continue

                    #  Si la peli/serie no existe en nuestro diccionario, la creamos
                    if tmdb_id not in catalogo_unificado:
                        catalogo_unificado[tmdb_id] = {
                            "tmdb_id": tmdb_id,
                            "titulo": media.get("title"),
                            "ano": media.get("year"),
                            "nota_media": media.get("rating", 0),
                            "total_votos": media.get("votes", 0),
                            "certificacion": media.get("certification", "N/A"),
                            "espectadores_live": 0,
                            "reproducciones_totales": 0,
                            "es_tendencia": False,
                            "es_popular": False,
                            "es_historico_vistas": False,
                        }

                    # Actualizamos las métricas específicas según el endpoint
                    if endpoint == "trending":
                        catalogo_unificado[tmdb_id]["espectadores_live"] = espectadores
                        catalogo_unificado[tmdb_id]["es_tendencia"] = True
                    elif endpoint == "played":
                        catalogo_unificado[tmdb_id]["reproducciones_totales"] = (
                            reproducciones
                        )
                        catalogo_unificado[tmdb_id]["es_historico_vistas"] = True
                    elif endpoint == "popular":
                        catalogo_unificado[tmdb_id]["es_popular"] = True

            elif respuesta.status_code == 429:
                print("Límite de API. Esperando 5 seg...")
                time.sleep(5)
            else:
                print(f"Error HTTP {respuesta.status_code}")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(1)  # Pausa entre endpoints

    carpeta_destino = f"src/data/raw/trakt/{tipo}"
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_archivo = os.path.join(carpeta_destino, f"trakt_{tipo}.csv")

    df_final = pd.DataFrame(list(catalogo_unificado.values()))
    df_final.to_csv(ruta_archivo, index=False)
    print(f"--- {len(df_final)} registros únicos guardados en {ruta_archivo} ---\n")


def ejecutar_pipeline():
    print("=== INICIANDO EXTRACCIÓN MAESTRA DE TRAKT ===\n")
    obtener_datos_unificados("movies")
    obtener_datos_unificados("shows")
    print("=== PIPELINE COMPLETADO ===")


if __name__ == "__main__":
    ejecutar_pipeline()
