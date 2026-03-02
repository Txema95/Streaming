import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Admin Panel", layout="wide")

st.title("🚀 Panel de Control de Datos")

# Sidebar para acciones
if st.sidebar.button("🔄 Sincronizar con MySQL"):
    response = requests.get("http://localhost:8000/usuarios")
    if response.status_code == 200:
        df = pd.DataFrame(response.json())
        st.session_state['datos'] = df
        st.success("Datos cargados!")
    else:
        st.error("Error al conectar con el Backend")
if st.sidebar.button("🔄 Importar datos"):
    response = requests.post("http://localhost:8000/importar_datos")
    if response.status_code == 200:
        st.success("Datos importados!")
    else:
        st.error("Error al conectar con el Backend")

# Mostrar tabla si hay datos
if 'datos' in st.session_state:
    st.write("### Listado de Usuarios")
    st.dataframe(st.session_state['datos'], use_container_width=True)