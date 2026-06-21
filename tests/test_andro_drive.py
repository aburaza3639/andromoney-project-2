import io
import os
import pytest
from unittest.mock import patch, MagicMock
import AndroMoney.settings as settings
import AndroMoney.andro_drive as andro_drive


class TestAuthenticate:
    def test_returns_cached_token_when_valid(self, tmp_path, monkeypatch):
        token_path = str(tmp_path / "token.json")
        open(token_path, "w").close()
        monkeypatch.setattr(settings, "TOKEN_PATH", token_path)

        mock_creds = MagicMock()
        mock_creds.valid = True

        with patch("AndroMoney.andro_drive.Credentials.from_authorized_user_file", return_value=mock_creds):
            result = andro_drive.authenticate()

        assert result is mock_creds

    def test_refreshes_expired_token(self, tmp_path, monkeypatch):
        token_path = str(tmp_path / "token.json")
        open(token_path, "w").close()
        monkeypatch.setattr(settings, "TOKEN_PATH", token_path)

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "some-token"
        mock_creds.to_json.return_value = "{}"

        with patch("AndroMoney.andro_drive.Credentials.from_authorized_user_file", return_value=mock_creds), \
             patch("AndroMoney.andro_drive.Request"):
            result = andro_drive.authenticate()

        mock_creds.refresh.assert_called_once()
        assert result is mock_creds

    def test_runs_oauth_flow_when_no_token(self, tmp_path, monkeypatch):
        token_path = str(tmp_path / "token.json")
        creds_path = str(tmp_path / "credentials.json")
        monkeypatch.setattr(settings, "TOKEN_PATH", token_path)
        monkeypatch.setattr(settings, "CREDENTIALS_PATH", creds_path)

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = "{}"

        with patch("AndroMoney.andro_drive.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
            mock_flow_cls.return_value.run_local_server.return_value = mock_creds
            result = andro_drive.authenticate()

        assert result is mock_creds
        assert os.path.exists(token_path)


class TestSearchFile:
    def test_returns_file_id_on_match(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {
            "files": [{"id": "abc123", "name": "AndroMoney.csv"}]
        }

        result = andro_drive.search_file(mock_service, "AndroMoney.csv")

        assert result == "abc123"

    def test_raises_when_no_file_found(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {"files": []}

        with pytest.raises(FileNotFoundError, match="AndroMoney.csv"):
            andro_drive.search_file(mock_service, "AndroMoney.csv")


class TestDownloadCsv:
    def test_returns_stringio_with_csv_content(self):
        csv_content = b"\xef\xbb\xbfcol1,col2\nval1,val2\n"
        mock_service = MagicMock()

        def fake_downloader(buffer, request):
            m = MagicMock()
            def fake_next_chunk():
                buffer.write(csv_content)
                return None, True
            m.next_chunk = fake_next_chunk
            return m

        with patch("AndroMoney.andro_drive.MediaIoBaseDownload", side_effect=fake_downloader):
            result = andro_drive.download_csv(mock_service, "abc123")

        assert isinstance(result, io.StringIO)
        assert result.read() == csv_content.decode("utf-8-sig")  # BOM stripped
