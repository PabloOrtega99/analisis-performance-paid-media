"""Pipeline completo: de las exportaciones a la base de datos consultable.

    python -m src.pipeline

Hace cuatro cosas, en este orden:

  1. Genera las exportaciones sinteticas si no estan (ver src/generar_datos.py).
  2. Lee las dos, las lleva a un esquema comun y las unifica.
  3. Guarda el resultado en CSV y en una tabla de SQLite.
  4. Crea la vista v_metricas_diarias, que es la unica puerta de entrada que
     el analisis usa para leer metricas derivadas.

Lo importante no es que funcione, es que sea repetible: borrar
data/processed/ y volver a ejecutarlo tiene que dar exactamente lo mismo.
"""

from pathlib import Path

import pandas as pd

from src import generar_datos
from src.base_datos import consultar, ejecutar_sql, guardar_en_sqlite
from src.limpieza import preparar_cliente_a, preparar_cliente_b, unificar

RAIZ = Path(__file__).resolve().parent.parent

RUTA_A = RAIZ / "data" / "raw" / "cliente_a_export.xlsx"
RUTA_B = RAIZ / "data" / "raw" / "cliente_b_export.csv"
RUTA_CSV = RAIZ / "data" / "processed" / "campanas_unificadas.csv"
RUTA_DB = RAIZ / "data" / "processed" / "campanas.db"
RUTA_VISTA = RAIZ / "sql" / "vista_metricas.sql"

TABLA = "campanas"


def _resumen(df, etiqueta):
    print(f"  {etiqueta:<12} {len(df):>7,} filas   "
          f"{df['fecha'].min():%Y-%m-%d} a {df['fecha'].max():%Y-%m-%d}   "
          f"areas: {', '.join(sorted(df['area'].unique()))}")


def main():
    print("Pipeline")
    print("-" * 72)

    # 1. Datos de partida -----------------------------------------------------
    if not RUTA_A.exists() or not RUTA_B.exists():
        print("No hay exportaciones en data/raw/. Generando las sinteticas:")
        generar_datos.main()
        print()

    # 2. Lectura y unificacion ------------------------------------------------
    df_a = preparar_cliente_a(RUTA_A)
    df_b_bruto = pd.read_csv(RUTA_B)
    df_b = preparar_cliente_b(RUTA_B)

    df_a["fecha"] = pd.to_datetime(df_a["fecha"])
    df_b["fecha"] = pd.to_datetime(df_b["fecha"])
    _resumen(df_a, "Cliente A")
    _resumen(df_b, "Cliente B")

    descartadas = len(df_b_bruto) - len(df_b)
    print(f"  {'descartadas':<12} {descartadas:>7,} filas del Cliente B sin area "
          f"reconocible (campanas de marca)")

    df = unificar(df_a, df_b)
    print(f"  {'unificado':<12} {len(df):>7,} filas")

    # 3. Salidas --------------------------------------------------------------
    RUTA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RUTA_CSV, index=False)
    guardar_en_sqlite(df, RUTA_DB, TABLA)

    # 4. Vista ----------------------------------------------------------------
    ejecutar_sql(RUTA_DB, RUTA_VISTA)
    filas_vista = consultar(RUTA_DB, "SELECT COUNT(*) AS n FROM v_metricas_diarias")
    print("-" * 72)
    print(f"  tabla {TABLA}: {len(df):,} filas")
    print(f"  vista v_metricas_diarias: {filas_vista.loc[0, 'n']:,} filas")

    # Cuadre: la vista agrega, asi que no puede cambiar los totales. Si este
    # control falla, el GROUP BY de la vista esta duplicando o perdiendo filas.
    control = consultar(RUTA_DB, """
        SELECT (SELECT ROUND(SUM(inversion_eur), 2) FROM campanas)            AS tabla,
               (SELECT ROUND(SUM(inversion_eur), 2) FROM v_metricas_diarias)  AS vista
    """)
    tabla_total, vista_total = control.loc[0, "tabla"], control.loc[0, "vista"]
    estado = "OK" if abs(tabla_total - vista_total) < 0.01 else "DESCUADRE"
    print(f"  cuadre de inversion tabla/vista: {tabla_total:,.2f} / "
          f"{vista_total:,.2f}  -> {estado}")

    print(f"\n  {RUTA_CSV.relative_to(RAIZ)}")
    print(f"  {RUTA_DB.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
