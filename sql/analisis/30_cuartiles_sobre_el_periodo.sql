-- Pregunta: ¿hay rendimientos decrecientes? Primer intento, el que sale mal.
--
-- Esta es la forma habitual de medir saturacion: partir los dias en cuartiles
-- de inversion sobre todo el periodo y mirar como cae el ROAS del cuartil 3 al
-- 4. La consulta esta bien escrita y el resultado es creible. Y para uno de los
-- dos clientes es falso.
--
-- La pista esta en la ultima columna: meses_distintos. Si un cuartil de
-- inversion contiene dias de dos o tres meses nada mas, ese cuartil no es un
-- nivel de inversion, es una epoca del ano. Cuando el presupuesto se fija mes
-- a mes, los cuartiles de un periodo largo ordenan meses, y lo que se acaba
-- midiendo es la temporada.
--
-- El contraste se ve comparando los dos clientes en esta misma tabla, y la
-- correccion esta en 31_saturacion_dentro_del_mes.sql.

WITH dias AS (
    SELECT cliente,
           area,
           fecha,
           strftime('%Y-%m', fecha) AS mes,
           inversion_eur,
           valor_compras
    FROM v_metricas_diarias
    WHERE pais = 'ES'
      AND strftime('%Y', fecha) = '2025'
      -- Los dias de inversion 0 llevan ingresos residuales de clics
      -- anteriores: dejarlos dentro infla el ROAS del cuartil bajo y
      -- exagera cualquier caida posterior.
      AND inversion_eur > 0
),

cuartiles AS (
    SELECT *,
           NTILE(4) OVER (PARTITION BY cliente, area ORDER BY inversion_eur)
               AS cuartil
    FROM dias
)

SELECT cliente,
       area,
       cuartil,
       COUNT(*)                                                 AS dias,
       -- Media por dia, no suma: cada cuartil tiene distinto numero de dias.
       ROUND(AVG(inversion_eur), 2)                             AS inversion_dia,
       ROUND(SUM(valor_compras) / NULLIF(SUM(inversion_eur), 0), 2) AS roas,
       COUNT(DISTINCT mes)                                      AS meses_distintos
FROM cuartiles
GROUP BY cliente, area, cuartil
ORDER BY cliente, area, cuartil;
