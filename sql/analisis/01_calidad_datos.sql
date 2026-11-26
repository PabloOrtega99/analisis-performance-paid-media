-- Pregunta: ¿que hay en estos datos que un analisis tiene que saber antes de
-- empezar a sacar conclusiones?
--
-- Tres controles, cada uno con el peso que tiene sobre los ingresos, porque
-- "hay 120 filas raras" no dice nada hasta que se sabe si son el 0,1 % o el
-- 30 % del negocio. Ese peso es el que decide si se arreglan, se excluyen o
-- se dejan documentadas.
--
-- COUNT(DISTINCT fecha) y no COUNT(*): la tabla tiene varias filas por dia,
-- asi que COUNT(*) contaria conjuntos de anuncios y no dias. Es un error que
-- no da fallo y devuelve una tabla perfectamente creible.

WITH totales AS (
    SELECT cliente, SUM(valor_compras) AS ingresos
    FROM campanas
    GROUP BY cliente
)

-- Filas con compras atribuidas y cero impresiones. No es imposible: puede
-- venir de una diferencia de configuracion entre exportaciones. Se conservan,
-- pero hay que saber cuanto pesan antes de decidirlo.
SELECT 'compras sin impresiones' AS control,
       c.cliente                 AS ambito,
       COUNT(*)                  AS filas,
       ROUND(SUM(c.valor_compras) * 100.0 / NULLIF(t.ingresos, 0), 2) AS pct_ingresos
FROM campanas c
JOIN totales t ON t.cliente = c.cliente
WHERE c.compras > 0 AND c.impresiones = 0
GROUP BY c.cliente

UNION ALL

-- Dias con inversion 0 que aun generan ingresos. Es atribucion residual de
-- clics anteriores, y es un estado valido, no un error. Pero inflan el ROAS
-- del tramo de poca inversion, asi que cualquier analisis de cuartiles o de
-- saturacion tiene que filtrarlos.
SELECT 'inversion 0 con ingresos',
       c.cliente,
       COUNT(*),
       ROUND(SUM(c.valor_compras) * 100.0 / NULLIF(t.ingresos, 0), 2)
FROM campanas c
JOIN totales t ON t.cliente = c.cliente
WHERE c.inversion_eur = 0 AND c.valor_compras > 0
GROUP BY c.cliente

UNION ALL

-- Dias del calendario sin ninguna fila. Un hueco NO se rellena con 0: un 0
-- significa "se invirtio 0 EUR" y un hueco significa "no sabemos". Solo se
-- rellena una pausa confirmada.
SELECT 'dias de calendario sin datos',
       cliente || ' / ' || pais,
       CAST(julianday(MAX(fecha)) - julianday(MIN(fecha)) + 1 AS INTEGER)
           - COUNT(DISTINCT fecha),
       NULL
FROM v_metricas_diarias
GROUP BY cliente, pais

ORDER BY control, ambito;
