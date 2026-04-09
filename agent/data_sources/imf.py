# agent/data_sources/imf.py
import json
import os
import requests
from datetime import date

IMF_BASE = "https://www.imf.org/external/datamapper/api/v1"
INDICATORS = {
    "capital_adequacy": "FSI_BCS_MT",
    "npl_ratio": "FSI_BCS_NN",
    "roe": "FSI_BCS_RE",
}


class IMFClient:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{date.today()}-imf-{key}.json")

    def _load_cache(self, key: str):
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_cache(self, key: str, data: dict):
        with open(self._cache_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _fetch_indicator(self, indicator_code: str, country: str = "DOM") -> dict:
        url = f"{IMF_BASE}/{indicator_code}/{country}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            values = data.get("values", {}).get(indicator_code, {}).get(country, {})
            if values:
                latest_year = max(values.keys())
                return {"year": latest_year, "value": float(values[latest_year])}
        except Exception:
            pass
        return {"year": None, "value": None}

    def get_capital_adequacy(self) -> dict:
        cached = self._load_cache("capital_adequacy")
        if cached is not None:
            return cached
        result = self._fetch_indicator(INDICATORS["capital_adequacy"])
        if result["value"] is not None:
            self._save_cache("capital_adequacy", result)
        return result

    def get_npl_ratio(self) -> dict:
        cached = self._load_cache("npl_ratio")
        if cached is not None:
            return cached
        result = self._fetch_indicator(INDICATORS["npl_ratio"])
        if result["value"] is not None:
            self._save_cache("npl_ratio", result)
        return result

    def get_roe(self) -> dict:
        cached = self._load_cache("roe_imf")
        if cached is not None:
            return cached
        result = self._fetch_indicator(INDICATORS["roe"])
        if result["value"] is not None:
            self._save_cache("roe_imf", result)
        return result

    def get_all(self) -> dict:
        return {
            "capital_adequacy": self.get_capital_adequacy(),
            "npl_ratio": self.get_npl_ratio(),
            "roe": self.get_roe(),
        }
