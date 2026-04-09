# agent/data_sources/superbancos.py
import json
import os
import requests
from datetime import date
from bs4 import BeautifulSoup

SB_URLS = [
    "https://www.superbancos.gob.do/estadisticas/sistema-financiero/",
    "https://www.superbancos.gob.do/bancos/index.php?option=com_content&view=article&id=158",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BancarioRD/1.0)"}


class SuperbancosClient:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{date.today()}-sb-{key}.json")

    def _load_cache(self, key: str):
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_cache(self, key: str, data):
        with open(self._cache_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _fetch_html(self) -> str:
        for url in SB_URLS:
            try:
                resp = requests.get(url, timeout=20, headers=HEADERS)
                resp.raise_for_status()
                return resp.text
            except Exception:
                continue
        return ""

    def _parse_table(self, html: str) -> list:
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        entities = []
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower().replace(" ", "_")
                       for th in rows[0].find_all(["th", "td"])]
            if not headers:
                continue
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) < len(headers):
                    continue
                entity = {}
                for i, h in enumerate(headers):
                    raw = cells[i].replace(",", "").replace("%", "").strip()
                    try:
                        entity[h] = float(raw)
                    except ValueError:
                        entity[h] = raw
                if entity:
                    entities.append(entity)
        return entities

    def _rank_by_growth(self, entities: list, field: str, prev_field: str, n: int = 5) -> list:
        ranked = []
        for e in entities:
            curr = e.get(field)
            prev = e.get(prev_field)
            if curr is not None and prev is not None and isinstance(curr, (int, float)) and isinstance(prev, (int, float)) and prev != 0:
                growth = (curr - prev) / abs(prev) * 100
                ranked.append({**e, "_growth_pct": round(growth, 2)})
        return sorted(ranked, key=lambda x: x["_growth_pct"], reverse=True)[:n]

    def get_system_indicators(self) -> dict:
        cached = self._load_cache("system")
        if cached is not None:
            return cached
        html = self._fetch_html()
        entities = self._parse_table(html)
        result = {
            "date": str(date.today()),
            "entities": entities,
            "source": "Superintendencia de Bancos RD",
        }
        if entities:
            self._save_cache("system", result)
        return result

    def get_rankings(self) -> dict:
        cached = self._load_cache("rankings")
        if cached is not None:
            return cached
        data = self.get_system_indicators()
        entities = data.get("entities", [])
        result = {
            "top_cartera_growth": self._rank_by_growth(entities, "cartera", "cartera_prev", n=5),
            "top_npl_increase": self._rank_by_growth(entities, "morosidad", "morosidad_prev", n=5),
        }
        if entities:
            self._save_cache("rankings", result)
        return result

    def get_all(self) -> dict:
        return {
            "system": self.get_system_indicators(),
            "rankings": self.get_rankings(),
        }
