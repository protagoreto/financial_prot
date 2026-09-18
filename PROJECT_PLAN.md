Sí. Antes de escribir una sola línea de código, conviene crear un **documento maestro del proyecto**. Será nuestro contrato de diseño: cualquier cambio posterior tendrá que quedar identificado como modificación del plan, para evitar que el proyecto vaya creciendo de forma descontrolada.

Te propongo este plan inicial.

# Plan maestro — Sistema Value Investing 1.0

**Objetivo:** construir un sistema automatizado que analice continuamente empresas, valore mis inversiones, controle mi cartera, detecte oportunidades y registre históricamente qué decía el modelo en cada momento.

---

## 1. Objetivo fundamental

El sistema deberá responder de forma automática:

1. **¿Qué empresas cumplen actualmente mis criterios?**
2. **¿Cuánto vale razonablemente cada empresa?**
3. **¿Qué rentabilidad anualizada puedo esperar a 5 años al precio actual?**
4. **¿A qué precio tendría sentido comprar para obtener 8%, 10%, 12% o 15% anual?**
5. **¿Qué riesgos pueden hacer que la valoración sea incorrecta?**
6. **¿Qué ha cambiado desde el último análisis?**
7. **¿Cómo están evolucionando mis inversiones reales?**
8. **¿Sigue siendo válida la tesis de cada inversión?**
9. **¿Qué habría dicho el modelo en el pasado y qué ocurrió posteriormente?**

El sistema **no será un sistema de predicción de precios**. Será un sistema de valoración y seguimiento de hipótesis.

---

# 2. Principio fundamental de diseño

Separaremos completamente:

### Datos

↓

### Cálculos

↓

### Valoración

↓

### Análisis cualitativo

↓

### Alertas

La IA **no podrá modificar silenciosamente los cálculos financieros**.

Por ejemplo:

```text
Precio = 50 €
EPS = 4 €
PER = 12,5x
```

Eso lo calcula Python.

La IA podrá decir:

> "El PER parece bajo porque el beneficio actual podría estar por encima de su nivel normal."

Pero no podrá cambiar el EPS porque "le parezca demasiado alto".

Esto será una regla central del proyecto.

---

# 3. Universo de inversión

La primera versión tendrá tres niveles.

### A. Universo automático

Inicialmente:

* IBEX 35
* principales índices europeos
* S&P 500
* Nasdaq
* empresas que podamos obtener mediante las fuentes de datos seleccionadas.

### B. Watchlist personal

Empresas que añadamos manualmente.

Por ejemplo:

```text
NEXTIL
ROVI
AMadeus
Repsol
Inditex
Santander
BBVA
...
```

### C. Cartera

Empresas que realmente poseas.

La cartera será independiente del radar.

Una empresa puede estar en el radar sin que la poseas.

---

# 4. Base de datos

Construiremos una base histórica.

Para cada empresa guardaremos:

### Precio

* precio diario
* máximo/mínimo
* volumen
* capitalización
* acciones en circulación

### Cuenta de resultados

* ingresos
* EBITDA
* EBIT
* beneficio neto
* EPS

### Balance

* deuda
* caja
* deuda neta
* patrimonio
* activos
* goodwill

### Cash flow

* CFO
* capex
* FCF
* FCF/share

### Accionistas

* dividendos
* recompras
* emisiones
* dilución

### Estimaciones

Y esto es **crítico**:

```text
Fecha de estimación
EPS estimado
Ingresos estimados
EBITDA estimado
FCF estimado
```

Conservaremos las estimaciones antiguas.

Así evitaremos **look-ahead bias** en el futuro backtest.

---

# 5. Métricas fundamentales

El motor calculará como mínimo:

### Valoración

* P/E
* P/E forward
* P/E normalizado
* EV/EBITDA
* EV/EBIT
* P/S
* P/B
* P/TBV
* FCF Yield
* Earnings Yield
* Dividend Yield
* Shareholder Yield

### Rentabilidad

* ROE
* ROIC
* ROA
* margen bruto
* margen EBITDA
* margen EBIT
* margen neto

### Crecimiento

* crecimiento ingresos
* crecimiento EBITDA
* crecimiento EBIT
* crecimiento EPS
* crecimiento FCF

En:

* 1 año
* 3 años
* 5 años

cuando los datos estén disponibles.

### Balance

* deuda neta
* Debt/EBITDA
* Interest Coverage
* Current Ratio
* evolución de deuda

---

# 6. Normalización de beneficios

Será uno de los módulos principales.

El sistema distinguirá:

**beneficio reportado**

de

**beneficio sostenible/normalizado**.

Para empresas cíclicas estudiaremos:

* media histórica
* mediana
* margen normalizado
* ciclo de beneficios
* ROIC normalizado
* FCF normalizado

Y marcaremos automáticamente situaciones como:

> Beneficio actual significativamente superior al promedio histórico.

Esto generará una alerta de posible **peak earnings**.

---

# 7. Valoración

Nunca dependeremos de un único método.

Cada empresa tendrá, cuando sea aplicable:

### Método 1

P/E normalizado

### Método 2

FCF Yield

### Método 3

EV/EBITDA

### Método 4

DCF

### Método 5

Dividend Discount Model

### Método 6

P/B o P/TBV

especialmente para bancos/aseguradoras.

### Método 7

SOTP

cuando sea necesario.

---

# 8. Valoración por escenarios

Como mínimo:

### Bear

### Base

### Bull

Cada escenario tendrá:

```text
Ingresos
Margen
EPS
FCF
Crecimiento
PER/EV-EBITDA terminal
```

Y producirá:

```text
Valor por acción
```

---

# 9. Rentabilidad esperada

Esta será una de las métricas centrales.

Usaremos:

**Rentabilidad esperada ≈ crecimiento EPS + dividendos + cambio de múltiplo**

pero calculada correctamente mediante composición.

Para cinco años:

```text
R = [(EPS futuro / EPS actual)
     ×
     (PE terminal / PE actual)
     ×
     (1 + dividend yield acumulado)]
     ^(1/5) - 1
```

La implementación exacta será definida antes de programar.

---

# 10. Precio máximo de compra

El sistema no se limitará a decir:

> Valor = 70 €

También calculará:

| Rentabilidad objetivo | Precio máximo |
| --------------------: | ------------: |
|                    8% |             X |
|                   10% |             X |
|                   12% |             X |
|                   15% |             X |

Esto será fundamental para convertir la valoración en una herramienta práctica.

---

# 11. Margen de seguridad

Mostraremos:

```text
Precio actual
Valor Bear
Valor Base
Valor Bull
```

y:

```text
Margen seguridad Bear
Margen seguridad Base
Margen seguridad Bull
```

Pero **no utilizaremos automáticamente un porcentaje fijo para todas las empresas**.

El margen requerido dependerá también de:

* volatilidad
* deuda
* ciclicidad
* calidad
* previsibilidad
* riesgo de dilución
* calidad del FCF.

---

# 12. Sistema de calidad

Crearemos un **Quality Score**, pero documentado.

No será una caja negra.

Por ejemplo:

```text
ROIC                  18/20
Balance               17/20
FCF                   16/20
Crecimiento            8/15
Márgenes              13/15
Ventaja competitiva    7/10
──────────────────────────
QUALITY SCORE         79/100
```

Los pesos serán configurables.

---

# 13. Value Score

Separado del Quality Score.

Evaluará:

* P/E normalizado
* FCF Yield
* EV/EBITDA
* descuento a DCF
* descuento a valor histórico
* retorno esperado

Así evitamos mezclar:

> "Empresa barata"

con:

> "Empresa buena".

---

# 14. Risk Score

Otro módulo independiente.

Evaluará:

* deuda
* volatilidad del beneficio
* ciclicidad
* concentración clientes
* regulación
* riesgo país
* dilución
* riesgo tecnológico
* riesgo de refinanciación
* dependencia de materias primas
* calidad contable cuando haya señales objetivas

---

# 15. Value Trap Detector

Será un módulo específico.

Buscará combinaciones como:

```text
PER bajo
+
EPS cayendo
+
FCF deteriorándose
+
ROIC bajo
+
deuda elevada
```

o:

```text
Dividend Yield alto
+
FCF insuficiente
+
pay-out insostenible
```

o:

```text
EV/EBITDA aparentemente bajo
+
EBITDA cíclicamente elevado
```

---

# 16. Score de oportunidad

No será simplemente una clasificación por PER.

Crearemos una matriz:

```text
              CALIDAD
           baja       alta
        ┌─────────┬─────────┐
barata  │ Value   │ Quality │
        │ Trap?   │ Value   │
        ├─────────┼─────────┤
cara    │ evitar? │ Quality │
        │         │ premium │
        └─────────┴─────────┘
```

Y el sistema mostrará **por qué** una empresa aparece como oportunidad.

---

# 17. Agentes de IA

La arquitectura prevista será:

### Agente 1 — Financial Analyst

Interpreta estados financieros.

### Agente 2 — Business Analyst

Analiza:

* modelo de negocio
* moat
* competencia
* pricing power
* crecimiento

### Agente 3 — Valuation Analyst

Revisa las hipótesis de valoración.

### Agente 4 — Risk Analyst

Busca riesgos y contradicciones.

### Agente 5 — News Analyst

Analiza noticias, resultados y acontecimientos recientes.

### Agente 6 — Investment Review

Integra todo y genera el informe.

**Los agentes no sustituirán al motor matemático.**

---

# 18. Control de calidad de la IA

Cada conclusión importante tendrá que indicar:

```text
HECHO
SUPUESTO
ESTIMACIÓN
INTERPRETACIÓN
```

Ejemplo:

> **Hecho:** deuda neta aumentó 15%.

> **Estimación:** EBITDA crecerá 10%.

> **Supuesto:** margen EBITDA normalizado 18%.

> **Interpretación:** el apalancamiento podría aumentar si no se cumple el crecimiento.

Esto será especialmente importante para evitar que la IA convierta una opinión en un dato.

---

# 19. Seguimiento de noticias

No queremos leer todas las noticias.

El sistema detectará eventos potencialmente relevantes:

* resultados
* guidance
* profit warning
* adquisiciones
* ampliaciones
* recompras
* dividendos
* cambios de dirección
* litigios relevantes
* regulación
* cambios de deuda
* cambios importantes de estimaciones

---

# 20. Cartera personal

Cada operación tendrá:

```text
Fecha
Empresa
Número acciones
Precio
Comisiones
Divisa
Motivo de compra
Tesis
Valoración
Precio objetivo
Rentabilidad esperada
```

Y las ventas:

```text
Fecha
Precio
Motivo
Resultado
```

---

# 21. Seguimiento de la tesis

Cada inversión tendrá una ficha:

```text
TESIS

¿Por qué compré?

Hipótesis de crecimiento:

Hipótesis de margen:

Valoración:

Catalizadores:

Riesgos:

Qué tendría que ocurrir para vender:
```

El sistema comprobará periódicamente estas condiciones.

---

# 22. Atribución de rentabilidad

La cartera se descompondrá en:

```text
Rentabilidad total
│
├── evolución EPS
├── expansión/contracción PER
├── dividendos
├── recompras
├── divisa
└── otros
```

Así podremos saber **de dónde vino realmente la rentabilidad**.

---

# 23. Benchmark

Compararemos la cartera contra referencias apropiadas.

Por ejemplo:

* IBEX 35
* S&P 500
* MSCI World

Pero separando:

**rentabilidad**

de

**riesgo asumido**.

Mediremos:

* CAGR
* volatilidad
* máximo drawdown
* Sharpe
* Sortino
* beta
* tracking error

---

# 24. Backtesting

Una fase posterior permitirá preguntar:

> ¿Qué habría hecho este modelo entre 2010 y 2025?

Pero únicamente utilizando información disponible **en cada fecha**.

Guardaremos:

```text
Fecha
Precio conocido entonces
Estimaciones disponibles entonces
Valoración calculada entonces
Decisión/señal entonces
Resultado posterior
```

Esto permitirá medir el modelo de verdad.

---

# 25. Alertas

Telegram será inicialmente el canal principal.

Tipos:

### 🟢 Nueva oportunidad

### 🟡 Cambio de valoración

### 🟠 Cambio de tesis

### 🔴 Riesgo importante

### 📊 Informe periódico

### 💼 Cartera

Y habrá un límite para evitar spam.

---

# 26. Frecuencia

Propongo:

### Diario

Precio + cambios importantes.

### Semanal

Radar completo.

### Trimestral

Revisión profunda de empresas.

### Anual

Revisión completa de metodología y rendimiento.

---

# 27. Dashboard

Tendrá inicialmente cinco pantallas:

### 1. Radar

Empresas interesantes ahora.

### 2. Empresa

Ficha completa.

### 3. Cartera

Mis inversiones.

### 4. Alertas

Cambios relevantes.

### 5. Historial

Qué decía el sistema anteriormente.

---

# 28. Tecnología

Primera versión:

```text
Python
GitHub
GitHub Actions
SQLite
APIs financieras
yfinance cuando resulte apropiado
Telegram
Streamlit
LLM/API
```

Más adelante:

```text
PostgreSQL
Docker
cloud hosting
```

No añadiremos infraestructura innecesaria hasta que sea necesaria.

---

# 29. Seguridad

Nunca guardaremos en GitHub:

* API keys
* tokens de Telegram
* contraseñas
* credenciales del broker

Utilizaremos:

**GitHub Secrets / variables de entorno.**

La información sensible de la cartera estará separada del código público.

---

# 30. Principio de reproducibilidad

Cada análisis tendrá:

```text
timestamp
versión del modelo
fuentes utilizadas
supuestos
datos de entrada
resultado
```

Por ejemplo:

```text
INDITEX
Analysis #000381

18/09/2026 06:00

Model version: 1.0.3

Fair Value:
64.80 €

Expected return:
11.7%

Data snapshot:
2026-09-18
```

Así podremos saber **exactamente por qué el sistema dijo lo que dijo**.

---

# 31. Roadmap de construcción

## FASE 0 — Diseño

**Ahora**

Definir:

* métricas
* fórmulas
* arquitectura
* fuentes
* criterios
* estructura de datos

**No programar todavía.**

---

## FASE 1 — Motor financiero

Construir:

* descarga datos
* base de datos
* ratios
* históricos
* EPS
* FCF
* deuda
* crecimiento

**Objetivo:** tener datos fiables.

---

## FASE 2 — Valoración

Construir:

* P/E
* FCF
* EV/EBITDA
* DCF
* escenarios
* precio máximo de compra
* rentabilidad esperada

**Objetivo:** reproducir matemáticamente nuestro método.

---

## FASE 3 — Radar

Analizar automáticamente cientos/miles de empresas.

**Objetivo:** descubrir oportunidades.

---

## FASE 4 — Cartera

Añadir:

* operaciones
* dividendos
* rendimiento
* tesis
* benchmark.

---

## FASE 5 — Alertas

Telegram.

**Objetivo:** que el sistema funcione aunque nosotros no lo abramos.

---

## FASE 6 — IA

Incorporar los agentes.

**Objetivo:** interpretación cualitativa y análisis de acontecimientos.

---

## FASE 7 — Backtest

Medir históricamente el modelo.

**Objetivo:** saber qué funciona y qué no.

---

# 32. Criterio de "proyecto terminado"

La versión 1.0 **no estará terminada** porque tengamos un script que imprime ratios.

Consideraremos que funciona cuando podamos hacer:

```text
$ python analyze_company.py INDITEX
```

y obtener automáticamente:

```text
────────────────────────────
INDITEX
18/09/2026
────────────────────────────

PRICE              XX €

QUALITY SCORE       XX/100
VALUE SCORE         XX/100
RISK SCORE          XX/100
VALUE TRAP          LOW/MED/HIGH

NORMALIZED EPS      XX €
FCF/SHARE           XX €
ROIC                XX %
NET DEBT/EBITDA     XX

FAIR VALUE

Bear                XX €
Base                XX €
Bull                XX €

EXPECTED RETURN

8%                  XX €
10%                 XX €
12%                 XX €
15%                 XX €

MAX BUY PRICE

8%                  XX €
10%                 XX €
12%                 XX €
15%                 XX €

THESIS STATUS       OK / REVIEW

────────────────────────────
```

Y que posteriormente el sistema pueda hacer esto **sin intervención humana** para todo el universo.

---

# 33. Regla para modificar el plan

Durante el desarrollo aparecerán problemas.

No quiero que eso nos lleve a cambiar silenciosamente el proyecto.

Cada cambio importante quedará registrado:

```text
CHANGELOG

v1.0
Plan inicial

v1.1
Cambio: fuente de datos X
Motivo: ...
Impacto: ...

v1.2
Cambio: fórmula FCF
Motivo: ...
Impacto: ...
```

Así podrás volver a este documento y comprobar:

**"¿Estamos construyendo lo que dijimos que íbamos a construir?"**

---

# 34. El documento de control

Te recomiendo guardar **este plan como `PROJECT_PLAN.md` en el repositorio**.

Y además tendremos:

```text
PROJECT_PLAN.md
ARCHITECTURE.md
VALUATION_METHOD.md
DATA_SOURCES.md
CHANGELOG.md
TODO.md
```

El más importante será:

### `VALUATION_METHOD.md`

Ahí quedarán congeladas las fórmulas.

Esto evitará que dentro de seis meses cambiemos accidentalmente la metodología y luego no sepamos por qué los resultados históricos han cambiado.

---

## Orden que propongo seguir a partir de ahora

**No empezaría todavía por Python.**

Primero haría estos cuatro documentos conceptuales:

**1. `VALUATION_METHOD.md`**
Todas las métricas, fórmulas, escenarios y criterios de valoración.

**2. `DATA_SOURCES.md`**
Qué datos necesitamos, de dónde salen, coste, frecuencia y fiabilidad.

**3. `ARCHITECTURE.md`**
Cómo se conectan Python, base de datos, APIs, agentes, GitHub y Telegram.

**4. `TODO.md`**
Lista de tareas concreta, que iremos marcando como completadas.

Una vez aprobados esos cuatro documentos, **empezamos a programar el MVP**.

Y una decisión que considero especialmente importante: **no introduciría todavía los agentes de IA**. Primero construiremos un motor financiero determinista que podamos auditar. Después pondremos la IA encima. Así, si dentro de un año el sistema dice que una empresa vale 100 €, podremos averiguar si el problema estaba en los datos, en la fórmula, en los supuestos o en la interpretación de la IA.
