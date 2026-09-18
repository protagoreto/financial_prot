# DATA_SOURCES.md

**Proyecto:** Sistema personal de análisis Value Investing
**Versión:** 1.0
**Estado:** Propuesta inicial para aprobación
**Fecha:** 18/09/2026

---

# 1. Objetivo

Definir las fuentes de datos que alimentarán el sistema de análisis Value Investing.

El principio fundamental será:

> Ningún dato crítico deberá entrar en el sistema sin conocer su procedencia, fecha y naturaleza.

---

# 2. Jerarquía de fuentes

Las fuentes tendrán cuatro niveles:

### Nivel 1 — Fuente primaria

Documentos publicados por la propia empresa o regulador.

Ejemplos:

* CNMV
* SEC
* informes anuales
* resultados trimestrales
* presentaciones de resultados
* comunicaciones corporativas

### Nivel 2 — Proveedor financiero estructurado

APIs especializadas que normalizan los datos.

Principal candidato inicial:

**EOD Historical Data (EODHD)**

### Nivel 3 — Fuente secundaria

Ejemplos:

* Yahoo Finance / yfinance
* otras APIs financieras

Se utilizarán para:

* prototipado;
* comprobación;
* datos auxiliares;
* redundancia.

### Nivel 4 — IA / información web

La IA podrá utilizar información pública para análisis cualitativo.

Nunca será la fuente primaria de una cifra financiera crítica.

---

# 3. EOD Historical Data

## Función

Será inicialmente nuestro **proveedor estructurado principal**.

EODHD ofrece datos de mercado, fundamentales, dividendos, splits, acciones, estados financieros y estimaciones, y cubre mercados estadounidenses y no estadounidenses. Su documentación indica cobertura de más de 60 bolsas y datos fundamentales históricos de distinta profundidad según el mercado y tamaño de la empresa.

## Datos que utilizaremos

* precios diarios;
* volumen;
* dividendos;
* splits;
* acciones;
* capitalización;
* income statement;
* balance sheet;
* cash flow;
* EBITDA;
* EBIT;
* beneficio neto;
* deuda;
* caja;
* FCF;
* earnings;
* estimaciones disponibles;
* calendario de resultados;
* información de empresas;
* índices y componentes cuando resulte aplicable.

Su API de fundamentales incluye estados financieros anuales y trimestrales y proporciona `filing_date` en los registros financieros, lo que resulta especialmente útil para conservar la fecha en que la información llegó al mercado.

## Ventajas

* cobertura internacional;
* API relativamente sencilla;
* datos estructurados;
* históricos;
* fundamentales;
* dividendos;
* acciones;
* calendarios;
* posibilidad de ampliar posteriormente.

## Coste inicial

El proveedor ofrece actualmente:

* plan gratuito limitado;
* EOD mundial desde aproximadamente 19,99 USD/mes;
* Fundamentals desde aproximadamente 59,99 USD/mes;
* paquete completo alrededor de 99,99 USD/mes en sus planes personales publicados.

Las tarifas pueden cambiar y se comprobarán antes de contratar.

## Decisión

**Proveedor principal inicial recomendado.**

No significa que todos sus datos se acepten sin validación.

---

# 4. CNMV

## Función

La CNMV será nuestra **fuente primaria para empresas españolas**.

La plataforma de la CNMV permite acceder a:

* informes financieros anuales;
* información financiera intermedia;
* gobierno corporativo;
* participaciones;
* autocartera;
* posiciones cortas;
* comunicaciones relevantes;
* otra información regulada y corporativa.

## Utilización

Especialmente para:

* IBEX;
* BME;
* empresas españolas pequeñas;
* empresas con datos incompletos en proveedores secundarios;
* validación de resultados;
* ampliaciones de capital;
* recompras;
* emisiones;
* operaciones corporativas.

## Prioridad

**Fuente primaria.**

Cuando exista discrepancia entre una fuente agregada y el documento oficial, el documento oficial tendrá prioridad, previa normalización.

---

# 5. SEC / EDGAR

## Función

Será nuestra **fuente primaria para empresas estadounidenses**.

La SEC proporciona APIs públicas para los filings y datos XBRL de los estados financieros. Las APIs incluyen `companyfacts` y datos de presentaciones de compañías y no requieren API key.

## Utilización

Especialmente para:

* 10-K;
* 10-Q;
* 8-K;
* datos XBRL;
* shares outstanding;
* ingresos;
* beneficios;
* activos;
* pasivos;
* cash flow;
* deuda.

## Prioridad

**Fuente primaria.**

---

# 6. yfinance

## Función

`yfinance` será nuestra herramienta auxiliar y de prototipado.

Su API proporciona:

* precios;
* estados financieros;
* balance;
* cash flow;
* dividendos;
* splits;
* earnings;
* estimaciones;
* revisiones de EPS;
* estimaciones de ingresos;
* noticias;
* filings SEC;
* acciones.

## Ventajas

* gratuita;
* sencilla;
* excelente para desarrollo inicial;
* integración directa con Python.

## Limitaciones

No será considerada nuestra fuente primaria para datos críticos.

En particular, no asumiremos que los datos actuales de estimaciones sean suficientes para reconstruir correctamente las expectativas históricas.

## Decisión

Utilizarla:

**Sí**

como:

* fallback;
* prototipo;
* comprobación;
* fuente secundaria.

No utilizarla como única fuente del sistema definitivo.

---

# 7. Alpha Vantage

Alpha Vantage proporciona:

* estados financieros;
* información fundamental;
* earnings;
* estimaciones de EPS e ingresos;
* historial de earnings;
* revisiones;
* listados de empresas activas y deslistadas.

Su endpoint de earnings estimates incluye estimaciones anuales y trimestrales y revisiones.

## Decisión

No será nuestro proveedor principal inicial.

Se conservará como posible:

* fuente secundaria;
* fuente de contraste;
* alternativa futura.

---

# 8. Datos de precios

Para el MVP:

**EODHD**

será la fuente principal.

Se almacenará:

```text
date
open
high
low
close
adjusted_close
volume
currency
source
retrieved_at
```

EODHD ofrece históricos diarios, semanales y mensuales y más de 30 años para muchos instrumentos.

---

# 9. Dividendos

Fuente principal:

**EODHD**

Fuente de validación:

**empresa / CNMV / SEC**

Se almacenará:

```text
ex_date
payment_date
amount
currency
type
source
```

No se utilizará simplemente el dividend yield actual para construir históricos.

---

# 10. Splits y operaciones corporativas

Se almacenarán:

* splits;
* reverse splits;
* ampliaciones;
* conversiones;
* recompras;
* emisiones;
* convertibles.

La información corporativa deberá tener fecha efectiva.

Esto es imprescindible para reconstruir correctamente:

**EPS/share**

y

**rentabilidad histórica**.

---

# 11. Estados financieros

Para cada periodo almacenaremos:

```text
company_id
period
period_type
filing_date
source
currency
revenue
ebitda
ebit
net_income
cash
debt
equity
cfo
capex
fcf
shares
```

La fecha importante para backtesting será:

**filing_date**

y no únicamente el final del periodo fiscal.

---

# 12. Dos fechas diferentes

El sistema diferenciará siempre:

### Period End

Fecha a la que corresponde el dato.

Ejemplo:

**31/12/2025**

### Filing / Publication Date

Fecha en la que el mercado pudo conocer el dato.

Ejemplo:

**25/02/2026**

Para backtesting utilizaremos la segunda.

---

# 13. Estimaciones de analistas

Este es uno de los puntos más importantes del proyecto.

Necesitamos distinguir:

### Estimación actual

> Lo que los analistas esperan hoy.

de:

### Estimación histórica

> Lo que los analistas esperaban en una fecha pasada.

El segundo dato es imprescindible para backtesting sin look-ahead bias.

---

# 14. Regla para estimaciones

No consideraremos suficiente disponer de:

```text
EPS 2026E = 5,20 €
```

Necesitamos conocer:

```text
fecha de observación
periodo estimado
estimación
número de analistas
mínimo
máximo
```

y, cuando sea posible:

```text
estimación anterior
fecha de revisión
dirección de la revisión
```

---

# 15. Historial de revisiones

El sistema almacenará:

```text
company
observation_date
fiscal_period
eps_estimate
revenue_estimate
ebitda_estimate
analyst_count
low
high
source
```

Ejemplo:

```text
01/01/2026
EPS 2026 = 5,20 €

01/04/2026
EPS 2026 = 5,45 €

01/07/2026
EPS 2026 = 5,10 €
```

Así podremos detectar:

**revisión positiva**

o

**revisión negativa**.

---

# 16. Limitación actual

No asumiremos que una API de estimaciones actual proporciona automáticamente un archivo completo y fiable de consenso histórico.

Antes de implementar el backtest se hará una investigación específica de proveedores que ofrezcan:

**point-in-time analyst estimates.**

Si el coste de ese dato profesional resulta demasiado elevado, el sistema tendrá dos modos:

### Modo operativo

Utiliza las mejores estimaciones actuales disponibles.

### Modo backtest

Utiliza únicamente datasets históricos point-in-time disponibles.

Nunca mezclaremos ambos y luego llamaremos al resultado "backtest limpio".

---

# 17. Datos históricos de empresas desaparecidas

Para evitar survivorship bias, el universo histórico deberá poder contener:

* empresas actualmente cotizadas;
* empresas deslistadas;
* empresas adquiridas;
* empresas quebradas;
* cambios de ticker.

Cuando la fuente lo permita, se conservará:

```text
active
delisted
delisting_date
reason
```

Alpha Vantage, por ejemplo, dispone de un endpoint de listing status que permite consultar valores activ
