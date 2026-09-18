# ARCHITECTURE.md

**Proyecto:** Sistema personal de análisis Value Investing
**Versión:** 1.0
**Estado:** Arquitectura inicial
**Fecha:** 18/09/2026

---

# 1. Objetivo

Construir un sistema modular capaz de:

* descargar datos financieros;
* almacenarlos históricamente;
* normalizarlos;
* calcular métricas;
* valorar empresas;
* analizar riesgos;
* detectar oportunidades;
* controlar una cartera personal;
* generar alertas;
* utilizar IA para análisis cualitativo;
* conservar el historial completo de cada análisis.

La arquitectura debe permitir sustituir proveedores y componentes sin reconstruir el sistema completo.

---

# 2. Principio arquitectónico

La arquitectura seguirá esta secuencia:

```text
FUENTES
   ↓
DATA INGESTION
   ↓
RAW DATA
   ↓
NORMALIZATION
   ↓
FINANCIAL METRICS
   ↓
VALUATION ENGINE
   ↓
RISK / QUALITY / VALUE
   ↓
PORTFOLIO
   ↓
AI ANALYSIS
   ↓
ALERT ENGINE
   ↓
TELEGRAM / DASHBOARD
```

La IA nunca será una dependencia necesaria para realizar los cálculos fundamentales.

---

# 3. Arquitectura por capas

## Capa 1 — Data Sources

Conectores independientes:

```text
EODHD
CNMV
SEC
yfinance
otros proveedores futuros
```

Cada proveedor tendrá su propio adaptador.

---

# 4. Capa 2 — Data Ingestion

Responsabilidad:

* descargar;
* validar;
* registrar;
* almacenar.

No realizará valoración.

Ejemplo:

```text
EODHD
   ↓
EODHDProvider
   ↓
Raw financial data
```

---

# 5. Capa 3 — Raw Data

Los datos originales se conservarán antes de transformarlos.

Esto permitirá:

* reproducir errores;
* auditar cambios;
* volver a procesar datos;
* cambiar reglas de normalización.

Nunca sobrescribiremos silenciosamente el dato original.

---

# 6. Capa 4 — Normalization

Convertirá datos heterogéneos en una estructura común.

Ejemplo:

```text
Proveedor A:
netIncome

Proveedor B:
net_income

Proveedor C:
NetIncome

                 ↓

Modelo interno:
net_income
```

También normalizará:

* monedas;
* unidades;
* fechas;
* periodos;
* acciones;
* dividendos;
* deuda;
* capex.

---

# 7. Capa 5 — Financial Metrics Engine

Calcula exclusivamente métricas financieras.

Ejemplos:

```text
EPS
EPS CAGR
P/E
EV
EV/EBITDA
FCF
FCF Yield
ROIC
ROE
Net Debt / EBITDA
Dividend Yield
Shareholder Yield
```

No generará opiniones.

---

# 8. Capa 6 — Normalized Earnings Engine

Módulo independiente.

Entrada:

```text
historial financiero
```

Salida:

```text
normalized_revenue
normalized_margin
normalized_ebit
normalized_net_income
normalized_eps
normalized_fcf
```

También calculará indicadores de ciclicidad.

---

# 9. Capa 7 — Valuation Engine

Será uno de los módulos centrales.

Métodos:

```text
PE
Normalized PE
FCF Yield
EV/EBITDA
DCF
DDM
P/B
P/TBV
SOTP
```

No todos los métodos se aplicarán a todas las empresas.

El tipo de empresa determinará qué métodos son relevantes.

---

# 10. Capa 8 — Scenario Engine

Construirá:

```text
BEAR
BASE
BULL
```

Cada escenario tendrá sus propios:

* ingresos;
* márgenes;
* EPS;
* FCF;
* crecimiento;
* múltiplo.

Resultado:

```text
fair_value_bear
fair_value_base
fair_value_bull
```

---

# 11. Capa 9 — Return Engine

Calcula:

```text
Expected Return
```

para diferentes horizontes y tasas objetivo.

Como mínimo:

```text
3 años
5 años
```

y:

```text
8%
10%
12%
15%
```

---

# 12. Capa 10 — Purchase Price Engine

Calcula el precio máximo que permite alcanzar cada rentabilidad objetivo.

Ejemplo:

```text
Price for 8%
Price for 10%
Price for 12%
Price for 15%
```

Esto será una función independiente para poder probarla matemáticamente.

---

# 13. Capa 11 — Quality Engine

Calcula:

```text
Quality Score
```

utilizando las variables definidas en `VALUATION_METHOD.md`.

El resultado debe ser explicable:

```text
ROIC             18/20
Balance          17/20
FCF              16/20
Growth            9/15
Margins          14/15
Moat              8/10
----------------------
TOTAL             82/100
```

---

# 14. Capa 12 — Risk Engine

Calcula:

```text
Risk Score
```

y señales específicas:

```text
Debt Risk
Cyclicality Risk
Dilution Risk
Liquidity Risk
Business Risk
Valuation Risk
```

---

# 15. Capa 13 — Value Trap Engine

No producirá un simple score.

Generará señales explicables:

```text
LOW
MEDIUM
HIGH
```

y las razones.

Ejemplo:

```text
VALUE TRAP WARNING

- EPS 2026 está 31% por encima de media 5Y
- margen EBITDA en máximo histórico
- deuda creciente
- FCF deteriorándose

Confidence: MEDIUM
```

---

# 16. Capa 14 — Opportunity Engine

Combinará:

```text
Quality
Value
Risk
Expected Return
Margin of Safety
Value Trap
```

para identificar oportunidades.

No será simplemente:

```text
sort by PE
```

---

# 17. Capa 15 — Portfolio Engine

Gestionará:

```text
Holdings
Transactions
Dividends
Cash
Fees
Currency
Portfolio weights
Cost basis
Realized gains
Unrealized gains
```

También almacenará la tesis de cada inversión.

---

# 18. Capa 16 — Thesis Engine

Cada inversión tendrá una estructura:

```text
Investment Thesis
    ↓
Hypotheses
    ↓
Expected outcomes
    ↓
Invalidation criteria
```

El sistema podrá comprobar si se cumplen.

---

# 19. Capa 17 — Event Engine

Detectará acontecimientos:

```text
Earnings
Guidance
Profit warning
Dividend change
Buyback
Capital increase
Acquisition
Debt change
Large EPS revision
Large price movement
```

No todos los acontecimientos generarán una alerta.

---

# 20. Capa 18 — AI Analyst

La IA entra aquí.

Nunca antes.

Recibirá datos estructurados procedentes de las capas anteriores.

Ejemplo:

```text
Financial Metrics
        +
Valuation
        +
Risk
        +
News
        ↓
      AI
```

---

# 21. Agentes IA

La primera arquitectura de agentes será:

```text
                    ┌───────────────┐
                    │ Financial     │
                    │ Analyst       │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          ↓                 ↓                 ↓
     Business           Valuation           Risk
     Analyst             Analyst            Analyst
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ↓
                    Investment Review
```

Un agente de noticias podrá funcionar de forma paralela.

---

# 22. Financial Analyst

Analizará:

* resultados;
* evolución financiera;
* márgenes;
* deuda;
* FCF;
* anomalías.

Su función será explicar:

**qué ha cambiado.**

---

# 23. Business Analyst

Analizará:

* modelo de negocio;
* competencia;
* moat;
* pricing power;
* crecimiento;
* reinversión;
* estructura competitiva.

Su función será explicar:

**por qué puede o no puede continuar creciendo el negocio.**

---

# 24. Valuation Analyst

Recibirá los cálculos realizados por Python.

No recalculará libremente las cifras.

Su función será:

* revisar supuestos;
* detectar inconsistencias;
* comparar métodos;
* explicar divergencias.

---

# 25. Risk Analyst

Buscará:

* riesgos financieros;
* riesgos operativos;
* riesgos regulatorios;
* concentración;
* deuda;
* dilución;
* riesgos de ejecución.

---

# 26. News Analyst

Procesará:

* resultados;
* comunicados;
* noticias;
* filings;
* cambios de guidance.

Su objetivo será identificar:

**información nueva material para la tesis.**

---

# 27. Investment Review Agent

Será el último agente.

Recibirá:

```text
Financial Analyst
Business Analyst
Valuation Analyst
Risk Analyst
News Analyst
```

y generará:

```text
Investment Review
```

Pero no podrá modificar los datos financieros.

---

# 28. Base de datos

MVP:

**SQLite**

Razones:

* cero configuración;
* un único archivo;
* SQL completo;
* transacciones ACID;
* suficiente para nuestro volumen inicial;
* fácil de copiar y respaldar.

SQLite es un motor embebido y serverless, por lo que no necesitamos mantener un servidor de base de datos durante el MVP.

---

# 29. Migración futura

Si el sistema crece considerablemente:

```text
SQLite
   ↓
PostgreSQL
```

El código de acceso a datos estará abstraído para permitir esta migración.

---

# 30. Esquema conceptual de base de datos

Tablas principales:

```text
companies
securities
prices
financials
cash_flows
balance_sheets
shares
dividends
estimates
estimate_revisions
corporate_actions
valuations
scenarios
risk_scores
quality_scores
value_scores
portfolio_transactions
portfolio_positions
investment_theses
alerts
analysis_runs
sources
```

---

# 31. Tabla companies

Campos principales:

```text
company_id
name
ticker
isin
country
sector
industry
currency
exchange
status
```

---

# 32. Tabla financials

Campos principales:

```text
company_id
period_end
filing_date
period_type
currency
revenue
ebitda
ebit
net_income
eps
shares
source_id
```

---

# 33. Tabla cash_flows

```text
company_id
period_end
filing_date
cfo
capex
fcf
source_id
```

---

# 34. Tabla balance_sheets

```text
company_id
period_end
filing_date
cash
debt
net_debt
equity
assets
source_id
```

---

# 35. Tabla estimates

```text
company_id
observation_date
fiscal_period
eps_estimate
revenue_estimate
ebitda_estimate
fcf_estimate
analyst_count
source_id
```

---

# 36. Tabla valuations

Cada análisis será histórico.

```text
valuation_id
company_id
analysis_date
model_version
price
eps
normalized_eps
fair_value_bear
fair_value_base
fair_value_bull
expected_return
price_8
price_10
price_12
price_15
```

---

# 37. Tabla analysis_runs

Permitirá reproducir cualquier análisis.

```text
run_id
timestamp
model_version
data_version
company_id
status
execution_time
error
```

---

# 38. Tabla sources

```text
source_id
provider
url
retrieved_at
publication_date
document_type
confidence
```

---

# 39. GitHub

Repositorio principal:

```text
value-investing-system
```

Estructura:

```text
value-investing-system/
│
├── README.md
├── PROJECT_PLAN.md
├── VALUATION_METHOD.md
├── DATA_SOURCES.md
├── ARCHITECTURE.md
├── CHANGELOG.md
├── TODO.md
│
├── src/
│   ├── data/
│   ├── normalization/
│   ├── metrics/
│   ├── valuation/
│   ├── scoring/
│   ├── portfolio/
│   ├── events/
│   ├── ai/
│   └── alerts/
│
├── tests/
│
├── scripts/
│
├── dashboard/
│
├── config/
│
└── .github/
    └── workflows/
```

---

# 40. Data directory

Los datos descargados no se mezclarán indiscriminadamente con el código.

```text
data/
├── raw/
├── processed/
├── snapshots/
└── exports/
```

Los datos sensibles de la cartera nunca deberán publicarse en un repositorio público.

---

# 41. GitHub Actions

Tendremos varios workflows.

```text
daily_market.yml
weekly_screening.yml
quarterly_review.yml
data_validation.yml
tests.yml
```

---

# 42. Daily Market Workflow

Frecuencia:

**diaria en días de mercado.**

Proceso:

```text
1. Descargar precios
2. Descargar nuevos datos
3. Actualizar base
4. Calcular cambios
5. Recalcular cartera
6. Detectar eventos
7. Ejecutar alertas
8. Generar resumen
```

---

# 43. Weekly Screening Workflow

Una vez por semana:

```text
1. Actualizar universo
2. Recalcular fundamentales
3. Valorar empresas
4. Ejecutar Quality Score
5. Ejecutar Value Score
6. Ejecutar Risk Score
7. Detectar oportunidades
8. Generar ranking
```

---

# 44. Quarterly Review Workflow

Después de resultados:

```text
1. Descargar filings
2. Actualizar financieros
3. Actualizar estimaciones
4. Recalcular valoración
5. Revisar tesis
6. Detectar cambios estructurales
7. Generar informes
```

---

# 45. Tests Workflow

Cada modificación del código deberá ejecutar:

```text
unit tests
data tests
valuation tests
integration tests
```

No se permitirá desplegar código con tests críticos fallando.

---

# 46. GitHub Actions y horarios

GitHub Actions permite ejecutar workflows programados mediante cron y admite zonas horarias IANA. Los workflows programados se ejecutan sobre la rama por defecto.

Para el proyecto utilizaremos horarios deliberadamente alejados del minuto exacto para reducir el riesgo de retrasos por carga de GitHub.

---

# 47. Ejecución local

Todo workflow deberá poder ejecutarse también localmente.

Ejemplo:

```bash
python -m src.pipeline.daily
```

Esto es obligatorio para poder depurar.

---

# 48. Dashboard

Primera interfaz:

**Streamlit**

Pantallas:

```text
Dashboard
Radar
Company
Portfolio
Alerts
History
```

Streamlit permite construir aplicaciones interactivas directamente desde Python y proporciona widgets, tablas y gráficos sin necesidad de desarrollar inicialmente un frontend separado.

---

# 49. Dashboard — Home

Mostrará:

```text
Portfolio Return
Expected Portfolio Return
Cash
Number of Holdings
New Opportunities
Thesis Alerts
Risk Alerts
```

---

# 50. Dashboard — Radar

Tabla:

```text
Company
Price
Quality
Value
Risk
Expected Return
Fair Value
Margin of Safety
Value Trap
```

Filtros:

* país;
* sector;
* score;
* retorno esperado;
* riesgo;
* market cap.

---

# 51. Dashboard — Company

Página individual:

```text
Price
Financials
Valuation
Scenarios
Risk
Quality
News
Thesis
Historical analyses
```

---

# 52. Dashboard — Portfolio

Mostrar:

```text
Position
Weight
Cost
Current Value
Gain/Loss
Dividends
Fair Value
Expected Return
Thesis Status
```

---

# 53. Telegram

Será el canal de alertas inicial.

No se enviará cada cambio de precio.

Solo:

```text
material events
opportunities
thesis changes
portfolio risks
weekly reports
```

---

# 54. Sistema de alertas

Todas las alertas pasarán por:

```text
Alert Engine
```

que decidirá:

```text
¿Es material?
   ↓
NO → guardar
   ↓
SÍ → notificar
```

---

# 55. Secrets

Nunca se almacenarán en Git:

```text
API keys
Telegram token
LLM API key
broker credentials
```

Se utilizarán variables de entorno y secrets de GitHub Actions.

---

# 56. Broker

Inicialmente:

**NO habrá conexión automática con el broker.**

La cartera se introducirá mediante:

* CSV;
* formulario;
* archivo de configuración;
* posteriormente API del broker.

No queremos introducir riesgo operativo innecesario en el MVP.

---

# 57. Separación de cartera

La información de cartera tendrá dos niveles:

### Código

Público si se desea.

### Datos

Privados.

Ejemplo:

```text
portfolio_private/
```

Nunca se subirá al repositorio público.

---

# 58. Flujo diario completo

```text
06:00
  ↓
Data ingestion
  ↓
Validation
  ↓
Database update
  ↓
Financial metrics
  ↓
Portfolio update
  ↓
Event detection
  ↓
Opportunity detection
  ↓
AI analysis SOLO si es necesario
  ↓
Alert engine
  ↓
Telegram
```

---

# 59. Flujo semanal

```text
Weekend
   ↓
Full universe scan
   ↓
Valuation
   ↓
Quality
   ↓
Value
   ↓
Risk
   ↓
Value Trap
   ↓
Opportunity ranking
   ↓
AI review
   ↓
Weekly report
```

---

# 60. Principio de coste

No utilizaremos IA para tareas que Python pueda realizar mejor.

Ejemplo:

Incorrecto:

```text
LLM → calcular PER
```

Correcto:

```text
Python → calcular PER
LLM → explicar si el PER es razonable
```

Esto reducirá:

* coste;
* errores;
* latencia;
* alucinaciones.

---

# 61. Principio de determinismo

El siguiente resultado debe ser reproducible:

```text
mismos datos
+
mismos supuestos
+
misma versión
=
mismo resultado
```

---

# 62. Versionado

Cada análisis incluirá:

```text
data_version
model_version
code_commit
timestamp
```

Así podremos reconstruir el análisis.

---

# 63. Gestión de errores

Si una API falla:

```text
Provider unavailable
```

el sistema:

1. registra el error;
2. intenta fallback;
3. marca los datos afectados;
4. evita producir una valoración falsa;
5. notifica si el problema es material.

---

# 64. Regla de "no valuation"

Si faltan datos críticos:

```text
VALUATION STATUS:
INSUFFICIENT DATA
```

No:

```text
VALUE = 74.23 €
```

---

# 65. Backtesting

El backtester será independiente del sistema operativo.

Entrada:

```text
date
universe
historical data
historical estimates
model version
```

Salida:

```text
signals
portfolio
returns
drawdown
volatility
Sharpe
Sortino
```

---

# 66. Point-in-time data

El backtester nunca podrá acceder a datos posteriores a la fecha de decisión.

Conceptualmente:

```text
                TIME
────────────────────────────────────→

Decision
   ↑
   │
Datos disponibles
   │
   X
No se permite información posterior
```

---

# 67. Futuro cambio a PostgreSQL

No se realizará hasta que exista una razón real:

* demasiados datos;
* múltiples usuarios;
* concurrencia;
* dashboard persistente en cloud;
* ejecución distribuida.

Mientras tanto:

**SQLite.**

---

# 68. Principio de simplicidad

La arquitectura inicial deberá poder ejecutarse:

```text
en un ordenador personal
```

y también:

```text
en GitHub Actions
```

sin modificar la lógica financiera.

---

# 69. Resultado final de arquitectura

```text
                         ┌─────────────┐
                         │ CNMV / SEC  │
                         └──────┬──────┘
                                │
┌───────────┐           ┌──────┴──────┐
│ EODHD     │──────────→│ DATA ENGINE │
└───────────┘           └──────┬──────┘
                                ↓
                        ┌───────────────┐
                        │ NORMALIZATION │
                        └───────┬───────┘
                                ↓
                    ┌──────────────────────┐
                    │ FINANCIAL METRICS    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ VALUATION ENGINE     │
                    └──────────┬───────────┘
                               ↓
             ┌─────────────────┼─────────────────┐
             ↓                 ↓                 ↓
         QUALITY             VALUE             RISK
             └─────────────────┼─────────────────┘
                               ↓
                       ┌───────────────┐
                       │ OPPORTUNITY   │
                       └───────┬───────┘
                               ↓
                       ┌───────────────┐
                       │ PORTFOLIO     │
                       └───────┬───────┘
                               ↓
                    ┌────────────────────┐
                    │ AI ANALYSTS         │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ ALERT ENGINE        │
                    └─────────┬──────────┘
                              ↓
                     ┌────────┴────────┐
                     ↓                 ↓
                 TELEGRAM          STREAMLIT
```

---

# 70. Regla arquitectónica definitiva

**El núcleo financiero no dependerá de la IA.**

Si mañana eliminamos completamente la IA del proyecto, deberá seguir siendo capaz de:

* descargar datos;
* calcular ratios;
* valorar empresas;
* calcular precios de compra;
* analizar la cartera;
* detectar oportunidades;
* generar alertas cuantitativas.

La IA será una **capa adicional de inteligencia cualitativa**, no el fundamento del sistema.
