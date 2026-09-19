"""Outlook / Hotmail Account & Token Checker Core Logic.
Validates refresh tokens, exchanges them for access tokens, checks account validity,
and retrieves inbox stats/messages from Microsoft Graph API.
"""
import re
import requests
from typing import Dict, Any, Tuple, Optional, List

DEFAULT_CLIENT_ID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"  # Mozilla Thunderbird preset
INBOX_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"

ERROR_MESSAGES = {
    "AADSTS70000": "Token tidak valid, kedaluwarsa, atau rusak.",
    "AADSTS700016": "Client ID tidak ditemukan di Azure AD.",
    "AADSTS700038": "Client ID tidak valid.",
    "AADSTS90023": "Aplikasi tidak memiliki izin untuk mengakses resource ini.",
    "AADSTS50173": "Sesi token kedaluwarsa. Perlu generate token baru.",
    "AADSTS900232": "Aplikasi tidak diizinkan untuk tipe akun ini.",
}

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_CLIENT_ID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def parse_outlook_lines(text: str) -> List[Dict[str, str]]:
    """Tolerant parser for Outlook / Hotmail lines.
    Formats supported:
      email|password|refresh_token|client_id
      email|refresh_token|client_id
      email:password:refresh_token
      refresh_token (standalone)
    """
    results = []
    seen = set()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in re.split(r"[|:;\t]+", line) if p.strip()]
        if not parts:
            continue

        email = ""
        password = ""
        token = ""
        client_id = DEFAULT_CLIENT_ID

        # Find email if exists
        email_match = _EMAIL_RE.search(line)
        if email_match:
            email = email_match.group(0).strip()

        # Find client_id if exists
        for p in parts:
            if _CLIENT_ID_RE.match(p):
                client_id = p
                break

        # Find refresh token (starts with M. or long token)
        for p in parts:
            if p.startswith("M.") or (len(p) > 50 and p != email and p != client_id):
                token = p
                break

        # If standard pipe separated
        if not token:
            if len(parts) >= 3 and parts[0] == email:
                token = parts[2] if len(parts) >= 4 else parts[1]
                password = parts[1] if len(parts) >= 4 else ""
            elif len(parts) == 1 and (parts[0].startswith("M.") or len(parts[0]) > 40):
                token = parts[0]

        if not token:
            continue

        # Extract password if not set
        if not password and len(parts) >= 2 and parts[0] == email and parts[1] != token:
            password = parts[1]

        key = f"{email}_{token[:20]}"
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "email": email or "Unknown Email",
            "password": password,
            "refresh_token": token,
            "client_id": client_id
        })

    return results


def check_outlook_account(email: str, password: str, refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None) -> Dict[str, Any]:
    """Check an Outlook/Hotmail account refresh token and retrieve inbox summary."""
    client_id = client_id or DEFAULT_CLIENT_ID
    out = {
        "ok": False,
        "email": email,
        "password": password,
        "client_id": client_id,
        "status": "DEAD",
        "unread_count": 0,
        "latest_subject": "",
        "latest_from": "",
        "latest_date": "",
        "error": ""
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None

    # Step 1: Exchange refresh token for access token
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
        "scope": "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/User.Read"
    }

    try:
        r = requests.post(TOKEN_URL, data=data, proxies=proxies, timeout=25)
        res_json = r.json()
    except Exception as e:
        out["error"] = f"Network / Proxy error: {str(e)}"
        return out

    if r.status_code != 200:
        err_desc = res_json.get("error_description") or res_json.get("error") or r.text[:120]
        # Friendly error mapping
        for code, msg in ERROR_MESSAGES.items():
            if code in err_desc:
                err_desc = f"[{code}] {msg}"
                break
        out["error"] = err_desc
        return out

    access_token = res_json.get("access_token")
    if not access_token:
        out["error"] = "Access token tidak ditemukan dalam respon"
        return out

    # Step 2: Fetch user profile (to verify email if unknown)
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        if not email or email == "Unknown Email":
            me_res = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, proxies=proxies, timeout=15)
            if me_res.status_code == 200:
                me_data = me_res.json()
                out["email"] = me_data.get("mail") or me_data.get("userPrincipalName") or email

        # Step 3: Fetch latest inbox message
        params = {
            "$orderby": "receivedDateTime desc",
            "$top": "1",
            "$select": "id,subject,from,receivedDateTime,isRead"
        }
        inbox_res = requests.get(INBOX_MESSAGES_URL, headers=headers, params=params, proxies=proxies, timeout=15)
        if inbox_res.status_code == 200:
            inbox_data = inbox_res.json().get("value", [])
            if inbox_data:
                latest = inbox_data[0]
                out["latest_subject"] = latest.get("subject") or "(Tanpa Subjek)"
                sender = latest.get("from", {}).get("emailAddress", {})
                out["latest_from"] = sender.get("name") or sender.get("address") or "Unknown"
                out["latest_date"] = (latest.get("receivedDateTime") or "")[:10]
    except Exception:
        pass

    out["ok"] = True
    out["status"] = "LIVE"
    return out
