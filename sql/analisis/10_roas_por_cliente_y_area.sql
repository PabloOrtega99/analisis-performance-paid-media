-- Pregunta: ¿cuanto pesa y cuanto rinde cada area en cada cliente?
--
-- Es la tabla de la que parte todo lo demas, y tiene dos detalles que cambian
-- el resultado:
--
-- 1. El ROAS se calcula sumando ingresos, sumando inversion y dividiendo al
--    final. Hacer AVG(roas) sobre los ROAS diarios de la vista da el mismo
--    peso a un dia de 20 EUR que a uno de 4.000, y en estos datos ese error
--    multiplica la cifra por mas de siete.
--
-- 2. El porcentaje de inversion se calcula con SUM(SUM(...)) OVER (PARTITION
--    BY cliente). La suma de dentro es la del grupo del GROUP BY; la de fuera,
--    la del cliente entero. Mezclar una columna de fila con un SUM de grupo
--    da porcentajes diminutos que parecen un problema de formato y no lo son.

SELECT cliente,
       area,
       COUNT(DISTINCT fecha)                AS dias,
       ROUND(SUM(inversion_eur), 2)         AS inversion,
       ROUND(SUM(inversion_eur) * 100.0
             / SUM(SUM(inversion_eur)) OVER (PARTITION BY cliente), 1)
                                            AS pct_inversion_cliente,
       ROUND(SUM(valor_compras), 2)         AS ingresos,
       ROUND(SUM(valor_compras) / NULLIF(SUM(inversion_eur), 0), 2) AS roas,
       ROUND(SUM(inversion_eur) / NULLIF(SUM(compras), 0), 2)       AS cpa,
       ROUND(SUM(valor_compras) / NULLIF(SUM(compras), 0), 2)       AS valor_medio_compra
FROM v_metricas_diarias
GROUP BY cliente, area
ORDER BY cliente, inversion DESC;
