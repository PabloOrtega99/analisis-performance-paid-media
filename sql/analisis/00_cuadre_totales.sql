-- Pregunta: la vista solo agrega la tabla, asi que puede cambiar el numero de
-- filas pero no los totales. ¿Cuadran?
--
-- Es el primer control que se ejecuta despues de cada pipeline. Un GROUP BY
-- mal escrito en la vista duplicaria filas sin dar ningun error: las tablas
-- seguirian saliendo y las cifras estarian infladas. Cuadrar los totales
-- contra un numero que ya se conoce es lo unico que lo detecta.
--
-- Las filas SI deben diferir: la tabla llega a nivel de conjunto de anuncios
-- y la vista agrega a dia, cliente, pais y area. Inversion, ingresos y
-- compras tienen que coincidir al centimo.

SELECT 'campanas (tabla)'   AS origen,
       COUNT(*)             AS filas,
       ROUND(SUM(inversion_eur), 2) AS inversion,
       ROUND(SUM(valor_compras), 2) AS ingresos,
       SUM(compras)         AS compras
FROM campanas

UNION ALL

SELECT 'v_metricas_diarias',
       COUNT(*),
       ROUND(SUM(inversion_eur), 2),
       ROUND(SUM(valor_compras), 2),
       SUM(compras)
FROM v_metricas_diarias;
