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
                            # CORRECCION: Ajustamos a las verdaderas columnas de la BDD -> id_usuario y username
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

# ---- PANTALLA PRINCIPAL DEL USUARIO (Logueado) ----
else:
    usuario = st.session_state["usuario_actual"]
    nombre_mostrar = usuario.get("name", f"Usuario #{usuario.get('id')}")

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
        "Descubre películas y series gracias a nuestro Recomendador de Inteligencia Artificial."
    )
    st.info(
        "El sistema de recomendación está en desarrollo. ¡Pronto podrás ver tu catálogo personalizado aquí!"
    )

    # Simulación de un buscador de catálogo
    search_query = st.text_input("Busca una película o serie...")

    if search_query:
        st.write(f"Resultados de búsqueda para: **{search_query}**")
        st.write("*(Simulación de catálogo...)*")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.image(
                "https://via.placeholder.com/300x450.png?text=Poster",
                use_container_width=True,
            )
            st.caption("Película Ejemplo 1")
        with c2:
            st.image(
                "https://via.placeholder.com/300x450.png?text=Poster",
                use_container_width=True,
            )
            st.caption("Película Ejemplo 2")
        with c3:
            st.image(
                "https://via.placeholder.com/300x450.png?text=Poster",
                use_container_width=True,
            )
            st.caption("Película Ejemplo 3")
        with c4:
            st.image(
                "https://via.placeholder.com/300x450.png?text=Poster",
                use_container_width=True,
            )
            st.caption("Película Ejemplo 4")
