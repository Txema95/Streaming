import pandas as pd

def convertir_json_to_csv():
    df = pd.read_json("src/data/raw/tmdb/series/catalogo_series_tmdb.jsonl", lines=True)
    df.to_csv('src/data/raw/tmdb/series/catalogo_series_tmdb.csv', index=False, encoding='utf-8-sig')
    print(df.head())

convertir_json_to_csv()