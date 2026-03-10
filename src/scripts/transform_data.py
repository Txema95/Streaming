import pandas as pd


def convertir_json_to_csv():
    df_series = pd.read_json(
        "src/data/raw/tmdb/series/catalogo_series_tmdb.jsonl", lines=True
    )
    df_series.to_csv(
        "src/data/raw/tmdb/series/catalogo_series_tmdb.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # df_movies = pd.read_json("src/data/raw/tmdb/movies/catalogo_peliculas_tmdb.jsonl", lines=True)
    # df_movies.to_csv('src/data/raw/tmdb/movies/catalogo_peliculas_tmdb.csv', index=False, encoding='utf-8-sig')


convertir_json_to_csv()
