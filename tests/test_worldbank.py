# tests/test_worldbank.py
import pytest
from unittest.mock import patch
from agent.data_sources.worldbank import WorldBankClient

def test_get_credit_gdp_returns_list(tmp_path):
    client = WorldBankClient(cache_dir=str(tmp_path))
    with patch('agent.data_sources.worldbank.requests.get') as mock_get:
        mock_get.return_value.json.return_value = [
            {"pages": 1},
            [{"date": "2024", "value": 31.92}, {"date": "2023", "value": 30.84}, {"date": "2022", "value": None}]
        ]
        mock_get.return_value.raise_for_status = lambda: None
        result = client.get_credit_to_gdp()
    assert isinstance(result, list)
    assert len(result) == 2  # None values filtered out
    assert result[0]['year'] == "2024"
    assert result[0]['value'] == 31.92

def test_cache_prevents_second_request(tmp_path):
    client = WorldBankClient(cache_dir=str(tmp_path))
    with patch('agent.data_sources.worldbank.requests.get') as mock_get:
        mock_get.return_value.json.return_value = [{"pages": 1}, [{"date": "2024", "value": 31.92}]]
        mock_get.return_value.raise_for_status = lambda: None
        client.get_credit_to_gdp()
        client.get_credit_to_gdp()
    assert mock_get.call_count == 1

def test_get_all_returns_expected_keys(tmp_path):
    client = WorldBankClient(cache_dir=str(tmp_path))
    with patch('agent.data_sources.worldbank.requests.get') as mock_get:
        mock_get.return_value.json.return_value = [{"pages": 1}, [{"date": "2024", "value": 5.0}]]
        mock_get.return_value.raise_for_status = lambda: None
        result = client.get_all()
    assert set(result.keys()) >= {"credit_gdp", "interest_spread", "gdp_growth"}
