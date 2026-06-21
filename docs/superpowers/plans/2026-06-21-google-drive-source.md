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
| `AndroMoney/andro_drive.py` | **New** — Drive auth, file search, CSV download |
| `AndroMoney/settings.py` | Add 4 Drive config fields |
| `AndroMoney/andro_data.py` | Fix `__init__`, add `get_source()`, update `andro_rawdata_get()` |
| `.gitignore` | Add `credentials.json`, `token.json` |
| `tests/__init__.py` | **New** — empty, makes `tests/` a package |
| `tests/test_andro_drive.py` | **New** — unit tests for `andro_drive.py` |
| `tests/test_andro_data.py` | **New** — unit tests for source resolution in `andro_data.py` |

---

### Task 1: Security configuration — `.gitignore`, `settings.py`, dependencies

**Files:**
- Modify: `.gitignore`
- Modify: `AndroMoney/settings.py`

**Interfaces:**
- Produces: `settings.USE_GOOGLE_DRIVE`, `settings.DRIVE_FILENAME`, `settings.CREDENTIALS_PATH`, `settings.TOKEN_PATH`

- [ ] **Step 1: Add credentials to `.gitignore`**

Append these two lines to `.gitignore`:
```
credentials.json
token.json
```

- [ ] **Step 2: Add Drive config fields to `settings.py`**

Append to `AndroMoney/settings.py` after the existing path constants:
```python

# Google Drive integration
USE_GOOGLE_DRIVE: bool = True
DRIVE_FILENAME: str = "AndroMoney.csv"
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
git add .gitignore AndroMoney/settings.py
git commit -m "config: add Google Drive settings and gitignore credentials"
```

---

### Task 2: Create `AndroMoney/andro_drive.py`

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_andro_drive.py`
- Create: `AndroMoney/andro_drive.py`

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
        csv_content = b"col1,col2\nval1,val2\n"
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
        assert result.read() == csv_content.decode("utf-8")
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_andro_drive.py -v
```
Expected: `ModuleNotFoundError: No module named 'AndroMoney.andro_drive'`

- [ ] **Step 4: Create `AndroMoney/andro_drive.py`**

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
import AndroMoney.settings as settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def authenticate() -> Credentials:
    """Return valid OAuth credentials, running browser flow on first use.

    Loads token from settings.TOKEN_PATH if present. On expiry, refreshes
    automatically. On first run (no token), opens a browser for consent and
    saves the new token to settings.TOKEN_PATH.
    """
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
    return creds


def search_file(service, filename: str) -> str:
    """Return the Drive file ID of the first file matching filename.

    Args:
        service:  Authenticated Drive API service client.
        filename: Exact filename to search for (e.g. 'AndroMoney.csv').

    Raises:
        FileNotFoundError: If no file with that name exists in Drive.
    """
    results = service.files().list(
        q=f"name='{filename}' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if not files:
        raise FileNotFoundError(f"No file named '{filename}' found in Google Drive")
    return files[0]["id"]


def download_csv(service, file_id: str) -> io.StringIO:
    """Download a Drive file and return its content as a StringIO.

    Args:
        service:  Authenticated Drive API service client.
        file_id:  Drive file ID to download.

    Returns:
        io.StringIO with the file content decoded as UTF-8.
    """
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return io.StringIO(buffer.read().decode("utf-8"))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_andro_drive.py -v
```
Expected: `6 passed`

- [ ] **Step 6: Commit**

```bash
git add AndroMoney/andro_drive.py tests/__init__.py tests/test_andro_drive.py
git commit -m "feat: add andro_drive module for Google Drive auth and CSV download"
```

---

### Task 3: Update `AndroMoney/andro_data.py`

**Files:**
- Create: `tests/test_andro_data.py`
- Modify: `AndroMoney/andro_data.py`

**Interfaces:**
- Consumes:
  - `andro_drive.authenticate() -> Credentials` (from Task 2)
  - `andro_drive.search_file(service, filename: str) -> str` (from Task 2)
  - `andro_drive.download_csv(service, file_id: str) -> io.StringIO` (from Task 2)
  - `settings.USE_GOOGLE_DRIVE`, `settings.DRIVE_FILENAME`, `settings.xlsx_FILE_PATH`
- Produces:
  - `AndroData.get_source() -> tuple[io.StringIO | str, str]`  — `(source, 'csv')` or `(path, 'excel')`

- [ ] **Step 1: Write failing tests**

Create `tests/test_andro_data.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_andro_data.py -v
```
Expected: `AttributeError: type object 'AndroData' has no attribute 'get_source'`

- [ ] **Step 3: Update `AndroMoney/andro_data.py`**

Replace the full file content with:

```python
"""
Data loading and transformation layer for AndroMoney transaction exports.

Provides two classes:
    AndroData       — base class handling source resolution (local or Google Drive).
    AndroDataMoney  — subclass that reads, filters, pivots, and applies FX
                      conversion to produce a SGD-normalised expense summary.
"""
import pandas as pd
import numpy as np
import AndroMoney.andro_fx
import AndroMoney.settings
import datetime


class AndroData(object):
    """Base class for AndroMoney data sources.

    Attributes:
        xlsx_file:  Local path fallback used when USE_GOOGLE_DRIVE is False.
        start_date: Filter start in YYYYMMDD format.
        end_date:   Filter end   in YYYYMMDD format.
    """

    def __init__(self, xlsx_file=None, start_date=None, end_date=None):
        self.xlsx_file = xlsx_file if xlsx_file else AndroMoney.settings.xlsx_FILE_PATH
        self.start_date = start_date
        self.end_date = end_date

    def get_source(self):
        """Return (source, format) for the pipeline data source.

        Returns:
            (io.StringIO, 'csv') when USE_GOOGLE_DRIVE is True —
                downloads AndroMoney.csv from Google Drive into memory.
            (str path, 'excel') when USE_GOOGLE_DRIVE is False —
                uses the local xlsx path from settings.
        """
        if AndroMoney.settings.USE_GOOGLE_DRIVE:
            import AndroMoney.andro_drive as _drive
            from googleapiclient.discovery import build
            creds = _drive.authenticate()
            service = build("drive", "v3", credentials=creds)
            file_id = _drive.search_file(service, AndroMoney.settings.DRIVE_FILENAME)
            sio = _drive.download_csv(service, file_id)
            return sio, "csv"
        return self.xlsx_file, "excel"


class AndroDataMoney(AndroData):
    """Reads and transforms AndroMoney transaction data."""

    def andro_rawdata_get(self):
        """Load the full transaction history from the configured source.

        Drops the sentinel row (Date == 10100101) and parses the Date column
        to datetime.

        Returns:
            DataFrame with all transactions, Date as datetime.
        """
        source, fmt = self.get_source()
        if fmt == "csv":
            df = pd.read_csv(source, index_col=0, header=1)
        else:
            df = pd.read_excel(source, index_col=0, header=1)
        drop_index = df.index[df["Date"] == 10100101]
        df = df.drop(drop_index)
        df["Date"] = pd.to_datetime(df["Date"].astype(str))
        return df

    def andro_data_get(self):
        """Filter raw transactions to the configured date range.

        Returns:
            DataFrame containing only rows where start_date <= Date <= end_date.
        """
        df = self.andro_rawdata_get()
        df1 = df.query("@self.end_date>=Date>=@self.start_date")
        return df1

    def andro_pivot_get(self):
        """Build a category × currency pivot table for the date range.

        Rows are the predefined Japanese expense categories (plus Business
        Expense). Columns are currency codes (e.g. SGD, JPY, HKD).
        Missing category/currency combinations are filled with 0.

        Returns:
            DataFrame pivot with categories as index and currencies as columns.
        """
        lst = ['住居費', '食料品', '光熱費', '通信費', '保険', '年金', '日常生活', '医療関連', '教育関連', '交通関係',
               'アパレル', '人間関係', 'レジャー・娯楽', '電子製品・モバイル', '自動車・バイク', '奨学金', '仕送り', 'その他', 'Business Expense']
        pivot_andromoney = pd.pivot_table(self.andro_data_get(), index=['Category'], columns='Currency', values='Amount',
                                          aggfunc=np.sum, fill_value=0)
        return pivot_andromoney.reindex(lst, axis='index', fill_value=0)

    def andro_pivot_get_fx(self):
        """Return the pivot table with a SGD-normalised 'sum' column.

        Fetches SGD/JPY and SGD/HKD closing rates via Yahoo Finance for the
        period, then converts each currency column to SGD and sums them.

        Returns:
            DataFrame pivot with an added 'sum' column (SGD equivalent),
            values rounded to 2 decimal places.
        """
        std = self.start_date[:4] + '-' + self.start_date[4:6] + '-' + self.start_date[6:]
        edd = self.end_date[:4] + '-' + self.end_date[4:6] + '-' + self.end_date[6:]
        pivot_andromoney = self.andro_pivot_get()
        fx = AndroMoney.andro_fx.return_fx(std, edd)

        has_jpy = 'JPY' in pivot_andromoney.columns
        has_hkd = 'HKD' in pivot_andromoney.columns

        if has_jpy and has_hkd:
            pivot_andromoney['sum'] = pivot_andromoney['HKD'] / fx[1] + pivot_andromoney['JPY'] / fx[0] + pivot_andromoney['SGD']
        elif has_jpy:
            pivot_andromoney['sum'] = pivot_andromoney['JPY'] / fx[0] + pivot_andromoney['SGD']
        elif has_hkd:
            pivot_andromoney['sum'] = pivot_andromoney['HKD'] / fx[1] + pivot_andromoney['SGD']
        else:
            pivot_andromoney['sum'] = pivot_andromoney['SGD']

        pivot_andromoney = pivot_andromoney.round(2)
        print(pivot_andromoney)
        return pivot_andromoney
```

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
git add AndroMoney/andro_data.py tests/test_andro_data.py
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
