import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import time
import extra_streamlit_components as stx  # Librería extra para manejar Cookies en el navegador

# Inicializamos el gestor de cookies para poder recordar al administrador
cookie_manager = stx.CookieManager()

# Configuramos el nombre de la pestaña del navegador y que ocupe el 100% del ancho de banda
st.set_page_config(page_title="Admin Panel", layout="wide")

# Intentamos leer todas las cookies instaladas actualmente en el navegador del usuario
cookies = cookie_manager.get_all()

# A veces las cookies tardan un pelín en cargar.
# Si no detectamos nada, pausamos 0.5 segundos y reintentamos.
if not cookies:
    time.sleep(0.5)
    cookies = cookie_manager.get_all()

# Buscamos específicamente si dentro de sus cookies existe la nuestra, llamada "disney_admin_session"
try:
    saved_cookie = cookies.get(cookie="disney_admin_session")
except:
    saved_cookie = None

##########################################################################################
st.session_state["admin_autenticado"] = True  # añadido para pruebas, eliminar luego
##########################################################################################

# 'st.session_state' es una especie de memoria temporal RAM que Streamlit mantiene viva
# mientras interactúas con la página. Si recargas (F5), se borra.
# Aquí comprobamos si el admin ya tiene la variable de "autenticado" guardada en esa memoria.
if "admin_autenticado" not in st.session_state:
    # Si no la tenía, comprobamos si sí que tiene la cookie guardada en el disco de su navegador
    if saved_cookie:
        st.session_state["admin_autenticado"] = True
    else:
        st.session_state["admin_autenticado"] = False

# --- ZONA DE LOGIN ---
# Si en la memoria temporal dice que NO está autenticado, le mostramos el formulario
if not st.session_state["admin_autenticado"]:
    st.title("Acceso de Administrador")
    st.markdown(
        "Por favor, identifícate como parte del equipo de desarrollo para acceder al panel."
    )

    # Declaramos un bloque de tipo formulario. Streamlit agrupa todo lo que haya dentro
    with st.form("admin_login_form"):
        admin_user = st.text_input("Usuario")
        admin_pass = st.text_input(
            "Contraseña", type="password"
        )  # type="password" oculta el texto con asteriscos
        submit_admin = st.form_submit_button("Acceder")

        # Este bloque 'if' solo se ejecuta en el instante en que el usuario hace clic en el botón "Acceder"
        if submit_admin:
            # Preparamos un diccionario con los datos, para mandarlo en formato JSON
            payload = {"username": admin_user, "password": admin_pass}
            try:
                # Enviamos una petición de tipo POST a la ruta segura /login de nuestro Backend FastAPI
                response = requests.post("http://localhost:8000/login", json=payload)

                # Si FastAPI nos devuelve un código HTTP 200 (¡Todo correcto!)
                if response.status_code == 200:
                    datos_usuario = (
                        response.json()
                    )  # Traducimos la respuesta a un diccionario Python

                    # Guardamos en la memoria temporal que el login ha sido un éxito
                    st.session_state["admin_autenticado"] = True
                    st.session_state["usuario_info"] = datos_usuario["user"]

                    # IMPORTANTE: Grabamos una Cookie en el navegador del usuario para que la próxima
                    # vez que entre mañana, no tenga que volver a poner la contraseña.
                    cookie_manager.set(
                        "disney_admin_session",
                        val=admin_user,
                        key="login_cookie",
                        path="/",
                    )

                    st.success(f"Bienvenido, {admin_user}.")
                    # Al hacer st.rerun(), obligamos a que el script de python se vuelva a leer desde
                    # la línea 1. Como ahora st.session_state ya es True, entrará directo por el ELSE principal (Línea 74).
                    st.rerun()

                elif response.status_code == 401:
                    st.error("Credenciales de administrador incorrectas.")
                else:
                    st.error(f"Error en el servidor: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("No se pudo conectar con el servidor backend.")

# --- PANEL DE ADMINISTRADOR (SI ESTÁ AUTENTICADO) ---
# Si llega a este 'else', es porque st.session_state["admin_autenticado"] es igual a True
else:
    st.title("Panel de Control de Administrador")
    st.markdown("Gestion de los datos y visualización de métricas clave.")

    # Botón de cerrar sesión: Borramos todas las pruebas de acceso
    if st.button("Cerrar Sesión de Administrador"):
        # 1. Borrar la cookie permanente del navegador
        cookie_manager.delete("disney_admin_session", key="logout_cookie")
        # 2. Limpiar la memoria temporal session_state
        st.session_state["admin_autenticado"] = False
        # Recargamos la app desde cero. Al llegar al 'if' de arriba, verá False y nos mandará al cajón de login.
        st.rerun()

    # st.sidebar es una barra lateral izquierda pegada al borde. Ponemos botones ahí.
    st.sidebar.header("Acciones de Datos")

    # Si se pulsa este botón le pedimos al Backend que averigue todos los usuarios de la base de datos MySQL
    if st.sidebar.button("Sincronizar con MySQL", use_container_width=True):
        response = requests.get("http://localhost:8000/usuarios")

        if response.status_code == 200:
            # pd.DataFrame transforma la enorme lista JSON en una tabla bidimensional
            df = pd.DataFrame(response.json())
            # Guardamos esa tabla en la memoria temporal para pintarla luego en pantalla.
            st.session_state["datos_usuarios"] = df
            st.sidebar.success("Usuarios cargados desde MySQL")
        else:
            st.sidebar.error("Error al conectar con el Backend")

    # Si pulsa importar, lanzamos el ETL
    # Ojo: Este botón congela la app mientras se procesan miles de filas
    if st.sidebar.button("Importar Datos a BD", use_container_width=True):
        response = requests.post("http://localhost:8000/importar_datos")
        if response.status_code == 200:
            st.sidebar.success("Catálogos importados correctamente!")
        else:
            st.sidebar.error("Error al conectar con el Backend")

    tab1, tab2 = st.tabs(["Gestión de Usuarios", "Análisis Exploratorio (EDA)"])

    with tab1:
        st.subheader("Listado de Usuarios (Sincronizados)")
        # Revisamos si hemos cargado los usuarios dándole al botón Sincronizar de la barra lateral
        if "datos_usuarios" in st.session_state:
            # st.dataframe se encarga de pintar la tabla en pantalla (habilitando filtros, poder hacer clic, etc)
            st.dataframe(st.session_state["datos_usuarios"], use_container_width=True)
        else:
            st.info(
                "Haz clic en 'Sincronizar con MySQL' en la barra lateral para ver los usuarios."
            )

    with tab2:
        st.subheader("Análisis Exploratorio de Datos del Catálogo")
        movies_path = "src/data/ready/dataset_final_movies.csv"
        ratings_path = "src/data/ready/ratings_finales_ia.csv"

        # os.path.exists sirve para que no pete la web al intentar cargar un archivo si algún desarrollador
        # todavía no ha generado la carpeta 'ready'. Comprueba si físicamente están ahí.
        if os.path.exists(movies_path) and os.path.exists(ratings_path):
            try:
                # Carga de datos
                df_movies = pd.read_csv(
                    movies_path, on_bad_lines="skip", engine="python"
                )
                df_ratings = pd.read_csv(
                    ratings_path, on_bad_lines="skip", engine="python"
                )

                # Gráfico 1: Top 10 pelis
                st.markdown(
                    "### Top 10 Películas con Mejores Valoraciones (Mín. 500 votos)"
                )
                top_movies = (
                    df_movies[df_movies["vote_count"] > 500]
                    .sort_values(by="vote_average", ascending=False)
                    .head(10)
                )
                fig1, ax1 = plt.subplots(figsize=(10, 6))
                sns.barplot(
                    x="vote_average",
                    y="titulo",
                    data=top_movies,
                    palette="viridis",
                    ax=ax1,
                )
                ax1.set_xlabel("Nota Media (Promedio de votos)")
                ax1.set_ylabel("Título")
                st.pyplot(fig1)

                st.divider()

                # Gráfico 2: Distribución de valoraciones por usuario
                st.markdown(
                    "### Distribución de la Cantidad de Valoraciones por Usuario"
                )
                user_counts = df_ratings["userId"].value_counts()
                fig2, ax2 = plt.subplots(figsize=(10, 6))
                sns.histplot(user_counts, bins=100, kde=True, color="blue", ax=ax2)
                ax2.set_xlabel("Número de películas valoradas por el usuario")
                ax2.set_ylabel("Cantidad de Usuarios")
                ax2.set_xlim(0, 500)
                st.pyplot(fig2)

                # Info importante
                cols_info = st.columns(3)
                cols_info[0].metric(
                    "Media valoraciones / usuario", f"{user_counts.mean():.2f}"
                )
                cols_info[1].metric(
                    "Usuarios con < 20 valoraciones", f"{(user_counts < 20).sum()}"
                )
                cols_info[2].metric("Total de usuarios", f"{len(user_counts)}")

                st.divider()

                # Gráfico 3: Distribución general de Puntuaciones
                st.markdown("### Distribución general de Puntuaciones (Estrellas)")
                fig3, ax3 = plt.subplots(figsize=(10, 6))
                sns.countplot(x="rating", data=df_ratings, palette="coolwarm", ax=ax3)
                ax3.set_xlabel("Puntuación (Rating)")
                ax3.set_ylabel("Cantidad de Votos")
                st.pyplot(fig3)

            except Exception as e:
                st.error(f"Error al procesar datos para EDA: {e}")
