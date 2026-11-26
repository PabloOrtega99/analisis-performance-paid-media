# Decisiones de método

Las decisiones que cambian el resultado, con el error que evita cada una. Están aquí y no en un
comentario del código porque son reutilizables: valen para cualquier análisis de medios, no solo
para este.

El hilo que las une: **ninguno de estos errores da un fallo.** Todos devuelven una tabla que se
puede llevar a una reunión. Por eso hay que buscarlos a propósito.

---

## 1. Un ratio agregado no es la media de los ratios

**El error.** Calcular el ROAS de un periodo como `AVG(roas_diario)`.

**Por qué falla.** Da el mismo peso a un día de 20 € que a uno de 4.000 €. Y los días de muy poca
inversión son justo los que tienen el ROAS más disparatado, porque reciben compras atribuidas a
clics de días anteriores con casi nada de gasto en el denominador.

**Cuánto.** Un 10 % de desvío de media en estos datos. En el mes de una pausa larga, un 105 %: el
promedio dice 22,5 y el ROAS real es 11,0.

**La regla.** Sumar el numerador, sumar el denominador, dividir al final. Y para no tener que
acordarse: las métricas derivadas se definen **una sola vez**, en una vista
(`sql/vista_metricas.sql`), y el análisis consulta la vista.

---

## 2. Un cuartil de inversión puede ser un mes disfrazado

**El error.** Medir saturación partiendo los días de un periodo largo en cuartiles de inversión.

**Por qué falla.** Cuando el presupuesto se fija una vez al mes y dentro del mes apenas se mueve,
ordenar los días por inversión **es ordenar los meses**. Y como el presupuesto sube en los meses de
más demanda, el cuartil de más inversión está hecho de los meses de mejor ROAS. Lo que se mide es la
temporada, y la conclusión sale del revés: *cuanto más invierte, mejor rinde.*

Es causalidad inversa. No es que invertir más suba el ROAS: es que cuando el ROAS va a ser alto se
invierte más.

**Cómo se detecta.** Cruzar el cuartil con el mes (`pd.crosstab`, o `COUNT(DISTINCT mes)` en SQL).
Si cada cuartil contiene dos o tres meses nada más, el cuartil no es un nivel de inversión.

**La regla.** La saturación se mide **dentro de cada mes**, comparando días del mismo mes entre sí.
Dentro de un mes la temporada es la misma a los dos lados de la comparación, así que ya no puede
explicar la diferencia.

---

## 3. Un grupo de comparación necesita un umbral mínimo

**El error.** Comparar la mitad alta del mes con la baja sin mirar cuánto se diferencian.

**Por qué falla.** Si la mitad alta invierte un 6 % más que la baja, la diferencia de ROAS entre las
dos es ruido. La prueba devuelve un número igual, y ese número se lee como si significara algo.

**La regla.** Solo cuentan los meses en los que la mitad alta invierte **al menos un 20 % más**. Lo
que queda fuera no es un dato que falte: es una pregunta que esos meses no pueden responder.

**El efecto secundario, que es un hallazgo en sí mismo.** El umbral deja al Cliente A con 3 meses
medibles por área y al B con más de veinte. La diferencia no es de los datos, es de cómo se gestiona
cada cuenta: una mueve el presupuesto al doble de un día a otro y la otra no lo mueve. **Cuánto se
puede medir en una cuenta depende de cómo se gestione**, y eso se dice junto al resultado.

---

## 4. "No se detecta" no es lo mismo que "no existe"

**El error.** Escribir *el Cliente A no satura* cuando lo medido es *no se detecta saturación en el
Cliente A*.

**Por qué importa.** Con 3 meses medibles por área, la prueba tiene poca potencia: podría no ver una
caída moderada aunque existiera. Es ausencia de evidencia, no evidencia de ausencia. Y nada de lo
medido vale fuera del rango de inversión observado: estos datos no dicen qué pasaría al doblar el
presupuesto.

**La regla.** La fuerza de la evidencia se escribe al lado del hallazgo, no en un anexo. Un
resultado débil presentado como fuerte es peor que no tener resultado, porque alguien decide con él.

---

## 5. Antes de leer un cambio, separarlo en sus factores

**El error.** Celebrar que el ROAS se ha multiplicado por tres.

**Por qué falla.** El ROAS es un producto de dos cosas:

```
ROAS = (compras / inversión) × valor medio por compra
```

Si mejora la cuenta, lo normal es que se mueva algo el valor medio por compra: otro mix de producto,
menos descuento, más unidades por pedido. Si lo que cambia es **cómo se cuentan** las compras, salta
el número de compras y el valor medio se queda clavado.

**La prueba que lo cierra.** Mirar si pasa a la vez en mercados independientes. Ninguna acción
comercial ocurre el mismo día en cinco países con el mismo salto.

**La regla.** Una ruptura de serie se **fecha y se acota**; la causa se confirma preguntando a quien
gestiona la cuenta. Y hasta entonces: ningún periodo de análisis cruza esa fecha, porque mezclaría
dos formas de contar sin que nada falle.

---

## 6. El ROAS medio y el ROAS marginal responden preguntas distintas

**El error.** Recomendar más presupuesto para el área de mejor ROAS medio.

**Por qué falla.** "Qué área rinde mejor" y "dónde pongo el euro siguiente" no son la misma pregunta.
El ROAS marginal —lo que devuelven los euros *de más* de los días altos del mes— puede ordenar las
áreas al revés que el medio. En estos datos lo hace.

**La regla.** Para repartir presupuesto manda el marginal. Con dos salvedades que se dicen en voz
alta: un marginal alto **no significa rentable** sin el margen de producto, y el marginal solo vale
dentro del rango de inversión observado.

---

## 7. Un dato raro se documenta, no se borra

**El error.** Limpiar las filas que no encajan.

**Por qué falla.** Las filas con inversión 0 e ingresos no son un fallo de carga: son compras
atribuidas a clics anteriores, y son lo que explica el borde de cada pausa. Borrarlas destruye esa
información. Dejarlas dentro de un cálculo de cuartiles infla el ROAS del tramo bajo.

**La regla.** Se conservan en la base de datos y se excluyen **en los cálculos donde distorsionan**,
con el filtro escrito en la consulta y no en una celda de notebook. Y antes de decidir nada se mide
**cuánto pesan sobre los ingresos**: "hay 131 filas raras" no dice nada hasta saber si son el 0,4 % o
el 30 % del negocio.

**El corolario.** Un hueco en el calendario **no se rellena con 0**. Un 0 significa "se invirtió
0 €"; un hueco significa "no sabemos". Solo se rellena una pausa confirmada, y para confirmarla hay
que comprobar que es un bloque seguido, que los demás mercados estaban activos y que la inversión
bajaba antes de empezar.

---

## 8. Comprobar lo que podría tumbar el hallazgo

El filtro que separa los días válidos deja dentro los del borde de las pausas: dos euros de inversión
y un ROAS de tres cifras. Esos días caen en la mitad baja del mes y **exagerarían la caída**, que es
precisamente el hallazgo.

El notebook repite la prueba sin ellos. Las medianas se mueven uno o dos puntos y el número de meses
con caída es el mismo: el hallazgo no dependía de ellos.

**La regla.** Antes de dar un resultado por bueno, identificar qué lo haría falso y comprobarlo. Son
diez minutos, y son la diferencia entre un resultado y un resultado en el que se puede confiar.
