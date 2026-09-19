# CapCut Checker (standalone)

Verifies CapCut accounts (`email:password` → **Pro/Free + expiry date**) by logging in through
CapCut's direct email API and reading the subscription. This is the same checker that ran behind
the admin panel's `/tools/capcut` page (removed 2026-09-17); only the web wrapper is gone — the
checking logic here is identical to the server's `capcut_check.py`.

## Files
- `capcut_check.py` — the checker (one function: `check_capcut_account`). Unchanged from server.
- `capcut_cli.py` — command-line runner: reads `email:pass` lines, checks them concurrently, prints/saves results.

## Install
```
pip install requests
```

## Run
```
# Windows (PowerShell)
$env:CAPCUT_PROXY = "http://USER-session-{sess}:PASS@gate.yourprovider.com:7000"
python capcut_cli.py accounts.txt --out results.csv

# Linux / macOS
export CAPCUT_PROXY='http://USER-session-{sess}:PASS@gate.yourprovider.com:7000'
python capcut_cli.py accounts.txt --out results.csv

# or pass it inline, and read from stdin
type accounts.txt | python capcut_cli.py --proxy "http://.../{sess}/..."
```

Options: `--workers N` (concurrency, default 6), `--retries N` (proxy-IP rotations per account,
default 6), `--timeout S`, `--out results.csv`.

## The proxy is required
CapCut soft-blocks datacenter and most home IPs on login (`error_code 7`). You **must** use a
**residential** proxy. Put the literal token `{sess}` somewhere in the proxy URL — it's replaced
with a fresh random session id on every attempt, so each retry exits from a new residential IP,
which is how the checker clears the block. If your provider rotates IPs automatically on its
gateway, you can omit `{sess}` and the URL is used as-is.

> The proxy string is a credential — it is **not** included in these files. Use the same
> residential provider you had configured on the server (`capcut_proxy` setting), or any
> residential proxy in the format above.

## Input format
The parser is tolerant — one account per line, in any of these shapes:
```
email@example.com:password
email@example.com|password|123456
1. email@example.com password
```
Header lines and trailing user-ids/junk are ignored; duplicate emails are dropped.

## Notes
- Each check logs out afterwards, so it doesn't burn the account's 2-login cap (1 desktop + 1 mobile).
- Credentials are sent only to CapCut's own endpoints (`login-row.www.capcut.com`,
  `commerce-api-sg.capcut.com`) through your proxy. Nothing is logged or sent anywhere else.
- Use it only on accounts you own or sell.
