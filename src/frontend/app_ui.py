import streamlit as st

st.set_page_config(
    page_title="Proyecto 4 - Streaming",
)

st.write("# Bienvenido al Sistema de Streaming")

st.sidebar.success("Selecciona un perfil en el panel de navegación de arriba.")

st.markdown(
    """
    Esta es la interfaz unificada del Proyecto 4 de Streaming. Hemos dividido 
    las funcionalidades en dos perfiles principales:

    **Selecciona una página en el menú de la izquierda** para comenzar:

    ### Administrador
    - Sincroniza datos con la base de datos MySQL.
    - Lanza procesos de importación y limpieza de datos (ETL).
    - Visualiza métricas analíticas clave (EDA interactivo).

    ### Usuario
    - Búsqueda en el catálogo de películas y series.
    - Motor de recomendación inteligente basado en IA *(Próximamente)*.
"""
)
