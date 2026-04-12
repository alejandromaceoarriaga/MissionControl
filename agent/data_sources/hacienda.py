# agent/data_sources/hacienda.py
import json
import os
import re
import requests
from datetime import date
from bs4 import BeautifulSoup

HACIENDA_URL = "https://www.hacienda.gob.do/estadisticas-fiscales/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BancarioRD/1.0)"}


class HaciendaClient:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{date.today()}-hacienda-{key}.json")

    def _load_cache(self, key: str):
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_cache(self, key: str, data: dict):
        with open(self._cache_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _fetch_html(self) -> str:
        try:
            resp = requests.get(HACIENDA_URL, timeout=20, headers=HEADERS)
            resp.raise_for_status()
            return resp.text
        except Exception:
            return ""

    def get_fiscal_summary(self) -> dict:
        cached = self._load_cache("fiscal")
        if cached is not None:
            return cached
        html = self._fetch_html()
        result = {"date": str(date.today()), "source": "Ministerio de Hacienda RD"}
        if html:
            text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
            deuda_match = re.search(r"[Dd]euda.*?([\d]+[.,][\d]+)\s*%?\s*(?:del\s*)?PIB", text)
            if deuda_match:
                result["deuda_pib_pct"] = deuda_match.group(1).replace(",", ".")
            self._save_cache("fiscal", result)
        return result

    def get_all(self) -> dict:
        return {"fiscal": self.get_fiscal_summary()}
