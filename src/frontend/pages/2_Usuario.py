import streamlit as st
import requests

st.set_page_config(page_title="SPIRE Streaming - Usuario", layout="wide")

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
                payload = {"username": username, "password": password}
                try:
                    response = requests.post(
                        "http://localhost:8000/login", json=payload
                    )

                    if response.status_code == 200:
                        datos_usuario = response.json()
                        st.session_state["usuario_autenticado"] = True
                        st.session_state["usuario_actual"] = datos_usuario["user"]
                        st.success("¡Login exitoso!")
                        st.rerun()  # Recarga la página para mostrar el catálogo
                    elif response.status_code == 401:
                        st.error(
                            "Credenciales incorrectas. Verifica tu usuario o regístrate en la otra pestaña."
                        )
                    else:
                        st.error(f"Error en el servidor: {response.status_code}")
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

    # --- BUSCADOR GLOBAL ---
    search_query = st.text_input("Busca por título o palabras clave...")

    # --- SELECTOR DE MODELO DE IA ---
    modelo_ia = st.sidebar.selectbox(
        "Motor de Recomendación",
        ["SVD (Rápido)", "KNN + Cosine (Explicable)", "Wide & Deep (Profundo)"],
        index=0,
    )
    mapa_endpoints = {
        "SVD (Rápido)": "recomendar",
        "KNN + Cosine (Explicable)": "recomendar/knn",
        "Wide & Deep (Profundo)": "recomendar/wnd",
    }
    endpoint_ia = mapa_endpoints[modelo_ia]

    # --- CARGA DE DATOS ---
    @st.cache_data
    def load_catalog_data():
        movies_path = "src/data/ready/dataset_final_movies.csv"
        shows_path = "src/data/ready/dataset_final_shows.csv"

        df_movies = pd.DataFrame()
        df_shows = pd.DataFrame()

        if os.path.exists(movies_path):
            try:
                df_movies = pd.read_csv(
                    movies_path, on_bad_lines="skip", engine="python"
                )
            except Exception:
                pass

        if os.path.exists(shows_path):
            try:
                df_shows = pd.read_csv(shows_path, on_bad_lines="skip", engine="python")
            except Exception:
                pass

        return df_movies, df_shows

    df_movies, df_shows = load_catalog_data()

    # =====================================================================================
    # Dibuja un grid de postales con poster, título y sinopsis
    # =====================================================================================
    def render_cards(df, limit=8, key_prefix="card", date_col="fecha_estreno"):
        """Dibuja una fila de postales con poster, título y botón de sinopsis."""
        if df.empty:
            st.info("No hay datos disponibles para mostrar.")
            return

        cols = st.columns(4)
        for idx, (_, row) in enumerate(df.head(limit).iterrows()):
            with cols[idx % 4]:
                # Poster
                poster_url = "https://via.placeholder.com/300x450.png?text=Sin+Poster"
                if (
                    pd.notna(row.get("poster_path"))
                    and str(row.get("poster_path")) != ""
                ):
                    poster_url = f"https://image.tmdb.org/t/p/w500{row['poster_path']}"
                st.image(poster_url, use_container_width=True)

                # Título truncado
                titulo = str(row.get("titulo", "Sin Título"))
                if len(titulo) > 30:
                    titulo = titulo[:27] + "..."

                # Año
                year = str(row.get(date_col, ""))[:4]
                if year and year != "nan":
                    st.markdown(f"**{titulo}** ({year})")
                else:
                    st.markdown(f"**{titulo}**")

                # Nota
                nota = row.get("vote_average", 0)
                if nota:
                    st.caption(f"{nota}")

                # Botón de sinopsis
                if st.button("Ver sinopsis", key=f"{key_prefix}_{idx}"):
                    st.toast(str(row.get("overview", "Sin sinopsis disponible.")))

    # =====================================================================================
    # Renderiza las recomendaciones IA dentro de una pestaña
    # =====================================================================================
    def render_recomendaciones_ia(key_prefix="ia", endpoint="recomendar"):
        """Llama al Backend y pinta las recomendaciones del modelo SVD."""
        user_id_ia = usuario.get("id_usuario", None)
        if not user_id_ia:
            st.info("Tu perfil no tiene un ID asociado para generar recomendaciones.")
            return

        try:
            resp_ia = requests.get(
                f"http://localhost:8000/{endpoint}/{user_id_ia}", params={"n": 8}
            )
            if resp_ia.status_code == 200:
                recomendaciones = resp_ia.json().get("recomendaciones", [])
                if recomendaciones:
                    cols_ia = st.columns(4)
                    for idx, rec in enumerate(recomendaciones):
                        with cols_ia[idx % 4]:
                            poster = rec.get("poster_path", "")
                            if poster and poster != "" and poster != "nan":
                                st.image(
                                    f"https://image.tmdb.org/t/p/w500{poster}",
                                    use_container_width=True,
                                )
                            else:
                                st.image(
                                    "https://via.placeholder.com/300x450.png?text=Sin+Poster",
                                    use_container_width=True,
                                )
                            titulo_rec = rec.get("titulo", "Sin Título")
                            if len(titulo_rec) > 30:
                                titulo_rec = titulo_rec[:27] + "..."
                            st.markdown(f"**{titulo_rec}**")
                            st.caption(
                                f"⭐ Predicción IA: {rec['predicted_rating']} / 5.0"
                            )
                            if st.button("Ver sinopsis", key=f"{key_prefix}_{idx}"):
                                st.toast(
                                    rec.get("overview", "Sin sinopsis disponible.")
                                )
                else:
                    st.info("No se encontraron recomendaciones para tu perfil.")
            elif resp_ia.status_code == 503:
                st.warning(
                    "El modelo de IA aún no está entrenado. Pídele al administrador que lo ejecute."
                )
            else:
                st.warning("No se pudieron obtener recomendaciones.")
        except requests.exceptions.ConnectionError:
            st.warning("No se pudo conectar con el Backend para recomendaciones.")

    # =====================================================================================
    # Contenido de una pestaña (recomendaciones + top rated + más vistos)
    # =====================================================================================
    def render_tab_content(df, search, is_movie=True, endpoint_ia="recomendar"):
        """Dibuja las 3 secciones dentro de una pestaña: IA, Top Rated, Más Visto."""
        prefix = "mov" if is_movie else "tv"
        date_col = "fecha_estreno" if is_movie else "first_air_date"

        # Si hay búsqueda activa, mostramos los resultados filtrados
        if search:
            st.subheader("Resultados de búsqueda")
            if not df.empty and "titulo" in df.columns:
                mask = df["titulo"].str.contains(search, case=False, na=False)
                resultados = df[mask]
                if not resultados.empty:
                    render_cards(
                        resultados,
                        limit=12,
                        key_prefix=f"{prefix}_search",
                        date_col=date_col,
                    )
                else:
                    st.info("No se encontraron resultados para tu búsqueda.")
            return

        # --- Sección 1: Recomendaciones IA ---
        st.subheader("Recomendado para ti")
        if is_movie:
            render_recomendaciones_ia(key_prefix=f"{prefix}_ia", endpoint=endpoint_ia)
        else:
            st.info(
                "Las recomendaciones de series están en desarrollo. De momento disfruta del catálogo."
            )

        st.divider()

        # --- Sección 2: Top mejor puntuadas ---
        st.subheader("Mejor puntuadas por la comunidad")
        if not df.empty and "vote_average" in df.columns and "vote_count" in df.columns:
            # Filtro mínimo de votos para que no salgan pelis con 1 voto y nota 10
            df_top = df[df["vote_count"] > 500].sort_values(
                by="vote_average", ascending=False
            )
            render_cards(df_top, limit=8, key_prefix=f"{prefix}_top", date_col=date_col)
        else:
            st.info("No hay datos suficientes para generar el ranking.")

        st.divider()

        # --- Sección 3: Lo más visto ---
        st.subheader("Lo más visto")
        if not df.empty and "vote_count" in df.columns:
            df_popular = df.sort_values(by="vote_count", ascending=False)
            render_cards(
                df_popular, limit=8, key_prefix=f"{prefix}_pop", date_col=date_col
            )
        else:
            st.info("No hay datos suficientes para generar lo más visto.")

    ###########################################################################################
    # --- PESTAÑAS PRINCIPALES ---
    ###########################################################################################

    tab_movies, tab_shows = st.tabs(["Películas", "Series"])

    with tab_movies:
        render_tab_content(
            df_movies, search_query, is_movie=True, endpoint_ia=endpoint_ia
        )

    with tab_shows:
        render_tab_content(
            df_shows, search_query, is_movie=False, endpoint_ia=endpoint_ia
        )
