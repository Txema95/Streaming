import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import time
import extra_streamlit_components as stx  

cookie_manager = stx.CookieManager()

st.set_page_config(page_title="Admin Panel", layout="wide")
cookies = cookie_manager.get_all()

if not cookies:
    time.sleep(0.5)  # Pausa de medio segundo para sincronizar
    cookies = cookie_manager.get_all()
try:
    saved_cookie = cookies.get(cookie="disney_admin_session")
except:
    saved_cookie = None

st.session_state["admin_autenticado"] = True #añadido para pruebas, eliminar luego

if "admin_autenticado" not in st.session_state:
    if saved_cookie:
        st.session_state["admin_autenticado"] = True
    else:
        st.session_state["admin_autenticado"] = False

if not st.session_state["admin_autenticado"]:
    st.title("Acceso de Administrador")
    st.markdown("Por favor, identifícate como parte del equipo de desarrollo para acceder al panel.")

    with st.form("admin_login_form"):
        admin_user = st.text_input("Usuario")
        admin_pass = st.text_input("Contraseña", type="password")
        submit_admin = st.form_submit_button("Acceder")

        if submit_admin:
            payload = {"username": admin_user, "password": admin_pass}
            try:
                response = requests.post("http://localhost:8000/login", json=payload)

                if response.status_code == 200:
                    datos_usuario = response.json()
                    
                    st.session_state["admin_autenticado"] = True
                    st.session_state["usuario_info"] = datos_usuario["user"]
                    
                    cookie_manager.set(
                        "disney_admin_session",
                        val=admin_user,
                        key="login_cookie",
                        path="/"
                    )
                    
                    st.success(f"Bienvenido, {admin_user}.")
                    st.rerun()
                
                elif response.status_code == 401:
                    st.error("Credenciales de administrador incorrectas.")
                else:
                    st.error(f"Error en el servidor: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("No se pudo conectar con el servidor backend.")
    
# --- PANEL DE ADMINISTRADOR (SI ESTÁ AUTENTICADO) ---
else:
    st.title("Panel de Control de Administrador")
    st.markdown("Gestion de los datos y visualización de métricas clave.")

    # Botón de cerrar sesión actualizado
    if st.button("Cerrar Sesión de Administrador"):
        # 1. Borrar cookie del navegador
        cookie_manager.delete("disney_admin_session", key="logout_cookie")
        # 2. Limpiar session state
        st.session_state["admin_autenticado"] = False
        st.rerun()

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

    tab1, tab2 = st.tabs(["Gestión de Usuarios", "Análisis Exploratorio (EDA)"])

    with tab1:
        st.subheader("Listado de Usuarios (Sincronizados)")
        if "datos_usuarios" in st.session_state:
            st.dataframe(st.session_state["datos_usuarios"], use_container_width=True)
        else:
            st.info("Haz clic en 'Sincronizar con MySQL' en la barra lateral para ver los usuarios.")

    with tab2:
        st.subheader("Análisis Exploratorio de Datos del Catálogo")
        movies_path = "src/data/ready/dataset_final_movies.csv"
        ratings_path = "src/data/ready/ratings_finales_ia.csv"

        if os.path.exists(movies_path) and os.path.exists(ratings_path):
            try:
                df_movies = pd.read_csv(movies_path)
                df_ratings = pd.read_csv(ratings_path)
                st.write("Visualizaciones de datos activas.")
            except Exception as e:
                st.error(f"Error al procesar datos: {e}")