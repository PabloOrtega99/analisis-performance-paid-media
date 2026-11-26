-- Vista v_metricas_diarias
--
-- Una unica definicion de cada metrica derivada, para que ningun analisis
-- tenga que volver a calcularla. El analisis consulta la vista; la tabla
-- campanas solo se usa para comprobar que la vista no ha perdido nada.
--
-- La razon de que exista: todas las metricas de aqui son ratios, y un ratio
-- agregado NO es la media de los ratios de cada fila. Hay que sumar el
-- numerador, sumar el denominador y dividir al final. Calcular AVG(roas)
-- sobre ROAS diarios da un numero que parece razonable y no lo es, porque da
-- el mismo peso a un dia de 20 EUR que a uno de 4.000. Teniendo la vista, esa
-- decision se toma una sola vez y en un sitio.
--
-- NULLIF(x, 0) evita la division por cero: SQLite devolveria NULL en lugar de
-- fallar, pero sin NULLIF seria un NULL silencioso y no una ausencia
-- declarada. Los dias con inversion 0 existen de verdad (son el borde de cada
-- pausa de cuenta) y tienen que llegar al analisis como NULL, no como cero.

DROP VIEW IF EXISTS v_metricas_diarias;

CREATE VIEW v_metricas_diarias AS
SELECT
    DATE(fecha)                  AS fecha,
    cliente,
    pais,
    area,

    -- Magnitudes: se suman.
    SUM(inversion_eur)           AS inversion_eur,
    SUM(impresiones)             AS impresiones,
    SUM(alcance)                 AS alcance,
    SUM(clics_enlace)            AS clics_enlace,
    SUM(clics_todos)             AS clics_todos,
    SUM(compras)                 AS compras,
    SUM(valor_compras)           AS valor_compras,
    SUM(visitas_landing)         AS visitas_landing,

    -- Ratios: suma del numerador partido por suma del denominador.
    SUM(valor_compras)    / NULLIF(SUM(inversion_eur), 0)        AS roas,
    SUM(inversion_eur)    / NULLIF(SUM(compras), 0)              AS cpa,
    SUM(valor_compras)    / NULLIF(SUM(compras), 0)              AS valor_medio_compra,
    SUM(inversion_eur)    / NULLIF(SUM(clics_enlace), 0)         AS cpc_enlace,
    SUM(inversion_eur) * 1000.0 / NULLIF(SUM(impresiones), 0)    AS cpm,
    SUM(clics_enlace) * 100.0 / NULLIF(SUM(impresiones), 0)      AS ctr_enlace,
    SUM(compras) * 100.0  / NULLIF(SUM(clics_enlace), 0)         AS tasa_conversion,

    -- Compras por cada 100 EUR invertidos. Es la metrica que separa un cambio
    -- de medicion de un cambio comercial: si salta mientras el valor medio por
    -- compra se queda plano, lo que ha cambiado es cuantas compras se cuentan.
    SUM(compras) * 100.0  / NULLIF(SUM(inversion_eur), 0)        AS compras_por_100eur

FROM campanas
GROUP BY DATE(fecha), cliente, pais, area;
