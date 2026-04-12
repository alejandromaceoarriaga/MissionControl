# agent/data_sources/worldbank.py
import json
import os
import requests
from datetime import date

WB_BASE = "https://api.worldbank.org/v2/country/DO/indicator"
INDICATORS = {
    "credit_gdp": "FS.AST.PRVT.GD.ZS",
    "interest_spread": "FR.INR.LNDP",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
}


class WorldBankClient:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{date.today()}-wb-{key}.json")

    def _load_cache(self, key: str):
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_cache(self, key: str, data):
        with open(self._cache_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _fetch(self, indicator_code: str, mrv: int = 5) -> list:
        url = f"{WB_BASE}/{indicator_code}?format=json&mrv={mrv}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        _, data = resp.json()
        return [{"year": d["date"], "value": d["value"]} for d in data if d["value"] is not None]

    def get_credit_to_gdp(self) -> list:
        cached = self._load_cache("credit_gdp")
        if cached is not None:
            return cached
        result = self._fetch(INDICATORS["credit_gdp"])
        self._save_cache("credit_gdp", result)
        return result

    def get_interest_spread(self) -> list:
        cached = self._load_cache("interest_spread")
        if cached is not None:
            return cached
        result = self._fetch(INDICATORS["interest_spread"])
        self._save_cache("interest_spread", result)
        return result

    def get_gdp_growth(self) -> list:
        cached = self._load_cache("gdp_growth")
        if cached is not None:
            return cached
        result = self._fetch(INDICATORS["gdp_growth"])
        self._save_cache("gdp_growth", result)
        return result

    def get_all(self) -> dict:
        return {
            "credit_gdp": self.get_credit_to_gdp(),
            "interest_spread": self.get_interest_spread(),
            "gdp_growth": self.get_gdp_growth(),
        }
