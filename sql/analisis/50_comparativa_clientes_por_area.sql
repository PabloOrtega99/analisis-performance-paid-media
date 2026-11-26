-- Pregunta: puestos uno al lado del otro, ¿que diferencia a los dos clientes?
--
-- Esta consulta es la mas facil de hacer mal, porque juntar dos cuentas en una
-- tabla es trivial y que la comparacion signifique algo no lo es. Cuatro
-- restricciones, y cada una elimina una conclusion falsa:
--
-- 1. Un solo mercado (ES). El Cliente A solo tiene uno; comparar su ES contra
--    el total del Cliente B seria comparar un pais contra cinco.
--
-- 2. Por area, nunca en total. Los dos clientes reparten la inversion entre
--    areas de forma muy distinta, asi que una diferencia en el total puede ser
--    solo el reparto. Comparar dentro de cada area quita ese efecto.
--
-- 3. Ventana comun y anterior a la ruptura del Cliente B (11/02/2026). Si la
--    ventana cruza la ruptura, el ROAS del Cliente B incluye dos regimenes de
--    medicion distintos y la comparacion no mide nada.
--
-- 4. Se informan los dias y las fechas de cada grupo. Cuando un area arranca a
--    mitad del historico en un cliente, su ventana real no es la de la
--    consulta, y hay que verlo en la tabla y no descubrirlo despues.
--
-- Lo que esta tabla NO permite concluir: que un cliente sea "mejor" que el
-- otro. Son sectores, catalogos y margenes distintos, y el margen de producto
-- no esta en estos datos. Lo comparable es el comportamiento: como responde
-- cada cuenta cuando se le sube la inversion, que es lo que mide
-- 31_saturacion_dentro_del_mes.sql.

WITH ventana AS (
    SELECT *
    FROM v_metricas_diarias
    WHERE pais = 'ES'
      AND fecha BETWEEN '2024-04-01' AND '2026-01-31'
      AND inversion_eur > 0
)

SELECT area,
       cliente,
       COUNT(DISTINCT fecha)                                     AS dias,
       MIN(fecha)                                                AS desde,
       MAX(fecha)                                                AS hasta,
       ROUND(AVG(inversion_eur), 2)                              AS inversion_dia,
       -- Cuanto mueve cada cuenta el presupuesto de un dia a otro, medido
       -- como el recorrido de la inversion diaria sobre su media. Es lo que
       -- decide si en esa cuenta se puede medir saturacion: sin variacion no
       -- hay nada que comparar.
       ROUND((MAX(inversion_eur) - MIN(inversion_eur))
             / NULLIF(AVG(inversion_eur), 0), 2)                  AS recorrido_inversion,
       ROUND(SUM(valor_compras) / NULLIF(SUM(inversion_eur), 0), 2) AS roas,
       ROUND(SUM(valor_compras) / NULLIF(SUM(compras), 0), 2)     AS valor_medio_compra
FROM ventana
GROUP BY area, cliente
ORDER BY area, cliente;
