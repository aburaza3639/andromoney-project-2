# Google Drive Source Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded local xlsx path with authenticated Google Drive CSV download as the pipeline's data source.

**Architecture:** A new `andro_drive.py` module handles all Drive concerns (OAuth auth, file search by name, CSV download into memory). `andro_data.py` gains a `get_source()` method that calls Drive when enabled and returns `(source, format)`. `andro_rawdata_get()` branches on format to use `pd.read_csv` or `pd.read_excel`. A settings flag toggles Drive on/off with no other code changes.

**Tech Stack:** `google-auth-oauthlib`, `google-api-python-client`, `pytest`

## Global Constraints

- Python 3.x (see `.python-version`)
- OAuth scope must be `https://www.googleapis.com/auth/drive.readonly` only — no write access
- `credentials.json` and `token.json` must never be committed to git
- `USE_GOOGLE_DRIVE = False` must restore original local-file behavior without requiring Google libs installed
- `andro_control.py`, `andro_writer.py`, `andro_fx.py`, `andro_money.py` must not be modified

---

## File Structure

| File | Role |
|------|------|
| `andromoney/andro_drive.py` | **New** — Drive auth, file search, CSV download |
| `andromoney/settings.py` | Add 4 Drive config fields |
| `andromoney/andro_data.py` | Fix `__init__`, add `get_source()`, update `andro_rawdata_get()` |
| `.gitignore` | Add `credentials.json`, `token.json` |
| `tests/__init__.py` | **New** — empty, makes `tests/` a package |
| `tests/test_andro_drive.py` | **New** — unit tests for `andro_drive.py` |
| `tests/test_andro_data.py` | **New** — unit tests for source resolution in `andro_data.py` |

---

### Task 1: Security configuration — `.gitignore`, `settings.py`, dependencies

**Files:**
- Modify: `.gitignore`
- Modify: `andromoney/settings.py`

**Interfaces:**
- Produces: `settings.USE_GOOGLE_DRIVE`, `settings.DRIVE_FILENAME`, `settings.CREDENTIALS_PATH`, `settings.TOKEN_PATH`

- [ ] **Step 1: Add credentials to `.gitignore`**

Append these two lines to `.gitignore`:
```
credentials.json
token.json
```

- [ ] **Step 2: Add Drive config fields to `settings.py`**

Append to `andromoney/settings.py` after the existing path constants:
```python

# Google Drive integration
USE_GOOGLE_DRIVE: bool = True
DRIVE_FILENAME: str = "AndroMoney"
CREDENTIALS_PATH: str = "credentials.json"
TOKEN_PATH: str = "token.json"
```

- [ ] **Step 3: Install new dependencies**

```bash
pip install google-auth-oauthlib google-api-python-client pytest
```

Expected: packages install without errors.

- [ ] **Step 4: Commit**

```bash
git add .gitignore andromoney/settings.py
git commit -m "config: add Google Drive settings and gitignore credentials"
```

---

### Task 2: Create `andromoney/andro_drive.py`

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_andro_drive.py`
- Create: `andromoney/andro_drive.py`

**Interfaces:**
- Consumes: `settings.TOKEN_PATH`, `settings.CREDENTIALS_PATH`
- Produces:
  - `andro_drive.authenticate() -> google.oauth2.credentials.Credentials`
  - `andro_drive.search_file(service, filename: str) -> str`  — raises `FileNotFoundError` if not found
  - `andro_drive.download_csv(service, file_id: str) -> io.StringIO`

- [ ] **Step 1: Create empty tests package**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 2: Write failing tests**

Create `tests/test_andro_drive.py`:

```python
import io
import os
import pytest
from unittest.mock import patch, MagicMock
import andromoney.settings as settings
import andromoney.andro_drive as andro_drive


class TestAuthenticate:
    def test_returns_cached_token_when_valid(self, tmp_path, monkeypatch):
        token_path = str(tmp_path / "token.json")
        open(token_path, "w").close()
        monkeypatch.setattr(settings, "TOKEN_PATH", token_path)

        mock_creds = MagicMock()
        mock_creds.valid = True

        with patch("andromoney.andro_drive.Credentials.from_authorized_user_file", return_value=mock_creds):
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

        with patch("andromoney.andro_drive.Credentials.from_authorized_user_file", return_value=mock_creds), \
             patch("andromoney.andro_drive.Request"):
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

        with patch("andromoney.andro_drive.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
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

        with patch("andromoney.andro_drive.MediaIoBaseDownload", side_effect=fake_downloader):
            result = andro_drive.download_csv(mock_service, "abc123")

        assert isinstance(result, io.StringIO)
        assert result.read() == csv_content.decode("utf-8-sig")
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_andro_drive.py -v
```
Expected: `ModuleNotFoundError: No module named 'andromoney.andro_drive'`

- [ ] **Step 4: Create `andromoney/andro_drive.py`**

```python
"""
Google Drive authentication and CSV download for AndroMoney pipeline.
"""
import io
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload
import andromoney.settings as settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def authenticate() -> Credentials:
    creds = None
    if os.path.exists(settings.TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(settings.TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(settings.TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
        os.chmod(settings.TOKEN_PATH, 0o600)
    return creds


def search_file(service, filename: str) -> str:
    results = service.files().list(
        q=f"name='{filename}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if not files:
        raise FileNotFoundError(f"No file named '{filename}' found in Google Drive")
    return files[0]["id"]


def download_csv(service, file_id: str) -> io.StringIO:
    request = service.files().export_media(fileId=file_id, mimeType="text/csv")
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return io.StringIO(buffer.read().decode("utf-8-sig"))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_andro_drive.py -v
```
Expected: `6 passed`

- [ ] **Step 6: Commit**

```bash
git add andromoney/andro_drive.py tests/__init__.py tests/test_andro_drive.py
git commit -m "feat: add andro_drive module for Google Drive auth and CSV download"
```

---

### Task 3: Update `andromoney/andro_data.py`

**Files:**
- Create: `tests/test_andro_data.py`
- Modify: `andromoney/andro_data.py`

**Interfaces:**
- Consumes:
  - `andro_drive.authenticate() -> Credentials` (from Task 2)
  - `andro_drive.search_file(service, filename: str) -> str` (from Task 2)
  - `andro_drive.download_csv(service, file_id: str) -> io.StringIO` (from Task 2)
  - `settings.USE_GOOGLE_DRIVE`, `settings.DRIVE_FILENAME`, `settings.XLSX_FILE_PATH`
- Produces:
  - `AndroData.get_source() -> tuple[io.StringIO | str, str]`  — `(source, 'csv')` or `(path, 'excel')`

- [ ] **Step 1: Write failing tests**

Create `tests/test_andro_data.py`:

```python
import io
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
import andromoney.settings as settings
from andromoney.andro_data import AndroData, AndroDataMoney


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

        with patch("andromoney.andro_drive.authenticate", return_value=mock_creds), \
             patch("googleapiclient.discovery.build", return_value=mock_service), \
             patch("andromoney.andro_drive.search_file", return_value="file123"), \
             patch("andromoney.andro_drive.download_csv", return_value=mock_sio):
            ad = AndroData(start_date="20251201", end_date="20251231")
            source, fmt = ad.get_source()

        assert fmt == "csv"
        assert source is mock_sio

    def test_returns_local_path_when_drive_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "USE_GOOGLE_DRIVE", False)
        monkeypatch.setattr(settings, "XLSX_FILE_PATH", "/local/path.xlsx")

        ad = AndroData(start_date="20251201", end_date="20251231")
        source, fmt = ad.get_source()

        assert fmt == "excel"
        assert source == "/local/path.xlsx"


class TestAndroRawdataGet:
    def test_uses_read_csv_for_drive_source(self):
        am = AndroDataMoney(start_date="20251201", end_date="20251231")
        sio = io.StringIO()

        with patch.object(am, "get_source", return_value=(sio, "csv")), \
             patch("andromoney.andro_data.pd.read_csv", return_value=_sample_df()) as mock_read:
            result = am.andro_rawdata_get()
            am.andro_rawdata_get()  # second call — must hit cache, not re-read

        mock_read.assert_called_once_with(sio, index_col=0, header=1)
        assert len(result) == 1
        assert pd.api.types.is_datetime64_any_dtype(result["Date"])
        assert mock_read.call_count == 1

    def test_uses_read_excel_for_local_source(self):
        am = AndroDataMoney(start_date="20251201", end_date="20251231")
        local_path = "/path/to/file.xlsx"

        with patch.object(am, "get_source", return_value=(local_path, "excel")), \
             patch("andromoney.andro_data.pd.read_excel", return_value=_sample_df()) as mock_read:
            result = am.andro_rawdata_get()
            am.andro_rawdata_get()  # second call — must hit cache, not re-read

        mock_read.assert_called_once_with(local_path, index_col=0, header=1)
        assert len(result) == 1
        assert pd.api.types.is_datetime64_any_dtype(result["Date"])
        assert mock_read.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_andro_data.py -v
```
Expected: `AttributeError: type object 'AndroData' has no attribute 'get_source'`

- [ ] **Step 3: Update `andromoney/andro_data.py`**

Replace the full file content with the updated version using `andromoney` imports and `XLSX_FILE_PATH`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_andro_data.py -v
```
Expected: `4 passed`

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: `10 passed`

- [ ] **Step 6: Commit**

```bash
git add andromoney/andro_data.py tests/test_andro_data.py
git commit -m "feat: update andro_data to support Google Drive CSV source"
```

---

## Setup guide (manual steps before first run)

After all tasks are complete, to use Google Drive:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create a project
2. Enable the **Google Drive API** on that project
3. Create **OAuth 2.0 credentials** → Application type: **Desktop app**
4. Download the JSON file and save it as `credentials.json` in the project root
5. Run the pipeline once: `python andro_money.py 20251201 20251231`
6. A browser tab opens — log in and grant read-only Drive access
7. `token.json` is saved automatically; all future runs are silent
