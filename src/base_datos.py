"""Carga el dataset unificado en SQLite y ejecuta los scripts .sql."""

import sqlite3


def guardar_en_sqlite(df, ruta_db, nombre_tabla):
    """Escribe el DataFrame como tabla, reemplazando la anterior.

    if_exists="replace" es deliberado: la base de datos es un producto del
    pipeline, no un almacen. Se puede borrar y regenerar entera, y asi nunca
    hay dudas sobre si lo que hay dentro corresponde al codigo actual.
    """
    conexion = sqlite3.connect(ruta_db)
    try:
        df.to_sql(nombre_tabla, conexion, if_exists="replace", index=False)
    finally:
        conexion.close()


def ejecutar_sql(ruta_db, ruta_sql):
    """Ejecuta un archivo .sql completo (puede tener varias sentencias)."""
    sql = ruta_sql.read_text(encoding="utf-8")
    conexion = sqlite3.connect(ruta_db)
    try:
        conexion.executescript(sql)
        conexion.commit()
    finally:
        conexion.close()


def consultar(ruta_db, sql):
    """Devuelve el resultado de una consulta como DataFrame."""
    import pandas as pd

    conexion = sqlite3.connect(ruta_db)
    try:
        return pd.read_sql_query(sql, conexion)
    finally:
        conexion.close()
