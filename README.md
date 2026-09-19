# Outlook Commander TUI

Interactive terminal application for viewing Outlook, Hotmail, and Live inboxes across multiple accounts. The complete application source lives in one file: `outlook_commander.py`.

Language: **English** | [Bahasa Indonesia](README-ID.md)

## Features

- Microsoft device-flow sign-in and refresh-token storage.
- Multi-account inbox dashboard powered by Microsoft Graph.
- Subject and sender search, local timestamps, and plain-text email reading.
- Latest-message or date-range retrieval.
- Authenticated HTTP/HTTPS and SOCKS5 proxies, with a connection test.
- Portable data files stored next to the executable.

## Run from Source

Requirements: Windows, Python 3.14 x64, and a terminal that supports Textual.

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 outlook_commander.py
```

The first launch creates the following files beside `outlook_commander.py`:

- `email_list.txt` — one email address per line; an optional password metadata field may follow `|`.
- `accounts_with_tokens.txt` — saved refresh tokens and Microsoft client IDs.

## Build the Windows EXE

Build one portable console executable:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-Executable.ps1
```

The output is `dist\OutlookCommander.exe`. End users do not need Python or Python packages. The executable remains a terminal application because its interface is built with Textual.

When the EXE is started, it creates and reads `email_list.txt` and `accounts_with_tokens.txt` in the EXE folder, even when launched through a shortcut with a different working directory. Use a writable folder; do not place it in `Program Files` unless the user has write permission.

## First-Time Setup

1. Start the application once so it creates `email_list.txt` in the application folder.
2. Add the email addresses to `email_list.txt`.
3. Return to the application and choose **Generate New Token**. If the generator was already open while you edited the file, close and reopen it so the account list is reloaded.
4. Select the input file, account, and client-ID preset.
5. Open the displayed Microsoft URL, enter the device code, and approve access.
6. Return to Home and choose **Manage Email**.

## Data Formats

`email_list.txt` accepts one account per line:

```text
account@example.com
account@example.com|optional-password-metadata
```

`accounts_with_tokens.txt` accepts either form:

```text
account@example.com|refresh_token|client_id
account@example.com|optional-password-metadata|refresh_token|client_id
```

Do not place the `|` character inside a field.

## Shortcuts

| Key | Action |
| --- | --- |
| `q` | Quit |
| `e` | Open dashboard from Home |
| `g` | Generate tokens |
| `h` | Return Home from dashboard |
| `r` | Refresh active inbox |
| `l` | Reload token-file accounts |
| `Esc` | Close or skip a modal |

## Security

`accounts_with_tokens.txt` contains credentials that can access mail. Treat it as a secret, do not commit or share it, and rotate/revoke a token if exposed. `email_list.txt` can also contain password metadata. Neither file is bundled into the executable.

## Project Layout

```text
outlook_commander.py       # Entire application source
requirements.txt           # Runtime Python dependencies
requirements-build.txt     # PyInstaller build dependency
scripts/Build-Executable.ps1
README.md
README-ID.md
dist/OutlookCommander.exe  # Generated output
```
