import pandas as pd


def clean_wrong_numerical_types(input_df: pd.DataFrame) -> pd.DataFrame:
    """
    parameters
    ------------

    input_data : pd.dataframe
    Cambiamos las "," por "." en las columnas numericas

    """

def check_duplicated(input_data: pd.DataFrame, column_id: str) -> pd.DataFrame:
    """Elimina las filas duplicadas basándose en un ID único."""
    return input_data.drop_duplicates(subset=[column_id])

def filter_adult_content(input_data: pd.DataFrame) -> pd.DataFrame:
    """Aplica el Filtro del Magnate: elimina contenido para adultos."""
    if 'adult' in input_data.columns:
        return input_data[input_data['adult'] == False]
    return input_data

def remove_empty_overviews(input_data: pd.DataFrame) -> pd.DataFrame:
    """Elimina películas o series que no tengan sinopsis."""
    input_data = input_data.dropna(subset=['overview'])
    return input_data[input_data['overview'].str.strip() != '']

