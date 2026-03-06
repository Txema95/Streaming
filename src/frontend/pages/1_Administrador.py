import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

st.set_page_config(page_title="Admin Panel", layout="wide")

st.title("Panel de Control de Administrador")
st.markdown("Gestion de los datos y visualizacion de métricas clave.")

# ---- PANEL LATERAL ----
st.sidebar.header("Acciones de Datos")

if st.sidebar.button("Sincronizar con MySQL", use_container_width=True):
    response = requests.get("http://localhost:8000/usuarios")
    if response.status_code == 200:
        df = pd.DataFrame(response.json())
        st.session_state["datos_usuarios"] = df
        st.sidebar.success("Usuarios cargados desde MySQL")
    else:
        st.sidebar.error("Error al conectar con el Backend")

if st.sidebar.button("Importar Datos a BD", use_container_width=True):
    response = requests.post("http://localhost:8000/importar_datos")
    if response.status_code == 200:
        st.sidebar.success("Catálogos importados correctamente!")
    else:
        st.sidebar.error("Error al conectar con el Backend")


# ---- PESTAÑAS PRINCIPALES ----
tab1, tab2 = st.tabs(["Gestión de Usuarios", "Análisis Exploratorio (EDA)"])

with tab1:
    st.subheader("Listado de Usuarios (Sincronizados)")
    if "datos_usuarios" in st.session_state:
        st.dataframe(st.session_state["datos_usuarios"], use_container_width=True)
    else:
        st.info(
            "Haz clic en 'Sincronizar con MySQL' en la barra lateral para ver los usuarios."
        )


with tab2:
    st.subheader("Análisis Exploratorio de Datos del Catálogo")
    st.markdown("Visualizaciones cargadas desde los datos limpios.")

    # Rutas a los CSV (Asegurando ruta absoluta al proyecto o relativa correcta)
    movies_path = "src/data/ready/dataset_final_movies.csv"
    ratings_path = "src/data/ready/ratings_finales_ia.csv"

    # Verificamos si los archivos existen antes de intentar leerlos
    if os.path.exists(movies_path) and os.path.exists(ratings_path):
        try:
            df_movies = pd.read_csv(movies_path)
            df_ratings = pd.read_csv(ratings_path)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Top 10 Películas con Mejores Valoraciones (>500)**")
                top_movies = (
                    df_movies[df_movies["vote_count"] > 500]
                    .sort_values(by="vote_average", ascending=False)
                    .head(10)
                )
                fig1, ax1 = plt.subplots(figsize=(8, 5))
                sns.barplot(
                    x="vote_average",
                    y="titulo",
                    data=top_movies,
                    palette="viridis",
                    ax=ax1,
                )
                ax1.set_xlabel("Nota Media")
                ax1.set_ylabel("Título")
                st.pyplot(fig1)

                st.markdown("**Distribución de Puntuaciones (Estrellas)**")
                fig3, ax3 = plt.subplots(figsize=(8, 5))
                sns.countplot(x="rating", data=df_ratings, palette="coolwarm", ax=ax3)
                ax3.set_xlabel("Puntuación (Rating)")
                ax3.set_ylabel("Cantidad de Votos")
                st.pyplot(fig3)

            with col2:
                st.markdown("**Cantidad de Valoraciones por Usuario**")
                user_counts = df_ratings["userId"].value_counts()
                fig2, ax2 = plt.subplots(figsize=(8, 5))
                sns.histplot(user_counts, bins=100, kde=True, color="blue", ax=ax2)
                ax2.set_xlim(0, 500)
                ax2.set_xlabel("Número de películas valoradas")
                ax2.set_ylabel("Cantidad de Usuarios")
                st.pyplot(fig2)

                st.info(f"""
                **Métricas Globales de Sistema IA**:
                - **Media de valoraciones/usuario**: {user_counts.mean():.2f}
                - **Total de usuarios**: {len(user_counts)}
                - **Riesgo Cold Start (<20 vals)**: {(user_counts < 20).sum()} usuarios
                """)
        except Exception as e:
            st.error(f"Error al procesar los datos para los gráficos: {e}")
    else:
        st.warning(
            f"No se encontraron los datasets en `src/data/ready/`. Asegúrate de ejecutar el flujo de datos primero."
        )
