# Google Drive Source Integration — Design Spec

**Date:** 2026-06-21
**Branch:** feature/add_login_g_v0.1
**Scope:** Add the ability to retrieve `AndroMoney.csv` from Google Drive as the pipeline's data source, replacing the hardcoded local xlsx path.

---

## Goals

- Download `AndroMoney.csv` from the user's personal Google Drive by filename search at runtime.
- Authenticate via OAuth 2.0 user credentials (browser login once, token cached locally).
- Keep credentials out of version control.
- Leave the rest of the pipeline (control, writer, FX, entry point) untouched.
- Allow easy toggle back to local file via a single settings flag.

## Out of Scope

- Uploading output files to Drive.
- Service account authentication.
- Searching by file ID (name-based search only).

---

## Architecture

### Files changed

| File | Change |
|------|--------|
| `AndroMoney/andro_drive.py` | **New** — Drive auth + search + download |
| `AndroMoney/settings.py` | Add 4 new config fields |
| `AndroMoney/andro_data.py` | Replace source resolution; branch on CSV vs Excel reader |
| `.gitignore` | Add `credentials.json`, `token.json` |

### Files unchanged

`andro_money.py`, `AndroMoney/andro_control.py`, `AndroMoney/andro_writer.py`, `AndroMoney/andro_fx.py`

### New dependencies

```
google-auth-oauthlib
google-api-python-client
```

---

## Module: `AndroMoney/andro_drive.py`

Three stateless functions:

### `authenticate() -> google.oauth2.credentials.Credentials`

- Loads `credentials.json` from `settings.CREDENTIALS_PATH`.
- If `token.json` exists (`settings.TOKEN_PATH`) and is valid, loads it; refreshes automatically if expired.
- On first run (no token), opens browser for OAuth consent and saves `token.json`.
- OAuth scope: `https://www.googleapis.com/auth/drive.readonly` — read-only, minimum necessary.

### `search_file(service, filename: str) -> str`

- Calls Drive API `files.list` with an exact name query: `name = 'AndroMoney.csv'`.
- Returns the file ID of the first matching result.
- Raises `FileNotFoundError(filename)` with a clear message if no file is found.

### `download_csv(service, file_id: str) -> io.StringIO`

- Streams file content via `files.get_media`.
- Returns an `io.StringIO` — no temp file written to disk.
- The StringIO is passed directly to `pd.read_csv()` in `andro_data.py`.

---

## Settings changes (`AndroMoney/settings.py`)

Four new fields added alongside existing paths:

```python
# Google Drive integration
USE_GOOGLE_DRIVE: bool = True
DRIVE_FILENAME: str = "AndroMoney.csv"
CREDENTIALS_PATH: str = "credentials.json"
TOKEN_PATH: str = "token.json"
```

- Set `USE_GOOGLE_DRIVE = False` to fall back to the existing local `xlsx_FILE_PATH` with no other changes.
- `CREDENTIALS_PATH` and `TOKEN_PATH` are relative to the project root (where the script is run from).

---

## Data layer changes (`AndroMoney/andro_data.py`)

### `AndroData.get_source() -> tuple[source, str]`

Replaces the role of the existing `get_xlsx_file_path()` static method. The `__init__` still sets `self.xlsx_file` from `settings.xlsx_FILE_PATH` for the local fallback; `get_source()` uses it when `USE_GOOGLE_DRIVE = False`.

- When `USE_GOOGLE_DRIVE = True`:
  1. Calls `andro_drive.authenticate()` to get credentials.
  2. Builds a Drive API service client.
  3. Calls `andro_drive.search_file(service, DRIVE_FILENAME)` to get the file ID.
  4. Calls `andro_drive.download_csv(service, file_id)` to get an `io.StringIO`.
  5. Returns `(StringIO, 'csv')`.
- When `USE_GOOGLE_DRIVE = False`:
  - Returns `(settings.xlsx_FILE_PATH, 'excel')`.

### `AndroDataMoney.andro_rawdata_get()`

Branches on the format returned by `get_source()`:

```python
source, fmt = self.get_source()
if fmt == 'csv':
    df = pd.read_csv(source, index_col=0, header=1)
else:
    df = pd.read_excel(source, index_col=0, header=1)
```

`header=1` and `index_col=0` are unchanged — only the reader function changes.

---

## Security

- `credentials.json` and `token.json` added to `.gitignore` — never committed.
- OAuth scope is `drive.readonly` — no write access to Drive.
- Token is refreshed automatically; re-auth only needed if revoked.
- No credentials stored in `settings.py` or any tracked file.

---

## Setup steps (for the user, not automated)

1. Create a project in Google Cloud Console.
2. Enable the Google Drive API.
3. Create OAuth 2.0 credentials (Desktop app type).
4. Download `credentials.json` and place it at the project root.
5. Run the pipeline once — browser opens for consent, `token.json` is saved.
6. All subsequent runs use the cached token silently.
