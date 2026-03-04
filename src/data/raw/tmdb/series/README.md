# Llamada al service: Datos de TV de TMDB (JSONL)

Este documento detalla la estructura y los códigos utilizados en los archivos extraídos de la API de TMDB para series de televisión.

## 2. Campos que devuelve la llamada al service
Cada línea de la respuesta contiene un objeto con los siguientes atributos:

### Identificación y Texto
* **`id`**: Identificador único numérico de la serie en TMDB.
* **`name`**: Nombre de la serie (traducido al idioma solicitado).
* **`original_name`**: Título original de la serie en su país de origen.
* **`original_language`**: Código de idioma (ISO 639-1) original (ej: `en`, `es`).
* **`origin_country`**: Lista de códigos de países de producción (ej: `["GB"]`).
* **`overview`**: Sinopsis o resumen de la trama de la serie.
* **`first_air_date`**: Fecha de emisión del primer episodio (Formato: `YYYY-MM-DD`).

### Métricas y Rendimiento
* **`popularity`**: **El Termómetro de Tendencia.**
    * *Explicación:* No mide la "calidad" histórica, sino el tráfico actual. Se basa en vistas diarias de la ficha, votos recientes y búsquedas en la plataforma. Es un valor dinámico que fluctúa cada 24 horas.
* **`vote_average`**: Nota media de los usuarios (escala del 0 al 10).
* **`vote_count`**: Cantidad total de usuarios que han calificado la serie.

### Multimedia y Clasificación

* **`poster_path`**: Ruta del archivo para el póster vertical.
* **`backdrop_path`**: Ruta del archivo para la imagen de fondo horizontal.
* **`adult`**: Booleano (`true`/`false`) que indica si el contenido es exclusivamente para adultos.
* **`genre_ids`**: Lista de números que corresponden a los géneros. 

| ID | Género | Descripción |
| :--- | :--- | :--- |
| **10759** | Action & Adventure | Acción y Aventuras (Series con ritmo alto). |
| **16** | Animación | Dibujos animados, anime y CGI. |
| **35** | Comedia | Humor, sitcoms y sketches. |
| **80** | Crimen | Policiales, detectives y gánsteres. |
| **99** | Documental | Hechos reales y contenido educativo. |
| **18** | Drama | Conflictos emocionales y narrativas serias. |
| **10751** | Familia | Contenido apto para todas las edades. |
| **10762** | Kids | Contenido dirigido específicamente a niños. |
| **10763** | News | Noticieros y programas de actualidad. |
| **10764** | Reality | Programas de telerrealidad y concursos. |
| **10765** | Sci-Fi & Fantasy | Ciencia ficción y mundos de fantasía. |
| **10766** | Soap | Telenovelas y dramas serializados diarios. |
| **10767** | Talk | Programas de entrevistas y Late Nights. |
| **10768** | War & Politics | Conflictos bélicos y tramas políticas. |
| **37** | Western | Historias del oeste. |

---

