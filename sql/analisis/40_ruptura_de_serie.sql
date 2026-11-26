-- Pregunta: el ROAS del Cliente B se multiplica a principios de 2026.
-- ¿Es que la cuenta mejoro, o es que cambio la forma de contar?
--
-- La consulta separa el ROAS en sus dos factores y los mira por mercado y por
-- mes:
--
--     ROAS = (compras / inversion) x valor medio por compra
--
-- Si mejora la cuenta, lo normal es que se mueva algo del valor medio por
-- compra: mas producto por pedido, menos descuento, otro mix. Si lo que
-- cambia es la medicion, salta el numero de compras contadas y el valor medio
-- se queda clavado.
--
-- Y hay una segunda prueba, la que decide: si pasa el mismo dia en todos los
-- mercados a la vez, no es comercial. Ninguna accion de negocio ocurre
-- simultaneamente en cinco paises con el mismo salto.
--
-- La consulta no afirma la causa. Fecha el cambio, lo acota a unos mercados y
-- descarta la explicacion comercial. La causa se confirma preguntando a quien
-- gestiona la cuenta, no con otra consulta.

SELECT pais,
       strftime('%Y-%m', fecha)                                  AS mes,
       COUNT(DISTINCT fecha)                                     AS dias,
       ROUND(SUM(inversion_eur) / COUNT(DISTINCT fecha), 2)      AS inversion_dia,
       -- Factor 1: cuantas compras se cuentan por cada 100 EUR.
       ROUND(SUM(compras) * 100.0 / NULLIF(SUM(inversion_eur), 0), 2)
                                                                 AS compras_por_100eur,
       -- Factor 2: cuanto vale cada compra.
       ROUND(SUM(valor_compras) / NULLIF(SUM(compras), 0), 2)     AS valor_medio_compra,
       ROUND(SUM(valor_compras) / NULLIF(SUM(inversion_eur), 0), 2) AS roas,
       CASE WHEN fecha >= '2026-02-11' THEN 'despues' ELSE 'antes' END
                                                                 AS tramo
FROM v_metricas_diarias
WHERE cliente = 'Cliente B'
  AND fecha BETWEEN '2025-10-01' AND '2026-05-31'
GROUP BY pais, strftime('%Y-%m', fecha),
         CASE WHEN fecha >= '2026-02-11' THEN 'despues' ELSE 'antes' END
ORDER BY pais, mes;
