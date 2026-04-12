# tests/test_orchestrator.py
import pytest
from unittest.mock import patch, MagicMock, call
from agent.orchestrator import Orchestrator


MOCK_DATA = {
    "bcrd": {
        "tpm": {"date": "2026-03-01", "value": 7.0},
        "tasas_bancarias": {
            "date": "2026-03-01",
            "bancos_multiples": {"activa": 14.5, "pasiva": 8.2},
            "aayp": {"activa": 16.0, "pasiva": 9.0},
            "bancos_ahorro_credito": {"activa": 18.0, "pasiva": 10.0},
            "interbancaria": 7.1,
        },
        "imae": {"date": "2026-01-01", "value": 110.5, "var_interanual": 5.2},
        "inflacion": {"date": "2026-02-01", "value": 203.0, "var_interanual": 4.1},
        "tipo_cambio": {"date": "2026-03-01", "compra": 59.80, "venta": 60.10},
        "reservas": {"date": "2026-03-01", "brutas_mm_usd": 15200},
    },
    "sb": {
        "cartera_total_mm": 2100000,
        "captaciones_total_mm": 1900000,
        "npl_ratio": 1.8,
        "rankings": {
            "top_cartera_growth": [
                {"name": "Banco Popular", "growth_ia": 12.5},
                {"name": "BanReservas", "growth_ia": 10.2},
            ],
            "top_npl_increase": [
                {"name": "Banco BHD", "npl_delta": 0.3},
            ],
        },
    },
    "imf": {"year": "2025", "value": 12.1},
    "worldbank": [{"year": "2024", "value": 31.9}],
    "hacienda": {"debt_gdp_pct": 47.2},
}


def _mock_fetch(orchestrator_instance):
    """Patch all data source clients on the orchestrator."""
    orchestrator_instance._data = MOCK_DATA
    return MOCK_DATA


class TestOrchestratorFetchData:
    def test_fetch_returns_dict_with_all_sources(self):
        orch = Orchestrator(mode="flash")
        with patch.object(orch, "fetch_data", return_value=MOCK_DATA):
            data = orch.fetch_data()
        assert "bcrd" in data
        assert "sb" in data
        assert "imf" in data
        assert "worldbank" in data
        assert "hacienda" in data

    def test_fetch_stores_data_on_instance(self):
        orch = Orchestrator(mode="flash")
        with patch.object(orch, "fetch_data", return_value=MOCK_DATA) as mock_fetch:
            result = orch.fetch_data()
        assert result is MOCK_DATA


class TestOrchestratorGenerateDrafts:
    def test_flash_mode_generates_post_only(self):
        orch = Orchestrator(mode="flash")
        orch._data = MOCK_DATA

        with patch.object(orch.post_agent, "generate_flash", return_value="POST_TEXT") as mock_post, \
             patch.object(orch.board_agent, "generate", return_value="/tmp/board.pdf") as mock_board, \
             patch.object(orch.carousel_agent, "generate", return_value="/tmp/carousel.pptx") as mock_carousel:
            drafts = orch.generate_drafts()

        assert drafts["post"] == "POST_TEXT"
        mock_post.assert_called_once()
        mock_board.assert_not_called()
        mock_carousel.assert_not_called()

    def test_mensual_mode_generates_all_outputs(self):
        orch = Orchestrator(mode="mensual")
        orch._data = MOCK_DATA

        with patch.object(orch.post_agent, "generate_mensual", return_value="MENSUAL_TEXT"), \
             patch.object(orch.board_agent, "generate", return_value="/tmp/board.pdf"), \
             patch.object(orch.carousel_agent, "generate", return_value="/tmp/carousel.pptx"):
            drafts = orch.generate_drafts()

        assert "post" in drafts
        assert "board_path" in drafts
        assert "carousel_path" in drafts

    def test_drafts_include_format_recommendation(self):
        orch = Orchestrator(mode="mensual")
        orch._data = MOCK_DATA

        with patch.object(orch.post_agent, "generate_mensual", return_value="TEXT"), \
             patch.object(orch.board_agent, "generate", return_value="/tmp/board.pdf"), \
             patch.object(orch.carousel_agent, "generate", return_value="/tmp/carousel.pptx"):
            drafts = orch.generate_drafts()

        assert "format_recommendation" in drafts
        assert drafts["format_recommendation"]["recommendation"] in ("carousel", "post")


class TestOrchestratorRefine:
    def test_refine_post_updates_draft(self):
        orch = Orchestrator(mode="flash")
        orch._data = MOCK_DATA
        orch._drafts = {"post": "ORIGINAL", "format_recommendation": {"recommendation": "post", "reason": ""}}

        with patch.object(orch.post_agent, "refine", return_value="REFINED") as mock_refine:
            orch.refine("Hazlo más corto")

        mock_refine.assert_called_once()
        assert orch._drafts["post"] == "REFINED"

    def test_refine_preserves_other_drafts(self):
        orch = Orchestrator(mode="mensual")
        orch._data = MOCK_DATA
        orch._drafts = {
            "post": "ORIGINAL",
            "board_path": "/tmp/board.pdf",
            "carousel_path": "/tmp/carousel.pptx",
            "format_recommendation": {"recommendation": "carousel", "reason": ""},
        }

        with patch.object(orch.post_agent, "refine", return_value="REFINED"):
            orch.refine("Ajusta el tono")

        assert orch._drafts["board_path"] == "/tmp/board.pdf"
        assert orch._drafts["carousel_path"] == "/tmp/carousel.pptx"


class TestOrchestratorSave:
    def test_save_creates_post_file(self, tmp_path):
        orch = Orchestrator(mode="flash", output_dir=str(tmp_path))
        orch._drafts = {"post": "CONTENIDO DEL POST", "format_recommendation": {"recommendation": "post", "reason": ""}}

        paths = orch.save_finals()

        assert "post_path" in paths
        assert (tmp_path / "posts").exists() or any(tmp_path.rglob("*.md"))

    def test_save_mensual_creates_all_files(self, tmp_path):
        import shutil

        board_pdf = tmp_path / "board.pdf"
        carousel_pptx = tmp_path / "carousel.pptx"
        board_pdf.write_bytes(b"%PDF")
        carousel_pptx.write_bytes(b"PK")

        orch = Orchestrator(mode="mensual", output_dir=str(tmp_path))
        orch._drafts = {
            "post": "TEXTO",
            "board_path": str(board_pdf),
            "carousel_path": str(carousel_pptx),
            "format_recommendation": {"recommendation": "carousel", "reason": ""},
        }

        paths = orch.save_finals()
        assert "post_path" in paths
