# Revisión Completa: Proyecto 4 - Streaming

---

## 1. Fallos, Incongruencias y Mejoras del Código Existente

### 🔴 Problemas Críticos

#### Seguridad: API Keys expuestas en [.env](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.env) comiteado a Git
El archivo [.env](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.env) contiene claves reales (TMDB, Trakt) y **no está en [.gitignore](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.gitignore)**. Cualquiera con acceso al repo puede ver estas credenciales.

> [!CAUTION]
> Añadir [.env](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.env) al [.gitignore](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.gitignore) inmediatamente y rotar las API keys comprometidas.

#### Seguridad: Contraseñas en texto plano soportadas
En [main_api.py:109-111](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/api/main_api.py#L109-L111), si la contraseña no es un hash bcrypt, se compara en **texto plano**. Esto es un riesgo de seguridad considerable.

#### Bypass de autenticación activo
En [1_Administrador.py:32](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/frontend/pages/1_Administrador.py#L32):
```python
st.session_state["admin_autenticado"] = True  # añadido para pruebas, eliminar luego
```
Esta línea salta toda la autenticación del admin. Debe eliminarse antes de cualquier entrega.

#### `@app.on_event("startup")` está deprecated
En [main_api.py:141](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/api/main_api.py#L141), FastAPI marcó `on_event` como deprecated. Debe usarse `lifespan` context manager.

---

### 🟠 Problemas Importantes

#### Modelos KNN y Wide&Deep no integrados en Backend/Frontend
Solo el modelo SVD está conectado al endpoint `/recomendar/{user_id}`. Los modelos 2 (KNN+CS) y 3 (Wide&Deep) están entrenados pero **sin endpoints ni interfaz** para usarlos. No hay forma de que el usuario los invoque.

#### Registro de usuarios NO funcional
En [2_Usuario.py:60-72](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/frontend/pages/2_Usuario.py#L60-L72), el registro es una **simulación visual** — no escribe en BD, no existe endpoint `POST /usuarios` en el backend.

#### README duplicado 3 veces
El [README.md](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/README.md) repite la misma sección de configuración de MySQL/Backend/Frontend **3 veces** (líneas 52-75, 90-128, 133-175).

#### Modelo Wide&Deep: rango de predicción inconsistente
En [rn_mlp.py:97](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/networks/dl/rn_mlp.py#L97):
```python
prediction = torch.sigmoid(prediction) * 5.5
```
Sigmoid × 5.5 produce rango [0, 5.5], pero los ratings son [0.5, 5.0]. En el test de [modelo_3_wide&deep.py:217](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_3_wide%26deep.py#L217) se hace `clamp(0.5, 5.0)`, pero eso no se aplica durante el entrenamiento (solo en evaluación), creando una discrepancia train/eval.

#### Pool de conexiones se ejecuta al importar
En [database.py:22](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/api/database.py#L22), la creación del pool de MySQL se ejecuta **a nivel de módulo**, por lo que si la DB no está disponible al importar, toda la aplicación crashea sin posibilidad de recuperación.

#### `except:` bare (sin especificar excepción)
En [modelo_2_knn+cs.py:235](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_2_knn+cs.py#L235) y [1_Administrador.py:28](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/frontend/pages/1_Administrador.py#L28), se usan `except:` desnudos que atrapan todas las excepciones (incluyendo `KeyboardInterrupt`), dificultando la depuración.

#### `video` falta en `CREATE TABLE contents`
La tabla SQL de [create_database.sql](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/data/scripts_sql/create_database.sql) no incluye la columna `video` que sí se inserta en la query de [etl.py:76-86](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/api/etl.py#L76-L86). Esto causará un error SQL al importar datos.

#### Tabla `content_stats` no se usa
Existe en el DDL pero el ETL nunca la rellena. Los datos de Trakt (tendencias, espectadores) se unifican en el CSV pero no se cargan en esta tabla.

---

### 🟡 Mejoras Recomendadas

| Área | Problema | Mejora |
|------|----------|--------|
| **Performance** | La función [recomendar()](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_1_SVD.py#192-231) itera sobre TODAS las películas no vistas (>50K) para cada petición | Precomputar top-N recomendaciones por usuario o usar un índice ANN (Approximate Nearest Neighbor) |
| **Modelos .pkl gigantes** | SVD pesa 930MB, KNN pesa 900MB | Estos modelos se guardan con `pickle` incluyendo todos los datos de entrenamiento de Surprise. Considerar guardar solo lo necesario |
| **Frontend EDA** | Se carga el CSV de 434MB de ratings en el admin con `pd.read_csv` en cada sesión | Precalcular estadísticas EDA o almacenarlas en la BD |
| **`set_page_config` llamado múltiples veces** | Tanto [app_ui.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/frontend/app_ui.py) como cada subpágina llaman a `set_page_config`, lo que puede causar warnings en Streamlit | Solo llamar desde la página principal |
| **Falta `load_dotenv()` en [trakt_tendencias_api_down.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/scripts/trakt_tendencias_api_down.py)** | Se usa `os.getenv("TRAKT_CLIENT_ID")` pero nunca se llama a `load_dotenv()` | Las variables de entorno no se cargarán, devolviendo `None` |
| **[tmdb_api_down.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/scripts/tmdb_api_down.py) usa `API_KEY` en vez de `TMDB_API_KEY`** | En [.env](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.env) la variable se llama `API_KEY`, pero en [.env.sample](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.env.sample) se llama `TMDB_API_KEY` | Inconsistencia que causará fallos: `os.getenv("TMDB_API_KEY")` no encontrará `API_KEY` |
| **Cold Start no implementado** | Para usuarios nuevos sin historial, no hay fallback (contenido popular, tendencias) | Implementar recomendación basada en popularidad/contenido |
| **Sin tests automatizados** | No hay ningún test unitario ni de integración en todo el proyecto | Añadir al menos tests para los endpoints de la API y las funciones de recomendación |
| **[pyproject.toml](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/pyproject.toml)** | Falta `torch` como dependencia | Si alguien clona el repo, no podrá entrenar el modelo 3 |

---

## 2. Modelos de IA Alternativos Recomendados

Los 3 modelos actuales (SVD, KNN+CS, Wide&Deep) son todos **collaborative filtering** puro. Esto crea un vacío importante:

### Modelos que Añadirían Valor

| Modelo | Tipo | Por qué encaja | Librería |
|--------|------|----------------|----------|
| **LightFM** | Híbrido (CF + Content) | Combina ratings con features del catálogo (género, idioma, popularidad). Resuelve **Cold Start** para nuevas películas | `lightfm` |
| **TF-IDF + Cosine Similarity** | Content-Based | Recomendación por similitud de sinopsis/overview. No necesita historial del usuario | `sklearn` |
| **Two-Tower (Retrieval + Ranking)** | Neural / Producción | Arquitectura Google recomendada en vuestros PDFs. Separa generación de candidatos de ranking. Escala mucho mejor que iterar sobre 50K pelis por usuario | `tensorflow-recommenders` o PyTorch |
| **ALS (Alternating Least Squares)** | CF Implícito | Más eficiente que SVD para datasets grandes. PySpark lo tiene nativo (que ya usáis en otro proyecto) | `pyspark.ml.recommendation.ALS` |
| **NCF (Neural Collaborative Filtering)** | Deep Learning | Reemplazaría el Wide&Deep con una arquitectura más moderna y demostrada (paper de He et al., 2017) | PyTorch |

> [!TIP]
> **Recomendación**: Añadir como mínimo **LightFM** (resuelve Cold Start) y **TF-IDF sobre sinopsis** (recomendación por contenido sin necesidad de historial). Ambos se integran fácilmente.

---

## 3. Modificaciones para Aplicar los Modelos en Streamlit

Actualmente solo SVD está conectado via FastAPI → Streamlit. Para integrar todos los modelos:

### 3.1. Crear endpoints para cada modelo en el Backend

```python
# En main_api.py - Añadir:
@app.get("/recomendar/knn/{user_id}")    # Modelo 2: KNN+CS
@app.get("/recomendar/wnd/{user_id}")    # Modelo 3: Wide&Deep
@app.get("/recomendar/ensemble/{user_id}") # Ensemble de los 3
```

**Para Wide&Deep**, se necesita una función de predicción que:
1. Cargue el modelo [.pth](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_3_wnd.pth) y los mappings [.pkl](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/wnd_mappings.pkl) al arrancar
2. Traduzca el `user_id` real al `user_idx` interno
3. Prediga ratings para todas las películas no vistas
4. Devuelva top-N

### 3.2. Selector de modelo en Streamlit

En [2_Usuario.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/frontend/pages/2_Usuario.py), añadir un `st.selectbox` para elegir el modelo:

```python
modelo_elegido = st.sidebar.selectbox(
    "Motor de Recomendación",
    ["SVD (Rápido)", "KNN + Cosine (Explicable)", "Wide&Deep (Profundo)", "Ensemble"]
)
# Mapear a endpoint correspondiente
endpoints = {
    "SVD (Rápido)": "/recomendar/svd/",
    "KNN + Cosine (Explicable)": "/recomendar/knn/",
    "Wide&Deep (Profundo)": "/recomendar/wnd/",
    "Ensemble": "/recomendar/ensemble/"
}
```

### 3.3. Dashboard de Comparación de Modelos (Admin)

En [1_Administrador.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/frontend/pages/1_Administrador.py), añadir una pestaña que muestre las métricas comparativas:

```python
tab1, tab2, tab3 = st.tabs(["Usuarios", "EDA", "Comparación Modelos"])
with tab3:
    st.subheader("Métricas por Modelo")
    data = {
        "Modelo": ["SVD", "KNN+CS", "Wide&Deep"],
        "RMSE": [rmse_svd, rmse_knn, rmse_wnd],
        "MAE": [mae_svd, mae_knn, mae_wnd],
        "Tiempo Entrenamiento": ["X min", "Y min", "Z min"],
        "Tamaño Modelo": ["930 MB", "900 MB", "6 MB"]
    }
    st.dataframe(pd.DataFrame(data))
```

### 3.4. Recomendación para Series

Actualmente las series no tienen recomendación IA. Para activarla:
- Crear un dataset de ratings para series (si existe), o
- Implementar recomendación **Content-Based** por sinopsis/género usando TF-IDF sobre [dataset_final_shows.csv](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/data/ready/dataset_final_shows.csv)

### 3.5. Corregir la función de arranque

Migrar de `@app.on_event("startup")` a `lifespan`:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cargar modelos al arrancar
    cargar_todos_los_modelos()
    yield
    # Limpieza al apagar (opcional)

app = FastAPI(lifespan=lifespan)
```

---

## 4. Métodos de los PDFs a Aplicar

De los PDFs de la carpeta `info/`, identifico los siguientes métodos clave que el proyecto debería implementar:

### Del PDF [20260227_Ranking_Recommendation_Systems.pptx.pdf](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/info/20260227_Ranking_Recommendation_Systems.pptx.pdf)

| Método | Estado Actual | Recomendación |
|--------|---------------|---------------|
| **Collaborative Filtering (CF)** | ✅ Implementado (SVD, KNN) | Correcto |
| **Content-Based Filtering** | ❌ No implementado | Añadir TF-IDF sobre `overview` + `genre_ids` |
| **Hybrid Systems** | ⚠️ Parcial (Wide&Deep) | Hacer un ensemble real de los 3 modelos |
| **Ranking vs. Rating** | ❌ Solo se predice rating | Implementar un **re-ranking** que considere diversidad, novedad y serendipity |

### Del PDF [20260306_Retrieval_Ranking_Recommendation_systems_Architectures.pptx.pdf](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/info/20260306_Retrieval_Ranking_Recommendation_systems_Architectures.pptx.pdf)

| Método | Aplicación en el Proyecto |
|--------|--------------------------|
| **Two-Stage: Retrieval → Ranking** | Actualmente se itera sobre TODAS las películas (≈50K) para cada predicción. Implementar una fase de **retrieval** (candidatos top-500 rápidos con ANN) y luego **ranking** (modelo preciso sobre los 500 candidatos). Esto mejoraría la latencia de >10s a <1s |
| **Candidate Generation** | Usar embeddings de SVD o Wide&Deep para crear un índice vectorial (FAISS, Annoy, ScaNN) |
| **Feature Crossing** | El Wide&Deep ya lo hace parcialmente, pero no usa features del catálogo (géneros, idioma, popularidad). Añadir estas features como input al componente Wide |

### Del PDF [20260313_Evaluation_Metrics_Recommendation_Systems.pptx.pdf](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/info/20260313_Evaluation_Metrics_Recommendation_Systems.pptx.pdf)

| Métrica | Estado | A Implementar |
|---------|--------|---------------|
| **RMSE / MAE** | ✅ Implementado | Ya los calculáis |
| **Precision@K** | ❌ No implementado | Calcular qué porcentaje de las top-K recomendaciones son relevantes (rating real ≥ 4.0) |
| **Recall@K** | ❌ No implementado | De todas las películas relevantes, ¿qué % captura el top-K? |
| **NDCG@K** | ❌ No implementado | Métrica de ranking que penaliza errores en las posiciones altas. **Es la más importante para un sistema de recomendación de producción** |
| **MAP (Mean Average Precision)** | ❌ No implementado | Promedio de la precisión en cada posición relevante |
| **Hit Rate / HR@K** | ❌ No implementado | ¿Alguna de las top-K ha sido calificada con ≥4 por el usuario? |
| **Coverage** | ❌ No implementado | ¿Qué porcentaje del catálogo total aparece en las recomendaciones? Mide el "Long Tail" |
| **Diversity** | ❌ No implementado | Medir variedad de géneros en las recomendaciones |

> [!IMPORTANT]
> RMSE/MAE miden la **calidad de predicción** del rating, pero no la **calidad del ranking**. Para un sistema de recomendación, las métricas de ranking (NDCG@K, Precision@K, Hit Rate) son **mucho más relevantes** que RMSE. Deberíais implementar al menos NDCG@K y Precision@K.

### Del PDF [20260320_Negative_Sampling_Production_Recommendation_Systems.pptx.pdf](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/info/20260320_Negative_Sampling_Production_Recommendation_Systems.pptx.pdf)

| Concepto | Aplicación |
|----------|------------|
| **Negative Sampling** | Actualmente los modelos entrenan solo con ratings explícitos (positivos). Implementar negative sampling para incluir películas que el usuario NO ha visto como "negativos implícitos". Esto mejora significativamente la quality de los rankings |
| **Popularity Bias Correction** | Los modelos actuales tienen sesgo hacia películas populares. Implementar **correction factor** basado en la frecuencia de cada ítem |
| **Hard Negatives** | No elegir negativos al azar: elegir películas que el modelo "casi" recomienda pero que son irrelevantes. Esto entrena modelos más discriminativos |
| **Serving Architecture** | Separar el entrenamiento offline del serving online. Precomputar recomendaciones en batch en vez de calcularlas en real-time por petición |

---

## Resumen de Prioridades

| Prioridad | Acción | Impacto |
|-----------|--------|---------|
| 🔴 **P0** | Eliminar [.env](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/.env) de Git y rotar API keys | Seguridad |
| 🔴 **P0** | Quitar el bypass de auth del admin (línea 32) | Seguridad |
| 🔴 **P0** | Añadir columna `video` al DDL SQL | La importación de datos falla |
| 🟠 **P1** | Integrar KNN y Wide&Deep en el Backend con endpoints | Funcionalidad |
| 🟠 **P1** | Implementar métricas NDCG@K y Precision@K | Evaluación |
| 🟠 **P1** | Añadir Content-Based (TF-IDF) para Cold Start | Funcionalidad |
| 🟡 **P2** | Implementar Two-Stage Retrieval+Ranking | Performance |
| 🟡 **P2** | Añadir LightFM o Two-Tower model | Modelos |
| 🟡 **P2** | Dashboard comparativo en Streamlit | UI |
| 🟢 **P3** | Limpiar README, añadir tests, optimizar | Calidad |
