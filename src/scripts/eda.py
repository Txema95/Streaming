##############################################################################################

# EDA - Análisis Exploratorio de Datos

##############################################################################################

# TOP 10 Peliculas con mejores valoraciones
# -----------------------------------------------------------

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Cargamos los datos
df_movies = pd.read_csv("src/data/ready/dataset_final_movies.csv")

# TOP 10 Peliculas con mejores valoraciones (filtro de >500 votos para dar relevancia)
top_movies = (
    df_movies[df_movies["vote_count"] > 500]
    .sort_values(by="vote_average", ascending=False)
    .head(10)
)

plt.figure(figsize=(10, 6))
sns.barplot(x="vote_average", y="titulo", data=top_movies, palette="viridis")
plt.title("Top 10 Películas con Mejores Valoraciones (Mín. 500 votos)")
plt.xlabel("Nota Media (Promedio de votos)")
plt.ylabel("Título")
plt.tight_layout()
plt.show()


##############################################################################################

# Distribucion del numero de valoracion por usuario
# -----------------------------------------------------------

# Cargamos la matriz IA
df_ratings = pd.read_csv("src/data/ready/ratings_finales_ia.csv")

# Contamos cuántas valoraciones ha hecho cada usuario
user_counts = df_ratings["userId"].value_counts()

plt.figure(figsize=(10, 6))
sns.histplot(user_counts, bins=100, kde=True, color="blue")
plt.title("Distribución de la Cantidad de Valoraciones por Usuario")
plt.xlabel("Número de películas valoradas por el usuario")
plt.ylabel("Cantidad de Usuarios")
plt.xlim(0, 500)  # Limitamos el gráfico para que no se deforme por los "súper usuarios"
plt.show()

# Infor importante
print(
    "---------------------------------------------------------------------------------"
)
print("Informacion importante: ")
print(f"Media de valoraciones por usuario: {user_counts.mean():.2f}")
print(
    f"Usuarios con menos de 20 valoraciones (riesgo de Cold Start): {(user_counts < 20).sum()}"
)
print(f"Total de usuarios: {len(user_counts)}")
print(
    "---------------------------------------------------------------------------------"
)

##############################################################################################

# Distribucion de las puntuaciones
# -----------------------------------------------------------

# Distribucion de las puntuaciones .
plt.figure(figsize=(10, 6))
sns.countplot(x="rating", data=df_ratings, palette="coolwarm")
plt.title("Distribución general de Puntuaciones (Estrellas)")
plt.xlabel("Puntuación (Rating)")
plt.ylabel("Cantidad de Votos (Millones)")
plt.show()
