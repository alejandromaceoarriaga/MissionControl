# tests/test_bcrd.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from io import BytesIO
from agent.data_sources.bcrd import BCRDClient

def _make_excel(data: dict) -> bytes:
    """Helper: create in-memory Excel bytes from a dict of {col: [values]}"""
    df = pd.DataFrame(data)
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()

def test_get_tpm_returns_float(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    excel_bytes = _make_excel({'Fecha': ['2026-03-01'], 'TPM': [5.25]})
    with patch.object(client, '_download_excel', return_value=pd.read_excel(BytesIO(excel_bytes))):
        result = client.get_tpm()
    assert isinstance(result['value'], float)
    assert result['value'] == 5.25
    assert 'date' in result

def test_get_tasas_bancarias_returns_dict(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    activa_bytes = _make_excel({'Fecha': ['2026-02-01'], 'BM': [13.27], 'AAyP': [14.5], 'BAC': [15.0]})
    pasiva_bytes = _make_excel({'Fecha': ['2026-02-01'], 'BM': [6.14], 'AAyP': [5.8], 'BAC': [5.5]})
    inter_bytes = _make_excel({'Fecha': ['2026-02-01'], 'Tasa': [6.06]})
    call_count = [0]
    excels = [
        pd.read_excel(BytesIO(activa_bytes)),
        pd.read_excel(BytesIO(pasiva_bytes)),
        pd.read_excel(BytesIO(inter_bytes)),
    ]
    def fake_download(url):
        result = excels[call_count[0] % len(excels)]
        call_count[0] += 1
        return result
    with patch.object(client, '_download_excel', side_effect=fake_download):
        result = client.get_tasas_bancarias()
    assert 'bancos_multiples' in result
    assert 'activa' in result['bancos_multiples']
    assert 'pasiva' in result['bancos_multiples']
    assert 'aayp' in result
    assert 'bancos_ahorro_credito' in result
    assert 'interbancaria' in result

def test_cache_is_used_on_second_call(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    excel_bytes = _make_excel({'Fecha': ['2026-03-01'], 'TPM': [5.25]})
    df = pd.read_excel(BytesIO(excel_bytes))
    with patch.object(client, '_download_excel', return_value=df) as mock_dl:
        client.get_tpm()
        client.get_tpm()
    assert mock_dl.call_count == 1  # second call uses cache

def test_get_imae_returns_var_interanual(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    # 14 rows: current + 13 months ago
    fechas = [f'2025-0{i+1}-01' for i in range(9)] + ['2025-10-01', '2025-11-01', '2025-12-01', '2026-01-01', '2026-02-01']
    valores = [100.0 + i for i in range(14)]
    excel_bytes = _make_excel({'Fecha': fechas, 'IMAE': valores})
    with patch.object(client, '_download_excel', return_value=pd.read_excel(BytesIO(excel_bytes))):
        result = client.get_imae()
    assert 'var_interanual' in result
    assert isinstance(result['var_interanual'], float)

def test_get_inflacion_returns_var_interanual(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    fechas = [f'2025-0{i+1}-01' for i in range(9)] + ['2025-10-01', '2025-11-01', '2025-12-01', '2026-01-01', '2026-02-01']
    valores = [100.0 + i * 0.5 for i in range(14)]
    excel_bytes = _make_excel({'Fecha': fechas, 'IPC': valores})
    with patch.object(client, '_download_excel', return_value=pd.read_excel(BytesIO(excel_bytes))):
        result = client.get_inflacion()
    assert 'var_interanual' in result
    assert isinstance(result['var_interanual'], float)
    assert 'value' in result

def test_get_reservas_returns_float(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    excel_bytes = _make_excel({'Fecha': ['2026-03-01'], 'Reservas': [16143.1]})
    with patch.object(client, '_download_excel', return_value=pd.read_excel(BytesIO(excel_bytes))):
        result = client.get_reservas()
    assert 'brutas_mm_usd' in result
    assert isinstance(result['brutas_mm_usd'], float)
    assert result['brutas_mm_usd'] == 16143.1

def test_get_tipo_cambio_uses_seam(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    html = '<html><body>Compra: 60.55 Venta: 61.19</body></html>'
    with patch.object(client, '_fetch_tipo_cambio_html', return_value=html) as mock_html:
        result = client.get_tipo_cambio()
    mock_html.assert_called_once()
    assert result['compra'] == 60.55
    assert result['venta'] == 61.19

def test_get_tpm_empty_series_returns_none(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    # All NaN column
    excel_bytes = _make_excel({'Fecha': ['2026-03-01'], 'TPM': [float('nan')]})
    with patch.object(client, '_download_excel', return_value=pd.read_excel(BytesIO(excel_bytes))):
        result = client.get_tpm()
    assert result['value'] is None

def test_get_all_returns_all_keys(tmp_path):
    client = BCRDClient(cache_dir=str(tmp_path))
    excel_bytes = _make_excel({'Fecha': ['2026-03-01'], 'Val': [5.25]})
    df = pd.read_excel(BytesIO(excel_bytes))
    with patch.object(client, '_download_excel', return_value=df):
        with patch.object(client, 'get_tipo_cambio', return_value={'compra': 60.55, 'venta': 61.19, 'date': '2026-04-01'}):
            result = client.get_all()
    expected_keys = {'tpm', 'tasas_bancarias', 'imae', 'inflacion', 'tipo_cambio', 'reservas'}
    assert expected_keys.issubset(set(result.keys()))
