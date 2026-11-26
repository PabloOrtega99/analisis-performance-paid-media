-- Pregunta: ¿como se mueven inversion y ROAS mes a mes, y como va cada mes
-- contra el mismo mes del ano anterior?
--
-- Dos decisiones:
--
-- 1. Inversion MEDIA POR DIA ACTIVO, no inversion total del mes. Los meses
--    tienen distinto numero de dias y, cuando hay pausas, muy distinto numero
--    de dias activos. Comparar totales mensuales mezcla "se invirtio mas al
--    dia" con "se invirtio mas dias".
--
-- 2. La comparativa interanual se hace con LAG particionado por cliente y por
--    numero de mes, ordenando por el mes completo. Asi la fila de 2026-03
--    tiene al lado la de 2025-03 y no la de 2026-02. Agrupar solo por el mes
--    sin el ano es el error que mezcla anos distintos en la misma fila:
--    SQLite no se queja y el resultado parece correcto.
--
-- En SQLite no existe EXTRACT(MONTH FROM fecha): se usa strftime.

WITH mensual AS (
    SELECT cliente,
           strftime('%Y-%m', fecha)  AS mes,
           COUNT(DISTINCT fecha)     AS dias_activos,
           SUM(inversion_eur)        AS inversion,
           SUM(valor_compras)        AS ingresos
    FROM v_metricas_diarias
    GROUP BY cliente, strftime('%Y-%m', fecha)
)

SELECT cliente,
       mes,
       dias_activos,
       ROUND(inversion / dias_activos, 2)              AS inversion_dia,
       ROUND(ingresos / NULLIF(inversion, 0), 2)       AS roas,
       ROUND(LAG(ingresos / NULLIF(inversion, 0))
                 OVER (PARTITION BY cliente, substr(mes, 6, 2)
                       ORDER BY mes), 2)               AS roas_ano_anterior,
       ROUND((ingresos / NULLIF(inversion, 0))
             / NULLIF(LAG(ingresos / NULLIF(inversion, 0))
                          OVER (PARTITION BY cliente, substr(mes, 6, 2)
                                ORDER BY mes), 0) * 100 - 100, 1)
                                                       AS var_interanual_pct
FROM mensual
ORDER BY cliente, mes;
