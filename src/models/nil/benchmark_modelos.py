"""
benchmark_modelos.py
====================
Benchmarking Framework para el Motor de Recomendación de la Plataforma de Streaming.

Objetivo: comparar empíricamente distintas arquitecturas de recomendación
optimizadas para métricas de RANKING (Precision@K, NDCG@K) en lugar de
métricas de error puntual (RMSE/MAE), ya que el negocio prioriza ordenar
correctamente el Top-K del catálogo para cada usuario.

Arquitecturas en competición
------------------------------
  1. BPR-MF   – Matrix Factorization entrenada con Bayesian Personalised Ranking Loss
                 (pairwise, estado del arte clásico para ranking implícito).
  2. NCF-Lite  – Neural Collaborative Filtering ligero (GMF + MLP fusionados),
                 entrenado con BCE sobre pares positivo/negativo.
  3. LightGCN  – Simplificación del Graph Convolutional Network para CF;
                 sin transformaciones no-lineales, solo propagación de embeddings
                 en el grafo usuario-ítem. State-of-the-art en benchmarks de ranking.

Restricciones de diseño
------------------------
  * NO se construyen matrices densas N×M.
  * Todo opera con embeddings dispersos + DataLoaders por lotes.
  * La sub-muestra inteligente garantiza que el proceso corra en 16 GB de RAM.

Uso
---
    python src/models/benchmark_modelos.py
    python src/models/benchmark_modelos.py --topk 20 --epochs 5 --emb-dim 64
"""

from __future__ import annotations

import argparse
import gc
import logging
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import psutil
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

# ---------------------------------------------------------------------------
# Configuración del logger
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes por defecto (sobreescribibles vía CLI)
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "ready", "ratings_finales_ia.csv"
)
MIN_USER_RATINGS: int = 200   # Usuarios con al menos N valoraciones
MIN_ITEM_RATINGS: int = 100   # Ítems con al menos N valoraciones
EMB_DIM: int = 32             # Dimensión de embeddings (RAM-friendly)
BATCH_SIZE: int = 2048        # Tamaño de lote para training
EPOCHS: int = 3               # Épocas de entrenamiento por modelo
TOP_K: int = 10               # K para Precision@K y NDCG@K
NEG_SAMPLES: int = 4          # Negativos por cada positivo (pairwise / BCE)
LIGHTGCN_LAYERS: int = 2      # Capas de propagación en LightGCN
LEARNING_RATE: float = 1e-3
DEVICE = torch.device("cpu")  # CPU para portabilidad; cambia a "cuda" si dispones de GPU


# ===========================================================================
# SECCIÓN 1 – MUESTREO INTELIGENTE (protección de RAM)
# ===========================================================================

def cargar_y_submuestrar(
    ruta: str,
    min_user_ratings: int = MIN_USER_RATINGS,
    min_item_ratings: int = MIN_ITEM_RATINGS,
) -> pd.DataFrame:
    """
    Lee el CSV de ratings y aplica filtrado iterativo para quedarse con
    usuarios e ítems 'activos'. Reduce drásticamente el tamaño del dataset
    sin introducir sesgo de selección, ya que se trabaja con los actores
    más informativos del grafo de interacciones.

    Returns
    -------
    df_filtrado : pd.DataFrame
        Columnas: userId (int), tmdb_id (int), rating (float).
        Los ids son reindexados a enteros contiguos [0, N) para los embeddings.
    """
    logger.info("Cargando dataset desde %s …", ruta)
    dtype_map = {"userId": "int32", "tmdb_id": "int32", "rating": "float32"}
    df = pd.read_csv(ruta, dtype=dtype_map)
    logger.info("  Filas originales : %d", len(df))

    # Filtrado iterativo (k-core) hasta convergencia
    prev_len = -1
    iteration = 0
    while len(df) != prev_len:
        prev_len = len(df)
        iteration += 1
        # Filtrar por actividad de usuario
        user_counts = df["userId"].value_counts()
        users_ok = user_counts[user_counts >= min_user_ratings].index
        df = df[df["userId"].isin(users_ok)]
        # Filtrar por popularidad de ítem
        item_counts = df["tmdb_id"].value_counts()
        items_ok = item_counts[item_counts >= min_item_ratings].index
        df = df[df["tmdb_id"].isin(items_ok)]

    logger.info(
        "  Sub-muestra final: %d filas | %d usuarios | %d ítems (tras %d iteraciones k-core)",
        len(df), df["userId"].nunique(), df["tmdb_id"].nunique(), iteration,
    )

    # Reindexar ids a enteros contiguos [0, N)
    user_map = {u: i for i, u in enumerate(sorted(df["userId"].unique()))}
    item_map = {it: i for i, it in enumerate(sorted(df["tmdb_id"].unique()))}
    df["userId"] = df["userId"].map(user_map).astype("int32")
    df["tmdb_id"] = df["tmdb_id"].map(item_map).astype("int32")

    return df.reset_index(drop=True)


# ===========================================================================
# SECCIÓN 2 – SPLIT TRAIN / TEST (leave-one-out por usuario)
# ===========================================================================

def split_leave_one_out(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Para cada usuario, reserva su interacción con rating más alto (o la última
    si hay empate) como test. El resto va a train.

    Este esquema es el estándar en papers de ranking (NCF, LightGCN, BPR).
    """
    df_sorted = df.sort_values(["userId", "rating"], ascending=[True, False])
    test_idx = df_sorted.groupby("userId").head(1).index
    test_df = df.loc[test_idx].reset_index(drop=True)
    train_df = df.drop(index=test_idx).reset_index(drop=True)
    logger.info(
        "Split: train=%d | test=%d (1 ítem por usuario)", len(train_df), len(test_df)
    )
    return train_df, test_df


# ===========================================================================
# SECCIÓN 3 – DATASETS PYTORCH
# ===========================================================================

class PairwiseDataset(Dataset):
    """
    Dataset para entrenamiento con pérdida pairwise (BPR / BCE negativos).
    Por cada interacción positiva genera `neg_samples` negativos aleatorios.
    NO cargar la matriz densa completa: solo listas de positivos por usuario.
    """

    def __init__(
        self,
        train_df: pd.DataFrame,
        n_items: int,
        neg_samples: int = NEG_SAMPLES,
    ) -> None:
        self.n_items = n_items
        self.neg_samples = neg_samples

        # Diccionario usuario -> conjunto de ítems positivos (para muestreo negativo)
        self.user_positives: Dict[int, set] = (
            train_df.groupby("userId")["tmdb_id"].apply(set).to_dict()
        )
        # Lista de interacciones (u, i_pos)
        self.interactions: np.ndarray = train_df[["userId", "tmdb_id"]].values.astype(
            np.int64
        )

    def __len__(self) -> int:
        return len(self.interactions) * self.neg_samples

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pos_idx = idx // self.neg_samples
        u, i_pos = self.interactions[pos_idx]
        positives = self.user_positives[u]

        # Muestreo negativo uniforme (rechazo simple)
        i_neg = np.random.randint(self.n_items)
        while i_neg in positives:
            i_neg = np.random.randint(self.n_items)

        return (
            torch.tensor(u, dtype=torch.long),
            torch.tensor(i_pos, dtype=torch.long),
            torch.tensor(i_neg, dtype=torch.long),
        )


# ===========================================================================
# SECCIÓN 4 – MODELOS
# ===========================================================================

# ---------------------------------------------------------------------------
# Modelo 1: BPR-MF (Matrix Factorization con BPR Loss)
# ---------------------------------------------------------------------------

class BPRMF(nn.Module):
    """
    Matrix Factorization clásica en la que los embeddings se aprenden
    minimizando la Bayesian Personalised Ranking Loss.

    BPR Loss: -log σ(r_ui - r_uj), maximiza la diferencia de score entre
    el ítem positivo (i) y el negativo (j) para cada usuario u.

    Referencia: Rendle et al., 2009 – "BPR: Bayesian Personalized Ranking
    from Implicit Feedback."
    """

    def __init__(self, n_users: int, n_items: int, emb_dim: int = EMB_DIM) -> None:
        super().__init__()
        self.user_emb = nn.Embedding(n_users, emb_dim)
        self.item_emb = nn.Embedding(n_items, emb_dim)
        self.user_bias = nn.Embedding(n_users, 1)
        self.item_bias = nn.Embedding(n_items, 1)
        # Inicialización normal con varianza pequeña (estabilidad)
        nn.init.normal_(self.user_emb.weight, std=0.01)
        nn.init.normal_(self.item_emb.weight, std=0.01)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.item_bias.weight)

    def score(self, users: torch.Tensor, items: torch.Tensor) -> torch.Tensor:
        """Calcula el score de relevancia para pares (usuario, ítem)."""
        u = self.user_emb(users)        # [B, D]
        it = self.item_emb(items)       # [B, D]
        ub = self.user_bias(users).squeeze(1)   # [B]
        ib = self.item_bias(items).squeeze(1)   # [B]
        return (u * it).sum(dim=1) + ub + ib    # [B]

    def forward(
        self,
        users: torch.Tensor,
        pos_items: torch.Tensor,
        neg_items: torch.Tensor,
    ) -> torch.Tensor:
        """Retorna BPR Loss para un lote de tripletas (u, i+, i-)."""
        pos_score = self.score(users, pos_items)
        neg_score = self.score(users, neg_items)
        loss = -torch.log(torch.sigmoid(pos_score - neg_score) + 1e-8).mean()
        return loss

    def predict_all_items(
        self, user_tensor: torch.Tensor, n_items: int
    ) -> torch.Tensor:
        """Scores de un único usuario contra todos los ítems. Usado en evaluación."""
        all_items = torch.arange(n_items, device=DEVICE)
        u = self.user_emb(user_tensor).expand(n_items, -1)  # [N, D]
        it = self.item_emb(all_items)                        # [N, D]
        ub = self.user_bias(user_tensor).expand(n_items, 1).squeeze(1)
        ib = self.item_bias(all_items).squeeze(1)
        return (u * it).sum(dim=1) + ub + ib                 # [N]


# ---------------------------------------------------------------------------
# Modelo 2: NCF-Lite (Neural Collaborative Filtering)
# ---------------------------------------------------------------------------

class NCFLite(nn.Module):
    """
    Neural Collaborative Filtering con dos ramas fusionadas:
      - GMF (Generalized Matrix Factorization): producto elemento a elemento.
      - MLP: concatena embeddings y los pasa por capas lineales.

    La capa final combina ambas ramas con una proyección 1-D que produce
    un logit interpretado como probabilidad de interacción positiva.

    Entrenado con Binary Cross-Entropy sobre pares (positivo, negativo).

    Referencia: He et al., 2017 – "Neural Collaborative Filtering."
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        emb_dim: int = EMB_DIM,
        mlp_layers: List[int] | None = None,
    ) -> None:
        super().__init__()
        if mlp_layers is None:
            mlp_layers = [emb_dim * 2, emb_dim, emb_dim // 2]

        # Embeddings separados para GMF y MLP
        self.gmf_user = nn.Embedding(n_users, emb_dim)
        self.gmf_item = nn.Embedding(n_items, emb_dim)
        self.mlp_user = nn.Embedding(n_users, emb_dim)
        self.mlp_item = nn.Embedding(n_items, emb_dim)

        # Bloque MLP
        mlp_modules: List[nn.Module] = []
        in_size = emb_dim * 2
        for out_size in mlp_layers:
            mlp_modules += [nn.Linear(in_size, out_size), nn.ReLU()]
            in_size = out_size
        self.mlp = nn.Sequential(*mlp_modules)

        # Capa de fusión GMF + MLP
        self.output_layer = nn.Linear(emb_dim + mlp_layers[-1], 1)

        nn.init.normal_(self.gmf_user.weight, std=0.01)
        nn.init.normal_(self.gmf_item.weight, std=0.01)
        nn.init.normal_(self.mlp_user.weight, std=0.01)
        nn.init.normal_(self.mlp_item.weight, std=0.01)

    def score(self, users: torch.Tensor, items: torch.Tensor) -> torch.Tensor:
        # Rama GMF
        gmf_out = self.gmf_user(users) * self.gmf_item(items)  # [B, D]
        # Rama MLP
        mlp_in = torch.cat(
            [self.mlp_user(users), self.mlp_item(items)], dim=1
        )  # [B, 2D]
        mlp_out = self.mlp(mlp_in)                              # [B, H]
        # Fusión y logit
        fused = torch.cat([gmf_out, mlp_out], dim=1)
        return self.output_layer(fused).squeeze(1)              # [B]

    def forward(
        self,
        users: torch.Tensor,
        pos_items: torch.Tensor,
        neg_items: torch.Tensor,
    ) -> torch.Tensor:
        """BCE Loss sobre pares positivo / negativo."""
        pos_score = self.score(users, pos_items)
        neg_score = self.score(users, neg_items)
        # Etiquetas: 1 para positivo, 0 para negativo
        scores = torch.cat([pos_score, neg_score])
        labels = torch.cat(
            [torch.ones_like(pos_score), torch.zeros_like(neg_score)]
        )
        return nn.functional.binary_cross_entropy_with_logits(scores, labels)

    def predict_all_items(
        self, user_tensor: torch.Tensor, n_items: int
    ) -> torch.Tensor:
        all_items = torch.arange(n_items, device=DEVICE)
        users_exp = user_tensor.expand(n_items)
        return self.score(users_exp, all_items)


# ---------------------------------------------------------------------------
# Modelo 3: LightGCN
# ---------------------------------------------------------------------------

class LightGCN(nn.Module):
    """
    Light Graph Convolutional Network para Collaborative Filtering.

    Elimina la transformación no-lineal del GCN clásico; solo propaga
    embeddings en el grafo bipartito usuario-ítem. El embedding final
    de cada nodo es la media ponderada de sus representaciones en cada
    capa (α_k = 1/(L+1)).

    La pérdida de entrenamiento es también BPR (como BPRMF), pero los
    embeddings capturan estructura de vecindad de orden superior en el
    grafo de interacciones.

    Referencia: He et al., 2020 – "LightGCN: Simplifying and Powering
    Graph Convolution Network for Recommendation."

    Nota de implementación: se usa propagación de mensajes en modo sparse
    (torch.sparse) para no materializar la matriz de adyacencia densa.
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        emb_dim: int = EMB_DIM,
        n_layers: int = LIGHTGCN_LAYERS,
    ) -> None:
        super().__init__()
        self.n_users = n_users
        self.n_items = n_items
        self.n_layers = n_layers

        # Embeddings iniciales (solo estos tienen parámetros entrenables)
        self.user_emb0 = nn.Embedding(n_users, emb_dim)
        self.item_emb0 = nn.Embedding(n_items, emb_dim)
        nn.init.normal_(self.user_emb0.weight, std=0.01)
        nn.init.normal_(self.item_emb0.weight, std=0.01)

        # La matriz de adyacencia normalizada se registra como buffer (no parámetro)
        self.register_buffer("adj", torch.zeros(1))  # placeholder; se setea en init_graph

    def init_graph(self, train_df: pd.DataFrame) -> None:
        """
        Construye la matriz de adyacencia simétrica normalizada en formato
        sparse (COO) a partir del dataframe de entrenamiento.

        La normalización sigue LightGCN: Â = D^{-1/2} A D^{-1/2}
        donde A es la matriz de adyacencia del grafo bipartito.
        """
        logger.info("  Construyendo grafo de adyacencia sparse para LightGCN …")
        users = torch.tensor(train_df["userId"].values, dtype=torch.long)
        items = torch.tensor(train_df["tmdb_id"].values, dtype=torch.long)

        n = self.n_users + self.n_items
        # Bloque superior derecho: usuario -> ítem
        row = torch.cat([users, items + self.n_users])
        col = torch.cat([items + self.n_users, users])
        values = torch.ones(row.size(0))

        # Normalización simétrica: d_i^{-1/2}
        edge_index = torch.stack([row, col], dim=0)
        deg = torch.zeros(n)
        deg.scatter_add_(0, row, torch.ones(row.size(0)))
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt[deg_inv_sqrt == float("inf")] = 0.0
        norm_values = deg_inv_sqrt[row] * values * deg_inv_sqrt[col]

        adj = torch.sparse_coo_tensor(edge_index, norm_values, size=(n, n))
        self.adj = adj.coalesce()
        logger.info("  Grafo creado: %d nodos, %d aristas (sparse)", n, row.size(0))

    def _propagate(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Propaga los embeddings L veces por el grafo y devuelve la media
        de todas las capas (embedding final LightGCN).
        """
        # Concatenar embeddings de usuario e ítem en un tensor conjunto
        emb0 = torch.cat([self.user_emb0.weight, self.item_emb0.weight], dim=0)
        emb = emb0
        all_embs = [emb0]

        for _ in range(self.n_layers):
            emb = torch.sparse.mm(self.adj, emb)
            all_embs.append(emb)

        # Media de capas (α_k = 1/(L+1))
        final_emb = torch.stack(all_embs, dim=1).mean(dim=1)
        users_emb = final_emb[: self.n_users]
        items_emb = final_emb[self.n_users :]
        return users_emb, items_emb

    def score(
        self,
        users: torch.Tensor,
        items: torch.Tensor,
        users_emb: torch.Tensor,
        items_emb: torch.Tensor,
    ) -> torch.Tensor:
        return (users_emb[users] * items_emb[items]).sum(dim=1)

    def forward(
        self,
        users: torch.Tensor,
        pos_items: torch.Tensor,
        neg_items: torch.Tensor,
    ) -> torch.Tensor:
        """BPR Loss con embeddings propagados por el grafo."""
        users_emb, items_emb = self._propagate()
        pos_score = self.score(users, pos_items, users_emb, items_emb)
        neg_score = self.score(users, neg_items, users_emb, items_emb)
        bpr_loss = -torch.log(
            torch.sigmoid(pos_score - neg_score) + 1e-8
        ).mean()
        # Regularización L2 sobre embeddings de entrada (no sobre los propagados)
        reg_loss = (
            self.user_emb0(users).norm(2).pow(2)
            + self.item_emb0(pos_items).norm(2).pow(2)
            + self.item_emb0(neg_items).norm(2).pow(2)
        ) / len(users) * 1e-4
        return bpr_loss + reg_loss

    def predict_all_items(
        self, user_tensor: torch.Tensor, n_items: int
    ) -> torch.Tensor:
        with torch.no_grad():
            users_emb, items_emb = self._propagate()
        u_emb = users_emb[user_tensor]          # [D]
        return (u_emb.unsqueeze(0) * items_emb).sum(dim=1)  # [N_items]


# ===========================================================================
# SECCIÓN 5 – MÉTRICAS DE RANKING
# ===========================================================================

def precision_at_k(
    recommended: List[int], relevant: set, k: int
) -> float:
    """Fracción de los primeros K recomendados que son relevantes."""
    hits = sum(1 for item in recommended[:k] if item in relevant)
    return hits / k


def ndcg_at_k(
    recommended: List[int], relevant: set, k: int
) -> float:
    """
    Normalized Discounted Cumulative Gain @K.
    Premia rangos altos de los ítems relevantes con descuento logarítmico.
    """
    dcg = sum(
        1.0 / np.log2(rank + 2)
        for rank, item in enumerate(recommended[:k])
        if item in relevant
    )
    # IDCG: todos los relevantes en las posiciones top
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / np.log2(rank + 2) for rank in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(
    recommended: List[int], relevant: set, k: int
) -> float:
    """Fracción de ítems relevantes que aparecen en los primeros K."""
    if not relevant:
        return 0.0
    hits = sum(1 for item in recommended[:k] if item in relevant)
    return hits / len(relevant)


# ===========================================================================
# SECCIÓN 6 – ENTRENADOR GENÉRICO
# ===========================================================================

@dataclass
class BenchmarkResult:
    """Contenedor de resultados para un modelo."""
    model_name: str
    precision_at_k: float = 0.0
    ndcg_at_k: float = 0.0
    recall_at_k: float = 0.0
    rmse: float = 0.0           # Anecdótico; no es la métrica principal
    avg_epoch_time_s: float = 0.0
    peak_ram_mb: float = 0.0
    total_train_time_s: float = 0.0
    epochs_trained: int = 0


def entrenar_modelo(
    model: nn.Module,
    train_loader: DataLoader,
    optimizer: optim.Optimizer,
    epochs: int,
) -> Tuple[float, float, float]:
    """
    Bucle de entrenamiento genérico para los tres modelos.

    Returns
    -------
    avg_epoch_time, total_time, peak_ram_mb
    """
    model.train()
    process = psutil.Process(os.getpid())

    tracemalloc.start()
    epoch_times: List[float] = []
    total_start = time.perf_counter()

    for epoch in range(1, epochs + 1):
        epoch_loss = 0.0
        epoch_start = time.perf_counter()

        for batch in train_loader:
            users, pos_items, neg_items = [t.to(DEVICE) for t in batch]
            optimizer.zero_grad()
            loss = model(users, pos_items, neg_items)
            loss.backward()
            # Gradient clipping para estabilidad numérica
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item()

        epoch_time = time.perf_counter() - epoch_start
        epoch_times.append(epoch_time)
        logger.info(
            "    Época %d/%d – Loss: %.4f – Tiempo: %.1fs",
            epoch, epochs, epoch_loss / len(train_loader), epoch_time,
        )

    total_time = time.perf_counter() - total_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # RAM real del proceso (más fiable que tracemalloc para objetos C)
    ram_mb = process.memory_info().rss / 1024**2

    return (
        float(np.mean(epoch_times)),
        total_time,
        ram_mb,
    )


# ===========================================================================
# SECCIÓN 7 – EVALUADOR DE RANKING
# ===========================================================================

@torch.no_grad()
def evaluar_ranking(
    model: nn.Module,
    test_df: pd.DataFrame,
    train_df: pd.DataFrame,
    n_items: int,
    k: int = TOP_K,
    max_users: int = 500,
) -> Tuple[float, float, float, float]:
    """
    Evalúa Precision@K, NDCG@K, Recall@K y RMSE (anecdótico).

    Estrategia: Para cada usuario de test, puntúa TODOS los ítems,
    excluye los que ya vio en train, y toma el Top-K. Si el ítem de
    test aparece en el Top-K → hit.

    El cálculo vectorizado por usuario evita matrices densas completas;
    en cada llamada solo se materializa un vector de n_items floats.

    Parameters
    ----------
    max_users : int
        Límite de usuarios a evaluar (para agilizar el benchmark).
    """
    model.eval()
    process = psutil.Process(os.getpid())

    # Ítems vistos por cada usuario en train (para exclusión)
    train_seen: Dict[int, set] = (
        train_df.groupby("userId")["tmdb_id"].apply(set).to_dict()
    )

    precisions, ndcgs, recalls = [], [], []
    sq_errors: List[float] = []

    # Muestreo de usuarios de test para agilizar
    test_users = test_df["userId"].unique()
    if len(test_users) > max_users:
        test_users = np.random.choice(test_users, size=max_users, replace=False)

    for uid in test_users:
        user_test = test_df[test_df["userId"] == uid]
        relevant_items = set(user_test["tmdb_id"].values)
        true_rating = float(user_test["rating"].iloc[0])

        user_tensor = torch.tensor(uid, dtype=torch.long, device=DEVICE)
        scores = model.predict_all_items(user_tensor, n_items).cpu().numpy()

        # Excluir ítems ya vistos en train
        seen = train_seen.get(uid, set())
        for s_item in seen:
            scores[s_item] = -np.inf

        top_k_items = np.argpartition(scores, -k)[-k:]
        top_k_items = top_k_items[np.argsort(scores[top_k_items])[::-1]].tolist()

        precisions.append(precision_at_k(top_k_items, relevant_items, k))
        ndcgs.append(ndcg_at_k(top_k_items, relevant_items, k))
        recalls.append(recall_at_k(top_k_items, relevant_items, k))

        # RMSE anecdótico: score del ítem de test vs. rating real normalizado
        for rel_item in relevant_items:
            pred_score = float(np.clip(scores[rel_item], 0, 1) * 5.0)
            sq_errors.append((pred_score - true_rating) ** 2)

    rmse = float(np.sqrt(np.mean(sq_errors))) if sq_errors else float("nan")
    return (
        float(np.mean(precisions)),
        float(np.mean(ndcgs)),
        float(np.mean(recalls)),
        rmse,
    )


# ===========================================================================
# SECCIÓN 8 – ORQUESTADOR DEL BENCHMARK
# ===========================================================================

def ejecutar_benchmark(
    df: pd.DataFrame,
    epochs: int = EPOCHS,
    emb_dim: int = EMB_DIM,
    batch_size: int = BATCH_SIZE,
    top_k: int = TOP_K,
    neg_samples: int = NEG_SAMPLES,
    lgcn_layers: int = LIGHTGCN_LAYERS,
) -> List[BenchmarkResult]:
    """
    Orquesta el benchmark completo: split, entrenamiento y evaluación
    de los tres modelos. Devuelve una lista de BenchmarkResult.
    """
    n_users = int(df["userId"].max()) + 1
    n_items = int(df["tmdb_id"].max()) + 1
    logger.info("Dimensiones del espacio: %d usuarios × %d ítems", n_users, n_items)

    train_df, test_df = split_leave_one_out(df)

    # Dataset y DataLoader pairwise (compartido por los tres modelos)
    pair_dataset = PairwiseDataset(train_df, n_items, neg_samples=neg_samples)
    train_loader = DataLoader(
        pair_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,   # 0 para compatibilidad Windows sin multiprocessing issues
        pin_memory=False,
    )

    results: List[BenchmarkResult] = []

    # ------------------------------------------------------------------
    # Definición de los competidores
    # ------------------------------------------------------------------
    competidores = [
        (
            "BPR-MF",
            BPRMF(n_users, n_items, emb_dim=emb_dim),
        ),
        (
            "NCF-Lite",
            NCFLite(n_users, n_items, emb_dim=emb_dim),
        ),
        (
            "LightGCN",
            LightGCN(n_users, n_items, emb_dim=emb_dim, n_layers=lgcn_layers),
        ),
    ]

    for model_name, model in competidores:
        logger.info("=" * 60)
        logger.info("ENTRENANDO: %s", model_name)
        logger.info("=" * 60)

        model = model.to(DEVICE)

        # Inicialización especial para LightGCN: construir grafo sparse
        if isinstance(model, LightGCN):
            model.init_graph(train_df)

        optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

        avg_epoch_t, total_t, peak_ram = entrenar_modelo(
            model, train_loader, optimizer, epochs
        )

        logger.info("Evaluando %s en test set (Top-%d)…", model_name, top_k)
        prec, ndcg, recall, rmse = evaluar_ranking(
            model, test_df, train_df, n_items, k=top_k
        )

        result = BenchmarkResult(
            model_name=model_name,
            precision_at_k=prec,
            ndcg_at_k=ndcg,
            recall_at_k=recall,
            rmse=rmse,
            avg_epoch_time_s=avg_epoch_t,
            peak_ram_mb=peak_ram,
            total_train_time_s=total_t,
            epochs_trained=epochs,
        )
        results.append(result)
        logger.info(
            "  Precision@%d=%.4f | NDCG@%d=%.4f | Recall@%d=%.4f | RMSE=%.4f",
            top_k, prec, top_k, ndcg, top_k, recall, rmse,
        )

        # Liberar memoria del modelo antes del siguiente
        del model
        gc.collect()

    return results


# ===========================================================================
# SECCIÓN 9 – TABLA RESUMEN
# ===========================================================================

def imprimir_tabla_resumen(results: List[BenchmarkResult], top_k: int) -> None:
    """
    Imprime en consola una tabla comparativa clara con todos los resultados
    del benchmark. La ordenación principal es por NDCG@K (métrica de negocio).
    """
    col_w = [14, 13, 13, 13, 10, 14, 14, 8]
    headers = [
        "Modelo",
        f"Precision@{top_k}",
        f"NDCG@{top_k}",
        f"Recall@{top_k}",
        "RMSE*",
        "T.époc (s)",
        "RAM pico (MB)",
        "Épocas",
    ]

    sep = "+" + "+".join("-" * w for w in col_w) + "+"
    header_row = (
        "|"
        + "|".join(h.center(w) for h, w in zip(headers, col_w))
        + "|"
    )

    print("\n")
    print("=" * 100)
    print("  BENCHMARK RESUMEN – Motor de Recomendación de Streaming")
    print(f"  Métrica principal: NDCG@{top_k}  |  * RMSE es anecdótico (no es objetivo de negocio)")
    print("=" * 100)
    print(sep)
    print(header_row)
    print(sep)

    sorted_results = sorted(results, key=lambda r: r.ndcg_at_k, reverse=True)
    for i, r in enumerate(sorted_results):
        medal = ["[1]", "[2]", "[3]"][i] if i < 3 else "   "
        row = "|".join([
            f" {medal} {r.model_name}".ljust(col_w[0] - 1) + " ",
            f"{r.precision_at_k:.4f}".center(col_w[1]),
            f"{r.ndcg_at_k:.4f}".center(col_w[2]),
            f"{r.recall_at_k:.4f}".center(col_w[3]),
            f"{r.rmse:.4f}".center(col_w[4]),
            f"{r.avg_epoch_time_s:.1f}".center(col_w[5]),
            f"{r.peak_ram_mb:.0f}".center(col_w[6]),
            f"{r.epochs_trained}".center(col_w[7]),
        ])
        print("|" + row + "|")
    print(sep)

    # Resumen textual
    best = sorted_results[0]
    print(
        f"\n  Ganador del benchmark: {best.model_name} "
        f"(NDCG@{top_k}={best.ndcg_at_k:.4f})"
    )
    if len(sorted_results) > 1:
        worst = sorted_results[-1]
        fastest = min(results, key=lambda r: r.avg_epoch_time_s)
        print(
            f"  Modelo más eficiente computacionalmente: {fastest.model_name} "
            f"({fastest.avg_epoch_time_s:.1f}s/época, {fastest.peak_ram_mb:.0f} MB)"
        )
    print()


# ===========================================================================
# SECCIÓN 10 – PUNTO DE ENTRADA
# ===========================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmarking Framework – Motor de Recomendación Streaming"
    )
    parser.add_argument(
        "--data", default=DATA_PATH,
        help="Ruta al CSV de ratings (userId, tmdb_id, rating)."
    )
    parser.add_argument(
        "--min-user-ratings", type=int, default=MIN_USER_RATINGS,
        help="Mínimo de valoraciones por usuario para incluirlo en la sub-muestra."
    )
    parser.add_argument(
        "--min-item-ratings", type=int, default=MIN_ITEM_RATINGS,
        help="Mínimo de valoraciones por ítem para incluirlo en la sub-muestra."
    )
    parser.add_argument(
        "--epochs", type=int, default=EPOCHS,
        help="Número de épocas de entrenamiento por modelo."
    )
    parser.add_argument(
        "--emb-dim", type=int, default=EMB_DIM,
        help="Dimensión de los embeddings de usuario e ítem."
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help="Tamaño del mini-lote para el DataLoader."
    )
    parser.add_argument(
        "--topk", type=int, default=TOP_K,
        help="K para las métricas de ranking Precision@K y NDCG@K."
    )
    parser.add_argument(
        "--neg-samples", type=int, default=NEG_SAMPLES,
        help="Número de negativos por interacción positiva en el dataset pairwise."
    )
    parser.add_argument(
        "--lgcn-layers", type=int, default=LIGHTGCN_LAYERS,
        help="Número de capas de propagación de LightGCN."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    lgcn_layers = args.lgcn_layers

    logger.info("=== BENCHMARKING FRAMEWORK - Motor de Recomendacion de Streaming ===")
    logger.info("Device: %s | Epochs: %d | Emb-Dim: %d | Top-K: %d",
                DEVICE, args.epochs, args.emb_dim, args.topk)

    # 1. Cargar y sub-muestrear datos (proteccion de RAM)
    df = cargar_y_submuestrar(
        ruta=args.data,
        min_user_ratings=args.min_user_ratings,
        min_item_ratings=args.min_item_ratings,
    )

    if len(df) == 0:
        logger.error(
            "La sub-muestra resultó vacía. "
            "Reduce --min-user-ratings o --min-item-ratings."
        )
        sys.exit(1)

    # 2. Ejecutar benchmark
    resultados = ejecutar_benchmark(
        df=df,
        epochs=args.epochs,
        emb_dim=args.emb_dim,
        batch_size=args.batch_size,
        top_k=args.topk,
        neg_samples=args.neg_samples,
        lgcn_layers=lgcn_layers,
    )

    # 3. Imprimir tabla comparativa
    imprimir_tabla_resumen(resultados, top_k=args.topk)
