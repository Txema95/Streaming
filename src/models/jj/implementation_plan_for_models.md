# Plan de Implementación: Motor de Recomendación de IA

## Contexto y Datos Disponibles

El proyecto ya tiene un pipeline de datos completo y limpio:

| Archivo | Filas | Columnas | Descripción |
|---|---|---|---|
| [ratings_finales_ia.csv](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/data/ready/ratings_finales_ia.csv) | **33.8M** | 3 (`userId`, `tmdb_id`, `rating`) | Matriz de interacciones usuario-peli |
| [dataset_final_movies.csv](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/data/ready/dataset_final_movies.csv) | **55.7K** | 23 (géneros, votos, posters, etc.) | Catálogo de películas con features |
| [dataset_final_shows.csv](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/data/ready/dataset_final_shows.csv) | ~50K | ~23 | Catálogo de series |

- **330K usuarios únicos**, **176K películas únicas**
- Ratings en rango **0.5 – 5.0**

> [!IMPORTANT]
> Con 33.8M de filas, los modelos que entrenen sobre toda la matriz tardarán mucho. **Recomiendo empezar con un subconjunto (ej: usuarios con ≥20 ratings)** para iterar rápido y luego escalar.

---

## Estrategia Recomendada: 3 Modelos en Cascada

Basándome en tus ideas y en los datos que tienes, propongo esta arquitectura de 3 capas que se complementan entre sí:

### Modelo 1: SVD (Singular Value Decomposition) — [modelo_FC_SVD.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_FC_SVD.py)
**Qué hace**: Factorización de la matriz usuario×película. Encuentra los "gustos latentes" de cada usuario y las "cualidades latentes" de cada película.
**Por qué empezar aquí**: 
- Es el modelo **más rápido** de entrenar y el que mejores resultados da con datos tipo rating.
- Sirve como **baseline** para comparar con modelos más complejos.
- Genera embeddings (vectores) de usuarios y películas que puedes reutilizar en los otros modelos.

**Librería**: `surprise` (scikit-surprise), que es el estándar para sistemas de recomendación con ratings explícitos.

### Modelo 2: KNN + Cosine Similarity — Clustering de usuarios
**Qué hace**: Agrupa usuarios similares y recomienda lo que les gustó a "los que se parecen a ti".
**Ventaja**: Es muy intuitivo y explica bien sus recomendaciones ("te recomendamos X porque a usuarios parecidos les gustó").
**Usa**: Los embeddings del SVD como input para calcular la similitud coseno entre usuarios.

### Modelo 3: Wide & Deep — [modelo_wide_deep.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_wide_deep.py)
**Qué hace**: Red neuronal híbrida que combina features "anchas" (géneros, popularidad) con features "profundas" (embeddings aprendidos).
**Por qué al final**: Es el más complejo. Necesita los features del catálogo + los embeddings del SVD.
**Librería**: PyTorch.

---

## Secuencia de Implementación

Propongo empezar **solo con el Modelo 1 (SVD)**, validarlo, integrarlo en el frontend, y luego ir añadiendo capas.

### Fase 1: SVD — [modelo_FC_SVD.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_FC_SVD.py)

#### [MODIFY] [modelo_FC_SVD.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/models/modelo_FC_SVD.py)

Implementar:
1. **Carga de datos**: Leer [ratings_finales_ia.csv](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/data/ready/ratings_finales_ia.csv) con un filtro (usuarios con ≥20 ratings) para reducir de 33M a ~5-10M filas.
2. **Entrenamiento SVD**: Usar `surprise.SVD()` con train/test split 80/20.
3. **Métricas**: Calcular RMSE y MAE sobre el test set.
4. **Función de predicción**: `recomendar(userId, n=10)` → devuelve las top-N películas que el usuario NO ha visto, ordenadas por rating predicho.
5. **Exportar modelo**: Guardar el modelo entrenado como `.pkl` para poder cargarlo desde el Backend sin re-entrenar.

### Fase 2: Integración en Backend

#### [MODIFY] [main_api.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/api/main_api.py)

- Nuevo endpoint `GET /recomendar/{user_id}` que cargue el modelo `.pkl` y devuelva las top-N películas recomendadas.

### Fase 3: Integración en Frontend

#### [MODIFY] [2_Usuario.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/src/frontend/pages/2_Usuario.py)

- Añadir una sección "Recomendaciones para ti" que llame al nuevo endpoint y pinte las postales.

---

## Dependencias Nuevas

```
uv add scikit-surprise
```

> [!NOTE]
> `scikit-surprise` incluye todo lo necesario para SVD, KNN y otras técnicas de filtrado colaborativo. No necesita PyTorch.

---

## Verificación

### Métricas del Modelo
- **RMSE ≤ 0.90** sobre el test set (benchmark razonable para SVD en MovieLens).
- **MAE ≤ 0.70**.

### Test Manual
1. Entrenar el modelo ejecutando `python src/models/modelo_FC_SVD.py`.
2. Verificar que se genera el archivo `.pkl` del modelo.
3. Arrancar [main.py](file:///c:/Users/User/Desktop/Programacion/Proyecto%204%20-%20Streaming/Proyecto%204%20-%20Streaming%20-%20main/main.py) y llamar a `http://localhost:8000/recomendar/1` para ver las recomendaciones del usuario 1.
4. Entrar en Streamlit como usuario y verificar que aparece la sección de recomendaciones.

---

## Decisiones que Necesito del Usuario

1. **¿Empezamos solo con el SVD** (Fase 1) y luego iteramos, o prefieres que implemente los 3 modelos de golpe?
2. **¿Filtro de usuarios**: ¿Te parece bien limitar a usuarios con ≥20 ratings para el entrenamiento inicial?
3. **¿Wide & Deep con PyTorch** o prefieres TensorFlow/Keras? (La arquitectura original de Google fue en TF, pero PyTorch es más flexible).
