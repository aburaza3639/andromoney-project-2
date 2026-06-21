import io
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
import AndroMoney.settings as settings
from AndroMoney.andro_data import AndroData, AndroDataMoney


def _sample_df():
    """Two-row DataFrame: one real transaction, one sentinel row."""
    return pd.DataFrame({
        "Date": [20251201, 10100101],
        "Category": ["食料品", "SENTINEL"],
        "Currency": ["SGD", "SGD"],
        "Amount": [10.0, 0.0],
    })


class TestGetSource:
    def test_returns_drive_stream_when_drive_enabled(self, monkeypatch):
        monkeypatch.setattr(settings, "USE_GOOGLE_DRIVE", True)
        monkeypatch.setattr(settings, "DRIVE_FILENAME", "AndroMoney.csv")

        mock_sio = io.StringIO("data")
        mock_creds = MagicMock()
        mock_service = MagicMock()

        with patch("AndroMoney.andro_drive.authenticate", return_value=mock_creds), \
             patch("googleapiclient.discovery.build", return_value=mock_service), \
             patch("AndroMoney.andro_drive.search_file", return_value="file123"), \
             patch("AndroMoney.andro_drive.download_csv", return_value=mock_sio):
            ad = AndroData(start_date="20251201", end_date="20251231")
            source, fmt = ad.get_source()

        assert fmt == "csv"
        assert source is mock_sio

    def test_returns_local_path_when_drive_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "USE_GOOGLE_DRIVE", False)
        monkeypatch.setattr(settings, "xlsx_FILE_PATH", "/local/path.xlsx")

        ad = AndroData(start_date="20251201", end_date="20251231")
        source, fmt = ad.get_source()

        assert fmt == "excel"
        assert source == "/local/path.xlsx"


class TestAndroRawdataGet:
    def test_uses_read_csv_for_drive_source(self):
        am = AndroDataMoney(start_date="20251201", end_date="20251231")
        sio = io.StringIO()

        with patch.object(am, "get_source", return_value=(sio, "csv")), \
             patch("AndroMoney.andro_data.pd.read_csv", return_value=_sample_df()) as mock_read:
            result = am.andro_rawdata_get()

        mock_read.assert_called_once_with(sio, index_col=0, header=1)
        assert len(result) == 1
        assert pd.api.types.is_datetime64_any_dtype(result["Date"])

    def test_uses_read_excel_for_local_source(self):
        am = AndroDataMoney(start_date="20251201", end_date="20251231")
        local_path = "/path/to/file.xlsx"

        with patch.object(am, "get_source", return_value=(local_path, "excel")), \
             patch("AndroMoney.andro_data.pd.read_excel", return_value=_sample_df()) as mock_read:
            result = am.andro_rawdata_get()

        mock_read.assert_called_once_with(local_path, index_col=0, header=1)
        assert len(result) == 1
        assert pd.api.types.is_datetime64_any_dtype(result["Date"])
