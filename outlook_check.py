"""Outlook / Hotmail Account & Webmail Core Logic.
Validates refresh tokens, exchanges them for access tokens, checks account validity,
and retrieves full inbox messages & HTML email bodies from Microsoft Graph API.
"""
import re
import requests
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone

DEFAULT_CLIENT_ID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"  # Mozilla Thunderbird preset
INBOX_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
SINGLE_MESSAGE_URL = "https://graph.microsoft.com/v1.0/me/messages"
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
    """Tolerant parser for Outlook / Hotmail lines."""
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

        email_match = _EMAIL_RE.search(line)
        if email_match:
            email = email_match.group(0).strip()

        for p in parts:
            if _CLIENT_ID_RE.match(p):
                client_id = p
                break

        for p in parts:
            if p.startswith("M.") or (len(p) > 50 and p != email and p != client_id):
                token = p
                break

        if not token:
            if len(parts) >= 3 and parts[0] == email:
                token = parts[2] if len(parts) >= 4 else parts[1]
                password = parts[1] if len(parts) >= 4 else ""
            elif len(parts) == 1 and (parts[0].startswith("M.") or len(parts[0]) > 40):
                token = parts[0]

        if not token:
            continue

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


def get_access_token(refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Exchanges refresh token for Microsoft Graph access token."""
    client_id = client_id or DEFAULT_CLIENT_ID
    proxies = {"http": proxy, "https": proxy} if proxy else None
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
        return None, f"Network / Proxy error: {str(e)}"

    if r.status_code != 200:
        err_desc = res_json.get("error_description") or res_json.get("error") or r.text[:120]
        for code, msg in ERROR_MESSAGES.items():
            if code in err_desc:
                err_desc = f"[{code}] {msg}"
                break
        return None, err_desc

    access_token = res_json.get("access_token")
    if not access_token:
        return None, "Access token tidak ditemukan dalam respon"

    return access_token, None


def check_outlook_account(email: str, password: str, refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None) -> Dict[str, Any]:
    """Checks an account and gets summary."""
    out = {
        "ok": False,
        "email": email,
        "password": password,
        "client_id": client_id or DEFAULT_CLIENT_ID,
        "refresh_token": refresh_token,
        "status": "DEAD",
        "unread_count": 0,
        "latest_subject": "",
        "latest_from": "",
        "latest_date": "",
        "error": ""
    }

    access_token, err = get_access_token(refresh_token, client_id, proxy)
    if not access_token:
        out["error"] = err
        return out

    headers = {"Authorization": f"Bearer {access_token}"}
    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        if not email or email == "Unknown Email":
            me_res = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, proxies=proxies, timeout=15)
            if me_res.status_code == 200:
                me_data = me_res.json()
                out["email"] = me_data.get("mail") or me_data.get("userPrincipalName") or email

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


def fetch_inbox_messages(refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None, top: int = 30) -> Dict[str, Any]:
    """Fetch list of messages in inbox."""
    access_token, err = get_access_token(refresh_token, client_id, proxy)
    if not access_token:
        return {"ok": False, "error": err, "messages": []}

    headers = {"Authorization": f"Bearer {access_token}"}
    proxies = {"http": proxy, "https": proxy} if proxy else None
    params = {
        "$orderby": "receivedDateTime desc",
        "$top": str(max(1, min(100, top))),
        "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead"
    }

    try:
        r = requests.get(INBOX_MESSAGES_URL, headers=headers, params=params, proxies=proxies, timeout=25)
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:120]}", "messages": []}

        data = r.json()
        raw_items = data.get("value", [])
        messages = []
        for item in raw_items:
            sender_obj = item.get("from", {}).get("emailAddress", {})
            sender_name = sender_obj.get("name") or sender_obj.get("address") or "Unknown"
            sender_addr = sender_obj.get("address") or ""

            # Relative / formatted time
            raw_dt = item.get("receivedDateTime", "")
            time_display = raw_dt[:10]
            try:
                dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                diff = now - dt
                if diff.total_seconds() < 3600:
                    mins = max(1, int(diff.total_seconds() // 60))
                    time_display = f"{mins}m ago"
                elif diff.total_seconds() < 86400:
                    hrs = int(diff.total_seconds() // 3600)
                    time_display = f"{hrs}h ago"
                elif diff.days == 1:
                    time_display = "Yesterday"
                elif diff.days < 7:
                    time_display = f"{diff.days}d ago"
                else:
                    time_display = dt.strftime("%d %b %Y")
            except Exception:
                pass

            messages.append({
                "id": item.get("id"),
                "subject": item.get("subject") or "(Tanpa Subjek)",
                "sender_name": sender_name,
                "sender_email": sender_addr,
                "preview": item.get("bodyPreview") or "",
                "time_display": time_display,
                "raw_date": raw_dt,
                "is_read": item.get("isRead", True)
            })

        return {"ok": True, "messages": messages}
    except Exception as e:
        return {"ok": False, "error": str(e), "messages": []}


def fetch_message_detail(message_id: str, refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None) -> Dict[str, Any]:
    """Fetch full message detail including HTML body."""
    access_token, err = get_access_token(refresh_token, client_id, proxy)
    if not access_token:
        return {"ok": False, "error": err}

    headers = {"Authorization": f"Bearer {access_token}"}
    proxies = {"http": proxy, "https": proxy} if proxy else None
    url = f"{SINGLE_MESSAGE_URL}/{message_id}"
    params = {
        "$select": "id,subject,from,toRecipients,receivedDateTime,body"
    }

    try:
        r = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=25)
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:120]}"}

        data = r.json()
        sender_obj = data.get("from", {}).get("emailAddress", {})
        sender_str = f"{sender_obj.get('name', '')} <{sender_obj.get('address', '')}>" if sender_obj.get('name') else sender_obj.get('address', 'Unknown')

        to_recipients = data.get("toRecipients", [])
        to_str = ", ".join([t.get("emailAddress", {}).get("address", "") for t in to_recipients if t.get("emailAddress")])

        body_obj = data.get("body", {})
        body_content = body_obj.get("content", "")
        body_type = body_obj.get("contentType", "text")

        raw_dt = data.get("receivedDateTime", "")
        formatted_date = raw_dt
        try:
            dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%d %b %Y, %H:%M")
        except Exception:
            pass

        return {
            "ok": True,
            "id": data.get("id"),
            "subject": data.get("subject") or "(Tanpa Subjek)",
            "from": sender_str,
            "to": to_str,
            "date": formatted_date,
            "body": body_content,
            "body_type": body_type
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
