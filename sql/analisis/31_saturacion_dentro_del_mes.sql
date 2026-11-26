-- Pregunta: ¿hay rendimientos decrecientes? Segundo intento, el que vale.
--
-- La correccion tiene dos partes. La primera es particionar tambien por mes,
-- para que los grupos se calculen DENTRO de cada mes y comparen dias del
-- mismo mes entre si: asi el calendario no puede disfrazarse de inversion,
-- porque a los dos lados de la comparacion hay el mismo mes.
--
-- La segunda es partir cada mes en dos mitades, NTILE(2), y no en cuatro. Un
-- mes tiene unos 30 dias: en cuartiles salen grupos de siete u ocho dias, y
-- entre el tercero y el cuarto apenas hay diferencia de inversion, asi que
-- casi ningun mes llega al umbral y la prueba se queda sin datos. Con dos
-- mitades hay unos quince dias en cada lado y la diferencia de inversion
-- entre ellas si es la que de verdad distingue a los dos clientes.
--
-- Las otras tres decisiones:
--
-- * WHERE inversion_eur > 0, antes del NTILE. Los dias de inversion cero con
--   ingresos residuales caerian en el cuartil bajo y le inflarian el ROAS, lo
--   que exagera la caida. El filtro va escrito en la consulta y no en una
--   celda de notebook, que es la ventaja real de tener el analisis en SQL.
--
-- * Se comparan las dos mitades del mes entre si, que es comparar el nivel
--   habitual de inversion con el nivel alto del mismo mes. No se compara el
--   dia mas flojo con el mas fuerte, que seria comparar dos situaciones que
--   no se parecen en nada.
--
-- * Solo cuentan los meses en los que la mitad alta invierte al menos un 20 %
--   mas que la baja. Si las dos invierten casi lo mismo, la comparacion no
--   mide saturacion: mide ruido. Ese umbral es el que deja a un cliente con
--   muchos meses medibles y al otro con muy pocos, y esa diferencia es en si
--   misma un hallazgo sobre como se gestiona cada cuenta.

WITH dias AS (
    SELECT cliente,
           area,
           strftime('%Y-%m', fecha) AS mes,
           inversion_eur,
           valor_compras
    FROM v_metricas_diarias
    WHERE pais = 'ES'
      AND inversion_eur > 0
      -- Febrero de 2026 del Cliente B contiene la ruptura de medicion que
      -- documenta 40_ruptura_de_serie.sql. Ese mes tiene dos formas de contar
      -- compras dentro, asi que comparar sus dos mitades no mide saturacion.
      AND NOT (cliente = 'Cliente B' AND strftime('%Y-%m', fecha) = '2026-02')
),

mitades AS (
    SELECT *,
           NTILE(2) OVER (PARTITION BY cliente, area, mes ORDER BY inversion_eur)
               AS mitad          -- 1 = mitad de menos inversion, 2 = la de mas
    FROM dias
),

por_mitad AS (
    SELECT cliente, area, mes, mitad,
           AVG(inversion_eur)                                   AS inversion_dia,
           SUM(valor_compras) / NULLIF(SUM(inversion_eur), 0)    AS roas
    FROM mitades
    GROUP BY cliente, area, mes, mitad
),

comparacion AS (
    SELECT baja.cliente,
           baja.area,
           baja.mes,
           alta.inversion_dia / NULLIF(baja.inversion_dia, 0)    AS ratio_inversion,
           (alta.roas / NULLIF(baja.roas, 0) - 1) * 100          AS var_roas_pct
    FROM por_mitad baja
    JOIN por_mitad alta
      ON  alta.cliente = baja.cliente
      AND alta.area    = baja.area
      AND alta.mes     = baja.mes
    WHERE baja.mitad = 1
      AND alta.mitad = 2
)

-- SQLite no tiene MEDIAN, asi que aqui se informa la media. El notebook
-- calcula la mediana sobre los mismos meses: cuenta la misma historia, pero
-- las dos cifras no son intercambiables y por eso la columna dice cual es.
SELECT cliente,
       area,
       COUNT(*)                                                 AS meses_medibles,
       SUM(CASE WHEN var_roas_pct < 0 THEN 1 ELSE 0 END)        AS meses_con_caida,
       ROUND(AVG(var_roas_pct), 1)                              AS var_roas_media_pct,
       ROUND(AVG(ratio_inversion), 2)                           AS ratio_inversion_medio
FROM comparacion
-- El umbral del 20 %: por debajo, el cuartil 4 no invierte lo bastante mas
-- que el 3 para que la comparacion signifique algo.
WHERE ratio_inversion >= 1.20
GROUP BY cliente, area
ORDER BY cliente, area;
