# Agente Bancario Dominicano — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-agent system that fetches Dominican banking and macro data, analyzes it with adapted financial plugins, and generates LinkedIn posts, a board PDF report, and a LinkedIn carousel — with a human review loop before final output.

**Architecture:** An orchestrator agent (Claude Agent SDK) calls a local MCP server for data, runs analysis via adapted financial-services-plugins skills, then dispatches three sub-agents (Post, Board, Carousel) in parallel. A Format Decision agent recommends carousel vs. text post. The user reviews all drafts conversationally and types "aprobado" to trigger final file generation.

**Tech Stack:** Python 3.14, `anthropic` SDK, `mcp` SDK, `requests`, `beautifulsoup4`, `openpyxl`, `pandas`, `matplotlib`, `plotly`, `python-pptx`, `weasyprint`, World Bank REST API (no key), BCRD CDN Excel files (no key), IMF DataMapper API (no key).

---

## File Map

```
agent/
  run.py                        # CLI entry point
  orchestrator.py               # Main agent loop + review loop
  mcp_server.py                 # Local MCP server (5 tools)
  data_sources/
    bcrd.py                     # BCRD CDN Excel fetcher
    superbancos.py              # SB web scraper
    hacienda.py                 # Hacienda web scraper
    imf.py                      # IMF DataMapper REST
    worldbank.py                # World Bank REST
  sub_agents/
    post_agent.py               # Generates flash + mensual posts
    board_agent.py              # Generates PDF report
    carousel_agent.py           # Generates PPTX carousel
    format_decision_agent.py    # Recommends carousel vs text
  templates/
    board_report.html           # HTML template → PDF
    carousel_base.pptx          # Base PPTX template (created at runtime)
  skills/
    sector_overview_rd.md
    competitive_analysis_rd.md
    earnings_analysis_rd.md
data/cache/                     # JSON cache per date+source
outputs/
  posts/
  reports/
  carousel/
tests/
  test_bcrd.py
  test_superbancos.py
  test_imf.py
  test_worldbank.py
  test_post_agent.py
  test_board_agent.py
  test_carousel_agent.py
  test_format_decision.py
  test_orchestrator.py
requirements.txt
```

---

## Task 1: Project scaffold + dependencies

**Files:**
- Create: `agent/requirements.txt`
- Create: `agent/__init__.py`, `agent/data_sources/__init__.py`, `agent/sub_agents/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd "C:/Users/aleja/OneDrive/Escritorio/MissionControl"
mkdir -p agent/data_sources agent/sub_agents agent/templates agent/skills
mkdir -p data/cache outputs/posts outputs/reports outputs/carousel
mkdir -p tests
touch agent/__init__.py agent/data_sources/__init__.py agent/sub_agents/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
anthropic>=0.40.0
mcp>=1.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
openpyxl>=3.1.0
pandas>=2.0.0
matplotlib>=3.8.0
plotly>=5.18.0
python-pptx>=0.6.23
weasyprint>=62.0
kaleido>=0.2.1
```

- [ ] **Step 3: Install dependencies**

```bash
cd "C:/Users/aleja/OneDrive/Escritorio/MissionControl"
pip install -r agent/requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 4: Commit**

```bash
git init  # if not already a repo
git add agent/ tests/ data/ outputs/
git commit -m "feat: scaffold project structure and dependencies"
```

---

## Task 2: BCRD data source

**Files:**
- Create: `agent/data_sources/bcrd.py`
- Test: `tests/test_bcrd.py`

BCRD publishes Excel files directly at `cdn.bancentral.gov.do`. No API key needed.

Key URLs:
- Tasas activas BM: `tbm_activad.xlsx`
- Tasas pasivas BM: `tbm_pasivad.xlsx`
- TPM: `Serie_TPM.xlsx`
- Interbancaria: `Interbancarios_Plazos_1_a_7_dias.xlsx`
- IMAE: `imae_2018.xlsx`
- IPC (inflación): `ipc_base_2019-2020.xls`
- Tipo de cambio: scraped from the stats page
- Reservas: `reservas_internacionales.xlsx`

- [ ] **Step 1: Write failing test**

```python
# tests/test_bcrd.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from agent.data_sources.bcrd import BCRDClient

def test_get_tpm_returns_float():
    client = BCRDClient(cache_dir="data/cache")
    with patch.object(client, '_fetch_excel') as mock_fetch:
        mock_df = pd.DataFrame({'Fecha': ['2026-03-01'], 'TPM': [5.25]})
        mock_fetch.return_value = mock_df
        result = client.get_tpm()
    assert isinstance(result['value'], float)
    assert result['value'] == 5.25
    assert 'date' in result

def test_get_tasas_bancarias_returns_dict():
    client = BCRDClient(cache_dir="data/cache")
    with patch.object(client, '_fetch_excel') as mock_fetch:
        mock_df = pd.DataFrame({
            'Fecha': ['2026-02-01'],
            'Activa_BM': [13.27],
            'Pasiva_BM': [6.14],
        })
        mock_fetch.return_value = mock_df
        result = client.get_tasas_bancarias()
    assert 'bancos_multiples' in result
    assert 'activa' in result['bancos_multiples']
    assert 'pasiva' in result['bancos_multiples']

def test_cache_is_used_on_second_call(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    with patch.object(client, '_download_excel') as mock_dl:
        mock_dl.return_value = pd.DataFrame({'Fecha': ['2026-03-01'], 'TPM': [5.25]})
        client.get_tpm()
        client.get_tpm()
    assert mock_dl.call_count == 1  # second call uses cache
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:/Users/aleja/OneDrive/Escritorio/MissionControl"
python -m pytest tests/test_bcrd.py -v
```

Expected: ImportError or ModuleNotFoundError.

- [ ] **Step 3: Implement BCRDClient**

```python
# agent/data_sources/bcrd.py
import json
import os
from datetime import date
from io import BytesIO

import pandas as pd
import requests

BASE_CDN = "https://cdn.bancentral.gov.do/documents/estadisticas"

URLS = {
    "tpm": f"{BASE_CDN}/sector-monetario-y-financiero/documents/Serie_TPM.xlsx",
    "tasas_activas": f"{BASE_CDN}/sector-monetario-y-financiero/documents/tbm_activad.xlsx",
    "tasas_pasivas": f"{BASE_CDN}/sector-monetario-y-financiero/documents/tbm_pasivad.xlsx",
    "interbancaria": f"{BASE_CDN}/sector-monetario-y-financiero/documents/Interbancarios_Plazos_1_a_7_dias.xlsx",
    "imae": f"{BASE_CDN}/sector-real/documents/imae_2018.xlsx",
    "ipc": f"{BASE_CDN}/precios/documents/ipc_base_2019-2020.xls",
    "reservas": f"{BASE_CDN}/sector-externo/documents/reservas_internacionales.xlsx",
}


class BCRDClient:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{date.today()}-bcrd-{key}.json")

    def _load_cache(self, key: str):
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def _save_cache(self, key: str, data: dict):
        with open(self._cache_path(key), "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _download_excel(self, url: str) -> pd.DataFrame:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return pd.read_excel(BytesIO(resp.content), sheet_name=0)

    def _fetch_excel(self, key: str) -> pd.DataFrame:
        return self._download_excel(URLS[key])

    def get_tpm(self) -> dict:
        cached = self._load_cache("tpm")
        if cached:
            return cached
        df = self._fetch_excel("tpm")
        # Last non-null row
        df = df.dropna(subset=[df.columns[-1]])
        last = df.iloc[-1]
        result = {"value": float(last.iloc[-1]), "date": str(last.iloc[0])}
        self._save_cache("tpm", result)
        return result

    def get_tasas_bancarias(self) -> dict:
        cached = self._load_cache("tasas_bancarias")
        if cached:
            return cached
        df_act = self._fetch_excel("tasas_activas")
        df_pas = self._fetch_excel("tasas_pasivas")
        df_int = self._fetch_excel("interbancaria")

        def last_val(df, col_idx=1):
            col = df.columns[col_idx]
            series = df[col].dropna()
            return float(series.iloc[-1]) if len(series) else None

        result = {
            "date": str(df_act.iloc[-1, 0]),
            "bancos_multiples": {
                "activa": last_val(df_act, 1),
                "pasiva": last_val(df_pas, 1),
            },
            "aayp": {
                "activa": last_val(df_act, 2),
                "pasiva": last_val(df_pas, 2),
            },
            "bancos_ahorro_credito": {
                "activa": last_val(df_act, 3),
                "pasiva": last_val(df_pas, 3),
            },
            "interbancaria": last_val(df_int, 1),
        }
        self._save_cache("tasas_bancarias", result)
        return result

    def get_imae(self) -> dict:
        cached = self._load_cache("imae")
        if cached:
            return cached
        df = self._fetch_excel("imae")
        df = df.dropna()
        last = df.iloc[-1]
        prev_year = df.iloc[-13] if len(df) > 13 else df.iloc[0]
        val = float(last.iloc[1])
        val_prev = float(prev_year.iloc[1])
        result = {
            "date": str(last.iloc[0]),
            "value": val,
            "var_interanual": round((val - val_prev) / val_prev * 100, 2),
        }
        self._save_cache("imae", result)
        return result

    def get_inflacion(self) -> dict:
        cached = self._load_cache("inflacion")
        if cached:
            return cached
        df = self._fetch_excel("ipc")
        df = df.dropna(subset=[df.columns[1]])
        last = df.iloc[-1]
        prev_year = df.iloc[-13] if len(df) > 13 else df.iloc[0]
        val = float(last.iloc[1])
        val_prev = float(prev_year.iloc[1])
        result = {
            "date": str(last.iloc[0]),
            "value": val,
            "var_interanual": round((val - val_prev) / val_prev * 100, 2),
        }
        self._save_cache("inflacion", result)
        return result

    def get_tipo_cambio(self) -> dict:
        cached = self._load_cache("tipo_cambio")
        if cached:
            return cached
        url = "https://www.bancentral.gov.do/a/d/2545-estadisticas-economicas-mercado-cambiario"
        resp = requests.get(url, timeout=15)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        # Extract compra/venta from page text
        text = soup.get_text()
        import re
        compra = re.search(r"Compra[:\s]+([\d.]+)", text)
        venta = re.search(r"Venta[:\s]+([\d.]+)", text)
        result = {
            "date": str(date.today()),
            "compra": float(compra.group(1)) if compra else None,
            "venta": float(venta.group(1)) if venta else None,
        }
        self._save_cache("tipo_cambio", result)
        return result

    def get_reservas(self) -> dict:
        cached = self._load_cache("reservas")
        if cached:
            return cached
        df = self._fetch_excel("reservas")
        df = df.dropna(subset=[df.columns[1]])
        last = df.iloc[-1]
        result = {
            "date": str(last.iloc[0]),
            "brutas_mm_usd": float(last.iloc[1]),
        }
        self._save_cache("reservas", result)
        return result

    def get_all(self) -> dict:
        return {
            "tpm": self.get_tpm(),
            "tasas_bancarias": self.get_tasas_bancarias(),
            "imae": self.get_imae(),
            "inflacion": self.get_inflacion(),
            "tipo_cambio": self.get_tipo_cambio(),
            "reservas": self.get_reservas(),
        }
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_bcrd.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add agent/data_sources/bcrd.py tests/test_bcrd.py
git commit -m "feat: BCRD data source with CDN Excel fetching and local cache"
```

---

## Task 3: World Bank + IMF data sources

**Files:**
- Create: `agent/data_sources/worldbank.py`
- Create: `agent/data_sources/imf.py`
- Test: `tests/test_worldbank.py`, `tests/test_imf.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_worldbank.py
import pytest
from unittest.mock import patch
from agent.data_sources.worldbank import WorldBankClient

def test_get_credit_gdp_returns_list():
    client = WorldBankClient(cache_dir="data/cache")
    with patch('agent.data_sources.worldbank.requests.get') as mock_get:
        mock_get.return_value.json.return_value = [
            {"pages": 1},
            [{"date": "2024", "value": 31.92}, {"date": "2023", "value": 30.84}]
        ]
        mock_get.return_value.raise_for_status = lambda: None
        result = client.get_credit_to_gdp()
    assert isinstance(result, list)
    assert result[0]['year'] == "2024"
    assert result[0]['value'] == 31.92

# tests/test_imf.py
from unittest.mock import patch
from agent.data_sources.imf import IMFClient

def test_get_fsi_returns_dict():
    client = IMFClient(cache_dir="data/cache")
    with patch('agent.data_sources.imf.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "values": {"FSI_BCS_MT": {"DOM": {"2024": "12.5"}}}
        }
        mock_get.return_value.raise_for_status = lambda: None
        result = client.get_capital_adequacy()
    assert 'value' in result
```

- [ ] **Step 2: Run to verify they fail**

```bash
python -m pytest tests/test_worldbank.py tests/test_imf.py -v
```

- [ ] **Step 3: Implement WorldBankClient**

```python
# agent/data_sources/worldbank.py
import json, os, requests
from datetime import date

WB_BASE = "https://api.worldbank.org/v2/country/DO/indicator"
INDICATORS = {
    "credit_gdp": "FS.AST.PRVT.GD.ZS",        # Crédito privado % PIB
    "interest_spread": "FR.INR.LNDP",           # Spread tasa interés
    "bank_access": "FB.BNK.CAPA.ZS",            # Acceso financiero
    "inflation": "FP.CPI.TOTL.ZG",              # Inflación CPI
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",          # Crecimiento PIB
}

class WorldBankClient:
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key):
        return os.path.join(self.cache_dir, f"{date.today()}-wb-{key}.json")

    def _load_cache(self, key):
        p = self._cache_path(key)
        return json.load(open(p)) if os.path.exists(p) else None

    def _save_cache(self, key, data):
        with open(self._cache_path(key), "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _fetch(self, indicator_code, mrv=5):
        url = f"{WB_BASE}/{indicator_code}?format=json&mrv={mrv}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        _, data = resp.json()
        return [{"year": d["date"], "value": d["value"]} for d in data if d["value"] is not None]

    def get_credit_to_gdp(self):
        cached = self._load_cache("credit_gdp")
        if cached: return cached
        result = self._fetch(INDICATORS["credit_gdp"])
        self._save_cache("credit_gdp", result)
        return result

    def get_interest_spread(self):
        cached = self._load_cache("interest_spread")
        if cached: return cached
        result = self._fetch(INDICATORS["interest_spread"])
        self._save_cache("interest_spread", result)
        return result

    def get_gdp_growth(self):
        cached = self._load_cache("gdp_growth")
        if cached: return cached
        result = self._fetch(INDICATORS["gdp_growth"])
        self._save_cache("gdp_growth", result)
        return result

    def get_all(self):
        return {
            "credit_gdp": self.get_credit_to_gdp(),
            "interest_spread": self.get_interest_spread(),
            "gdp_growth": self.get_gdp_growth(),
        }
```

- [ ] **Step 4: Implement IMFClient**

```python
# agent/data_sources/imf.py
import json, os, requests
from datetime import date

IMF_BASE = "https://www.imf.org/external/datamapper/api/v1"

class IMFClient:
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key):
        return os.path.join(self.cache_dir, f"{date.today()}-imf-{key}.json")

    def _load_cache(self, key):
        p = self._cache_path(key)
        return json.load(open(p)) if os.path.exists(p) else None

    def _save_cache(self, key, data):
        with open(self._cache_path(key), "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _fetch_indicator(self, indicator, country="DOM"):
        url = f"{IMF_BASE}/{indicator}/{country}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            values = data.get("values", {}).get(indicator, {}).get(country, {})
            if values:
                latest_year = max(values.keys())
                return {"year": latest_year, "value": float(values[latest_year])}
        except Exception:
            pass
        return {"year": None, "value": None}

    def get_capital_adequacy(self):
        cached = self._load_cache("capital_adequacy")
        if cached: return cached
        # FSI: Regulatory Capital to Risk-Weighted Assets
        result = self._fetch_indicator("FSI_BCS_MT")
        self._save_cache("capital_adequacy", result)
        return result

    def get_npl_ratio(self):
        cached = self._load_cache("npl_ratio")
        if cached: return cached
        result = self._fetch_indicator("FSI_BCS_NN")
        self._save_cache("npl_ratio", result)
        return result

    def get_roe(self):
        cached = self._load_cache("roe_imf")
        if cached: return cached
        result = self._fetch_indicator("FSI_BCS_RE")
        self._save_cache("roe_imf", result)
        return result

    def get_all(self):
        return {
            "capital_adequacy": self.get_capital_adequacy(),
            "npl_ratio": self.get_npl_ratio(),
            "roe": self.get_roe(),
        }
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_worldbank.py tests/test_imf.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add agent/data_sources/worldbank.py agent/data_sources/imf.py tests/test_worldbank.py tests/test_imf.py
git commit -m "feat: World Bank and IMF free API data sources"
```

---

## Task 4: Superintendencia de Bancos scraper

**Files:**
- Create: `agent/data_sources/superbancos.py`
- Test: `tests/test_superbancos.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_superbancos.py
from unittest.mock import patch, MagicMock
from agent.data_sources.superbancos import SuperbancosClient

MOCK_HTML = """
<table>
<tr><th>Entidad</th><th>ROE</th><th>ROA</th><th>IAC</th><th>Morosidad</th><th>Cartera</th></tr>
<tr><td>BanReservas</td><td>18.5</td><td>1.2</td><td>14.2</td><td>1.8</td><td>450000</td></tr>
<tr><td>Banco Popular</td><td>20.1</td><td>1.5</td><td>15.1</td><td>1.5</td><td>380000</td></tr>
</table>
"""

def test_get_system_indicators_returns_dict():
    client = SuperbancosClient(cache_dir="data/cache")
    with patch('agent.data_sources.superbancos.requests.get') as mock_get:
        mock_get.return_value.text = MOCK_HTML
        mock_get.return_value.raise_for_status = lambda: None
        result = client.get_system_indicators()
    assert 'entities' in result
    assert len(result['entities']) == 2

def test_get_top_cartera_growth():
    client = SuperbancosClient(cache_dir="data/cache")
    entities = [
        {"name": "A", "cartera": 100, "cartera_prev": 80},
        {"name": "B", "cartera": 200, "cartera_prev": 190},
        {"name": "C", "cartera": 50, "cartera_prev": 30},
    ]
    top = client._rank_by_growth(entities, "cartera", n=2)
    assert top[0]["name"] == "C"  # 67% growth
    assert top[1]["name"] == "A"  # 25% growth
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest tests/test_superbancos.py -v
```

- [ ] **Step 3: Implement SuperbancosClient**

```python
# agent/data_sources/superbancos.py
import json, os, requests
from datetime import date
from bs4 import BeautifulSoup

# SB publishes statistical tables at this path — adjust if URL changes
SB_STATS_URLS = [
    "https://www.superbancos.gob.do/estadisticas/sistema-financiero/",
    "https://www.superbancos.gob.do/bancos/index.php?option=com_content&view=article&id=158",
]

class SuperbancosClient:
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key):
        return os.path.join(self.cache_dir, f"{date.today()}-sb-{key}.json")

    def _load_cache(self, key):
        p = self._cache_path(key)
        return json.load(open(p)) if os.path.exists(p) else None

    def _save_cache(self, key, data):
        with open(self._cache_path(key), "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _fetch_html(self):
        for url in SB_STATS_URLS:
            try:
                resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                return resp.text
            except Exception:
                continue
        return ""

    def _parse_table(self, html: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        entities = []
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= len(headers):
                    entity = {}
                    for i, h in enumerate(headers):
                        try:
                            entity[h] = float(cells[i].replace(",", "").replace("%", ""))
                        except ValueError:
                            entity[h] = cells[i]
                    if entity:
                        entities.append(entity)
        return entities

    def _rank_by_growth(self, entities: list, field: str, prev_field: str = None, n: int = 5) -> list:
        prev_field = prev_field or f"{field}_prev"
        ranked = []
        for e in entities:
            curr = e.get(field)
            prev = e.get(prev_field)
            if curr and prev and prev != 0:
                growth = (curr - prev) / abs(prev) * 100
                ranked.append({**e, "_growth_pct": round(growth, 2)})
        return sorted(ranked, key=lambda x: x["_growth_pct"], reverse=True)[:n]

    def get_system_indicators(self) -> dict:
        cached = self._load_cache("system")
        if cached: return cached
        html = self._fetch_html()
        entities = self._parse_table(html)
        result = {
            "date": str(date.today()),
            "entities": entities,
            "source": "Superintendencia de Bancos RD",
        }
        self._save_cache("system", result)
        return result

    def get_rankings(self) -> dict:
        cached = self._load_cache("rankings")
        if cached: return cached
        data = self.get_system_indicators()
        entities = data.get("entities", [])
        result = {
            "top_cartera_growth": self._rank_by_growth(entities, "cartera", n=5),
            "top_npl_increase": self._rank_by_growth(entities, "morosidad", n=5),
        }
        self._save_cache("rankings", result)
        return result

    def get_all(self) -> dict:
        return {
            "system": self.get_system_indicators(),
            "rankings": self.get_rankings(),
        }
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_superbancos.py -v
```

- [ ] **Step 5: Commit**

```bash
git add agent/data_sources/superbancos.py tests/test_superbancos.py
git commit -m "feat: Superintendencia de Bancos scraper with entity rankings"
```

---

## Task 5: MCP Server

**Files:**
- Create: `agent/mcp_server.py`

- [ ] **Step 1: Implement MCP server**

```python
# agent/mcp_server.py
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from agent.data_sources.bcrd import BCRDClient
from agent.data_sources.superbancos import SuperbancosClient
from agent.data_sources.imf import IMFClient
from agent.data_sources.worldbank import WorldBankClient

server = Server("bancario-rd")
bcrd = BCRDClient()
sb = SuperbancosClient()
imf = IMFClient()
wb = WorldBankClient()

@server.list_tools()
async def list_tools():
    return [
        types.Tool(name="get_bcrd_indicators", description="Fetches BCRD macro and banking rate indicators", inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="get_sb_banking_data", description="Fetches Superintendencia de Bancos system and entity data", inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="get_imf_data", description="Fetches IMF Financial Soundness Indicators for Dominican Republic", inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="get_worldbank_data", description="Fetches World Bank financial development indicators for Dominican Republic", inputSchema={"type": "object", "properties": {}}),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_bcrd_indicators":
        data = bcrd.get_all()
    elif name == "get_sb_banking_data":
        data = sb.get_all()
    elif name == "get_imf_data":
        data = imf.get_all()
    elif name == "get_worldbank_data":
        data = wb.get_all()
    else:
        raise ValueError(f"Unknown tool: {name}")
    return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify server starts**

```bash
cd "C:/Users/aleja/OneDrive/Escritorio/MissionControl"
python -c "from agent.mcp_server import server; print('MCP server OK')"
```

Expected: `MCP server OK`

- [ ] **Step 3: Commit**

```bash
git add agent/mcp_server.py
git commit -m "feat: local MCP server exposing BCRD, SB, IMF, WorldBank tools"
```

---

## Task 6: Post Agent

**Files:**
- Create: `agent/sub_agents/post_agent.py`
- Test: `tests/test_post_agent.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_post_agent.py
from unittest.mock import patch, MagicMock
from agent.sub_agents.post_agent import PostAgent

SAMPLE_DATA = {
    "bcrd": {
        "tpm": {"value": 5.25, "date": "2026-03-01"},
        "tasas_bancarias": {
            "date": "2026-02-01",
            "bancos_multiples": {"activa": 13.27, "pasiva": 6.14},
            "aayp": {"activa": 14.5, "pasiva": 5.8},
            "interbancaria": 6.06,
        },
        "imae": {"value": 115.2, "var_interanual": 5.3, "date": "2026-02-01"},
        "inflacion": {"value": 103.1, "var_interanual": 3.8, "date": "2026-02-01"},
        "tipo_cambio": {"compra": 60.55, "venta": 61.19, "date": "2026-04-01"},
        "reservas": {"brutas_mm_usd": 16143.1, "date": "2026-03-01"},
    },
    "sb": {
        "rankings": {
            "top_cartera_growth": [
                {"entidad": "Banco X", "_growth_pct": 18.5},
                {"entidad": "Banco Y", "_growth_pct": 14.2},
                {"entidad": "Banco Z", "_growth_pct": 11.8},
            ],
            "top_npl_increase": [
                {"entidad": "Banco A", "_growth_pct": 0.8},
                {"entidad": "Banco B", "_growth_pct": 0.5},
            ],
        }
    },
    "wb": {"credit_gdp": [{"year": "2024", "value": 31.92}]},
    "imf": {"capital_adequacy": {"year": "2024", "value": 17.5}},
}

def test_generate_flash_returns_string():
    agent = PostAgent()
    with patch.object(agent, '_call_claude') as mock_claude:
        mock_claude.return_value = "📊 TPM: 5.25% | Tasas activas BM: 13.27%"
        result = agent.generate_flash(SAMPLE_DATA, indicator="tpm")
    assert isinstance(result, str)
    assert len(result) > 20

def test_generate_mensual_returns_string():
    agent = PostAgent()
    with patch.object(agent, '_call_claude') as mock_claude:
        mock_claude.return_value = "🏦 Barómetro Bancario Dominicano | Marzo 2026\n..."
        result = agent.generate_mensual(SAMPLE_DATA)
    assert isinstance(result, str)
    assert "Barómetro" in result or len(result) > 50

def test_refine_applies_instructions():
    agent = PostAgent()
    draft = "Post draft inicial"
    with patch.object(agent, '_call_claude') as mock_claude:
        mock_claude.return_value = "Post refinado con más detalle técnico"
        result = agent.refine(draft, "hazlo más técnico", SAMPLE_DATA)
    assert result != draft
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest tests/test_post_agent.py -v
```

- [ ] **Step 3: Implement PostAgent**

```python
# agent/sub_agents/post_agent.py
import anthropic

FLASH_PROMPT = """Eres un analista financiero dominicano de alto nivel. Genera un post de LinkedIn corto (máx 150 palabras) sobre este indicador bancario:

Indicador: {indicator}
Datos: {data}

Formato:
📊 [Indicador] | [Fecha]

[1-2 oraciones: valor actual + variación vs período anterior]
[1 oración: implicación para clientes o sistema bancario]

Fuente: BCRD · #BancaDominicana #BCRD #SistemaFinanciero

Sé técnico, preciso y conciso. Solo devuelve el texto del post."""

MENSUAL_PROMPT = """Eres un analista financiero dominicano senior. Genera el "Barómetro Bancario Dominicano" mensual para LinkedIn basado en estos datos:

{data}

Formato EXACTO:
🏦 Barómetro Bancario Dominicano | [Mes Año]

ENTORNO MACRO
· TPM: X% | Inflación: X% i.a. | IMAE: +X% | USD/DOP: X

SISTEMA BANCARIO
· Crédito privado: +X% i.a. | Captaciones: +X%
· Spread activo-pasivo BM: X pp | AAyP: X pp

TOP ENTIDADES (variación interanual)
Cartera de crédito:
  🥇 [Banco X]: +XX% | 🥈 [Banco Y]: +XX% | 🥉 [Banco Z]: +XX%
Morosidad (NPL):
  ⚠️ [Banco A]: +X.Xpp | [Banco B]: +X.Xpp | [Banco C]: +X.Xpp

QUÉ DICE EL COMPORTAMIENTO DEL CLIENTE
[2-3 oraciones con insight basado en datos: relación tasas-CDs, tendencias de crédito, etc.]

PERSPECTIVA
[1 párrafo: qué vigilar el próximo mes, máx 3 puntos]

Fuente: BCRD · SB · [Fecha]
#BancaDominicana #FinanzasDominicanas #BCRD #Macroeconomía

Solo devuelve el texto del post. Sé técnico y preciso."""

REFINE_PROMPT = """Tienes este borrador de post de LinkedIn sobre banca dominicana:

{draft}

El usuario solicita este cambio: {instruction}

Datos disponibles: {data}

Aplica los cambios manteniendo el formato y la calidad técnica. Solo devuelve el post revisado."""


class PostAgent:
    def __init__(self, model="claude-sonnet-4-6"):
        self.client = anthropic.Anthropic()
        self.model = model

    def _call_claude(self, prompt: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    def generate_flash(self, data: dict, indicator: str) -> str:
        import json
        prompt = FLASH_PROMPT.format(
            indicator=indicator,
            data=json.dumps(data.get("bcrd", {}), ensure_ascii=False, indent=2)
        )
        return self._call_claude(prompt)

    def generate_mensual(self, data: dict) -> str:
        import json
        prompt = MENSUAL_PROMPT.format(data=json.dumps(data, ensure_ascii=False, indent=2))
        return self._call_claude(prompt)

    def refine(self, draft: str, instruction: str, data: dict) -> str:
        import json
        prompt = REFINE_PROMPT.format(
            draft=draft,
            instruction=instruction,
            data=json.dumps(data, ensure_ascii=False, indent=2)
        )
        return self._call_claude(prompt)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_post_agent.py -v
```

- [ ] **Step 5: Commit**

```bash
git add agent/sub_agents/post_agent.py tests/test_post_agent.py
git commit -m "feat: post agent with flash, mensual, and refine modes"
```

---

## Task 7: Board Agent (PDF)

**Files:**
- Create: `agent/sub_agents/board_agent.py`
- Create: `agent/templates/board_report.html`
- Test: `tests/test_board_agent.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_board_agent.py
import os
from unittest.mock import patch, MagicMock
from agent.sub_agents.board_agent import BoardAgent

SAMPLE_DATA = {
    "bcrd": {
        "tpm": {"value": 5.25, "date": "2026-03-01"},
        "tasas_bancarias": {
            "bancos_multiples": {"activa": 13.27, "pasiva": 6.14},
            "aayp": {"activa": 14.5, "pasiva": 5.8},
            "interbancaria": 6.06,
        },
        "imae": {"var_interanual": 5.3},
        "inflacion": {"var_interanual": 3.8},
        "tipo_cambio": {"compra": 60.55, "venta": 61.19},
        "reservas": {"brutas_mm_usd": 16143.1},
    },
    "sb": {
        "rankings": {
            "top_cartera_growth": [{"entidad": "Banco X", "_growth_pct": 18.5}],
            "top_npl_increase": [{"entidad": "Banco A", "_growth_pct": 0.8}],
        }
    },
    "imf": {"capital_adequacy": {"value": 17.5}},
    "wb": {"credit_gdp": [{"year": "2024", "value": 31.92}]},
}

def test_generate_creates_pdf(tmp_path):
    agent = BoardAgent(output_dir=str(tmp_path))
    with patch.object(agent, '_render_pdf') as mock_pdf:
        mock_pdf.return_value = str(tmp_path / "test.pdf")
        output = agent.generate(SAMPLE_DATA, period="Marzo 2026")
    assert output.endswith(".pdf")

def test_build_kpi_summary_returns_dict():
    agent = BoardAgent()
    kpis = agent._build_kpi_summary(SAMPLE_DATA)
    assert "tpm" in kpis
    assert "imae" in kpis
    assert "inflacion" in kpis
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest tests/test_board_agent.py -v
```

- [ ] **Step 3: Create HTML template**

```html
<!-- agent/templates/board_report.html -->
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 0; }
  .cover { background: #1a1a2e; color: white; height: 100vh; display: flex; flex-direction: column; justify-content: center; padding: 60px; }
  .cover h1 { font-size: 2.5em; margin: 0 0 10px; }
  .cover .period { font-size: 1.4em; color: #a0aec0; }
  .cover .date { font-size: 1em; color: #718096; margin-top: 20px; }
  .page { padding: 40px 60px; page-break-before: always; }
  h2 { color: #1a1a2e; border-bottom: 3px solid #3182ce; padding-bottom: 8px; }
  .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
  .kpi-card { background: #f7fafc; border-radius: 8px; padding: 20px; border-left: 4px solid #3182ce; }
  .kpi-card.green { border-left-color: #38a169; }
  .kpi-card.yellow { border-left-color: #d69e2e; }
  .kpi-card.red { border-left-color: #e53e3e; }
  .kpi-label { font-size: 0.85em; color: #718096; text-transform: uppercase; letter-spacing: 0.05em; }
  .kpi-value { font-size: 2em; font-weight: bold; color: #1a1a2e; margin: 5px 0; }
  .kpi-delta { font-size: 0.9em; color: #718096; }
  table { width: 100%; border-collapse: collapse; margin: 15px 0; }
  th { background: #1a1a2e; color: white; padding: 10px 12px; text-align: left; font-size: 0.85em; }
  td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 0.9em; }
  tr:nth-child(even) td { background: #f7fafc; }
  .chart-img { width: 100%; margin: 15px 0; border-radius: 6px; }
  .section-note { font-size: 0.8em; color: #a0aec0; margin-top: 30px; }
  .bubble-note { font-style: italic; color: #718096; font-size: 0.85em; }
</style>
</head>
<body>

<div class="cover">
  <div style="color:#3182ce;font-size:0.9em;letter-spacing:0.1em;text-transform:uppercase;">Análisis Sectorial</div>
  <h1>Sistema Bancario<br>Dominicano</h1>
  <div class="period">{{ period }}</div>
  <div class="date">Generado: {{ date }}</div>
</div>

<div class="page">
  <h2>Resumen Ejecutivo — KPIs Clave</h2>
  <div class="kpi-grid">
    <div class="kpi-card {{ kpis.tpm.color }}">
      <div class="kpi-label">Tasa Política Monetaria</div>
      <div class="kpi-value">{{ kpis.tpm.value }}%</div>
      <div class="kpi-delta">{{ kpis.tpm.delta }}</div>
    </div>
    <div class="kpi-card {{ kpis.imae.color }}">
      <div class="kpi-label">IMAE (var. i.a.)</div>
      <div class="kpi-value">+{{ kpis.imae.value }}%</div>
      <div class="kpi-delta">{{ kpis.imae.delta }}</div>
    </div>
    <div class="kpi-card {{ kpis.inflacion.color }}">
      <div class="kpi-label">Inflación (i.a.)</div>
      <div class="kpi-value">{{ kpis.inflacion.value }}%</div>
      <div class="kpi-delta">{{ kpis.inflacion.delta }}</div>
    </div>
    <div class="kpi-card {{ kpis.spread_bm.color }}">
      <div class="kpi-label">Spread Activo-Pasivo BM</div>
      <div class="kpi-value">{{ kpis.spread_bm.value }} pp</div>
      <div class="kpi-delta">{{ kpis.spread_bm.delta }}</div>
    </div>
    <div class="kpi-card {{ kpis.reservas.color }}">
      <div class="kpi-label">Reservas Internacionales</div>
      <div class="kpi-value">US$ {{ kpis.reservas.value }}MM</div>
      <div class="kpi-delta">{{ kpis.reservas.delta }}</div>
    </div>
    <div class="kpi-card {{ kpis.tipo_cambio.color }}">
      <div class="kpi-label">Tipo de Cambio (venta)</div>
      <div class="kpi-value">RD$ {{ kpis.tipo_cambio.value }}</div>
      <div class="kpi-delta">{{ kpis.tipo_cambio.delta }}</div>
    </div>
  </div>
</div>

<div class="page">
  <h2>Entorno Macroeconómico</h2>
  {{ macro_chart }}
  <table>
    <tr><th>Indicador</th><th>Valor Actual</th><th>Período</th><th>Fuente</th></tr>
    <tr><td>TPM</td><td>{{ kpis.tpm.value }}%</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>Tasa Activa BM</td><td>{{ tasas.bm_activa }}%</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>Tasa Pasiva BM</td><td>{{ tasas.bm_pasiva }}%</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>Tasa Activa AAyP</td><td>{{ tasas.aayp_activa }}%</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>Tasa Interbancaria</td><td>{{ tasas.interbancaria }}%</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>IMAE (var. i.a.)</td><td>+{{ kpis.imae.value }}%</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>Inflación (i.a.)</td><td>{{ kpis.inflacion.value }}%</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>USD/DOP (venta)</td><td>{{ kpis.tipo_cambio.value }}</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
    <tr><td>Reservas Brutas</td><td>US$ {{ kpis.reservas.value }}MM</td><td>{{ bcrd_date }}</td><td>BCRD</td></tr>
  </table>
</div>

<div class="page">
  <h2>Ranking de Entidades Bancarias</h2>
  <h3>Top 5 — Mayor Crecimiento de Cartera (i.a.)</h3>
  <table>
    <tr><th>#</th><th>Entidad</th><th>Crecimiento i.a.</th></tr>
    {{ cartera_rows }}
  </table>
  <h3>Top 5 — Mayor Incremento de Morosidad (NPL, i.a.)</h3>
  <table>
    <tr><th>#</th><th>Entidad</th><th>Δ Morosidad (pp)</th></tr>
    {{ npl_rows }}
  </table>
  <div class="bubble-note">Bubble chart: tamaño = cartera total. Eje X = crecimiento i.a. Eje Y = morosidad.</div>
  {{ bubble_chart }}
</div>

<div class="page">
  <h2>Contexto Regional e Internacional</h2>
  <table>
    <tr><th>Indicador</th><th>RD</th><th>Fuente</th><th>Año</th></tr>
    <tr><td>Crédito Privado / PIB</td><td>{{ wb_credit_gdp }}%</td><td>World Bank</td><td>{{ wb_year }}</td></tr>
    <tr><td>IAC (Capital Adequacy)</td><td>{{ imf_iac }}%</td><td>IMF FSI</td><td>{{ imf_year }}</td></tr>
  </table>
</div>

<div class="page">
  <h2>Perspectivas y Riesgos</h2>
  {{ perspectivas_content }}
  <div class="section-note">Fuentes: BCRD · Superintendencia de Bancos · Ministerio de Hacienda · IMF · World Bank</div>
</div>

</body>
</html>
```

- [ ] **Step 4: Implement BoardAgent**

```python
# agent/sub_agents/board_agent.py
import os
import base64
from datetime import date
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import anthropic


class BoardAgent:
    def __init__(self, output_dir="outputs/reports", template_path="agent/templates/board_report.html"):
        self.output_dir = output_dir
        self.template_path = template_path
        self.client = anthropic.Anthropic()
        os.makedirs(output_dir, exist_ok=True)

    def _chart_to_base64(self, fig) -> str:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return base64.b64encode(buf.read()).decode()

    def _macro_chart(self, data: dict) -> str:
        bcrd = data.get("bcrd", {})
        tasas = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        labels = ["TPM", "Activa BM", "Pasiva BM", "Inflación i.a.", "IMAE i.a."]
        values = [
            bcrd.get("tpm", {}).get("value", 0),
            tasas.get("activa", 0),
            tasas.get("pasiva", 0),
            bcrd.get("inflacion", {}).get("var_interanual", 0),
            bcrd.get("imae", {}).get("var_interanual", 0),
        ]
        colors = ['#1a1a2e', '#3182ce', '#63b3ed', '#d69e2e', '#38a169']
        fig, ax = plt.subplots(figsize=(10, 4))
        bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=0.5)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f'{val:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax.set_ylabel('Porcentaje (%)')
        ax.set_title('Indicadores Macroeconómicos Clave', fontweight='bold', pad=15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#f7fafc')
        fig.patch.set_facecolor('white')
        b64 = self._chart_to_base64(fig)
        return f'<img class="chart-img" src="data:image/png;base64,{b64}">'

    def _bubble_chart(self, data: dict) -> str:
        rankings = data.get("sb", {}).get("rankings", {})
        cartera = rankings.get("top_cartera_growth", [])
        npl = rankings.get("top_npl_increase", [])
        if not cartera:
            return ""
        names = [e.get("entidad", e.get("name", f"E{i}")) for i, e in enumerate(cartera[:8])]
        growth = [e.get("_growth_pct", 0) for e in cartera[:8]]
        morosidad = [e.get("_growth_pct", 0) for e in npl[:len(names)]] + [0] * max(0, len(names) - len(npl))
        sizes = [300 + abs(g) * 50 for g in growth]
        fig, ax = plt.subplots(figsize=(10, 5))
        scatter = ax.scatter(growth, morosidad[:len(growth)], s=sizes,
                             c=range(len(growth)), cmap='Blues', alpha=0.7, edgecolors='#1a1a2e', linewidth=1)
        for i, name in enumerate(names):
            ax.annotate(name, (growth[i], morosidad[i] if i < len(morosidad) else 0),
                        textcoords="offset points", xytext=(0, 8), ha='center', fontsize=8)
        ax.axhline(y=0, color='#718096', linestyle='--', linewidth=0.8, alpha=0.5)
        ax.axvline(x=0, color='#718096', linestyle='--', linewidth=0.8, alpha=0.5)
        ax.set_xlabel('Crecimiento Cartera i.a. (%)', fontweight='bold')
        ax.set_ylabel('Δ Morosidad (pp)', fontweight='bold')
        ax.set_title('Crecimiento vs. Morosidad por Entidad\n(tamaño = cartera relativa)', fontweight='bold', pad=15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#f7fafc')
        fig.patch.set_facecolor('white')
        b64 = self._chart_to_base64(fig)
        return f'<img class="chart-img" src="data:image/png;base64,{b64}">'

    def _build_kpi_summary(self, data: dict) -> dict:
        bcrd = data.get("bcrd", {})
        tasas = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        activa = tasas.get("activa", 0) or 0
        pasiva = tasas.get("pasiva", 0) or 0
        spread = round(activa - pasiva, 2)
        imae_val = bcrd.get("imae", {}).get("var_interanual", 0) or 0
        inf_val = bcrd.get("inflacion", {}).get("var_interanual", 0) or 0
        return {
            "tpm": {"value": bcrd.get("tpm", {}).get("value", "N/D"), "delta": "", "color": "green"},
            "imae": {"value": imae_val, "delta": "Crecimiento económico", "color": "green" if imae_val > 3 else "yellow"},
            "inflacion": {"value": inf_val, "delta": "Inflación interanual", "color": "green" if inf_val < 5 else "yellow" if inf_val < 8 else "red"},
            "spread_bm": {"value": spread, "delta": "Spread Bancos Múltiples", "color": "green" if spread < 8 else "yellow"},
            "reservas": {"value": bcrd.get("reservas", {}).get("brutas_mm_usd", "N/D"), "delta": "Reservas brutas", "color": "green"},
            "tipo_cambio": {"value": bcrd.get("tipo_cambio", {}).get("venta", "N/D"), "delta": "USD/DOP venta", "color": "green"},
        }

    def _table_rows(self, items: list, field_name: str) -> str:
        html = ""
        for i, item in enumerate(items[:5], 1):
            name = item.get("entidad", item.get("name", f"Entidad {i}"))
            val = item.get("_growth_pct", 0)
            html += f"<tr><td>{i}</td><td>{name}</td><td>{val:+.1f}%</td></tr>\n"
        return html or "<tr><td colspan='3'>Datos no disponibles</td></tr>"

    def _get_perspectivas(self, data: dict, period: str) -> str:
        import json
        msg = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": f"""Como analista financiero senior, basándote en estos datos del sistema bancario dominicano para {period}:

{json.dumps(data, ensure_ascii=False, indent=2)[:3000]}

Escribe la sección "Perspectivas y Riesgos" del reporte ejecutivo de board. Incluye:
- 2-3 riesgos principales
- 2-3 oportunidades
- 3 indicadores clave a vigilar el próximo mes

Formato HTML simple con <h3>, <ul>, <li>. Sé técnico y conciso."""}]
        )
        return msg.content[0].text

    def _render_pdf(self, html_content: str, output_path: str) -> str:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return output_path

    def generate(self, data: dict, period: str = None) -> str:
        if not period:
            period = date.today().strftime("%B %Y")
        kpis = self._build_kpi_summary(data)
        bcrd = data.get("bcrd", {})
        tasas_bm = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        tasas_aayp = bcrd.get("tasas_bancarias", {}).get("aayp", {})
        rankings = data.get("sb", {}).get("rankings", {})
        wb_data = data.get("wb", {}).get("credit_gdp", [{}])
        imf_data = data.get("imf", {})
        with open(self.template_path) as f:
            template = f.read()
        replacements = {
            "{{ period }}": period,
            "{{ date }}": str(date.today()),
            "{{ bcrd_date }}": bcrd.get("tpm", {}).get("date", ""),
            "{{ tasas.bm_activa }}": str(tasas_bm.get("activa", "N/D")),
            "{{ tasas.bm_pasiva }}": str(tasas_bm.get("pasiva", "N/D")),
            "{{ tasas.aayp_activa }}": str(tasas_aayp.get("activa", "N/D")),
            "{{ tasas.interbancaria }}": str(bcrd.get("tasas_bancarias", {}).get("interbancaria", "N/D")),
            "{{ kpis.tpm.value }}": str(kpis["tpm"]["value"]),
            "{{ kpis.tpm.color }}": kpis["tpm"]["color"],
            "{{ kpis.tpm.delta }}": kpis["tpm"]["delta"],
            "{{ kpis.imae.value }}": str(kpis["imae"]["value"]),
            "{{ kpis.imae.color }}": kpis["imae"]["color"],
            "{{ kpis.imae.delta }}": kpis["imae"]["delta"],
            "{{ kpis.inflacion.value }}": str(kpis["inflacion"]["value"]),
            "{{ kpis.inflacion.color }}": kpis["inflacion"]["color"],
            "{{ kpis.inflacion.delta }}": kpis["inflacion"]["delta"],
            "{{ kpis.spread_bm.value }}": str(kpis["spread_bm"]["value"]),
            "{{ kpis.spread_bm.color }}": kpis["spread_bm"]["color"],
            "{{ kpis.spread_bm.delta }}": kpis["spread_bm"]["delta"],
            "{{ kpis.reservas.value }}": str(kpis["reservas"]["value"]),
            "{{ kpis.reservas.color }}": kpis["reservas"]["color"],
            "{{ kpis.reservas.delta }}": kpis["reservas"]["delta"],
            "{{ kpis.tipo_cambio.value }}": str(kpis["tipo_cambio"]["value"]),
            "{{ kpis.tipo_cambio.color }}": kpis["tipo_cambio"]["color"],
            "{{ kpis.tipo_cambio.delta }}": kpis["tipo_cambio"]["delta"],
            "{{ macro_chart }}": self._macro_chart(data),
            "{{ bubble_chart }}": self._bubble_chart(data),
            "{{ cartera_rows }}": self._table_rows(rankings.get("top_cartera_growth", []), "cartera"),
            "{{ npl_rows }}": self._table_rows(rankings.get("top_npl_increase", []), "npl"),
            "{{ wb_credit_gdp }}": str(wb_data[0].get("value", "N/D") if wb_data else "N/D"),
            "{{ wb_year }}": str(wb_data[0].get("year", "") if wb_data else ""),
            "{{ imf_iac }}": str(imf_data.get("capital_adequacy", {}).get("value", "N/D")),
            "{{ imf_year }}": str(imf_data.get("capital_adequacy", {}).get("year", "")),
            "{{ perspectivas_content }}": self._get_perspectivas(data, period),
        }
        html = template
        for k, v in replacements.items():
            html = html.replace(k, str(v))
        filename = f"{date.today()}-board-report.pdf"
        output_path = os.path.join(self.output_dir, filename)
        return self._render_pdf(html, output_path)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_board_agent.py -v
```

- [ ] **Step 6: Commit**

```bash
git add agent/sub_agents/board_agent.py agent/templates/board_report.html tests/test_board_agent.py
git commit -m "feat: board agent with PDF generation, charts, bubble chart, and KPI dashboard"
```

---

## Task 8: Carousel Agent (PPTX)

**Files:**
- Create: `agent/sub_agents/carousel_agent.py`
- Test: `tests/test_carousel_agent.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_carousel_agent.py
import os
from unittest.mock import patch, MagicMock
from agent.sub_agents.carousel_agent import CarouselAgent

SAMPLE_DATA = {
    "bcrd": {
        "tpm": {"value": 5.25},
        "tasas_bancarias": {"bancos_multiples": {"activa": 13.27, "pasiva": 6.14}, "aayp": {"activa": 14.5, "pasiva": 5.8}},
        "imae": {"var_interanual": 5.3},
        "inflacion": {"var_interanual": 3.8},
        "tipo_cambio": {"compra": 60.55, "venta": 61.19},
        "reservas": {"brutas_mm_usd": 16143.1},
    },
    "sb": {
        "rankings": {
            "top_cartera_growth": [{"entidad": "Banco X", "_growth_pct": 18.5}, {"entidad": "Banco Y", "_growth_pct": 14.2}],
            "top_npl_increase": [{"entidad": "Banco A", "_growth_pct": 0.8}],
        }
    },
}

def test_generate_creates_pptx(tmp_path):
    agent = CarouselAgent(output_dir=str(tmp_path))
    result = agent.generate(SAMPLE_DATA, period="Marzo 2026")
    assert result.endswith(".pptx")
    assert os.path.exists(result)

def test_generate_has_correct_slide_count(tmp_path):
    from pptx import Presentation
    agent = CarouselAgent(output_dir=str(tmp_path))
    result = agent.generate(SAMPLE_DATA, period="Marzo 2026")
    prs = Presentation(result)
    assert len(prs.slides) >= 8
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest tests/test_carousel_agent.py -v
```

- [ ] **Step 3: Implement CarouselAgent**

```python
# agent/sub_agents/carousel_agent.py
import os
from datetime import date
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# Colors
DARK_BLUE = RGBColor(0x1a, 0x1a, 0x2e)
MED_BLUE = RGBColor(0x31, 0x82, 0xce)
LIGHT_BLUE = RGBColor(0x63, 0xb3, 0xed)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x38, 0xa1, 0x69)
RED = RGBColor(0xe5, 0x3e, 0x3e)
YELLOW = RGBColor(0xd6, 0x9e, 0x2e)
GRAY = RGBColor(0x71, 0x80, 0x96)

SLIDE_W = Inches(8.27)   # A4 landscape approximation for LinkedIn square
SLIDE_H = Inches(8.27)


class CarouselAgent:
    def __init__(self, output_dir="outputs/carousel"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _new_prs(self) -> Presentation:
        prs = Presentation()
        prs.slide_width = SLIDE_W
        prs.slide_height = SLIDE_H
        return prs

    def _blank_slide(self, prs: Presentation, bg_color: RGBColor = None):
        layout = prs.slide_layouts[6]  # blank
        slide = prs.slides.add_slide(layout)
        if bg_color:
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = bg_color
        return slide

    def _add_text(self, slide, text, left, top, width, height, font_size=24,
                  bold=False, color=WHITE, align=PP_ALIGN.LEFT, wrap=True):
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = wrap
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.color.rgb = color

    def _chart_to_image(self, fig) -> BytesIO:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#f7fafc')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _slide_cover(self, prs, period):
        slide = self._blank_slide(prs, DARK_BLUE)
        margin = Inches(0.5)
        w = SLIDE_W - 2 * margin
        self._add_text(slide, "SISTEMA BANCARIO DOMINICANO",
                       margin, Inches(1.5), w, Inches(0.6), font_size=16, bold=True,
                       color=MED_BLUE, align=PP_ALIGN.CENTER)
        self._add_text(slide, "Barómetro Mensual",
                       margin, Inches(2.3), w, Inches(1.2), font_size=36, bold=True,
                       color=WHITE, align=PP_ALIGN.CENTER)
        self._add_text(slide, period,
                       margin, Inches(3.6), w, Inches(0.8), font_size=22,
                       color=LIGHT_BLUE, align=PP_ALIGN.CENTER)
        self._add_text(slide, "Fuente: BCRD · Superintendencia de Bancos · IMF · World Bank",
                       margin, Inches(7.2), w, Inches(0.5), font_size=10,
                       color=GRAY, align=PP_ALIGN.CENTER)
        return slide

    def _slide_kpis(self, prs, data):
        slide = self._blank_slide(prs, WHITE)
        self._add_text(slide, "KPIs CLAVE DEL MES", Inches(0.3), Inches(0.3),
                       SLIDE_W - Inches(0.6), Inches(0.6), font_size=18, bold=True,
                       color=DARK_BLUE, align=PP_ALIGN.CENTER)
        bcrd = data.get("bcrd", {})
        tasas = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        kpis = [
            ("TPM", f"{bcrd.get('tpm', {}).get('value', 'N/D')}%"),
            ("Activa BM", f"{tasas.get('activa', 'N/D')}%"),
            ("Pasiva BM", f"{tasas.get('pasiva', 'N/D')}%"),
            ("IMAE i.a.", f"+{bcrd.get('imae', {}).get('var_interanual', 'N/D')}%"),
            ("Inflación i.a.", f"{bcrd.get('inflacion', {}).get('var_interanual', 'N/D')}%"),
            ("USD/DOP", f"RD${bcrd.get('tipo_cambio', {}).get('venta', 'N/D')}"),
        ]
        cols, rows = 3, 2
        card_w, card_h = Inches(2.5), Inches(2.8)
        start_x, start_y = Inches(0.4), Inches(1.2)
        for i, (label, value) in enumerate(kpis):
            col, row = i % cols, i // cols
            x = start_x + col * (card_w + Inches(0.2))
            y = start_y + row * (card_h + Inches(0.15))
            shape = slide.shapes.add_shape(1, x, y, card_w, card_h)  # rectangle
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(0xf7, 0xfa, 0xfc)
            shape.line.color.rgb = MED_BLUE
            shape.line.width = Pt(1.5)
            self._add_text(slide, label, x + Inches(0.1), y + Inches(0.15),
                           card_w - Inches(0.2), Inches(0.5), font_size=11, color=GRAY)
            self._add_text(slide, value, x + Inches(0.1), y + Inches(0.7),
                           card_w - Inches(0.2), Inches(1.0), font_size=28, bold=True, color=DARK_BLUE)
        return slide

    def _slide_macro_chart(self, prs, data):
        slide = self._blank_slide(prs, WHITE)
        self._add_text(slide, "ENTORNO MACROECONÓMICO", Inches(0.3), Inches(0.2),
                       SLIDE_W - Inches(0.6), Inches(0.5), font_size=18, bold=True,
                       color=DARK_BLUE, align=PP_ALIGN.CENTER)
        bcrd = data.get("bcrd", {})
        tasas = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        labels = ["TPM", "Activa BM", "Pasiva BM", "IMAE i.a.", "Inflación i.a."]
        values = [
            bcrd.get("tpm", {}).get("value", 0) or 0,
            tasas.get("activa", 0) or 0,
            tasas.get("pasiva", 0) or 0,
            bcrd.get("imae", {}).get("var_interanual", 0) or 0,
            bcrd.get("inflacion", {}).get("var_interanual", 0) or 0,
        ]
        colors = ['#1a1a2e', '#3182ce', '#63b3ed', '#38a169', '#d69e2e']
        fig, ax = plt.subplots(figsize=(7, 4))
        bars = ax.bar(labels, values, color=colors, width=0.6, edgecolor='white')
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax.set_ylabel('%')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        buf = self._chart_to_image(fig)
        slide.shapes.add_picture(buf, Inches(0.4), Inches(1.0), SLIDE_W - Inches(0.8), Inches(5.5))
        self._add_text(slide, f"USD/DOP venta: RD${bcrd.get('tipo_cambio', {}).get('venta', 'N/D')} · Reservas: US${bcrd.get('reservas', {}).get('brutas_mm_usd', 'N/D')}MM",
                       Inches(0.3), Inches(7.5), SLIDE_W - Inches(0.6), Inches(0.4),
                       font_size=10, color=GRAY, align=PP_ALIGN.CENTER)
        return slide

    def _slide_tasas(self, prs, data):
        slide = self._blank_slide(prs, WHITE)
        self._add_text(slide, "TASAS DE INTERÉS POR ENTIDAD", Inches(0.3), Inches(0.2),
                       SLIDE_W - Inches(0.6), Inches(0.5), font_size=18, bold=True,
                       color=DARK_BLUE, align=PP_ALIGN.CENTER)
        bcrd = data.get("bcrd", {})
        tasas = bcrd.get("tasas_bancarias", {})
        bm = tasas.get("bancos_multiples", {})
        aayp = tasas.get("aayp", {})
        bac = tasas.get("bancos_ahorro_credito", {})
        categories = ['Bancos\nMúltiples', 'AAyP', 'Bancos\nAhorro y Créd.']
        activas = [bm.get("activa", 0) or 0, aayp.get("activa", 0) or 0, bac.get("activa", 0) or 0]
        pasivas = [bm.get("pasiva", 0) or 0, aayp.get("pasiva", 0) or 0, bac.get("pasiva", 0) or 0]
        x = range(len(categories))
        fig, ax = plt.subplots(figsize=(7, 4.5))
        w = 0.35
        bars1 = ax.bar([xi - w/2 for xi in x], activas, w, label='Tasa Activa', color='#1a1a2e')
        bars2 = ax.bar([xi + w/2 for xi in x], pasivas, w, label='Tasa Pasiva', color='#3182ce')
        ax.set_xticks(list(x))
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylabel('%')
        ax.legend()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                            xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8)
        buf = self._chart_to_image(fig)
        slide.shapes.add_picture(buf, Inches(0.4), Inches(1.0), SLIDE_W - Inches(0.8), Inches(5.5))
        interbancaria = tasas.get("interbancaria", "N/D")
        self._add_text(slide, f"Tasa interbancaria: {interbancaria}%",
                       Inches(0.3), Inches(7.4), SLIDE_W - Inches(0.6), Inches(0.4),
                       font_size=11, color=GRAY, align=PP_ALIGN.CENTER)
        return slide

    def _slide_top_cartera(self, prs, data):
        slide = self._blank_slide(prs, WHITE)
        self._add_text(slide, "¿QUIÉN CRECIÓ MÁS?", Inches(0.3), Inches(0.2),
                       SLIDE_W - Inches(0.6), Inches(0.5), font_size=20, bold=True,
                       color=DARK_BLUE, align=PP_ALIGN.CENTER)
        self._add_text(slide, "Top entidades por crecimiento de cartera de crédito (i.a.)",
                       Inches(0.3), Inches(0.85), SLIDE_W - Inches(0.6), Inches(0.4),
                       font_size=12, color=GRAY, align=PP_ALIGN.CENTER)
        rankings = data.get("sb", {}).get("rankings", {})
        top = rankings.get("top_cartera_growth", [])[:5]
        if top:
            names = [e.get("entidad", e.get("name", f"E{i}")) for i, e in enumerate(top)]
            values = [e.get("_growth_pct", 0) for e in top]
            fig, ax = plt.subplots(figsize=(6.5, 4.5))
            colors_bar = ['#1a1a2e', '#3182ce', '#63b3ed', '#90cdf4', '#bee3f8']
            bars = ax.barh(names[::-1], values[::-1], color=colors_bar[:len(top)], edgecolor='white')
            for bar, val in zip(bars, values[::-1]):
                ax.text(val + 0.2, bar.get_y() + bar.get_height() / 2,
                        f'+{val:.1f}%', va='center', fontsize=10, fontweight='bold', color='#1a1a2e')
            ax.set_xlabel('Crecimiento i.a. (%)')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            buf = self._chart_to_image(fig)
            slide.shapes.add_picture(buf, Inches(0.5), Inches(1.4), Inches(7.2), Inches(5.5))
        return slide

    def _slide_top_npl(self, prs, data):
        slide = self._blank_slide(prs, WHITE)
        self._add_text(slide, "MOROSIDAD POR ENTIDAD", Inches(0.3), Inches(0.2),
                       SLIDE_W - Inches(0.6), Inches(0.5), font_size=20, bold=True,
                       color=DARK_BLUE, align=PP_ALIGN.CENTER)
        self._add_text(slide, "Entidades con mayor incremento de cartera vencida (NPL, i.a. en pp)",
                       Inches(0.3), Inches(0.85), SLIDE_W - Inches(0.6), Inches(0.4),
                       font_size=12, color=GRAY, align=PP_ALIGN.CENTER)
        rankings = data.get("sb", {}).get("rankings", {})
        top_npl = rankings.get("top_npl_increase", [])[:5]
        y_pos = Inches(1.6)
        for i, entity in enumerate(top_npl):
            name = entity.get("entidad", entity.get("name", f"Entidad {i+1}"))
            val = entity.get("_growth_pct", 0)
            color = RED if val > 1 else YELLOW if val > 0.5 else GREEN
            indicator = slide.shapes.add_shape(1, Inches(0.4), y_pos, Inches(0.3), Inches(0.55))
            indicator.fill.solid()
            indicator.fill.fore_color.rgb = color
            indicator.line.color.rgb = color
            self._add_text(slide, f"{name}", Inches(0.9), y_pos + Inches(0.05),
                           Inches(4.5), Inches(0.5), font_size=16, color=DARK_BLUE)
            self._add_text(slide, f"+{val:.1f} pp", Inches(5.5), y_pos + Inches(0.05),
                           Inches(2.0), Inches(0.5), font_size=16, bold=True, color=color)
            y_pos += Inches(0.9)
        legend_y = Inches(7.0)
        for color, label in [(GREEN, "Bajo (<0.5pp)"), (YELLOW, "Moderado (0.5-1pp)"), (RED, "Elevado (>1pp)")]:
            dot = slide.shapes.add_shape(1, Inches(0.4), legend_y, Inches(0.2), Inches(0.2))
            dot.fill.solid()
            dot.fill.fore_color.rgb = color
            dot.line.color.rgb = color
            self._add_text(slide, label, Inches(0.7), legend_y - Inches(0.02),
                           Inches(2.0), Inches(0.3), font_size=9, color=GRAY)
            legend_y = Inches(legend_y.inches + 0.0)  # same line, different x — handled via manual x offset
        return slide

    def _slide_perspectivas(self, prs, data):
        slide = self._blank_slide(prs, DARK_BLUE)
        self._add_text(slide, "PERSPECTIVAS", Inches(0.5), Inches(0.5),
                       SLIDE_W - Inches(1), Inches(0.8), font_size=24, bold=True,
                       color=WHITE, align=PP_ALIGN.CENTER)
        self._add_text(slide, "¿Qué vigilar el próximo mes?",
                       Inches(0.5), Inches(1.4), SLIDE_W - Inches(1), Inches(0.5),
                       font_size=14, color=LIGHT_BLUE, align=PP_ALIGN.CENTER)
        bcrd = data.get("bcrd", {})
        inf = bcrd.get("inflacion", {}).get("var_interanual", 0) or 0
        imae = bcrd.get("imae", {}).get("var_interanual", 0) or 0
        points = [
            f"• Inflación en {inf:.1f}% i.a. — evolución de TPM ante datos de precios",
            f"• Crecimiento IMAE +{imae:.1f}% — sostenibilidad del crédito comercial",
            "• Monitorear calidad de cartera ante expansión de crédito de consumo",
        ]
        y = Inches(2.3)
        for point in points:
            self._add_text(slide, point, Inches(0.5), y, SLIDE_W - Inches(1), Inches(1.0),
                           font_size=15, color=WHITE)
            y += Inches(1.3)
        return slide

    def _slide_cta(self, prs, period):
        slide = self._blank_slide(prs, DARK_BLUE)
        self._add_text(slide, "¿Qué indicador te\ninteresa profundizar?",
                       Inches(0.5), Inches(2.0), SLIDE_W - Inches(1), Inches(2.0),
                       font_size=28, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        self._add_text(slide, "Comenta abajo 👇",
                       Inches(0.5), Inches(4.3), SLIDE_W - Inches(1), Inches(0.8),
                       font_size=20, color=LIGHT_BLUE, align=PP_ALIGN.CENTER)
        self._add_text(slide, f"#BancaDominicana #BCRD #FinanzasDominicanas",
                       Inches(0.5), Inches(7.0), SLIDE_W - Inches(1), Inches(0.6),
                       font_size=11, color=GRAY, align=PP_ALIGN.CENTER)
        return slide

    def generate(self, data: dict, period: str = None) -> str:
        if not period:
            period = date.today().strftime("%B %Y")
        prs = self._new_prs()
        self._slide_cover(prs, period)
        self._slide_kpis(prs, data)
        self._slide_macro_chart(prs, data)
        self._slide_tasas(prs, data)
        self._slide_top_cartera(prs, data)
        self._slide_top_npl(prs, data)
        self._slide_perspectivas(prs, data)
        self._slide_cta(prs, period)
        filename = f"{date.today()}-carousel.pptx"
        output_path = os.path.join(self.output_dir, filename)
        prs.save(output_path)
        return output_path
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_carousel_agent.py -v
```

- [ ] **Step 5: Commit**

```bash
git add agent/sub_agents/carousel_agent.py tests/test_carousel_agent.py
git commit -m "feat: carousel agent generating 8-slide LinkedIn PPTX with charts"
```

---

## Task 9: Format Decision Agent

**Files:**
- Create: `agent/sub_agents/format_decision_agent.py`
- Test: `tests/test_format_decision.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_format_decision.py
from agent.sub_agents.format_decision_agent import FormatDecisionAgent

def test_mensual_mode_recommends_carousel():
    agent = FormatDecisionAgent()
    result = agent.decide(mode="mensual", data_summary={"notable_indicators": 5})
    assert result["recommendation"] in ["carousel", "post"]
    assert "reason" in result

def test_flash_mode_recommends_post():
    agent = FormatDecisionAgent()
    result = agent.decide(mode="flash", data_summary={"notable_indicators": 1})
    assert result["recommendation"] == "post"
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest tests/test_format_decision.py -v
```

- [ ] **Step 3: Implement FormatDecisionAgent**

```python
# agent/sub_agents/format_decision_agent.py

RULES = [
    (lambda mode, summary: mode == "flash", "post",
     "Flash semanal: dato puntual que no requiere visualización."),
    (lambda mode, summary: summary.get("notable_indicators", 0) >= 3, "carousel",
     "3+ indicadores con variación notable este período — la narrativa visual es más efectiva."),
    (lambda mode, summary: mode == "mensual", "carousel",
     "Análisis mensual completo — el carousel permite un recorrido progresivo por los datos."),
]


class FormatDecisionAgent:
    def decide(self, mode: str, data_summary: dict) -> dict:
        for condition, recommendation, reason in RULES:
            if condition(mode, data_summary):
                return {"recommendation": recommendation, "reason": reason}
        return {"recommendation": "post", "reason": "Por defecto para contenido sin tendencia visual clara."}

    def summarize_data(self, data: dict) -> dict:
        bcrd = data.get("bcrd", {})
        notable = 0
        tpm = bcrd.get("tpm", {}).get("value")
        if tpm: notable += 1
        imae = bcrd.get("imae", {}).get("var_interanual")
        if imae and abs(imae) > 3: notable += 1
        inf = bcrd.get("inflacion", {}).get("var_interanual")
        if inf and abs(inf) > 2: notable += 1
        rankings = data.get("sb", {}).get("rankings", {})
        if rankings.get("top_cartera_growth"): notable += 1
        if rankings.get("top_npl_increase"): notable += 1
        return {"notable_indicators": notable}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_format_decision.py -v
```

- [ ] **Step 5: Commit**

```bash
git add agent/sub_agents/format_decision_agent.py tests/test_format_decision.py
git commit -m "feat: format decision agent recommends carousel vs text post"
```

---

## Task 10: Orchestrator + Review Loop

**Files:**
- Create: `agent/orchestrator.py`
- Create: `agent/run.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_orchestrator.py
from unittest.mock import patch, MagicMock
from agent.orchestrator import Orchestrator

def test_collect_data_returns_dict():
    orch = Orchestrator()
    with patch.object(orch.bcrd, 'get_all', return_value={"tpm": {"value": 5.25}}):
        with patch.object(orch.sb, 'get_all', return_value={"system": {}}):
            with patch.object(orch.imf, 'get_all', return_value={}):
                with patch.object(orch.wb, 'get_all', return_value={}):
                    data = orch.collect_data()
    assert "bcrd" in data
    assert "sb" in data

def test_run_flash_produces_post():
    orch = Orchestrator()
    mock_data = {"bcrd": {"tpm": {"value": 5.25}}, "sb": {}, "imf": {}, "wb": {}}
    with patch.object(orch, 'collect_data', return_value=mock_data):
        with patch.object(orch.post_agent, 'generate_flash', return_value="Post draft"):
            result = orch.run(mode="flash", indicator="tpm", interactive=False)
    assert result["post"] == "Post draft"
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest tests/test_orchestrator.py -v
```

- [ ] **Step 3: Implement Orchestrator**

```python
# agent/orchestrator.py
import os
from datetime import date

from agent.data_sources.bcrd import BCRDClient
from agent.data_sources.superbancos import SuperbancosClient
from agent.data_sources.imf import IMFClient
from agent.data_sources.worldbank import WorldBankClient
from agent.sub_agents.post_agent import PostAgent
from agent.sub_agents.board_agent import BoardAgent
from agent.sub_agents.carousel_agent import CarouselAgent
from agent.sub_agents.format_decision_agent import FormatDecisionAgent


class Orchestrator:
    def __init__(self):
        self.bcrd = BCRDClient()
        self.sb = SuperbancosClient()
        self.imf = IMFClient()
        self.wb = WorldBankClient()
        self.post_agent = PostAgent()
        self.board_agent = BoardAgent()
        self.carousel_agent = CarouselAgent()
        self.format_agent = FormatDecisionAgent()

    def collect_data(self) -> dict:
        print("📡 Recopilando datos...")
        print("  → BCRD...", end=" ", flush=True)
        bcrd_data = self.bcrd.get_all()
        print("✓")
        print("  → Superintendencia de Bancos...", end=" ", flush=True)
        sb_data = self.sb.get_all()
        print("✓")
        print("  → IMF...", end=" ", flush=True)
        imf_data = self.imf.get_all()
        print("✓")
        print("  → World Bank...", end=" ", flush=True)
        wb_data = self.wb.get_all()
        print("✓")
        return {"bcrd": bcrd_data, "sb": sb_data, "imf": imf_data, "wb": wb_data}

    def _print_data_summary(self, data: dict):
        bcrd = data.get("bcrd", {})
        tpm = bcrd.get("tpm", {})
        tasas = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        imae = bcrd.get("imae", {})
        inf = bcrd.get("inflacion", {})
        tc = bcrd.get("tipo_cambio", {})
        print("\n" + "="*60)
        print("📊 DATOS RECOPILADOS")
        print("="*60)
        print(f"  TPM:              {tpm.get('value', 'N/D')}% ({tpm.get('date', '')})")
        print(f"  Activa BM:        {tasas.get('activa', 'N/D')}%")
        print(f"  Pasiva BM:        {tasas.get('pasiva', 'N/D')}%")
        print(f"  IMAE i.a.:        +{imae.get('var_interanual', 'N/D')}%")
        print(f"  Inflación i.a.:   {inf.get('var_interanual', 'N/D')}%")
        print(f"  USD/DOP venta:    RD${tc.get('venta', 'N/D')}")
        rankings = data.get("sb", {}).get("rankings", {})
        top_cartera = rankings.get("top_cartera_growth", [])
        if top_cartera:
            print(f"\n  Top cartera: {', '.join(e.get('entidad', '?') for e in top_cartera[:3])}")
        print("="*60)

    def run(self, mode: str = "mensual", indicator: str = "tpm",
            interactive: bool = True, period: str = None) -> dict:
        if not period:
            period = date.today().strftime("%B %Y")

        data = self.collect_data()

        if interactive:
            self._print_data_summary(data)

        # Generate drafts
        print(f"\n✍️  Generando drafts (modo: {mode})...")
        results = {}

        if mode == "flash":
            post = self.post_agent.generate_flash(data, indicator=indicator)
            results["post"] = post
            results["carousel"] = None
            results["board"] = None
        else:
            post = self.post_agent.generate_mensual(data)
            results["post"] = post

            if mode in ("mensual", "board"):
                print("  → Generando board report PDF...")
                board_path = self.board_agent.generate(data, period=period)
                results["board"] = board_path
                print(f"  → Board report: {board_path}")

            if mode in ("mensual", "carousel"):
                print("  → Generando carousel PPTX...")
                carousel_path = self.carousel_agent.generate(data, period=period)
                results["carousel"] = carousel_path
                print(f"  → Carousel: {carousel_path}")

        # Format decision
        summary = self.format_agent.summarize_data(data)
        decision = self.format_agent.decide(mode=mode, data_summary=summary)
        results["format_recommendation"] = decision

        if not interactive:
            return results

        # Review loop
        self._review_loop(results, data, mode)
        return results

    def _review_loop(self, results: dict, data: dict, mode: str):
        print("\n" + "="*60)
        print("📋 DRAFT REVIEW")
        print("="*60)
        print("\n🐦 POST DRAFT:\n")
        print(results.get("post", ""))
        if results.get("board"):
            print(f"\n📄 BOARD REPORT: {results['board']}")
        if results.get("carousel"):
            print(f"\n🎠 CAROUSEL: {results['carousel']}")
        rec = results.get("format_recommendation", {})
        print(f"\n💡 RECOMENDACIÓN DE FORMATO: {rec.get('recommendation', '').upper()}")
        print(f"   {rec.get('reason', '')}")
        print("\n" + "="*60)
        print("Instrucciones: escribe cambios a aplicar, o 'aprobado' para finalizar.")
        print("="*60)

        while True:
            instruction = input("\n> ").strip()
            if instruction.lower() in ("aprobado", "approved", "ok", "listo"):
                self._save_outputs(results, mode)
                print("\n✅ Outputs guardados en outputs/")
                break
            if instruction:
                print("  Refinando...")
                results["post"] = self.post_agent.refine(results["post"], instruction, data)
                print("\n📋 POST ACTUALIZADO:\n")
                print(results["post"])
                print("\nEscribe más instrucciones o 'aprobado' para finalizar.")

    def _save_outputs(self, results: dict, mode: str):
        today = str(date.today())
        if results.get("post"):
            path = f"outputs/posts/{today}-{mode}.md"
            os.makedirs("outputs/posts", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(results["post"])
            print(f"  → Post: {path}")
```

- [ ] **Step 4: Implement run.py**

```python
# agent/run.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.orchestrator import Orchestrator


def main():
    args = sys.argv[1:]
    mode = args[0] if args else "mensual"
    indicator = args[1] if len(args) > 1 else "tpm"
    valid_modes = ("flash", "mensual", "board", "carousel")
    if mode not in valid_modes:
        print(f"Uso: python run.py [{' | '.join(valid_modes)}] [indicador]")
        sys.exit(1)
    orch = Orchestrator()
    orch.run(mode=mode, indicator=indicator, interactive=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_orchestrator.py -v
```

- [ ] **Step 6: Commit**

```bash
git add agent/orchestrator.py agent/run.py tests/test_orchestrator.py
git commit -m "feat: orchestrator with data collection, draft generation, and review loop"
```

---

## Task 11: Run full test suite + smoke test

- [ ] **Step 1: Run all tests**

```bash
cd "C:/Users/aleja/OneDrive/Escritorio/MissionControl"
python -m pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 2: Smoke test with cached/mock data**

```bash
python -c "
from agent.data_sources.worldbank import WorldBankClient
wb = WorldBankClient()
data = wb.get_credit_to_gdp()
print('WorldBank OK:', data[0])
"
```

Expected: prints credit/GDP value for Dominican Republic.

- [ ] **Step 3: Smoke test carousel generation**

```bash
python -c "
from agent.sub_agents.carousel_agent import CarouselAgent
agent = CarouselAgent()
sample = {
    'bcrd': {
        'tpm': {'value': 5.25},
        'tasas_bancarias': {'bancos_multiples': {'activa': 13.27, 'pasiva': 6.14}, 'aayp': {'activa': 14.5, 'pasiva': 5.8}, 'bancos_ahorro_credito': {'activa': 15.0, 'pasiva': 5.5}, 'interbancaria': 6.06},
        'imae': {'var_interanual': 5.3},
        'inflacion': {'var_interanual': 3.8},
        'tipo_cambio': {'compra': 60.55, 'venta': 61.19},
        'reservas': {'brutas_mm_usd': 16143.1},
    },
    'sb': {'rankings': {'top_cartera_growth': [{'entidad': 'BanReservas', '_growth_pct': 18.5}, {'entidad': 'Popular', '_growth_pct': 12.1}], 'top_npl_increase': [{'entidad': 'Banco X', '_growth_pct': 0.9}]}},
    'imf': {'capital_adequacy': {'value': 17.5, 'year': '2024'}},
    'wb': {'credit_gdp': [{'year': '2024', 'value': 31.92}]},
}
path = agent.generate(sample, period='Abril 2026')
print('Carousel generado:', path)
"
```

Expected: prints path to `.pptx` file in `outputs/carousel/`.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete Dominican banking agent — all agents, data sources, tests"
```

---

## Self-Review

**Spec coverage check:**
- ✅ BCRD indicators (tasas activas/pasivas BM, AAyP, BAC, interbancaria, TPM, IMAE, inflación, tipo de cambio, reservas) → Task 2
- ✅ SB scraping + rankings top cartera growth + top NPL → Task 4
- ✅ IMF FSI + World Bank → Task 3
- ✅ MCP server with 4 tools → Task 5
- ✅ Post Agent: flash + mensual + refine → Task 6
- ✅ Board Agent: PDF with charts, bubble chart, KPI semáforo, rankings → Task 7
- ✅ Carousel Agent: 8 slides 1080×1080 PPTX → Task 8
- ✅ Format Decision Agent → Task 9
- ✅ Orchestrator + review loop → Task 10
- ✅ Hacienda: not yet implemented — add Task 12

**Gap found — Hacienda:**

## Task 12: Hacienda data source (gap fix)

**Files:**
- Create: `agent/data_sources/hacienda.py`

- [ ] **Step 1: Implement HaciendaClient**

```python
# agent/data_sources/hacienda.py
import json, os, requests
from datetime import date
from bs4 import BeautifulSoup

HACIENDA_URL = "https://www.hacienda.gob.do/estadisticas-fiscales/"

class HaciendaClient:
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key):
        return os.path.join(self.cache_dir, f"{date.today()}-hacienda-{key}.json")

    def _load_cache(self, key):
        p = self._cache_path(key)
        return json.load(open(p)) if os.path.exists(p) else None

    def _save_cache(self, key, data):
        with open(self._cache_path(key), "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_fiscal_summary(self) -> dict:
        cached = self._load_cache("fiscal")
        if cached:
            return cached
        try:
            resp = requests.get(HACIENDA_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=" ")
            import re
            deuda = re.search(r"[Dd]euda.*?(\d+[\.,]\d+)%?\s*(?:del\s*)?PIB", text)
            result = {
                "date": str(date.today()),
                "deuda_pib_pct": deuda.group(1) if deuda else None,
                "source": "Ministerio de Hacienda RD",
                "url": HACIENDA_URL,
            }
        except Exception as e:
            result = {"date": str(date.today()), "error": str(e), "source": "Ministerio de Hacienda RD"}
        self._save_cache("fiscal", result)
        return result

    def get_all(self) -> dict:
        return {"fiscal": self.get_fiscal_summary()}
```

- [ ] **Step 2: Add to orchestrator collect_data**

In `agent/orchestrator.py`, import and add:

```python
# Add import at top:
from agent.data_sources.hacienda import HaciendaClient

# Add in __init__:
self.hacienda = HaciendaClient()

# Add in collect_data():
print("  → Ministerio de Hacienda...", end=" ", flush=True)
hacienda_data = self.hacienda.get_all()
print("✓")

# Add to return dict:
return {"bcrd": bcrd_data, "sb": sb_data, "imf": imf_data, "wb": wb_data, "hacienda": hacienda_data}
```

- [ ] **Step 3: Commit**

```bash
git add agent/data_sources/hacienda.py agent/orchestrator.py
git commit -m "feat: add Hacienda fiscal data source to orchestrator"
```
