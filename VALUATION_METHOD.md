# VALUATION_METHOD.md

**Proyecto:** Sistema personal de análisis Value Investing
**Versión:** 1.0
**Estado:** Propuesta inicial para aprobación
**Fecha:** 18/09/2026

---

## 1. Objetivo

El sistema tiene como objetivo estimar:

1. La calidad económica de una empresa.
2. Su situación financiera.
3. Su capacidad de generar beneficios y flujo de caja sostenible.
4. Su valor intrínseco mediante varios métodos.
5. La rentabilidad anualizada esperada a medio/largo plazo.
6. El precio máximo de compra compatible con una rentabilidad objetivo.
7. Los principales riesgos que pueden invalidar la valoración.

El sistema no pretende predecir el precio de una acción a corto plazo.

---

# 2. Principio fundamental

La valoración se realizará separando:

**Datos → Cálculos → Supuestos → Valoración → Riesgos → Interpretación.**

Los datos y cálculos financieros serán deterministas y reproducibles.

La IA podrá interpretar información y plantear hipótesis, pero no podrá modificar silenciosamente los datos ni las fórmulas financieras.

---

# 3. Horizonte temporal

El horizonte principal será:

**5 años.**

Se utilizarán horizontes adicionales cuando sean necesarios:

* 3 años para empresas de crecimiento rápido.
* 5 años como estándar.
* 7-10 años para negocios muy estables cuando sea apropiado.

El sistema deberá indicar siempre el horizonte utilizado.

---

# 4. Beneficio por acción

Definición:

**EPS = beneficio neto atribuible / acciones diluidas**

Cuando sea posible se utilizará el número de acciones diluidas.

Se distinguirá entre:

* EPS histórico.
* EPS TTM.
* EPS forward.
* EPS normalizado.
* EPS estimado.

Nunca se mezclarán sin indicarlo.

---

# 5. Crecimiento del EPS

Se calcularán:

* crecimiento interanual;
* CAGR 3 años;
* CAGR 5 años;
* crecimiento estimado futuro.

Para un periodo de n años:

**CAGR = (EPS_final / EPS_inicial)^(1/n) - 1**

Cuando existan valores negativos o distorsiones extraordinarias, no se calculará automáticamente un CAGR convencional.

---

# 6. EPS normalizado

Para empresas cíclicas se calculará un EPS normalizado.

Podrán utilizarse:

* media histórica;
* mediana histórica;
* promedio ponderado;
* margen normalizado;
* beneficio correspondiente a condiciones económicas normales.

El método utilizado deberá quedar registrado.

El sistema deberá detectar posibles situaciones de:

**peak earnings**

cuando el beneficio actual esté significativamente por encima de su nivel histórico normalizado.

---

# 7. P/E

Definición:

**P/E = precio / EPS**

Se calcularán por separado:

* P/E TTM.
* P/E forward.
* P/E normalizado.
* P/E terminal utilizado en la valoración.

Nunca se considerará automáticamente que un P/E bajo implica infravaloración.

---

# 8. Earnings Yield

Definición:

**Earnings Yield = EPS / precio = 1 / P/E**

Es una medida de rentabilidad implícita de los beneficios actuales.

No se interpretará como rentabilidad total esperada.

---

# 9. Flujo de caja libre

Definición base:

**FCF = Cash Flow from Operations - Capex**

Cuando existan particularidades contables relevantes, se documentará el tratamiento utilizado.

Se calcularán:

* FCF total.
* FCF/share.
* FCF Yield.
* FCF normalizado.

---

# 10. FCF Yield

Definición:

**FCF Yield = FCF / Enterprise Value**

Cuando resulte más apropiado para el tipo de empresa se podrá utilizar:

**FCF Yield sobre equity = FCF disponible para accionistas / capitalización**

El sistema deberá indicar qué definición utiliza.

---

# 11. EV/EBITDA

Definición:

**EV = capitalización + deuda neta + intereses minoritarios + otros ajustes relevantes**

**EV/EBITDA = EV / EBITDA**

Será especialmente relevante para:

* industriales;
* infraestructuras;
* telecomunicaciones;
* empresas con estructuras de capital heterogéneas.

No se utilizará como métrica principal cuando EBITDA no represente adecuadamente la economía del negocio.

---

# 12. Rentabilidad sobre capital

Se calcularán:

**ROE = beneficio neto / equity**

y, cuando los datos permitan una estimación consistente:

**ROIC = NOPAT / capital invertido**

Se analizará tanto el valor actual como su evolución histórica.

---

# 13. Balance

Se analizarán como mínimo:

* deuda bruta;
* caja;
* deuda neta;
* deuda neta/EBITDA;
* cobertura de intereses;
* evolución de deuda;
* vencimientos cuando estén disponibles.

El nivel de deuda modificará el riesgo y los múltiplos apropiados.

---

# 14. Dilución

El sistema controlará:

* acciones en circulación;
* crecimiento/reducción del número de acciones;
* ampliaciones de capital;
* stock options;
* convertibles;
* recompras.

Se calculará:

**Dilución anual = crecimiento de acciones en circulación**

cuando sea posible.

La previsión de EPS deberá utilizar acciones futuras razonables cuando existan evidencias de dilución.

---

# 15. Dividendos

Se calcularán:

* dividend yield;
* payout;
* crecimiento del dividendo;
* cobertura mediante FCF;
* sostenibilidad.

No se asumirá que un dividendo alto es necesariamente atractivo.

---

# 16. Shareholder Yield

Cuando existan datos suficientes:

**Shareholder Yield = Dividend Yield + Buyback Yield**

Las emisiones netas de acciones deberán considerarse para evitar interpretar como retorno para accionistas una recompra que quede compensada por nueva emisión.

---

# 17. Rentabilidad esperada a 5 años

La fórmula principal será:

**R = [(EPS futuro / EPS actual) × (PE terminal / PE actual) × factor dividendos]^(1/5) - 1**

El componente de dividendos se calculará mediante un modelo explícito y no mediante una simple suma si la reinversión o el crecimiento del dividendo hacen que dicha aproximación sea inadecuada.

Para análisis rápidos podrá utilizarse:

**Rentabilidad aproximada ≈ crecimiento EPS + dividend yield + efecto anualizado del múltiplo**

pero se identificará expresamente como aproximación.

---

# 18. Recompras

Cuando el crecimiento utilizado sea crecimiento de EPS por acción:

**no se añadirá automáticamente el buyback yield a la rentabilidad esperada.**

La razón es que las recompras ya pueden estar incorporadas en el crecimiento del EPS/share.

Se evitará así el doble conteo.

---

# 19. Valoración por P/E

Valor:

**Valor = EPS normalizado × P/E razonable**

El P/E razonable se establecerá a partir de:

* crecimiento;
* calidad;
* ROIC;
* estabilidad;
* balance;
* ciclicidad;
* historial de múltiplos;
* características del sector.

Nunca se asignará automáticamente el mismo múltiplo a todas las empresas.

---

# 20. Valoración por FCF

Valor simplificado:

**Valor = FCF normalizado / FCF Yield requerido**

Para empresas con crecimiento elevado se utilizarán modelos de crecimiento explícitos o DCF.

---

# 21. DCF

El DCF utilizará:

* periodo explícito;
* crecimiento de ingresos;
* evolución de márgenes;
* impuestos;
* capex;
* capital circulante;
* FCF;
* WACC;
* crecimiento terminal.

Se producirán tres escenarios:

**Bear / Base / Bull**

Los supuestos deberán quedar almacenados.

No se permitirá modificar simultáneamente demasiadas variables sin dejar constancia del cambio.

---

# 22. Valoración de bancos y aseguradoras

Para entidades financieras se priorizarán:

* P/B;
* P/TBV;
* ROE;
* ROTCE;
* crecimiento del valor contable;
* calidad del capital;
* coste del riesgo;
* payout;
* rentabilidad sobre capital.

El P/E podrá utilizarse como métrica complementaria.

No se aplicará el EV/EBITDA convencional a bancos como método principal.

---

# 23. Empresas cíclicas

En empresas cíclicas se dará prioridad a:

* beneficio normalizado;
* margen normalizado;
* FCF a lo largo del ciclo;
* deuda neta;
* posición dentro del ciclo;
* múltiplo sobre beneficios normalizados.

Se evitará valorar una empresa exclusivamente con el beneficio del año actual.

---

# 24. Empresas de crecimiento

En empresas de crecimiento se prestará especial atención a:

* crecimiento orgánico;
* crecimiento por adquisiciones;
* margen incremental;
* ROIC;
* FCF;
* dilución;
* tamaño de mercado;
* reinversión;
* duración del crecimiento.

Un P/E elevado no será considerado automáticamente negativo si existe capacidad demostrable de crecimiento y creación de valor.

---

# 25. Escenarios

Cada empresa tendrá como mínimo:

### Bear

Supuestos conservadores.

### Base

Hipótesis consideradas más representativas.

### Bull

Hipótesis favorables pero plausibles.

Cada escenario deberá especificar:

* ingresos;
* margen;
* EPS;
* FCF;
* crecimiento;
* múltiplo terminal.

---

# 26. Valor intrínseco

El sistema mostrará:

**Valor Bear**

**Valor Base**

**Valor Bull**

No se generará inicialmente un único "valor verdadero".

Cuando varios métodos sean aplicables se mostrará también el rango obtenido.

---

# 27. Precio máximo de compra

Para una rentabilidad objetivo R:

**Precio máximo = valor futuro descontado a la rentabilidad requerida**

Para una valoración basada en EPS:

**Precio máximo = EPS_actual × (1+g)^n × PE_terminal / (1+R)^n**

La fórmula se adaptará cuando se utilice DCF, FCF u otro método.

Se calcularán como mínimo:

* precio para 8%;
* precio para 10%;
* precio para 12%;
* precio para 15%.

---

# 28. Margen de seguridad

Se calculará:

**Margen de seguridad = 1 - precio actual / valor estimado**

Se mostrarán separadamente los márgenes frente a:

* Bear;
* Base;
* Bull.

No se utilizará un margen de seguridad idéntico para todas las empresas.

---

# 29. Quality Score

Puntuación interna de 0 a 100.

Componentes iniciales:

* ROIC/ROE;
* balance;
* FCF;
* márgenes;
* crecimiento;
* estabilidad;
* ventaja competitiva.

Los pesos serán configurables y quedarán documentados.

La puntuación nunca sustituirá al análisis individual.

---

# 30. Value Score

Puntuación interna de 0 a 100 basada en:

* valoración relativa;
* valoración absoluta;
* FCF Yield;
* P/E normalizado;
* descuento a valor intrínseco;
* rentabilidad esperada;
* margen de seguridad.

---

# 31. Risk Score

Puntuación interna de 0 a 100.

Evaluará:

* deuda;
* volatilidad de beneficios;
* ciclicidad;
* dilución;
* concentración;
* regulación;
* riesgo de financiación;
* dependencia de materias primas;
* riesgos específicos del negocio.

La interpretación exacta de la escala deberá quedar documentada antes de utilizarla para decisiones automáticas.

---

# 32. Value Trap Detector

Se generarán señales cuando existan combinaciones como:

* P/E bajo + beneficios decrecientes;
* P/E bajo + FCF negativo;
* dividend yield elevado + cobertura insuficiente;
* EV/EBITDA bajo + EBITDA en máximo cíclico;
* deuda elevada + caída de beneficios;
* ROIC persistentemente bajo;
* deterioro estructural de márgenes;
* crecimiento del EPS provocado principalmente por reducción de acciones;
* deterioro simultáneo de varias métricas fundamentales.

El sistema no declarará automáticamente que existe una "value trap"; generará una señal para revisión.

---

# 33. Hurdle Rates

Se utilizarán como referencias:

**8%**

**10%**

**12%**

**15%**

Estas tasas no constituyen recomendaciones de inversión.

Son simplemente diferentes requisitos de rentabilidad utilizados para calcular precios de compra y comparar escenarios.

---

# 34. Calidad de los datos

Cada dato deberá conservar:

* fuente;
* fecha;
* periodo fiscal;
* fecha de publicación cuando esté disponible;
* unidad;
* moneda;
* timestamp de descarga.

Se distinguirá entre:

**dato reportado**

**dato estimado**

**dato calculado**

**supuesto**

---

# 35. Datos históricos y look-ahead bias

Para backtesting solamente se utilizará información que hubiera estado disponible en la fecha evaluada.

Ejemplo:

Para simular una decisión tomada el 01/06/2022 no se podrán utilizar:

* resultados publicados posteriormente;
* revisiones posteriores de estimaciones;
* datos financieros futuros;
* composición futura del índice.

Este principio será obligatorio.

---

# 36. Versionado del modelo

Cada valoración almacenará:

* versión del modelo;
* fecha;
* datos utilizados;
* supuestos;
* resultado.

Ejemplo:

**Model v1.0.0**

Esto permitirá comparar cambios metodológicos.

---

# 37. Revisión de una inversión

Una inversión será revisada cuando:

* cambie significativamente la valoración;
* cambie el crecimiento esperado;
* cambie el FCF;
* cambie la deuda;
* exista dilución relevante;
* cambie la tesis;
* exista una noticia material;
* se publiquen resultados.

No se generará una alerta únicamente porque el precio haya cambiado.

---

# 38. Tesis de inversión

Cada posición deberá registrar:

* motivo de compra;
* hipótesis de crecimiento;
* hipótesis de margen;
* valoración;
* catalizadores;
* riesgos;
* condiciones que invalidarían la tesis.

El sistema deberá comprobar periódicamente esas condiciones.

---

# 39. Separación entre valoración y decisión

El sistema proporcionará:

**datos + análisis + escenarios + rentabilidad esperada + riesgos**

La decisión final de inversión permanecerá separada del cálculo.

---

# 40. Resultado estándar

Toda empresa deberá poder producir una ficha comparable:

**Precio actual**

**EPS**

**EPS normalizado**

**FCF/share**

**P/E**

**P/E normalizado**

**EV/EBITDA**

**FCF Yield**

**ROIC**

**ROE**

**Deuda neta/EBITDA**

**Quality Score**

**Value Score**

**Risk Score**

**Value Trap Signals**

**Valor Bear**

**Valor Base**

**Valor Bull**

**Precio máximo 8%**

**Precio máximo 10%**

**Precio máximo 12%**

**Precio máximo 15%**

**Rentabilidad esperada 5 años**

**Estado de la tesis**

---

# 41. Regla de prudencia

Cuando los datos sean insuficientes, inconsistentes o poco fiables:

**el sistema deberá decir "datos insuficientes"**

en lugar de fabricar una valoración.

La ausencia de información no será interpretada como una oportunidad.

---

# 42. Regla de trazabilidad

Cualquier cifra importante mostrada al usuario deberá poder remontarse hasta:

**fuente → dato original → transformación → fórmula → resultado.**

Esta será una característica obligatoria del sistema.
