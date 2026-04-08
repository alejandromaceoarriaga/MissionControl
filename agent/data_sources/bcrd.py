# agent/data_sources/bcrd.py
import json
import os
import re
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

BCRD_STATS_URL = "https://www.bancentral.gov.do/a/d/2545-estadisticas-economicas-mercado-cambiario"


class BCRDClient:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{date.today()}-bcrd-{key}.json")

    def _load_cache(self, key: str):
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_cache(self, key: str, data: dict):
        with open(self._cache_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _download_excel(self, url: str) -> pd.DataFrame:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return pd.read_excel(BytesIO(resp.content), sheet_name=0)

    def _last_numeric(self, df: pd.DataFrame, col_idx: int = 1):
        col = df.columns[col_idx]
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        return float(series.iloc[-1]) if len(series) else None

    def get_tpm(self) -> dict:
        cached = self._load_cache("tpm")
        if cached:
            return cached
        df = self._download_excel(URLS["tpm"])
        numeric_col = df.columns[-1]
        series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
        date_col = df.columns[0]
        last_idx = series.index[-1]
        result = {
            "value": float(series.iloc[-1]),
            "date": str(df[date_col].iloc[last_idx]),
        }
        self._save_cache("tpm", result)
        return result

    def get_tasas_bancarias(self) -> dict:
        cached = self._load_cache("tasas_bancarias")
        if cached:
            return cached
        df_act = self._download_excel(URLS["tasas_activas"])
        df_pas = self._download_excel(URLS["tasas_pasivas"])
        df_int = self._download_excel(URLS["interbancaria"])

        result = {
            "date": str(df_act.iloc[-1, 0]),
            "bancos_multiples": {
                "activa": self._last_numeric(df_act, 1),
                "pasiva": self._last_numeric(df_pas, 1),
            },
            "aayp": {
                "activa": self._last_numeric(df_act, 2) if df_act.shape[1] > 2 else None,
                "pasiva": self._last_numeric(df_pas, 2) if df_pas.shape[1] > 2 else None,
            },
            "bancos_ahorro_credito": {
                "activa": self._last_numeric(df_act, 3) if df_act.shape[1] > 3 else None,
                "pasiva": self._last_numeric(df_pas, 3) if df_pas.shape[1] > 3 else None,
            },
            "interbancaria": self._last_numeric(df_int, 1),
        }
        self._save_cache("tasas_bancarias", result)
        return result

    def get_imae(self) -> dict:
        cached = self._load_cache("imae")
        if cached:
            return cached
        df = self._download_excel(URLS["imae"])
        numeric_col = df.columns[1]
        series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
        val = float(series.iloc[-1])
        var_ia = None
        if len(series) > 12:
            val_prev = float(series.iloc[-13])
            var_ia = round((val - val_prev) / abs(val_prev) * 100, 2)
        result = {
            "date": str(df.iloc[series.index[-1], 0]),
            "value": val,
            "var_interanual": var_ia,
        }
        self._save_cache("imae", result)
        return result

    def get_inflacion(self) -> dict:
        cached = self._load_cache("inflacion")
        if cached:
            return cached
        df = self._download_excel(URLS["ipc"])
        numeric_col = df.columns[1]
        series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
        val = float(series.iloc[-1])
        var_ia = None
        if len(series) > 12:
            val_prev = float(series.iloc[-13])
            var_ia = round((val - val_prev) / abs(val_prev) * 100, 2)
        result = {
            "date": str(df.iloc[series.index[-1], 0]),
            "value": val,
            "var_interanual": var_ia,
        }
        self._save_cache("inflacion", result)
        return result

    def get_tipo_cambio(self) -> dict:
        cached = self._load_cache("tipo_cambio")
        if cached:
            return cached
        try:
            resp = requests.get(BCRD_STATS_URL, timeout=15)
            text = resp.text
            compra_match = re.search(r"[Cc]ompra[:\s]+([\d.]+)", text)
            venta_match = re.search(r"[Vv]enta[:\s]+([\d.]+)", text)
            result = {
                "date": str(date.today()),
                "compra": float(compra_match.group(1)) if compra_match else None,
                "venta": float(venta_match.group(1)) if venta_match else None,
            }
        except Exception as e:
            result = {"date": str(date.today()), "compra": None, "venta": None, "error": str(e)}
        self._save_cache("tipo_cambio", result)
        return result

    def get_reservas(self) -> dict:
        cached = self._load_cache("reservas")
        if cached:
            return cached
        df = self._download_excel(URLS["reservas"])
        numeric_col = df.columns[1]
        series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
        result = {
            "date": str(df.iloc[series.index[-1], 0]),
            "brutas_mm_usd": float(series.iloc[-1]),
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
