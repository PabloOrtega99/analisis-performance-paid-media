"""Genera las dos exportaciones sinteticas de las que parte el proyecto.

Por que este archivo existe
---------------------------
El analisis original se hizo sobre datos de dos clientes reales de Meta Ads y
esos datos no se pueden publicar. Lo que si se puede publicar es el problema:
dos exportaciones con formatos distintos, con las anomalias que obligan a
tomar decisiones de analisis, y un generador que las reconstruye.

Los datos que salen de aqui son inventados. Clientes, mercados y fechas no
corresponden a ninguna cuenta real. Lo que si esta calibrado es la *estructura*,
porque es lo que el analisis tiene que detectar:

  Cliente A  presupuesto que se fija mes a mes, con muy poca variacion dentro
             del mes, y un ROAS que sigue a la temporada. No tiene rendimientos
             decrecientes en el rango observado. Los dias de mas inversion caen
             en los meses de mas demanda, asi que un analisis por cuartiles
             sobre todo el periodo concluye lo contrario de lo que pasa.

  Cliente B  presupuesto que se mueve mucho de un dia a otro y una curva de
             respuesta con rendimientos decrecientes de verdad
             (compras proporcionales a inversion^beta, con beta < 1).

  Cliente B  una ruptura de medicion: un dia, el numero de compras atribuidas
             salta en todos los mercados a la vez mientras el valor medio por
             compra se queda plano. Tres mercados se quedan en un nivel nuevo
             y dos vuelven al suyo tras una semana baja.

  Cliente B  pausas de cuenta: bloques de dias en los que la inversion cae a
             cero y aun entran ingresos residuales, y despues la fila
             desaparece. Son dias que hay que excluir de cualquier calculo de
             saturacion, y los que explican el borde de cada pausa.

  Cliente B  composicion que cambia: un area que arranca a mitad del historico
             y otra con un hueco de varios meses.

Uso
---
    python -m src.generar_datos
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "data" / "raw"

SEMILLA = 20260101

# ---------------------------------------------------------------------------
# Cliente A
# ---------------------------------------------------------------------------

A_INICIO, A_FIN = "2024-01-01", "2026-06-30"
A_AREAS = {"MUJER": 0.60, "HOMBRE": 0.20, "INFANTIL": 0.20}

# Inversion diaria base de la cuenta, por mes del ano. El presupuesto se decide
# una vez al mes, asi que dentro del mes apenas se mueve: es lo que hace que
# los cuartiles de inversion de un periodo largo ordenen meses y no inversion.
A_NIVEL_MES = {1: 900, 2: 1000, 3: 1500, 4: 1300, 5: 1250, 6: 1100,
               7: 1000, 8: 700, 9: 1400, 10: 1600, 11: 2600, 12: 2300}

# ROAS base por mes. Sube en los meses de campana. Que el presupuesto y la
# demanda suban a la vez es lo normal en una cuenta gestionada, y es
# exactamente lo que confunde a un analisis por cuartiles.
A_ROAS_MES = {1: 7.0, 2: 7.6, 3: 9.5, 4: 9.0, 5: 8.8, 6: 8.2,
              7: 7.8, 8: 6.6, 9: 9.2, 10: 10.5, 11: 14.0, 12: 12.5}

A_ROAS_AREA = {"MUJER": 1.00, "HOMBRE": 0.80, "INFANTIL": 1.15}
A_VALOR_COMPRA = {"MUJER": 62.0, "HOMBRE": 55.0, "INFANTIL": 42.0}

# ---------------------------------------------------------------------------
# Cliente B
# ---------------------------------------------------------------------------

B_INICIO, B_FIN = "2024-04-01", "2026-06-30"
B_MERCADOS = {"ES": 0.34, "FR": 0.26, "DE": 0.18, "IT": 0.13, "NL": 0.09}
B_AREAS = ["WOMEN", "MEN", "KIDS"]

# beta de la curva de respuesta: compras ~ inversion ** beta.
# Por debajo de 1 hay rendimientos decrecientes, y el ROAS cae con la
# inversion segun inversion ** (beta - 1).
B_BETA = {"WOMEN": 0.62, "MEN": 0.44, "KIDS": 0.54}

# Ruido diario sobre las compras esperadas. Sin el, la saturacion saldria en
# todos los meses sin excepcion, y unos datos sin excepciones no se parecen a
# unos datos reales: la prueba tiene que poder fallar en algun mes.
B_RUIDO_DIARIO = 0.45

B_VALOR_COMPRA = {"WOMEN": 58.0, "MEN": 51.0, "KIDS": 39.0}
B_NIVEL_BASE = 2200.0

# Escala de la conversion. Calibrada para que el ROAS de la cuenta quede en un
# rango creible incluso en los mercados y meses en los que se cuentan compras
# de menos: una cuenta que lleva dos anos activa no esta perdiendo dinero.
B_CONVERSION = 3.0

# Ruptura de medicion.
B_RUPTURA = pd.Timestamp("2026-02-11")
B_RUPTURA_SALTO = {"ES": 3.0, "DE": 3.6, "NL": 2.6}          # nivel nuevo
B_RUPTURA_VUELVE = ["FR", "IT"]                               # vuelven al suyo
B_SEMANA_BAJA = (pd.Timestamp("2026-02-03"), pd.Timestamp("2026-02-10"))

# Infraconteo previo en los tres mercados que se quedan en un nivel nuevo:
# antes de la ruptura cuentan de menos, y el 11/02 se corrige.
B_INFRACONTEO_DESDE = pd.Timestamp("2025-07-01")

# Pausas de la cuenta en ES: (inicio, fin) inclusive.
B_PAUSAS_ES = [("2025-03-04", "2025-03-14"),
               ("2025-08-06", "2025-08-12"),
               ("2025-11-27", "2025-12-02")]
B_PAUSA_CUENTA = ("2024-12-09", "2024-12-15")   # esta afecta a todos

# Composicion que cambia.
B_MEN_DESDE = pd.Timestamp("2025-09-15")
B_KIDS_HUECO = (pd.Timestamp("2025-06-01"), pd.Timestamp("2025-08-31"))


def _dias_de_pausa(tramos):
    dias = set()
    for inicio, fin in tramos:
        dias.update(pd.date_range(inicio, fin))
    return dias


def _dias_de_borde(tramos, margen=2):
    """Dias pegados a una pausa, por delante y por detras.

    Una cuenta no se apaga de golpe: baja a unos pocos euros antes de parar y
    arranca igual de despacio. Esos dias tienen una inversion minima y aun
    reciben compras atribuidas a clics anteriores, asi que su ROAS se dispara
    a cifras de tres digitos. No son un error y no se borran, pero son
    exactamente los que revientan cualquier media de ratios y los que inflan
    el cuartil de menos inversion.
    """
    pausa = _dias_de_pausa(tramos)
    borde = set()
    for inicio, fin in tramos:
        inicio, fin = pd.Timestamp(inicio), pd.Timestamp(fin)
        borde.update(pd.date_range(inicio - pd.Timedelta(days=margen),
                                   inicio - pd.Timedelta(days=1)))
        borde.update(pd.date_range(fin + pd.Timedelta(days=1),
                                   fin + pd.Timedelta(days=margen)))
    return borde - pausa


def _metricas_de_trafico(rng, inversion, ctr_enlace, cpc):
    """Deriva impresiones, alcance y clics de la inversion.

    Se calculan desde el CPC y el CTR para que CPM, CTR y CPC salgan en rangos
    creibles y coherentes entre si, en lugar de inventar cada columna aparte.
    """
    clics_enlace = np.maximum(1, np.round(inversion / cpc))
    impresiones = np.maximum(clics_enlace, np.round(clics_enlace / ctr_enlace))
    alcance = np.round(impresiones / rng.uniform(1.4, 2.6, size=len(inversion)))
    # Los clics (todos) incluyen reacciones, comentarios y clics fuera del
    # enlace, asi que siempre son mas que los clics en el enlace.
    clics_todos = np.round(clics_enlace * rng.uniform(1.5, 2.4, size=len(inversion)))
    visitas = np.round(clics_enlace * rng.uniform(0.62, 0.88, size=len(inversion)))
    return impresiones, alcance, clics_enlace, clics_todos, visitas


def generar_cliente_a(rng):
    """Exportacion del Cliente A: un mercado, area en columna propia."""
    fechas = pd.date_range(A_INICIO, A_FIN)
    filas = []

    # Algunos meses llevan una revision de presupuesto a mitad de mes. Son los
    # unicos en los que la inversion se mueve lo suficiente dentro del mes
    # para poder medir saturacion: en el resto, la mitad alta invierte un 6 %
    # mas que la baja y la prueba no tiene con que comparar.
    meses = sorted({(f.year, f.month) for f in fechas})
    revision = {m: (rng.choice([1.38, 1.30, 0.74]) if rng.random() < 0.22 else 1.0)
                for m in meses}

    for area, peso in A_AREAS.items():
        nivel = np.array([A_NIVEL_MES[f.month] for f in fechas]) * peso
        nivel = nivel * np.array([
            revision[(f.year, f.month)] if f.day >= 16 else 1.0 for f in fechas])
        # Fuera de esas revisiones, la variacion dentro del mes es de +/-6 %.
        inversion = nivel * rng.uniform(0.94, 1.06, size=len(fechas))

        roas = (np.array([A_ROAS_MES[f.month] for f in fechas])
                * A_ROAS_AREA[area]
                * rng.normal(1.0, 0.11, size=len(fechas)))
        # Deriva suave a lo largo del historico, para que no sea un calendario
        # perfectamente ciclico.
        roas *= np.linspace(0.92, 1.12, len(fechas))
        roas = np.clip(roas, 1.5, None)

        valor = inversion * roas
        compras = np.maximum(1, np.round(valor / A_VALOR_COMPRA[area]))
        valor = compras * A_VALOR_COMPRA[area] * rng.uniform(0.9, 1.1, size=len(fechas))

        imp, alc, cle, clt, vis = _metricas_de_trafico(
            rng, inversion,
            ctr_enlace=rng.uniform(0.004, 0.009, size=len(fechas)),
            cpc=rng.uniform(0.30, 0.55, size=len(fechas)),
        )

        filas.append(pd.DataFrame({
            "Inicio del informe": fechas,
            "Nombre de la cuenta": "Cuenta A",
            "Categoria de campana": area,
            "Importe gastado (EUR)": inversion.round(2),
            "Impresiones": imp.astype("int64"),
            "Alcance": alc.astype("int64"),
            "Clics en el enlace": cle.astype("int64"),
            "Clics (todos)": clt.astype("int64"),
            "Compras": compras.astype("int64"),
            "Valor de conversion de compras": valor.round(2),
            "Visitas a la pagina de destino": vis.astype("int64"),
        }))

    df = pd.concat(filas, ignore_index=True)
    df = df.sort_values(["Inicio del informe", "Categoria de campana"], ignore_index=True)

    # Dos columnas que no se usan, una de ellas con el espacio duro (\xa0) que
    # Meta mete entre el numero y el signo de porcentaje en sus exportaciones.
    # Es un detalle real: hace que el nombre de la columna no coincida con lo
    # que se ve en pantalla y que un drop() por nombre falle con KeyError.
    df["Reproducciones de video de 25\xa0%"] = 0
    df["Clasificacion de calidad"] = "-"
    return df


def generar_cliente_b(rng):
    """Exportacion del Cliente B: cinco mercados, area dentro del nombre."""
    fechas = pd.date_range(B_INICIO, B_FIN)
    pausas_es = _dias_de_pausa(B_PAUSAS_ES)
    pausa_cuenta = _dias_de_pausa([B_PAUSA_CUENTA])
    bordes_es = _dias_de_borde(B_PAUSAS_ES)
    bordes_cuenta = _dias_de_borde([B_PAUSA_CUENTA])
    filas = []

    for mercado, peso in B_MERCADOS.items():
        for area in B_AREAS:
            for fecha in fechas:
                if area == "MEN" and fecha < B_MEN_DESDE:
                    continue
                if area == "KIDS" and B_KIDS_HUECO[0] <= fecha <= B_KIDS_HUECO[1]:
                    continue

                en_pausa = fecha in pausa_cuenta or (
                    mercado == "ES" and fecha in pausas_es)
                en_borde = not en_pausa and (
                    fecha in bordes_cuenta
                    or (mercado == "ES" and fecha in bordes_es))

                nivel = B_NIVEL_BASE * peso * (0.34 if area == "KIDS" else
                                               0.30 if area == "MEN" else 1.0)
                # Escalones de gestion de la cuenta.
                if fecha >= pd.Timestamp("2025-04-01"):
                    nivel *= 1.9
                if fecha >= pd.Timestamp("2025-10-01"):
                    nivel *= 0.75

                if en_pausa:
                    # Los primeros dias de la pausa la inversion ya es cero
                    # pero siguen entrando compras atribuidas a clics
                    # anteriores. Despues la fila deja de existir.
                    dias_dentro = sum(
                        1 for d in pd.date_range(fecha - pd.Timedelta(days=4), fecha)
                        if d in pausas_es or d in pausa_cuenta)
                    if dias_dentro > 3:
                        continue
                    inversion = 0.0
                    compras = max(0, int(rng.poisson(3)))
                    valor = compras * B_VALOR_COMPRA[area] * rng.uniform(0.9, 1.1)
                    imp = alc = cle = clt = vis = 0
                elif en_borde:
                    # Apagado o arranque: unos pocos euros y compras que
                    # vienen de antes. El ROAS de estos dias es de tres
                    # cifras y no significa nada.
                    inversion = float(rng.uniform(0.8, 8.0))
                    compras = max(1, int(rng.poisson(3)))
                    valor = compras * B_VALOR_COMPRA[area] * rng.uniform(0.9, 1.1)
                    imp = int(inversion * rng.uniform(900, 1600))
                    alc = int(imp / rng.uniform(1.4, 2.6))
                    cle = max(1, int(inversion / rng.uniform(0.22, 0.48)))
                    clt = int(cle * rng.uniform(1.5, 2.4))
                    vis = int(cle * rng.uniform(0.62, 0.88))
                else:
                    # Mucha variacion dentro del mes: es lo que permite medir
                    # saturacion en este cliente y no en el A.
                    inversion = float(nivel * rng.lognormal(0.0, 0.48))
                    inversion = max(inversion, 5.0)

                    # Curva de respuesta con rendimientos decrecientes.
                    escala = nivel if nivel > 0 else 1.0
                    base = B_CONVERSION * (1.0 if area == "KIDS"
                                           else 1.18 if area == "WOMEN" else 0.9)
                    compras_esperadas = (base * (escala / B_VALOR_COMPRA[area])
                                         * (inversion / escala) ** B_BETA[area]
                                         * (3.4 if fecha.month in (11, 12) else 2.6)
                                         * rng.lognormal(0.0, B_RUIDO_DIARIO))
                    compras = max(1, int(rng.poisson(max(compras_esperadas, 0.6))))
                    valor = compras * B_VALOR_COMPRA[area] * rng.uniform(0.88, 1.12)

                    imp, alc, cle, clt, vis = _metricas_de_trafico(
                        rng, np.array([inversion]),
                        ctr_enlace=rng.uniform(0.005, 0.012, size=1),
                        cpc=rng.uniform(0.22, 0.48, size=1),
                    )
                    imp, alc, cle, clt, vis = (int(imp[0]), int(alc[0]), int(cle[0]),
                                               int(clt[0]), int(vis[0]))

                # Ruptura de medicion. Solo toca el numero de compras; el valor
                # medio por compra se queda igual, que es la firma del cambio
                # de medicion frente a una mejora comercial.
                factor = 1.0
                if mercado in B_RUPTURA_SALTO:
                    if B_INFRACONTEO_DESDE <= fecha < B_RUPTURA:
                        factor = 1.0 / B_RUPTURA_SALTO[mercado]
                elif mercado in B_RUPTURA_VUELVE:
                    if B_SEMANA_BAJA[0] <= fecha <= B_SEMANA_BAJA[1]:
                        factor = 0.42

                if factor != 1.0:
                    compras = max(0, int(round(compras * factor)))
                    valor = compras * B_VALOR_COMPRA[area] * rng.uniform(0.88, 1.12)

                # La exportacion del Cliente B llega a nivel de conjunto de
                # anuncios, asi que un mismo dia, mercado y area tiene varias
                # filas. Es lo que obliga a agregar antes de calcular
                # cualquier ratio, y la razon de que exista la vista.
                etapas = list(rng.choice(["PROSP", "RMKT", "PERFORMANCE-MAX"],
                                         size=rng.integers(1, 4), replace=False))
                reparto = rng.dirichlet(np.full(len(etapas), 2.5))
                # Las compras son enteras: se reparten con una multinomial
                # para que la suma de las filas sea exactamente la del dia.
                compras_split = rng.multinomial(compras, reparto)

                for etapa, parte, compras_fila in zip(etapas, reparto, compras_split):
                    # El nombre del conjunto de anuncios lleva el area dentro,
                    # en una nomenclatura inventada para este repositorio. Es
                    # la que obliga a extraer el area de una cadena de texto.
                    conjunto = f"{mercado}_{etapa}_{area}_BAU_{fecha.year}"
                    filas.append({
                        "Dia": fecha,
                        "Nombre de la cuenta": f"[{mercado}]",
                        "Nombre del conjunto de anuncios": conjunto,
                        "Importe gastado (EUR)": round(inversion * parte, 2),
                        "Impresiones": int(imp * parte),
                        "Alcance": int(alc * parte),
                        "Clics en el enlace": int(cle * parte),
                        "Clics (todos)": int(clt * parte),
                        "Compras": int(compras_fila),
                        "Valor de conversion de compras": round(
                            compras_fila * B_VALOR_COMPRA[area]
                            * rng.uniform(0.88, 1.12), 2),
                        "Visitas a la pagina de destino": int(vis * parte),
                    })

    df = pd.DataFrame(filas).sort_values(
        ["Dia", "Nombre de la cuenta", "Nombre del conjunto de anuncios"],
        ignore_index=True)

    # Filas sin area reconocible: campanas de marca que el analisis por area
    # tiene que descartar, no adivinar.
    marca = df.sample(frac=0.03, random_state=7).copy()
    marca["Nombre del conjunto de anuncios"] = (
        marca["Nombre de la cuenta"].str.strip("[]") + "_BRAND_AWARENESS_BAU")
    df = pd.concat([df, marca], ignore_index=True)

    # Un punado de filas con compras atribuidas y cero impresiones, con
    # inversion por encima de cero. En los datos reales salian de una
    # diferencia de configuracion entre las dos exportaciones de origen. No es
    # un error que haya que arreglar: es una rareza cuyo peso sobre los
    # ingresos hay que medir antes de decidir si se conserva.
    candidatas = df.index[(df["Compras"] > 0) & (df["Importe gastado (EUR)"] > 0)]
    sin_impresiones = pd.Index(
        rng.choice(candidatas, size=int(len(candidatas) * 0.004), replace=False))
    df.loc[sin_impresiones, ["Impresiones", "Alcance", "Clics en el enlace",
                             "Clics (todos)", "Visitas a la pagina de destino"]] = 0

    return df.sort_values(["Dia", "Nombre de la cuenta"], ignore_index=True)


def main():
    rng = np.random.default_rng(SEMILLA)
    DESTINO.mkdir(parents=True, exist_ok=True)

    df_a = generar_cliente_a(rng)
    ruta_a = DESTINO / "cliente_a_export.xlsx"
    df_a.to_excel(ruta_a, sheet_name="BBDD", index=False)
    print(f"Cliente A: {len(df_a):,} filas -> {ruta_a.relative_to(RAIZ)}")

    df_b = generar_cliente_b(rng)
    ruta_b = DESTINO / "cliente_b_export.csv"
    df_b.to_csv(ruta_b, index=False)
    print(f"Cliente B: {len(df_b):,} filas -> {ruta_b.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
