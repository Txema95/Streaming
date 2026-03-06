import streamlit as st

st.set_page_config(page_title="JJ Streaming - Usuario", layout="wide")

st.title(" Bienvenido a SPIRE ")
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

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.image(
            "https://via.placeholder.com/300x450.png?text=Poster",
            use_container_width=True,
        )
        st.caption("Película Ejemplo 1")
    with col2:
        st.image(
            "https://via.placeholder.com/300x450.png?text=Poster",
            use_container_width=True,
        )
        st.caption("Película Ejemplo 2")
    with col3:
        st.image(
            "https://via.placeholder.com/300x450.png?text=Poster",
            use_container_width=True,
        )
        st.caption("Película Ejemplo 3")
    with col4:
        st.image(
            "https://via.placeholder.com/300x450.png?text=Poster",
            use_container_width=True,
        )
        st.caption("Película Ejemplo 4")
