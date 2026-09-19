# TODO — Value Investing System

## 1. Objetivo

Convertir el diseño definido en `PROJECT_PLAN.md`, `VALUATION_METHOD.md`, `DATA_SOURCES.md` y `ARCHITECTURE.md` en un sistema ejecutable, reproducible y automatizable.

El sistema deberá poder:

1. Obtener datos financieros y de mercado.
2. Almacenarlos conservando trazabilidad.
3. Calcular métricas financieras de forma determinista.
4. Valorar empresas mediante varios métodos.
5. Analizar calidad, riesgo y posibles trampas de valor.
6. Analizar la cartera personal.
7. Detectar oportunidades.
8. Explicar cambios relevantes mediante IA.
9. Generar alertas.
10. Ejecutarse automáticamente.
11. Mantener histórico de análisis.
12. Permitir backtesting sin look-ahead bias.

---

# 2. Estado global

| Milestone | Objetivo                            | Estado       |
| --------- | ----------------------------------- | ------------ |
| M0        | Metodología y arquitectura          | ✅ COMPLETADO |
| M1        | Repositorio y estructura técnica    | ⬜ TODO       |
| M2        | Base de datos y modelo de datos     | ⬜ TODO       |
| M3        | Ingesta y normalización de datos    | ⬜ TODO       |
| M4        | Motor de métricas                   | ⬜ TODO       |
| M5        | Motor de valoración                 | ⬜ TODO       |
| M6        | Quality / Value / Risk / Value Trap | ⬜ TODO       |
| M7        | Análisis de cartera                 | ⬜ TODO       |
| M8        | Radar de oportunidades              | ⬜ TODO       |
| M9        | Automatización diaria/semanal       | ⬜ TODO       |
| M10       | Capa de IA                          | ⬜ TODO       |
| M11       | Telegram                            | ⬜ TODO       |
| M12       | Dashboard Streamlit                 | ⬜ TODO       |
| M13       | Backtesting                         | ⬜ TODO       |
| M14       | Hardening / producción              | ⬜ TODO       |

---

# 3. Documentación

| ID      | Tarea                       | Dependencias        | Estado |
| ------- | --------------------------- | ------------------- | ------ |
| DOC-001 | Crear `PROJECT_PLAN.md`     | —                   | ✅      |
| DOC-002 | Crear `VALUATION_METHOD.md` | DOC-001             | ✅      |
| DOC-003 | Crear `DATA_SOURCES.md`     | DOC-001             | ✅      |
| DOC-004 | Crear `ARCHITECTURE.md`     | DOC-002/003         | ✅      |
| DOC-005 | Crear `TODO.md`             | DOC-001/002/003/004 | ✅      |
| DOC-006 | Crear `CHANGELOG.md`        | —                   | ⬜      |
| DOC-007 | Crear `README.md`           | M1                  | ⬜      |

---

# 4. M1 — Repositorio y estructura técnica

## Objetivo

Crear la estructura Python mínima sin implementar todavía lógica financiera compleja.

| ID     | Tarea                            | Dependencias | Criterio de aceptación                  | Estado |
| ------ | -------------------------------- | ------------ | --------------------------------------- | ------ |
| M1-001 | Crear estructura de directorios  | —            | Todos los directorios definidos existen | ⬜      |
| M1-002 | Crear `pyproject.toml`           | M1-001       | Proyecto instalable localmente          | ⬜      |
| M1-003 | Crear configuración central      | M1-001       | Configuración separada del código       | ⬜      |
| M1-004 | Crear sistema de logging         | M1-002       | Ejecuciones registradas                 | ⬜      |
| M1-005 | Crear `.gitignore`               | M1-001       | Secretos y datos privados excluidos     | ⬜      |
| M1-006 | Crear `.env.example`             | M1-001       | Variables necesarias documentadas       | ⬜      |
| M1-007 | Crear estructura de tests        | M1-002       | `pytest` ejecuta correctamente          | ⬜      |
| M1-008 | Crear primer pipeline ejecutable | M1-002       | `python -m src.pipeline.daily` funciona | ⬜      |

### Definition of Done

El proyecto debe poder clonarse e instalarse en otro ordenador y ejecutar una aplicación Python mínima sin modificar la lógica financiera.

---

# 5. M2 — Base de datos

## Objetivo

Implementar SQLite como base de datos inicial.

## Tablas iniciales

* `companies`
* `securities`
* `prices`
* `financials`
* `cash_flows`
* `balance_sheets`
* `shares`
* `dividends`
* `estimates`
* `estimate_revisions`
* `corporate_actions`
* `valuations`
* `scenarios`
* `quality_scores`
* `value_scores`
* `risk_scores`
* `portfolio_transactions`
* `portfolio_positions`
* `investment_theses`
* `alerts`
* `analysis_runs`
* `sources`

| ID     | Tarea                              | Dependencias | Criterio de aceptación                      | Estado |
| ------ | ---------------------------------- | ------------ | ------------------------------------------- | ------ |
| M2-001 | Crear esquema SQLite               | M1           | DB creada automáticamente                   | ⬜      |
| M2-002 | Crear migrations/schema versioning | M2-001       | Cambios de esquema reproducibles            | ⬜      |
| M2-003 | Implementar tabla `companies`      | M2-001       | Empresas identificables de forma única      | ⬜      |
| M2-004 | Implementar tablas financieras     | M2-001       | Datos históricos almacenables               | ⬜      |
| M2-005 | Implementar tablas de mercado      | M2-001       | Precios y corporate actions almacenables    | ⬜      |
| M2-006 | Implementar tabla `estimates`      | M2-001       | Estimates con fecha de observación          | ⬜      |
| M2-007 | Implementar tabla `sources`        | M2-001       | Cada dato crítico puede rastrearse a fuente | ⬜      |
| M2-008 | Implementar `analysis_runs`        | M2-001       | Cada análisis queda registrado              | ⬜      |
| M2-009 | Crear constraints                  | M2-003/004   | Duplicados y datos inválidos detectados     | ⬜      |
| M2-010 | Crear tests DB                     | M2-001/009   | Tests pasan                                 | ⬜      |

### Regla crítica

Los datos financieros deben conservar:

* `period_end`
* `filing_date`
* `publication_date` cuando exista
* `source_id`
* moneda
* unidad
* tipo de período
* fecha de adquisición del dato

La fecha de publicación es fundamental para el backtesting.

---

# 6. M3 — Data Ingestion & Normalization

## Objetivo

Crear una capa de proveedores intercambiables.

### Proveedores

1. EODHD
2. CNMV
3. SEC
4. yfinance

La arquitectura debe permitir añadir otros proveedores posteriormente.

| ID     | Tarea                         | Dependencias       | Criterio de aceptación                | Estado |
| ------ | ----------------------------- | ------------------ | ------------------------------------- | ------ |
| M3-001 | Crear interfaz `DataProvider` | M2                 | Proveedores intercambiables           | ⬜      |
| M3-002 | Implementar provider yfinance | M3-001             | Obtención de precios básica           | ⬜      |
| M3-003 | Implementar provider EODHD    | M3-001             | Market/fundamental data               | ⬜      |
| M3-004 | Implementar CNMV              | M3-001             | Filings españoles procesables         | ⬜      |
| M3-005 | Implementar SEC               | M3-001             | Filings estadounidenses procesables   | ⬜      |
| M3-006 | Guardar datos RAW             | M3-002/003/004/005 | Respuesta original conservada         | ⬜      |
| M3-007 | Normalizar unidades           | M3-006             | Unidades homogéneas                   | ⬜      |
| M3-008 | Normalizar monedas            | M3-006             | Conversión reproducible               | ⬜      |
| M3-009 | Normalizar shares             | M3-006             | Dilución/corporate actions tratadas   | ⬜      |
| M3-010 | Detectar discrepancias        | M3-007/008/009     | Conflictos marcados                   | ⬜      |
| M3-011 | Sistema de calidad A/B/C/D    | M3-010             | Cada dato crítico tiene quality grade | ⬜      |
| M3-012 | Tests de ingestión            | M3-002/003         | Casos reales y mocks                  | ⬜      |

### Regla

Nunca sobrescribir silenciosamente un dato anterior.

Los datos históricos deben ser versionables.

---

# 7. M4 — Motor de métricas

## Objetivo

Toda métrica financiera debe calcularse mediante Python, no mediante el LLM.

### Métricas

* Revenue growth
* EPS
* EPS growth
* EPS CAGR
* normalized EPS
* P/E
* forward P/E
* normalized P/E
* earnings yield
* FCF
* FCF/share
* FCF yield
* EBITDA
* EBIT
* EV
* EV/EBITDA
* ROE
* ROIC
* debt
* cash
* net debt
* net debt/EBITDA
* interest coverage
* dividend yield
* payout ratio
* buyback yield
* shareholder yield
* dilution

| ID     | Tarea                         | Dependencias | Criterio de aceptación             | Estado |
| ------ | ----------------------------- | ------------ | ---------------------------------- | ------ |
| M4-001 | Implementar EPS               | M3           | Coincide con cálculo independiente | ⬜      |
| M4-002 | Implementar crecimiento       | M4-001       | YoY/CAGR correctos                 | ⬜      |
| M4-003 | Implementar P/E               | M4-001       | TTM/forward/normalized             | ⬜      |
| M4-004 | Implementar FCF               | M3           | CFO - Capex                        | ⬜      |
| M4-005 | Implementar FCF yield         | M4-004       | Cálculo reproducible               | ⬜      |
| M4-006 | Implementar EV                | M3           | EV correctamente calculado         | ⬜      |
| M4-007 | Implementar EV/EBITDA         | M4-006       | Resultado validado                 | ⬜      |
| M4-008 | Implementar ROE               | M3           | Resultado validado                 | ⬜      |
| M4-009 | Implementar ROIC              | M3           | Resultado validado                 | ⬜      |
| M4-010 | Implementar leverage          | M3           | Ratios de deuda                    | ⬜      |
| M4-011 | Implementar dividendos        | M3           | Yield/payout                       | ⬜      |
| M4-012 | Implementar shareholder yield | M3           | Dividendos + recompras - emisión   | ⬜      |
| M4-013 | Implementar dilution          | M3           | Evolución shares                   | ⬜      |
| M4-014 | Tests de métricas             | M4-001/013   | Cobertura de casos críticos        | ⬜      |

---

# 8. M5 — Motor de valoración

## Objetivo

Convertir métricas y supuestos en valoraciones reproducibles.

## Métodos

### Empresas generales

* P/E
* normalized P/E
* FCF yield
* DCF
* EV/EBITDA

### Bancos

* P/B
* P/TBV
* ROE/ROTCE
* dividend/buyback
* crecimiento del book value

### Aseguradoras

* P/B
* ROE
* normalized earnings
* capital
* dividend/buyback

### Cíclicas

* normalized earnings
* normalized FCF
* normalized margins

### Conglomerados

* SOTP

| ID     | Tarea                           | Dependencias | Criterio de aceptación             | Estado |
| ------ | ------------------------------- | ------------ | ---------------------------------- | ------ |
| M5-001 | Implementar P/E valuation       | M4           | Fair value reproducible            | ⬜      |
| M5-002 | Implementar normalized P/E      | M4           | Earnings normalizados              | ⬜      |
| M5-003 | Implementar FCF valuation       | M4           | Fair value reproducible            | ⬜      |
| M5-004 | Implementar EV/EBITDA valuation | M4           | Fair value reproducible            | ⬜      |
| M5-005 | Implementar DCF                 | M4           | Bear/Base/Bull                     | ⬜      |
| M5-006 | Implementar DDM                 | M4           | Aplicable cuando corresponda       | ⬜      |
| M5-007 | Implementar P/B                 | M4           | Aplicable a financieras            | ⬜      |
| M5-008 | Implementar P/TBV               | M4           | Aplicable a bancos                 | ⬜      |
| M5-009 | Implementar SOTP                | M4           | Segmentos valorables               | ⬜      |
| M5-010 | Implementar escenarios          | M5-001/009   | Bear/Base/Bull                     | ⬜      |
| M5-011 | Implementar expected return     | M5-010       | 3Y/5Y/7Y/10Y                       | ⬜      |
| M5-012 | Implementar purchase price      | M5-011       | 8/10/12/15% hurdle                 | ⬜      |
| M5-013 | Implementar margin of safety    | M5-010       | Bear/Base/Bull                     | ⬜      |
| M5-014 | Versionar modelo                | M5-001/013   | Cada valoración identifica versión | ⬜      |
| M5-015 | Tests de valoración             | M5-014       | Casos de referencia pasan          | ⬜      |

### Regla crítica

El motor debe distinguir:

**Datos**

de

**Supuestos**

de

**Resultados calculados**

Nunca mezclar los tres.

---

# 9. M6 — Quality / Value / Risk / Value Trap

## Quality Score

Variables potenciales:

* ROIC
* ROE
* márgenes
* estabilidad de beneficios
* FCF
* balance
* crecimiento
* moat

## Value Score

Variables potenciales:

* normalized P/E
* FCF yield
* descuento a fair value
* expected return
* margin of safety

## Risk Score

Variables:

* deuda
* volatilidad de beneficios
* ciclicidad
* concentración
* regulación
* commodities
* refinanciación
* dilución

## Value Trap Engine

No debe decir simplemente "value trap".

Debe producir señales:

* beneficios decrecientes
* FCF deteriorándose
* deuda creciente
* ROIC decreciente
* dilución
* deterioro de márgenes
* deterioro estructural del negocio
* payout no cubierto
* valoración aparentemente barata pero con earnings normalizados inferiores

| ID     | Tarea             | Dependencias | Criterio de aceptación   | Estado |
| ------ | ----------------- | ------------ | ------------------------ | ------ |
| M6-001 | Quality Engine    | M4           | Score explicable         | ⬜      |
| M6-002 | Value Engine      | M5           | Score explicable         | ⬜      |
| M6-003 | Risk Engine       | M4           | Score explicable         | ⬜      |
| M6-004 | Value Trap Engine | M4/M5        | Señales explicables      | ⬜      |
| M6-005 | Tests scoring     | M6-001/004   | Resultados deterministas | ⬜      |

---

# 10. M7 — Portfolio Engine

## Objetivo

Analizar las inversiones reales del usuario sin mezclar datos privados con el repositorio público.

### Datos

* posiciones
* compras
* ventas
* dividendos
* comisiones
* impuestos cuando corresponda
* efectivo
* moneda
* coste
* precio actual
* peso
* P/L
* fair value
* expected return
* thesis
* risk

| ID     | Tarea                            | Dependencias | Criterio de aceptación              | Estado |
| ------ | -------------------------------- | ------------ | ----------------------------------- | ------ |
| M7-001 | Importar portfolio CSV           | M2           | Posiciones correctamente importadas | ⬜      |
| M7-002 | Registrar transacciones          | M7-001       | Cost basis correcto                 | ⬜      |
| M7-003 | Calcular pesos                   | M7-002       | Suma ≈ 100% + cash                  | ⬜      |
| M7-004 | Calcular P/L                     | M7-002       | Realizado/no realizado              | ⬜      |
| M7-005 | Registrar dividendos             | M7-002       | Dividendos asociados a posición     | ⬜      |
| M7-006 | Calcular fair value cartera      | M5           | Fair value agregado                 | ⬜      |
| M7-007 | Calcular expected return cartera | M5           | Weighted expected return            | ⬜      |
| M7-008 | Analizar concentración           | M7-003       | Riesgos identificados               | ⬜      |
| M7-009 | Integrar thesis                  | M7-006       | Estado de tesis por posición        | ⬜      |
| M7-010 | Tests portfolio                  | M7-001/009   | Casos de prueba pasan               | ⬜      |

### Regla de privacidad

Los datos personales de cartera no se subirán al repositorio GitHub público.

---

# 11. M8 — Opportunity / Radar Engine

## Objetivo

Analizar un universo amplio y detectar empresas que merezcan investigación.

El sistema no debe utilizar una única métrica.

Pipeline:

```text
Universe
   ↓
Data Quality Filter
   ↓
Financial Quality
   ↓
Balance Sheet
   ↓
Growth / Normalized Earnings
   ↓
Valuation
   ↓
Expected Return
   ↓
Margin of Safety
   ↓
Risk
   ↓
Value Trap Signals
   ↓
Opportunity Candidates
```

| ID     | Tarea                       | Dependencias | Criterio de aceptación                     | Estado |
| ------ | --------------------------- | ------------ | ------------------------------------------ | ------ |
| M8-001 | Definir universo inicial    | M3           | Universo reproducible                      | ⬜      |
| M8-002 | Crear filtros de datos      | M3           | Empresas con datos insuficientes excluidas | ⬜      |
| M8-003 | Crear screening financiero  | M4           | Métricas calculadas                        | ⬜      |
| M8-004 | Integrar valuation          | M5           | Fair values disponibles                    | ⬜      |
| M8-005 | Integrar quality/value/risk | M6           | Scores disponibles                         | ⬜      |
| M8-006 | Crear opportunity engine    | M8-003/005   | Candidatos explicables                     | ⬜      |
| M8-007 | Crear histórico del radar   | M8-006       | Cambios almacenados                        | ⬜      |
| M8-008 | Tests radar                 | M8-006       | Resultados reproducibles                   | ⬜      |

### Regla

El radar genera **candidatos para investigar**, no decisiones automáticas de inversión.

---

# 12. M9 — Automatización

## Jobs

### Diario

```text
Market data
↓
Data validation
↓
Database update
↓
Metrics
↓
Portfolio
↓
Events
↓
Material alerts
```

### Semanal

```text
Universe scan
↓
Fundamentals
↓
Valuation
↓
Scores
↓
Opportunity radar
↓
AI review
↓
Weekly report
```

### Trimestral

```text
Filings
↓
Financial statements
↓
Estimates
↓
Valuation
↓
Thesis review
↓
Structural changes
```

| ID     | Tarea                          | Dependencias | Criterio de aceptación   | Estado |
| ------ | ------------------------------ | ------------ | ------------------------ | ------ |
| M9-001 | Crear daily pipeline           | M4/M7        | Ejecución local correcta | ⬜      |
| M9-002 | Crear weekly pipeline          | M8           | Screening automático     | ⬜      |
| M9-003 | Crear quarterly pipeline       | M5/M6        | Revisión fundamental     | ⬜      |
| M9-004 | Crear GitHub Actions daily     | M9-001       | Job automático           | ⬜      |
| M9-005 | Crear GitHub Actions weekly    | M9-002       | Job automático           | ⬜      |
| M9-006 | Crear GitHub Actions quarterly | M9-003       | Job automático           | ⬜      |
| M9-007 | Crear data validation workflow | M3           | Errores detectados       | ⬜      |
| M9-008 | Crear tests workflow           | M1           | Tests automáticos        | ⬜      |
| M9-009 | Registrar execution logs       | M9-004/008   | Fallos auditables        | ⬜      |

---

# 13. M10 — AI Analyst Layer

## Principio

La IA no calcula las métricas financieras fundamentales.

Python calcula:

* ratios
* valoración
* escenarios
* scores
* expected returns
* purchase prices
* portfolio metrics

La IA interpreta y explica.

## Agentes

### Financial Analyst

Pregunta:

> ¿Qué ha cambiado en los números?

### Business Analyst

Pregunta:

> ¿Qué está ocurriendo con el negocio?

### Valuation Analyst

Pregunta:

> ¿Son razonables los supuestos utilizados?

### Risk Analyst

Pregunta:

> ¿Qué puede romper la tesis?

### News Analyst

Pregunta:

> ¿Qué noticias pueden modificar materialmente la tesis?

### Investment Review Agent

Integra los análisis anteriores.

| ID      | Tarea                     | Dependencias | Criterio de aceptación          | Estado |
| ------- | ------------------------- | ------------ | ------------------------------- | ------ |
| M10-001 | Definir prompts/versiones | M6           | Prompts versionados             | ⬜      |
| M10-002 | Financial Analyst         | M4           | Explica cambios cuantitativos   | ⬜      |
| M10-003 | Business Analyst          | M10-001      | Análisis cualitativo trazable   | ⬜      |
| M10-004 | Valuation Analyst         | M5           | Revisa supuestos                | ⬜      |
| M10-005 | Risk Analyst              | M6           | Identifica riesgos              | ⬜      |
| M10-006 | News Analyst              | M3           | Analiza eventos relevantes      | ⬜      |
| M10-007 | Investment Review         | M10-002/006  | Informe integrado               | ⬜      |
| M10-008 | Guardrails                | M10-007      | IA no modifica datos calculados | ⬜      |
| M10-009 | Tests AI                  | M10-008      | Outputs estructurados           | ⬜      |

### Regla

Si eliminamos la IA, el sistema debe seguir funcionando financieramente.

---

# 14. M11 — Telegram

## Objetivo

Enviar únicamente información material.

### Alertas

* nueva oportunidad
* cambio importante de valoración
* deterioro de FCF
* deterioro de balance
* earnings surprise
* guidance
* adquisición
* ampliación de capital
* recompra
* dividendo
* cambio relevante de tesis
* riesgo material
* revisión semanal

| ID      | Tarea                  | Dependencias | Criterio de aceptación        | Estado |
| ------- | ---------------------- | ------------ | ----------------------------- | ------ |
| M11-001 | Crear Telegram adapter | M9           | Mensaje enviado correctamente | ⬜      |
| M11-002 | Crear alert engine     | M9           | Filtra materialidad           | ⬜      |
| M11-003 | Plantillas de mensajes | M11-001      | Mensajes estructurados        | ⬜      |
| M11-004 | Rate limiting          | M11-001      | Sin spam                      | ⬜      |
| M11-005 | Tests                  | M11-002      | Alertas reproducibles         | ⬜      |

---

# 15. M12 — Streamlit Dashboard

## Pantallas

### Home

* cartera
* rentabilidad
* expected return
* cash
* alertas
* oportunidades

### Radar

* empresa
* precio
* Quality
* Value
* Risk
* expected return
* fair value
* margin of safety
* value trap signals

### Company

* precio
* resultados
* FCF
* deuda
* valoración
* escenarios
* riesgos
* noticias
* tesis
* histórico

### Portfolio

* posiciones
* pesos
* coste
* valor
* P/L
* dividendos
* fair value
* expected return
* thesis

### Alerts

* alertas activas
* historial

| ID      | Tarea                | Dependencias | Criterio de aceptación | Estado |
| ------- | -------------------- | ------------ | ---------------------- | ------ |
| M12-001 | Crear Streamlit base | M1           | App ejecutable         | ⬜      |
| M12-002 | Home                 | M7           | Dashboard funcional    | ⬜      |
| M12-003 | Radar                | M8           | Screening visible      | ⬜      |
| M12-004 | Company page         | M5/M6        | Análisis completo      | ⬜      |
| M12-005 | Portfolio page       | M7           | Cartera visible        | ⬜      |
| M12-006 | Alerts page          | M11          | Historial visible      | ⬜      |
| M12-007 | Charts históricos    | M2           | Datos trazables        | ⬜      |

---

# 16. M13 — Backtesting

## Objetivo

Comprobar si la metodología funciona históricamente sin utilizar información futura.

## Inputs

* fecha
* universo
* datos disponibles en esa fecha
* estimaciones disponibles en esa fecha
* modelo
* parámetros

## Outputs

* señales
* posiciones
* rentabilidad
* drawdown
* volatilidad
* Sharpe
* Sortino
* turnover
* exposición
* resultados por sector
* resultados por tipo de empresa

| ID      | Tarea                       | Dependencias | Criterio de aceptación           | Estado |
| ------- | --------------------------- | ------------ | -------------------------------- | ------ |
| M13-001 | Crear dataset point-in-time | M3           | Sin información futura           | ⬜      |
| M13-002 | Historical estimates        | M3           | Estimates fechados correctamente | ⬜      |
| M13-003 | Historical universe         | M3           | Sin survivorship bias            | ⬜      |
| M13-004 | Backtest engine             | M5/M8        | Ejecución reproducible           | ⬜      |
| M13-005 | Performance metrics         | M13-004      | Métricas calculadas              | ⬜      |
| M13-006 | Drawdown analysis           | M13-004      | Max drawdown y duración          | ⬜      |
| M13-007 | Sensitivity analysis        | M13-004      | Parámetros comparables           | ⬜      |
| M13-008 | Backtest report             | M13-005      | Informe reproducible             | ⬜      |
| M13-009 | Tests anti-lookahead        | M13-001/004  | Future data bloqueada            | ⬜      |

### Regla crítica

Un backtest que utiliza estimates actuales para reconstruir decisiones históricas NO se considerará un backtest point-in-time válido.

---

# 17. M14 — Production Hardening

| ID      | Tarea                    | Dependencias | Criterio de aceptación      | Estado |
| ------- | ------------------------ | ------------ | --------------------------- | ------ |
| M14-001 | Error handling providers | M3           | Fallos controlados          | ⬜      |
| M14-002 | Retry system             | M9           | Reintentos configurables    | ⬜      |
| M14-003 | Data quality monitoring  | M3           | Datos anómalos detectados   | ⬜      |
| M14-004 | Backup database          | M2           | Backup automático           | ⬜      |
| M14-005 | Secrets management       | M9           | Ningún secreto en Git       | ⬜      |
| M14-006 | Reproducibility metadata | M5           | data/model/code version     | ⬜      |
| M14-007 | Monitoring               | M9           | Fallos notificados          | ⬜      |
| M14-008 | Documentation final      | M14          | Sistema documentado         | ⬜      |
| M14-009 | End-to-end test          | M14          | Pipeline completo operativo | ⬜      |

---

# 18. Definition of Done del proyecto

El proyecto se considerará operativo cuando:

* [ ] Puede descargar datos automáticamente.
* [ ] Conserva los datos RAW.
* [ ] Puede reconstruir cómo se obtuvo cada dato.
* [ ] Puede calcular todas las métricas fundamentales.
* [ ] Puede valorar una empresa.
* [ ] Puede producir Bear/Base/Bull.
* [ ] Puede calcular expected return.
* [ ] Puede calcular precios de compra para diferentes hurdles.
* [ ] Puede analizar calidad.
* [ ] Puede analizar riesgo.
* [ ] Puede detectar señales de value trap.
* [ ] Puede analizar la cartera.
* [ ] Puede escanear un universo.
* [ ] Puede generar alertas.
* [ ] Puede ejecutar jobs automáticamente.
* [ ] Puede mostrar los resultados en dashboard.
* [ ] Puede utilizar IA para análisis cualitativo.
* [ ] Puede funcionar sin IA para cálculos financieros.
* [ ] Mantiene versiones de datos y modelos.
* [ ] Tiene tests automatizados.
* [ ] Tiene control de errores.
* [ ] Tiene backtesting point-in-time.

---

# 19. Reglas de desarrollo

## Regla 1 — No inventar datos

Si un dato crítico no existe:

```text
DATOS INSUFICIENTES
```

No se sustituirá silenciosamente por una estimación inventada.

---

## Regla 2 — No mezclar datos y supuestos

Ejemplo:

```text
EPS 2025 = dato
EPS 2026E = estimate
g 2027-2030 = supuesto
P/E terminal = supuesto
Fair Value = cálculo
```

Cada elemento debe conservar su naturaleza.

---

## Regla 3 — No look-ahead

Una ejecución histórica solo puede utilizar información disponible en la fecha de decisión.

---

## Regla 4 — Determinismo

Con:

```text
misma data
+
mismos supuestos
+
misma versión del modelo
```

debe producirse:

```text
mismo resultado
```

---

## Regla 5 — Trazabilidad

Todo resultado importante debe poder seguirse:

```text
SOURCE
  ↓
RAW DATA
  ↓
NORMALIZED DATA
  ↓
METRIC
  ↓
ASSUMPTION
  ↓
VALUATION
  ↓
INTERPRETATION
```

---

## Regla 6 — La IA no modifica la realidad financiera

La IA puede:

* interpretar
* resumir
* detectar relaciones
* plantear preguntas
* identificar riesgos
* revisar supuestos

Pero no puede alterar silenciosamente:

* EPS
* FCF
* deuda
* shares
* fair value
* expected return
* scores

---

# 20. Plan de ejecución recomendado

No implementar todo simultáneamente.

## Sprint 1

```text
M1 → Repository
M2 → Database
```

Resultado:

> Tenemos una aplicación Python con una base SQLite correctamente estructurada.

---

## Sprint 2

```text
M3 → Data ingestion
M4 → Metrics
```

Resultado:

> Podemos introducir una empresa y obtener sus principales métricas financieras.

---

## Sprint 3

```text
M5 → Valuation
```

Resultado:

> Podemos introducir una empresa y obtener Bear/Base/Bull, fair value, expected return y precios de compra.

---

## Sprint 4

```text
M6 → Quality / Value / Risk
M8 → Radar
```

Resultado:

> El sistema puede buscar y filtrar oportunidades.

---

## Sprint 5

```text
M7 → Portfolio
```

Resultado:

> El sistema puede analizar las inversiones personales.

---

## Sprint 6

```text
M9 → Automation
M11 → Telegram
```

Resultado:

> El sistema funciona automáticamente y comunica cambios relevantes.

---

## Sprint 7

```text
M10 → AI
M12 → Dashboard
```

Resultado:

> Tenemos la capa de análisis cualitativo y una interfaz usable.

---

## Sprint 8

```text
M13 → Backtesting
M14 → Hardening
```

Resultado:

> Podemos evaluar históricamente la metodología y dejar el sistema preparado para uso continuo.

---

# 21. Control de desviaciones

Cualquier cambio respecto a `PROJECT_PLAN.md`, `VALUATION_METHOD.md`, `DATA_SOURCES.md` o `ARCHITECTURE.md` debe registrarse aquí.

| Fecha | Cambio | Motivo | Impacto | Aprobado |
| ----- | ------ | ------ | ------- | -------- |
| —     | —      | —      | —       | —        |

No modificar silenciosamente la arquitectura.

---

# 22. Estado actual del proyecto

### Completado

```text
[████████████████████] Documentación conceptual
```

### Siguiente objetivo

```text
[                    ] M1 — Repository & technical scaffold
```

### Próximo entregable

El siguiente paso de implementación será crear:

```text
value-investing-system/
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
├── PROJECT_PLAN.md
├── VALUATION_METHOD.md
├── DATA_SOURCES.md
├── ARCHITECTURE.md
├── TODO.md
├── CHANGELOG.md
├── src/
├── tests/
├── scripts/
├── dashboard/
├── config/
└── .github/
    └── workflows/
```

A partir de este punto, cada incremento del proyecto deberá actualizar el estado de este `TODO.md`.

---

# 23. Principio rector

El sistema debe responder de forma reproducible a cinco preguntas:

1. **¿Qué estoy comprando?**
2. **¿Cuánto vale razonablemente?**
3. **¿Qué estoy pagando por ello?**
4. **¿Qué retorno espero si mis hipótesis son correctas?**
5. **¿Qué puede hacer que mi tesis sea incorrecta?**

La automatización debe reducir el trabajo repetitivo, no sustituir el juicio de inversión.

La arquitectura final debe permitir que el usuario pueda inspeccionar cualquier resultado y reconstruir cómo se obtuvo.
