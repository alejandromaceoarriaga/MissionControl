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
    with patch.object(agent, '_call_claude', return_value="📊 TPM: 5.25%"):
        result = agent.generate_flash(SAMPLE_DATA, indicator="tpm")
    assert isinstance(result, str)
    assert len(result) > 5

def test_generate_mensual_returns_string():
    agent = PostAgent()
    with patch.object(agent, '_call_claude', return_value="🏦 Barómetro Bancario Dominicano | Marzo 2026\n..."):
        result = agent.generate_mensual(SAMPLE_DATA)
    assert isinstance(result, str)
    assert len(result) > 10

def test_refine_returns_different_string():
    agent = PostAgent()
    draft = "Post draft inicial"
    with patch.object(agent, '_call_claude', return_value="Post refinado con más detalle"):
        result = agent.refine(draft, "hazlo más técnico", SAMPLE_DATA)
    assert isinstance(result, str)
    assert result != draft

def test_call_claude_uses_anthropic_client():
    agent = PostAgent()
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="respuesta del modelo")]
    with patch.object(agent.client.messages, 'create', return_value=mock_msg) as mock_create:
        result = agent._call_claude("prompt de prueba")
    mock_create.assert_called_once()
    assert result == "respuesta del modelo"
