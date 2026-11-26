"""Lee las dos exportaciones y las deja en un esquema comun.

El problema que resuelve este modulo: los dos clientes exportan la misma
informacion con formatos distintos. El Cliente A trae el area en una columna
propia; el Cliente B la trae dentro del nombre del conjunto de anuncios y hay
que extraerla de la cadena. Hasta que las dos no hablan el mismo idioma no se
puede comparar nada.
"""

# ---------------------------------------------------------------------------
# Bloque 1: importaciones y esquema de columnas
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

COLUMNAS_CLIENTE_A = {
    "Inicio del informe": "fecha",
    "Importe gastado (EUR)": "inversion_eur",
    "Impresiones": "impresiones",
    "Alcance": "alcance",
    "Clics en el enlace": "clics_enlace",
    "Clics (todos)": "clics_todos",
    "Compras": "compras",
    "Valor de conversion de compras": "valor_compras",
    "Visitas a la pagina de destino": "visitas_landing",
}

COLUMNAS_CLIENTE_B = {
    "Dia": "fecha",
    "Importe gastado (EUR)": "inversion_eur",
    "Impresiones": "impresiones",
    "Alcance": "alcance",
    "Clics en el enlace": "clics_enlace",
    "Clics (todos)": "clics_todos",
    "Compras": "compras",
    "Valor de conversion de compras": "valor_compras",
    "Visitas a la pagina de destino": "visitas_landing",
}

# El Cliente A categoriza en espanol y el B en ingles. El esquema comun va en
# ingles, asi que el A se traduce al cargarlo.
AREAS_CLIENTE_A = {"MUJER": "Women", "HOMBRE": "Men", "INFANTIL": "Kids"}

ORDEN_FINAL = ["fecha", "cliente", "pais", "area", "inversion_eur",
               "impresiones", "alcance", "clics_enlace", "clics_todos",
               "compras", "valor_compras", "visitas_landing"]


# ---------------------------------------------------------------------------
# Bloque 2: limpieza de nombres de columnas
# ---------------------------------------------------------------------------

def limpiar_nombres_columnas(df):
    """Normaliza los nombres de las columnas tal y como llegan de Meta.

    Meta exporta algunas cabeceras con un espacio duro (\\xa0) en lugar de un
    espacio normal. En pantalla no se distingue, asi que el nombre parece
    coincidir y cualquier operacion por nombre falla con KeyError sin que se
    vea el motivo. Esta funcion es la primera que se llama sobre cada
    exportacion, antes de tocar nada mas.
    """
    df = df.copy()
    df.columns = df.columns.str.replace("\xa0", " ").str.strip()
    return df


# ---------------------------------------------------------------------------
# Bloque 3: derivacion del area
# ---------------------------------------------------------------------------

def extraer_area(nombres):
    """Saca el area (Women / Men / Kids) del nombre del conjunto de anuncios.

    Dos trampas que obligan a escribirlo asi:

    1. "men" esta dentro de "women" y "man" dentro de "performance". Buscar la
       subcadena a secas clasificaria como Men todo lo que en realidad es
       Women, y el orden de las condiciones no basta por si solo.
    2. El limite de palabra \\b no sirve, porque los nombres separan con
       guiones bajos y acaban en numeros, y tanto "_" como los digitos cuentan
       como caracteres de palabra. Asi que "WOMEN_2026" no tiene un limite de
       palabra donde hace falta.

    La solucion son las comprobaciones de alrededor (?<![a-z]) y (?![a-z]):
    exigen que lo que rodea al termino no sea una letra, sin importar si es un
    guion bajo, un digito o el principio de la cadena.

    Devuelve None en las filas sin area reconocible, que son las que el
    analisis por area tiene que descartar en lugar de adivinar.
    """
    nombres = nombres.str.lower()
    condiciones = [
        nombres.str.contains(r"(?<![a-z])women(?![a-z])", regex=True),
        nombres.str.contains(r"(?<![a-z])kids(?![a-z])", regex=True),
        nombres.str.contains(r"(?<![a-z])(?:men|man)(?![a-z])", regex=True),
    ]
    return np.select(condiciones, ["Women", "Kids", "Men"], default=None)


# ---------------------------------------------------------------------------
# Bloque 4: preparacion de cada cliente
# ---------------------------------------------------------------------------

def preparar_cliente_a(ruta):
    """Cliente A: un mercado, area en columna propia, exportacion en Excel."""
    df = pd.read_excel(ruta, sheet_name="BBDD")
    df = limpiar_nombres_columnas(df)

    df["area"] = df["Categoria de campana"].map(AREAS_CLIENTE_A)
    df = df.rename(columns=COLUMNAS_CLIENTE_A, errors="raise")

    df["cliente"] = "Cliente A"
    df["pais"] = "ES"
    return df[ORDEN_FINAL]


def preparar_cliente_b(ruta):
    """Cliente B: cinco mercados, area dentro del nombre, exportacion en CSV."""
    df = pd.read_csv(ruta)
    df = limpiar_nombres_columnas(df)

    df["area"] = extraer_area(df["Nombre del conjunto de anuncios"])
    # Las filas sin area son campanas de marca: no entran en un analisis por
    # area. Se descartan aqui y el pipeline deja escrito cuantas eran.
    df = df[df["area"].notna()]

    df["pais"] = df["Nombre de la cuenta"].str.strip("[]")
    df = df.rename(columns=COLUMNAS_CLIENTE_B, errors="raise")

    df["cliente"] = "Cliente B"
    return df[ORDEN_FINAL]


# ---------------------------------------------------------------------------
# Bloque 5: unificacion
# ---------------------------------------------------------------------------

def unificar(df_a, df_b):
    """Apila los dos clientes y deja la fecha como fecha de verdad."""
    df = pd.concat([df_a, df_b], ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df
