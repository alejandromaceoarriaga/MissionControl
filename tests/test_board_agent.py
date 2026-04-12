# tests/test_board_agent.py
import os
from unittest.mock import patch, MagicMock
from agent.sub_agents.board_agent import BoardAgent

SAMPLE_DATA = {
    "bcrd": {
        "tpm": {"value": 5.25, "date": "2026-03-01"},
        "tasas_bancarias": {
            "date": "2026-02-01",
            "bancos_multiples": {"activa": 13.27, "pasiva": 6.14},
            "aayp": {"activa": 14.5, "pasiva": 5.8},
            "bancos_ahorro_credito": {"activa": 15.0, "pasiva": 5.5},
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
                {"entidad": "BanReservas", "_growth_pct": 18.5},
                {"entidad": "Popular", "_growth_pct": 14.2},
                {"entidad": "BHD", "_growth_pct": 11.8},
            ],
            "top_npl_increase": [
                {"entidad": "Banco X", "_growth_pct": 0.9},
                {"entidad": "Banco Y", "_growth_pct": 0.5},
            ],
        }
    },
    "imf": {"capital_adequacy": {"value": 17.5, "year": "2024"}},
    "wb": {"credit_gdp": [{"year": "2024", "value": 31.92}]},
    "hacienda": {"fiscal": {"deuda_pib_pct": "40.2", "date": "2026-04-01"}},
}

def test_generate_creates_pdf(tmp_path):
    agent = BoardAgent(output_dir=str(tmp_path))
    with patch.object(agent, '_get_perspectivas', return_value="Perspectivas de prueba."):
        output = agent.generate(SAMPLE_DATA, period="Abril 2026")
    assert output.endswith(".pdf")
    assert os.path.exists(output)
    assert os.path.getsize(output) > 1000  # non-trivial PDF

def test_build_kpi_summary_returns_dict():
    agent = BoardAgent()
    kpis = agent._build_kpi_summary(SAMPLE_DATA)
    assert "tpm" in kpis
    assert "imae" in kpis
    assert "inflacion" in kpis
    assert "spread_bm" in kpis
    assert kpis["tpm"]["value"] == 5.25
    assert kpis["spread_bm"]["value"] == round(13.27 - 6.14, 2)

def test_semaforo_colors_correct():
    agent = BoardAgent()
    kpis = agent._build_kpi_summary(SAMPLE_DATA)
    # IMAE > 3 → green
    assert kpis["imae"]["color"] == "green"
    # inflacion 3.8 < 5 → green
    assert kpis["inflacion"]["color"] == "green"
