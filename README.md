# Value Investing System

Automated, reproducible system for fundamental analysis, valuation, portfolio analysis and opportunity screening.

Current milestone: **M1 — technical scaffold**.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m src.pipeline.daily
pytest
```

Core rule: Python performs deterministic financial calculations; AI is an explanatory layer.
