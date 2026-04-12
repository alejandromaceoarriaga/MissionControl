# tests/test_imf.py
import pytest
from unittest.mock import patch
from agent.data_sources.imf import IMFClient

def test_get_capital_adequacy_returns_dict(tmp_path):
    client = IMFClient(cache_dir=str(tmp_path))
    with patch('agent.data_sources.imf.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "values": {"FSI_BCS_MT": {"DOM": {"2023": "17.5", "2024": "18.2"}}}
        }
        mock_get.return_value.raise_for_status = lambda: None
        result = client.get_capital_adequacy()
    assert 'value' in result
    assert 'year' in result
    assert result['value'] == 18.2
    assert result['year'] == "2024"

def test_imf_returns_none_on_api_error(tmp_path):
    client = IMFClient(cache_dir=str(tmp_path))
    with patch('agent.data_sources.imf.requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        result = client.get_capital_adequacy()
    assert result['value'] is None

def test_get_all_returns_expected_keys(tmp_path):
    client = IMFClient(cache_dir=str(tmp_path))
    with patch('agent.data_sources.imf.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "values": {"FSI_BCS_MT": {"DOM": {"2024": "17.5"}},
                       "FSI_BCS_NN": {"DOM": {"2024": "2.1"}},
                       "FSI_BCS_RE": {"DOM": {"2024": "12.3"}}}
        }
        mock_get.return_value.raise_for_status = lambda: None
        result = client.get_all()
    assert set(result.keys()) >= {"capital_adequacy", "npl_ratio", "roe"}
