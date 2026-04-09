# tests/test_superbancos.py
from unittest.mock import patch
from agent.data_sources.superbancos import SuperbancosClient

MOCK_HTML = """
<html><body>
<table>
<tr><th>Entidad</th><th>ROE</th><th>ROA</th><th>IAC</th><th>Morosidad</th><th>Cartera</th><th>Cartera_prev</th></tr>
<tr><td>BanReservas</td><td>18.5</td><td>1.2</td><td>14.2</td><td>1.8</td><td>450000</td><td>380000</td></tr>
<tr><td>Banco Popular</td><td>20.1</td><td>1.5</td><td>15.1</td><td>1.5</td><td>380000</td><td>340000</td></tr>
<tr><td>Scotiabank</td><td>15.0</td><td>0.9</td><td>13.5</td><td>2.1</td><td>120000</td><td>108000</td></tr>
</table>
</body></html>
"""

def test_get_system_indicators_returns_entities(tmp_path):
    client = SuperbancosClient(cache_dir=str(tmp_path))
    with patch.object(client, '_fetch_html', return_value=MOCK_HTML):
        result = client.get_system_indicators()
    assert 'entities' in result
    assert len(result['entities']) == 3

def test_rank_by_growth_sorts_descending(tmp_path):
    client = SuperbancosClient(cache_dir=str(tmp_path))
    entities = [
        {"name": "A", "cartera": 100.0, "cartera_prev": 80.0},
        {"name": "B", "cartera": 200.0, "cartera_prev": 190.0},
        {"name": "C", "cartera": 50.0, "cartera_prev": 30.0},
    ]
    top = client._rank_by_growth(entities, "cartera", "cartera_prev", n=3)
    assert top[0]["name"] == "C"   # ~67% growth
    assert top[1]["name"] == "A"   # 25% growth
    assert top[2]["name"] == "B"   # ~5% growth

def test_get_rankings_returns_top_lists(tmp_path):
    client = SuperbancosClient(cache_dir=str(tmp_path))
    with patch.object(client, '_fetch_html', return_value=MOCK_HTML):
        result = client.get_rankings()
    assert 'top_cartera_growth' in result
    assert 'top_npl_increase' in result

def test_fetch_html_error_returns_empty_string(tmp_path):
    client = SuperbancosClient(cache_dir=str(tmp_path))
    with patch('agent.data_sources.superbancos.requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        html = client._fetch_html()
    assert html == ""
