import streamlit as st
import requests

st.set_page_config(page_title="JJ Streaming - Usuario", layout="wide")

# Validar si el usuario está logueado en Streamlit Session State
if "usuario_autenticado" not in st.session_state:
    st.session_state["usuario_autenticado"] = False
    st.session_state["usuario_actual"] = None

# ---- PANTALLA DE ACCESO (Login / Registro) ----
if not st.session_state["usuario_autenticado"]:
    st.title("Iniciar Sesión o Registrarse en SPIRE")
    st.markdown(
        "Por favor, introduce tus credenciales para acceder al catálogo o crea una nueva cuenta."
    )

    tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Registrarse"])

    # --- PESTAÑA LOGIN ---
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit_button = st.form_submit_button("Entrar")

            if submit_button:
                try:
                    response = requests.get("http://localhost:8000/usuarios")
                    if response.status_code == 200:
                        usuarios = response.json()

                        usuario_encontrado = None
                        for u in usuarios:
                            if (
                                str(u.get("id_usuario")) == username
                                or u.get("username") == username
                            ):
                                usuario_encontrado = u
                                break

                        if usuario_encontrado:
                            st.session_state["usuario_autenticado"] = True
                            st.session_state["usuario_actual"] = usuario_encontrado
                            st.success("¡Login exitoso!")
                            st.rerun()  # Recarga la página para mostrar el catálogo
                        else:
                            st.error(
                                "Credenciales incorrectas. Verifica tu usuario o regístrate en la otra pestaña."
                            )
                    else:
                        st.error("Error conectando con el servidor de Backend.")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

    # --- PESTAÑA REGISTRO ---
    with tab_registro:
        st.info("Crea tu cuenta en SPIRE.")
        with st.form("register_form"):
            new_username = st.text_input("Nombre de Usuario Nuevo")
            new_password = st.text_input("Contraseña", type="password")
            new_password_confirm = st.text_input(
                "Confirmar Contraseña", type="password"
            )
            btn_register = st.form_submit_button("Registrarse")

            if btn_register:
                if not new_username or not new_password:
                    st.warning("Por favor, rellena todos los campos.")
                elif new_password != new_password_confirm:
                    st.error("Las contraseñas no coinciden.")
                else:
                    # En un entorno real se haría un POST a un endpoint /usuarios del backend
                    st.success(
                        f"¡Usuario '{new_username}' registrado! (Simulación Frontend Local)"
                    )
                    st.info(
                        "Ya puedes ir a la pestaña 'Iniciar Sesión' y entrar (usando Mock por ahora no te dejará entrar ya que no escribí en BD, es una simulación visual)."
                    )
#################################################################################################
# ---- PANTALLA PRINCIPAL DEL USUARIO (Logueado) ----
else:
    import pandas as pd
    import os

    usuario = st.session_state["usuario_actual"]
    nombre_mostrar = usuario.get("username", f"Usuario #{usuario.get('id_usuario')}")

    # Barra superior con Logout
    col_titulo, col_logout = st.columns([8, 2])
    with col_titulo:
        st.title(f"Bienvenido a SPIRE, {nombre_mostrar}!")
    with col_logout:
        st.write("")  # Espacio
        if st.button("Cerrar Sesión"):
            st.session_state["usuario_autenticado"] = False
            st.session_state["usuario_actual"] = None
            st.rerun()

    st.markdown(
        "Descubre Películas y Series gracias a nuestro Recomendador de Inteligencia Artificial."
    )
    st.info(
        "El motor de Inteligencia Artificial está en desarrollo. De momento puedes navegar por el catálogo completo."
    )

    # --- CARGA DE DATOS ---
    @st.cache_data
    def load_catalog_data():
        movies_path = "src/data/ready/dataset_final_movies.csv"
        shows_path = "src/data/ready/dataset_final_shows.csv"

        df_movies = pd.DataFrame()
        df_shows = pd.DataFrame()

        # Leemos solo algunas columnas para no colapsar la memoria de Streamlit
        cols_movies = [
            "tmdb_id",
            "titulo",
            "overview",
            "release_date",
            "poster_path",
            "vote_average",
        ]
        cols_shows = [
            "tmdb_id",
            "titulo",
            "overview",
            "first_air_date",
            "poster_path",
            "vote_average",
        ]

        if os.path.exists(movies_path):
            try:
                df_movies = pd.read_csv(movies_path, usecols=cols_movies)
            except Exception:
                df_movies = pd.read_csv(movies_path)

        if os.path.exists(shows_path):
            try:
                df_shows = pd.read_csv(shows_path, usecols=cols_shows)
            except Exception:
                df_shows = pd.read_csv(shows_path)

        return df_movies, df_shows

    df_movies, df_shows = load_catalog_data()

    # --- BUSCADOR GLOBAL ---
    search_query = st.text_input("Busca por título o palabras clave...")

    # --- PESTAÑAS DEL CATÁLOGO ---
    tab_movies, tab_shows = st.tabs(["Películas", "Series"])

    # Función para dibujar las postales
    def render_catalog(df, query, limit=12, is_movie=True):
        if df.empty:
            st.warning(
                "El catálogo no está disponible porque faltan los archivos de datos en `src/data/ready/`."
            )
            return

        # Filtrado por búsqueda
        if query:
            mask = df["titulo"].str.contains(query, case=False, na=False)
            filtered_df = df[mask]
        else:
            if "vote_average" in df.columns:
                filtered_df = df.sort_values(by="vote_average", ascending=False)
            else:
                filtered_df = df

        results_to_show = filtered_df.head(limit)

        if results_to_show.empty:
            st.write("No se encontraron resultados para tu búsqueda.")
            return

        st.write(f"Mostrando {len(results_to_show)} resultados destacados...")

        # Grid de 4 columnas
        cols = st.columns(4)
        for index, (_, row) in enumerate(results_to_show.iterrows()):
            col = cols[index % 4]
            with col:
                # Poster
                poster_url = "https://via.placeholder.com/300x450.png?text=Sin+Poster"
                if pd.notna(row.get("poster_path")):
                    poster_url = f"https://image.tmdb.org/t/p/w500{row['poster_path']}"

                st.image(poster_url, use_container_width=True)
                titulo = row.get("titulo", "Sin Título")

                # Truncamos strings
                if len(str(titulo)) > 30:
                    titulo = titulo[:27] + "..."

                # Obtener año según si es peli (release) o serie (first air)
                date_col = "release_date" if is_movie else "first_air_date"
                year = str(row.get(date_col, ""))[:4]

                if year != "nan" and year:
                    st.markdown(f"**{titulo}** ({year})")
                else:
                    st.markdown(f"**{titulo}**")

                if st.button(
                    "Ver detalles",
                    key=f"{'mov' if is_movie else 'tv'}_{row.get('tmdb_id', index)}",
                ):
                    st.toast(row.get("overview", "Sin Sinopsis disponible."))

    with tab_movies:
        st.subheader("Mejores Películas")
        render_catalog(df_movies, search_query, limit=12, is_movie=True)

    with tab_shows:
        st.subheader("Mejores Series")
        render_catalog(df_shows, search_query, limit=12, is_movie=False)
