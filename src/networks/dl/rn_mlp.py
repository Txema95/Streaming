"""
========================================================================================
 RED NEURONAL: WIDE & DEEP LEARNING
========================================================================================
 Paper Original: "Wide & Deep Learning for Recommender Systems" (Google, 2016)

 Arquitectura Híbrida:
 1. WIDE (Ancha): Una regresión lineal que "memoriza" reglas hiper-específicas.
    Por ejemplo: Si Usuario "X" + Película "Y" = Interacción Directa.
 2. DEEP (Profunda): Una red neuronal multicapa (MLP) con Embeddings que "generaliza".
    Por ejemplo: Identifica que la Película "A" es parecida a la "B", aunque el usuario
    nunca haya visto la "A".

 Ambos modelos entrenan *juntos y a la vez* (Joint Training), y sus predicciones
 se suman al final para emitir el veredicto de la nota de la película (0.5 a 5.0).
========================================================================================
"""

import torch
import torch.nn as nn


class WideAndDeepModel(nn.Module):
    def __init__(self, num_users, num_movies, embedding_dim=32, hidden_layers=[64, 32]):
        """
        Inicializa las capas matemáticas de nuestra red neuronal.

        :param num_users: Cantidad total de usuarios únicos en el catálogo.
        :param num_movies: Cantidad total de películas únicas en el catálogo.
        :param embedding_dim: Tamaño del vector profundo (Deep) de cada usuario/película.
        :param hidden_layers: Lista con la cantidad de neuronas en las capas ocultas (Deep).
        """
        super(WideAndDeepModel, self).__init__()

        # ------------------------------------------------------------------------
        # PARTE 1: MODELO WIDE (Memorización)
        # ------------------------------------------------------------------------
        # El modelo lineal asocia directamente un "peso" o "sesgo" a cada película
        # y a cada usuario de manera individual.
        self.wide_user = nn.Embedding(num_users, 1)
        self.wide_movie = nn.Embedding(num_movies, 1)
        self.wide_bias = nn.Parameter(torch.zeros(1))

        # ------------------------------------------------------------------------
        # PARTE 2: MODELO DEEP (Generalización)
        # ------------------------------------------------------------------------
        # Creamos 'Embeddings' (Vectores multidimensionales densos).
        # Si embedding_dim=32, cada película/usuario será descrita por 32 números.
        self.deep_user_embed = nn.Embedding(num_users, embedding_dim)
        self.deep_movie_embed = nn.Embedding(num_movies, embedding_dim)

        # Construimos la Red Neuronal (MLP - Multi-Layer Perceptron) dinámicamente
        deep_layers = []

        # La entrada será la suma del tamaño del vector de usuario + vector de película
        input_dim = embedding_dim * 2

        for hidden_dim in hidden_layers:
            deep_layers.append(nn.Linear(input_dim, hidden_dim))  # Capa matemática
            deep_layers.append(nn.ReLU())  # Activación (no linealidad)
            deep_layers.append(nn.Dropout(0.2))  # Previene que la red memorice
            input_dim = hidden_dim  # Prepara la siguiente capa

        # Capa Final del modelo Deep: Reduce todas las neuronas a 1 solo número (la nota)
        deep_layers.append(nn.Linear(input_dim, 1))

        # Empaquetamos todo en una secuencia
        self.deep_network = nn.Sequential(*deep_layers)

    def forward(self, user_idx, movie_idx):
        """
        Este es el "bucle de pensamiento" de la red.
        Cada vez que le pasamos un usuario y una película, ejecuta estas matemáticas
        para predecir qué nota de 0.5 a 5 estrellas le pondrá.
        """
        # --- 1. Cálculo del modelo WIDE ---
        wide_out = (
            self.wide_user(user_idx) + self.wide_movie(movie_idx) + self.wide_bias
        )

        # --- 2. Cálculo del modelo DEEP ---
        user_emb = self.deep_user_embed(user_idx)
        movie_emb = self.deep_movie_embed(movie_idx)

        # Unimos (concatenamos) la "personalidad" del usuario y la "información" de la peli
        deep_input = torch.cat([user_emb, movie_emb], dim=1)

        # Pasamos la unión por las neuronas ocultas
        deep_out = self.deep_network(deep_input)

        # --- 3. COMBINACIÓN WIDE + DEEP ---
        # La decisión final (sumamos la intuición Deep con el recuerdo Wide)
        prediction = wide_out + deep_out

        # Estabilizador matemático: Obligamos a que la red no escupa números infinitos 
        # (lo que causaba explosión de gradiente). Lo encerramos entre 0 y 5.5 estrellas.
        prediction = torch.sigmoid(prediction) * 5.5

        # Devolvemos la predicción achollando dimensiones extra innecesarias (ej: [[4.3]] -> [4.3])
        return prediction.squeeze(-1)
