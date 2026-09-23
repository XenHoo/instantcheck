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
           "is_pro": False, "error": ""}
    if not email or not password:
        out["error"] = "missing email/password"
        return out
    last_err = "login failed"
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
                    return out
                out["error"] = "login failed: %s" % (dd.get("description")
                                                     or j.get("message") or "invalid credentials")
                return out
            out["user_id"] = dd.get("user_id_str") or (str(dd.get("user_id")) if dd.get("user_id") else "")
            body = {"scene": ["vip", "workspace"], "vip_levels": ["vip"], "app_id": int(CAPCUT_AID)}
            hdr2 = dict(_WEB_HDR); hdr2["Content-Type"] = "application/json"
            sr = s.post(SUB_URL, json=body, headers=hdr2, timeout=timeout)
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
            return out
        except Exception:
            last_err = "network/proxy error"
            continue
    out["error"] = last_err
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
    client_id = client_id or DEFAULT_CLIENT_ID
    proxies = {"http": proxy, "https": proxy} if proxy else None
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token
    }
    try:
        r = requests.post(TOKEN_URL, data=data, proxies=proxies, timeout=15)
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
            me_res = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, proxies=proxies, timeout=10)
            if me_res.status_code == 200:
                me_data = me_res.json()
                out["email"] = me_data.get("mail") or me_data.get("userPrincipalName") or email

        params = {
            "$orderby": "receivedDateTime desc",
            "$top": "1",
            "$select": "id,subject,from,receivedDateTime,isRead"
        }
        inbox_res = requests.get(INBOX_MESSAGES_URL, headers=headers, params=params, proxies=proxies, timeout=10)
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

def fetch_inbox_messages(refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None, top: int = 50) -> Dict[str, Any]:
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
        # Check all messages endpoint first (captures Inbox, Junk, Focus, Other)
        r = requests.get(SINGLE_MESSAGE_URL, headers=headers, params=params, proxies=proxies, timeout=15)
        if r.status_code != 200:
            # Fallback to inbox folder
            r = requests.get(INBOX_MESSAGES_URL, headers=headers, params=params, proxies=proxies, timeout=15)
        
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:120]}", "messages": []}

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
    access_token, err = get_access_token(refresh_token, client_id, proxy)
    if not access_token:
        return {"ok": False, "error": err}

    headers = {"Authorization": f"Bearer {access_token}"}
    proxies = {"http": proxy, "https": proxy} if proxy else None
    url = f"{SINGLE_MESSAGE_URL}/{message_id}"
    params = {"$select": "id,subject,from,toRecipients,receivedDateTime,body"}

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
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

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

    body {
      background-color: var(--bg-wood-dark);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(180, 83, 9, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(217, 119, 6, 0.08) 0%, transparent 45%);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      margin: 0;
      padding: 0;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .top-navbar {
      background-color: #140d07;
      border-bottom: 2px solid #382415;
      padding: 8px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 68px;
      flex-shrink: 0;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    }

    .brand-title {
      font-family: 'Cinzel', serif;
      font-weight: 800;
      font-size: 1.25rem;
      letter-spacing: 1.5px;
      background: linear-gradient(180deg, #fffbeb 0%, #fcd34d 50%, #d97706 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 2px 10px rgba(217, 119, 6, 0.3);
    }
    .brand-sub {
      font-size: 0.72rem;
      letter-spacing: 2px;
      color: #b45309;
      font-weight: 700;
      text-transform: uppercase;
    }

    .nav-tabs-custom {
      background: #0d0805;
      padding: 4px;
      border-radius: 10px;
      border: 1px solid #382415;
      display: inline-flex;
      gap: 4px;
      align-items: center;
    }
    .nav-tab-btn, .nav-tabs-custom .nav-link {
      color: var(--text-muted);
      border: none;
      outline: none;
      font-weight: 600;
      font-size: 0.88rem;
      padding: 8px 20px;
      border-radius: 8px;
      background: transparent;
      cursor: pointer;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      user-select: none;
    }
    .nav-tab-btn:hover, .nav-tabs-custom .nav-link:hover {
      color: var(--gold-light);
      background-color: #24160d;
    }
    .nav-tab-btn.active, .nav-tabs-custom .nav-link.active {
      color: #1a0f05 !important;
      font-weight: 700;
      background: linear-gradient(135deg, #fcd34d 0%, #f59e0b 50%, #d97706 100%) !important;
      box-shadow: 0 2px 12px var(--gold-glow);
    }

    .main-tab-content {
      flex: 1;
      overflow: hidden;
      display: flex;
    }

    .tab-pane-custom {
      width: 100%;
      height: 100%;
      display: none;
      flex-direction: column;
      flex: 1 1 0%;
      overflow: hidden;
    }
    .tab-pane-custom.active {
      display: flex !important;
    }

    .trackmail-container {
      display: flex;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }

    .tm-sidebar {
      width: 290px;
      background-color: #120c08;
      border-right: 1px solid #2d1c10;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .tm-sidebar-header {
      padding: 14px 18px;
      border-bottom: 1px solid #2d1c10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #170f0a;
    }
    .tm-accounts-list {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
    }
    .tm-account-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      margin-bottom: 5px;
      border: 1px solid transparent;
      background: #18110b;
      transition: all 0.15s;
    }
    .tm-account-item:hover {
      background-color: #261a11;
      border-color: #5c3b1e;
    }
    .tm-account-item.active {
      background-color: #2d1d13;
      border-color: #d97706;
      box-shadow: 0 0 10px rgba(217, 119, 6, 0.2);
    }
    .tm-avatar {
      width: 32px;
      height: 32px;
      border-radius: 6px;
      background: linear-gradient(135deg, #452e1d, #2b1a0d);
      border: 1px solid #78471c;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 0.85rem;
      color: #fef3c7;
      flex-shrink: 0;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
    }
    .status-dot.live { background-color: var(--dot-green); box-shadow: 0 0 8px rgba(34, 197, 94, 0.7); }
    .status-dot.dead { background-color: var(--dot-red); box-shadow: 0 0 8px rgba(239, 68, 68, 0.7); }

    .tm-messages-col {
      width: 360px;
      background-color: #140d08;
      border-right: 1px solid #2d1c10;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .tm-messages-header {
      padding: 14px 18px;
      border-bottom: 1px solid #2d1c10;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #170f0a;
    }
    .tm-messages-list {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
    }
    .tm-message-item {
      padding: 12px;
      border-radius: 8px;
      cursor: pointer;
      margin-bottom: 6px;
      border: 1px solid #2d1c10;
      background-color: #19110b;
      transition: all 0.15s;
    }
    .tm-message-item:hover {
      background-color: #271a11;
      border-color: #5c3b1e;
    }
    .tm-message-item.active {
      border-color: #f59e0b;
      background-color: #2b1d13;
      box-shadow: 0 0 10px rgba(245, 158, 11, 0.2);
    }
    .tm-unread-dot {
      width: 6px;
      height: 6px;
      background-color: #f59e0b;
      border-radius: 50%;
      display: inline-block;
      margin-right: 6px;
      box-shadow: 0 0 6px rgba(245, 158, 11, 0.8);
    }

    .tm-reader-col {
      flex: 1;
      background-color: #0f0a06;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .tm-reader-topbar {
      padding: 12px 24px;
      border-bottom: 1px solid #2d1c10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background-color: #170f0a;
    }
    .tm-reader-content {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .tm-meta-card {
      background-color: #18110b;
      border: 1px solid #382415;
      border-radius: 10px;
      padding: 18px 22px;
    }
    .tm-email-iframe {
      width: 100%;
      min-height: 550px;
      border: 1px solid #382415;
      border-radius: 10px;
      background-color: #ffffff;
      flex: 1;
    }

    .tm-platform-chips {
      display: flex;
      gap: 4px;
      overflow-x: auto;
      padding: 6px 10px;
      background-color: #120b06;
      border-bottom: 1px solid #2d1c10;
      scrollbar-width: none;
    }
    .tm-platform-chips::-webkit-scrollbar { display: none; }
    .tm-chip-btn {
      border: 1px solid #382415;
      background: #1c120a;
      color: #a89f91;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.15s;
    }
    .tm-chip-btn:hover {
      color: #fef3c7;
      border-color: #78471c;
      background: #2b1a0d;
    }
    .tm-chip-btn.active {
      background: linear-gradient(135deg, #f59e0b, #d97706);
      color: #180f07 !important;
      font-weight: 700;
      border-color: #f59e0b;
      box-shadow: 0 0 8px rgba(245, 158, 11, 0.3);
    }
    .otp-highlight-card {
      background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(217, 119, 6, 0.08));
      border: 1px solid #d97706;
      border-radius: 10px;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      box-shadow: 0 4px 15px rgba(217, 119, 6, 0.15);
    }
    .otp-code-text {
      font-family: monospace;
      font-size: 1.5rem;
      font-weight: 800;
      letter-spacing: 4px;
      color: #fef08a;
      text-shadow: 0 0 10px rgba(254, 240, 138, 0.4);
    }
    .btn-xs {
      padding: 1px 6px;
      font-size: 0.7rem;
      border-radius: 4px;
    }

    .capcut-container {
      width: 100%;
      height: 100%;
      overflow-y: auto;
      padding: 28px 36px;
    }
    .card-theme {
      background-color: #18110b;
      border: 1px solid #382415;
      border-radius: 12px;
    }
    .form-control-theme {
      background-color: #0f0a06;
      border: 1px solid #382415;
      color: #fef3c7;
    }
    .form-control-theme:focus {
      background-color: #0f0a06;
      border-color: #d97706;
      color: #fef3c7;
      box-shadow: 0 0 0 0.25rem rgba(217, 119, 6, 0.25);
    }
    .btn-gold {
      background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
      color: #180f07;
      font-weight: 700;
      border: none;
      transition: all 0.2s;
    }
    .btn-gold:hover {
      background: linear-gradient(135deg, #b45309 0%, #d97706 100%);
      color: #ffffff;
      box-shadow: 0 0 14px var(--gold-glow);
    }
    .btn-outline-gold {
      border: 1px solid #b45309;
      color: #fcd34d;
    }
    .btn-outline-gold:hover {
      background-color: #2b1d13;
      border-color: #f59e0b;
      color: #ffffff;
    }

    /* ================= RESPONSIVE STYLES (Mobile, Tablet, Laptop, Desktop) ================= */
    @media (max-width: 1199px) {
      .tm-sidebar { width: 250px; }
      .tm-messages-col { width: 310px; }
      .nav-tab-btn { padding: 8px 14px; font-size: 0.84rem; }
    }

    @media (max-width: 991px) {
      body {
        height: auto;
        min-height: 100vh;
        overflow-x: hidden;
        overflow-y: auto;
      }
      .top-navbar {
        height: auto;
        padding: 10px 14px;
        flex-direction: column;
        gap: 10px;
        align-items: center;
      }
      .brand-container {
        justify-content: center;
        text-align: center;
      }
      .nav-tabs-custom {
        width: 100%;
        display: flex;
        overflow-x: auto;
        white-space: nowrap;
        justify-content: flex-start;
        padding: 4px;
        scrollbar-width: none;
      }
      .nav-tabs-custom::-webkit-scrollbar {
        display: none;
      }
      .nav-tab-btn {
        flex: 1 0 auto;
        justify-content: center;
        padding: 8px 12px;
        font-size: 0.8rem;
      }
      .main-tab-content {
        overflow: visible;
        flex: none;
        height: auto;
      }
      .tab-pane-custom {
        height: auto;
        min-height: calc(100vh - 140px);
        overflow: visible;
      }
      .trackmail-container {
        flex-direction: column;
        height: auto;
        overflow: visible;
        gap: 12px;
        padding: 12px 10px;
      }
      /* TrackMail Responsive View Switcher on Mobile/Tablet */
      .trackmail-container {
        display: flex;
        width: 100%;
        height: 100%;
        overflow: hidden;
      }

      @media (max-width: 991px) {
        .trackmail-container {
          display: block !important;
          width: 100%;
          height: auto;
          overflow: visible;
          padding: 0 !important;
        }
        .tm-view-accounts .tm-sidebar { display: flex !important; width: 100% !important; min-height: calc(100vh - 140px); border-radius: 0; border: none; }
        .tm-view-accounts .tm-messages-col { display: none !important; }
        .tm-view-accounts .tm-reader-col { display: none !important; }

        .tm-view-inbox .tm-sidebar { display: none !important; }
        .tm-view-inbox .tm-messages-col { display: flex !important; width: 100% !important; min-height: calc(100vh - 140px); border-radius: 0; border: none; }
        .tm-view-inbox .tm-reader-col { display: none !important; }

        .tm-view-reader .tm-sidebar { display: none !important; }
        .tm-view-reader .tm-messages-col { display: none !important; }
        .tm-view-reader .tm-reader-col { display: flex !important; width: 100% !important; min-height: calc(100vh - 140px); border-radius: 0; border: none; }

        .tm-sidebar {
          width: 100%;
          border: none;
          max-height: none;
        }
        .tm-messages-col {
          width: 100%;
          border: none;
          max-height: none;
        }
        .tm-reader-col {
          width: 100%;
          border: none;
          min-height: 500px;
        }
        .tm-email-iframe {
          min-height: 480px;
        }
        .capcut-container {
          padding: 16px 12px;
          overflow: visible;
          height: auto;
        }
      }
    }

    @media (max-width: 576px) {
      .top-navbar {
        padding: 8px 10px;
      }
      .brand-title {
        font-size: 1.1rem;
      }
      .brand-sub {
        font-size: 0.62rem;
        letter-spacing: 1px;
      }
      .nav-tab-btn {
        padding: 7px 10px;
        font-size: 0.75rem;
      }
      .nav-tab-btn i {
        margin-right: 4px !important;
      }
      .capcut-container {
        padding: 12px 8px;
      }
      .card-theme {
        padding: 1rem !important;
      }
      .tm-reader-topbar {
        padding: 10px 12px;
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }
      .tm-reader-content {
        padding: 12px;
      }
      .table-responsive {
        font-size: 0.75rem;
      }
    }
  </style>
</head>
<body>

  <div class="top-navbar">
    <div class="d-flex align-items-center gap-3 brand-container">
      <img src="/logo.png" alt="ChenStore" style="height: 42px; border-radius: 8px; border: 1px solid #78471c; box-shadow: 0 2px 8px rgba(0,0,0,0.5);" onerror="this.style.display='none'">
      <div>
        <div class="brand-title">ChenStore</div>
        <div class="brand-sub">MULTI TOOLS • LAYANAN SOSMED</div>
      </div>
    </div>
    
    <div class="nav-tabs-custom" id="mainTabs">
      <button type="button" class="nav-tab-btn active" id="btn-tab-mail" onclick="switchTab('mail')">
        <i class="fa-solid fa-inbox me-2 text-warning"></i>Mail Checker
      </button>
      <button type="button" class="nav-tab-btn" id="btn-tab-capcut" onclick="switchTab('capcut')">
        <i class="fa-solid fa-film me-2 text-warning"></i>CapCut Checker
      </button>
      <button type="button" class="nav-tab-btn" id="btn-tab-2fa" onclick="switchTab('2fa')">
        <i class="fa-solid fa-key me-2 text-warning"></i>2FA Generator
      </button>
      <button type="button" class="nav-tab-btn" id="btn-tab-proxy" onclick="switchTab('proxy')">
        <i class="fa-solid fa-server me-2 text-warning"></i>Proxy Checker
      </button>
    </div>
  </div>

  <div class="main-tab-content">
    
    <div id="tab-mail" class="tab-pane-custom active">
      <div id="trackmailContainer" class="trackmail-container tm-view-accounts">
        
        <div class="tm-sidebar">
          <div class="tm-sidebar-header">
            <span class="small fw-bold text-uppercase text-warning" style="letter-spacing: 0.5px;">
              <i class="fa-solid fa-users-viewfinder me-1"></i> Accounts (<span id="tmAccountCount">0</span>)
            </span>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-secondary p-1" title="Clear All" onclick="clearAllOutlookAccounts()">
                <i class="fa-solid fa-trash-can fa-xs text-danger"></i>
              </button>
            </div>
          </div>

          <!-- Quick Search & Upload Bar -->
          <div class="p-2 border-bottom border-secondary" style="background: #110a06;">
            <div class="input-group input-group-sm mb-2">
              <span class="input-group-text bg-dark border-secondary text-secondary p-1 px-2"><i class="fa-solid fa-magnifying-glass fa-xs"></i></span>
              <input type="text" id="tmAccountSearch" class="form-control form-control-sm form-control-theme" placeholder="Cari email akun..." oninput="renderAccountsList()" onkeydown="handleAccountSearchKeydown(event)">
            </div>
            <div class="d-flex gap-1 mb-1">
              <input type="file" id="tmDirectTxtFile" accept=".txt,.csv" style="display:none" onchange="handleTxtFileUpload(event)">
              <button class="btn btn-sm btn-outline-gold flex-grow-1 py-1" style="font-size: 0.74rem;" onclick="document.getElementById('tmDirectTxtFile').click()" title="Upload File .TXT (Bulk Auto-read)">
                <i class="fa-solid fa-file-arrow-up me-1"></i>Upload .TXT
              </button>
              <button class="btn btn-sm btn-gold py-1 px-3" style="font-size: 0.74rem;" data-bs-toggle="modal" data-bs-target="#addAccountModal" title="Tambah Akun Manual">
                <i class="fa-solid fa-plus me-1"></i>Add
              </button>
            </div>
            <div class="d-flex justify-content-between align-items-center mt-1 px-1">
              <span id="tmAccountModeStatus" class="text-secondary small" style="font-size: 0.7rem;">Mode: Cari Email</span>
              <button id="btnToggleShowAll" class="btn btn-sm btn-link p-0 text-warning text-decoration-none small" style="font-size: 0.72rem;" onclick="toggleShowAllAccounts()">
                <i class="fa-solid fa-eye me-1"></i>Tampilkan Semua
              </button>
            </div>
          </div>

          <div class="tm-accounts-list" id="tmAccountsContainer">
            <div class="text-center text-muted py-5 small">
              Belum ada akun.<br>Upload file <b>.TXT</b> atau klik <b>Add</b>.
            </div>
          </div>
        </div>

        <div class="tm-messages-col">
          <div class="tm-messages-header">
            <div class="d-flex align-items-center gap-2">
              <button class="btn btn-sm btn-outline-warning py-0 px-2 d-lg-none" onclick="setMailView('accounts')" title="Kembali ke Daftar Akun">
                <i class="fa-solid fa-chevron-left me-1"></i>Akun
              </button>
              <span class="fw-bold small text-uppercase text-warning" id="tmInboxTitle">
                <i class="fa-regular fa-folder-open me-1"></i> INBOX (0)
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
              <input type="text" id="tmMessageSearch" class="form-control form-control-sm form-control-theme" placeholder="Filter pengirim / subjek..." oninput="renderCurrentMessages()">
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

          <div class="tm-messages-list" id="tmMessagesContainer">
            <div class="text-center text-muted py-5 small">
              Pilih akun di sebelah kiri untuk melihat pesan inbox.
            </div>
          </div>
        </div>

        <div class="tm-reader-col">
          <div class="tm-reader-topbar">
            <div class="d-flex align-items-center gap-2 overflow-hidden">
              <button class="btn btn-sm btn-outline-warning py-0 px-2 d-lg-none flex-shrink-0" onclick="setMailView('inbox')" title="Kembali ke Inbox">
                <i class="fa-solid fa-chevron-left me-1"></i>Inbox
              </button>
              <span class="fw-semibold text-truncate text-warning" id="tmActiveEmailLabel" style="max-width: 240px;">Pilih Akun</span>
              <span id="tmConnectionBadge" class="badge bg-dark border border-secondary text-secondary px-2 py-1 flex-shrink-0">
                ● Standby
              </span>
            </div>
            <div class="d-flex gap-2 flex-shrink-0">
              <button class="btn btn-sm btn-outline-gold" onclick="copyCurrentEmail()" title="Copy Email">
                <i class="fa-regular fa-copy me-1"></i> Copy
              </button>
              <button class="btn btn-sm btn-outline-gold" onclick="refreshCurrentInbox()" title="Refresh">
                <i class="fa-solid fa-arrows-rotate"></i>
              </button>
            </div>
          </div>

          <div class="tm-reader-content" id="tmReaderContent">
            <div class="text-center text-muted my-auto">
              <i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i>
              <h5 class="text-light">Belum ada email yang dipilih</h5>
              <p class="small text-secondary">Klik salah satu email dari daftar inbox untuk membaca isi surat.</p>
            </div>
          </div>
        </div>

      </div>
    </div>

    <div id="tab-capcut" class="tab-pane-custom">
      <div class="capcut-container">
        <div class="row g-4">
          
          <div class="col-lg-5">
            <div class="card card-theme p-4 shadow-sm">
              <h5 class="fw-bold mb-3 text-warning"><i class="fa-solid fa-film me-2"></i>Input Akun CapCut</h5>
              
              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold">DAFTAR AKUN (email:pass, email|pass, dll)</label>
                <textarea id="ccAccountsInput" class="form-control form-control-theme" rows="7" placeholder="user1@example.com:password123&#10;user2@example.com|password456"></textarea>
                <div class="d-flex justify-content-between mt-1">
                  <small id="ccAccountCount" class="text-muted">Total: 0 akun</small>
                  <button class="btn btn-sm btn-link text-decoration-none p-0 text-danger" onclick="document.getElementById('ccAccountsInput').value=''; updateCapcutCount();">Clear</button>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold">RESIDENTIAL PROXY URL (Wajib)</label>
                <input type="text" id="ccProxyInput" class="form-control form-control-theme" placeholder="http://user-session-{sess}:pass@gate.provider.com:7000" value="{{ default_proxy }}">
                <small class="text-muted" style="font-size: 0.75rem;">Gunakan token <code>{sess}</code> untuk rotasi IP otomatis.</small>
              </div>

              <div class="row g-2 mb-3">
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold">THREADS</label>
                  <input type="number" id="ccWorkersInput" class="form-control form-control-theme" value="6" min="1" max="25">
                </div>
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold">IP RETRIES</label>
                  <input type="number" id="ccRetriesInput" class="form-control form-control-theme" value="6" min="1" max="15">
                </div>
              </div>

              <div class="d-flex gap-2">
                <button id="btnStartCapcut" class="btn btn-gold flex-grow-1 py-2" onclick="startCapcutChecking()">
                  <i class="fa-solid fa-play me-2"></i>Mulai Check CapCut
                </button>
                <button id="btnStopCapcut" class="btn btn-outline-secondary py-2" onclick="stopCapcutChecking()" disabled>
                  <i class="fa-solid fa-stop me-2"></i>Stop
                </button>
              </div>

              <div class="mt-4">
                <div class="d-flex justify-content-between small text-secondary mb-1">
                  <span>Progress</span>
                  <span id="ccProgressText" class="text-warning">0 / 0 (0%)</span>
                </div>
                <div class="progress" style="height: 6px; background-color: #0f0a06;">
                  <div id="ccProgressBar" class="progress-bar bg-warning" style="width: 0%;"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="col-lg-7">
            <div class="card card-theme p-4 shadow-sm">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold mb-0 text-warning"><i class="fa-solid fa-square-poll-vertical me-2"></i>Hasil Pengecekan CapCut</h5>
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
                    <i class="fa-solid fa-crown me-1"></i>PRO / VIP 
                    <span id="proCount" class="badge bg-success badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('proResult')">Copy</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('proResult', 'capcut_pro.txt')">Save</button>
                  </div>
                </div>
                <textarea id="proResult" class="form-control form-control-theme border-success" rows="4" readonly placeholder="Akun PRO akan muncul di sini..."></textarea>
              </div>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-info">
                    <i class="fa-solid fa-user me-1"></i>FREE / REGULAR
                    <span id="freeCount" class="badge bg-info text-dark badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('freeResult')">Copy</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('freeResult', 'capcut_free.txt')">Save</button>
                  </div>
                </div>
                <textarea id="freeResult" class="form-control form-control-theme border-info" rows="4" readonly placeholder="Akun FREE akan muncul di sini..."></textarea>
              </div>

              <div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-danger">
                    <i class="fa-solid fa-circle-xmark me-1"></i>DEAD / ERROR
                    <span id="dieCount" class="badge bg-danger badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('dieResult')">Copy</button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('dieResult', 'capcut_die.txt')">Save</button>
                  </div>
                </div>
                <textarea id="dieResult" class="form-control form-control-theme border-danger" rows="3" readonly placeholder="Akun Gagal akan muncul di sini..."></textarea>
              </div>

            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- TAB 2FA GENERATOR -->
    <div id="tab-2fa" class="tab-pane-custom">
      <div class="capcut-container">
        <div class="row g-4 justify-content-center">
          
          <!-- Single 2FA Generator -->
          <div class="col-lg-5 col-md-12">
            <div class="card card-theme p-4 shadow-sm h-100">
              <div class="d-flex align-items-center gap-2 mb-3">
                <i class="fa-solid fa-shield-halved text-warning fs-5"></i>
                <h5 class="fw-bold mb-0 text-warning">Quick 2FA Code (Single)</h5>
              </div>
              <p class="text-secondary small mb-3">
                Masukkan 2FA Secret Key (Base32) untuk mendapatkan kode verifikasi 6 digit instan.
              </p>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0">2FA SECRET KEY</label>
                  <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none small" onclick="document.getElementById('single2faSecret').value=''; resetSingle2fa();">
                    <i class="fa-solid fa-trash-can fa-xs me-1"></i>Clear
                  </button>
                </div>
                <div class="input-group">
                  <input type="text" id="single2faSecret" class="form-control form-control-theme" placeholder="Contoh: JBSWY3DPEHPK3PXP" autocomplete="off" spellcheck="false" oninput="if(!this.value.trim()) resetSingle2fa();" onkeydown="if(event.key==='Enter') generateSingle2fa()">
                  <button class="btn btn-gold px-3" type="button" onclick="generateSingle2fa()">
                    <i class="fa-solid fa-bolt me-1"></i> Get Code
                  </button>
                </div>
              </div>

              <!-- Single Result Card -->
              <div id="single2faResultBox" class="p-3 rounded border border-secondary text-center my-auto" style="background: #120b06;">
                <div class="text-secondary small mb-1">AUTHENTICATOR CODE</div>
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
                    <i class="fa-regular fa-copy me-1"></i> Salin Kode
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
                  <h5 class="fw-bold mb-0 text-warning">Bulk 2FA Generator</h5>
                </div>
              </div>
              <p class="text-secondary small mb-3">
                Mendukung paste banyak Secret Key atau baris combo (format <code>email|pass|secret</code> atau secret per baris).
              </p>

              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0">INPUT LIST SECRETS / COMBOS</label>
                  <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none small" onclick="clearBulk2fa()">
                    <i class="fa-solid fa-trash-can fa-xs me-1"></i>Clear
                  </button>
                </div>
                <textarea id="bulk2faInput" class="form-control form-control-theme" rows="6" placeholder="Contoh format:&#10;user1@email.com|pass1|JBSWY3DPEHPK3PXP&#10;user2@email.com:pass2:4X72J6...&#10;HXDMVJZTGNCDESRR..." oninput="if(!this.value.trim()) clearBulk2fa()"></textarea>
              </div>

              <div class="d-flex gap-2 mb-3">
                <button id="btnRunBulk2fa" class="btn btn-gold flex-grow-1 py-2" onclick="generateBulk2fa()">
                  <i class="fa-solid fa-arrows-rotate me-1"></i> Generate All Codes
                </button>
                <button class="btn btn-outline-gold px-3" onclick="copyField('bulk2faOutput')" title="Salin Hasil">
                  <i class="fa-regular fa-copy me-1"></i> Copy
                </button>
                <button class="btn btn-outline-gold px-3" onclick="downloadField('bulk2faOutput', '2fa_codes.txt')" title="Simpan ke file TXT">
                  <i class="fa-solid fa-download me-1"></i> Save
                </button>
              </div>

              <div class="mb-0">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0">HASIL (FORMAT COMBO + 2FA CODE)</label>
                  <span id="bulk2faCount" class="badge bg-dark border border-secondary text-warning small">0 generated</span>
                </div>
                <textarea id="bulk2faOutput" class="form-control form-control-theme border-warning" rows="6" readonly placeholder="Hasil kode 2FA akan muncul di sini..."></textarea>
              </div>

            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- TAB PROXY CHECKER -->
    <div id="tab-proxy" class="tab-pane-custom">
      <div class="capcut-container">
        <div class="row g-3">
          
          <!-- Left Column: Input & Settings -->
          <div class="col-lg-4 col-md-12">
            <div class="card card-theme p-3 shadow-sm h-100 d-flex flex-column">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="d-flex align-items-center gap-2">
                  <i class="fa-solid fa-server text-warning fs-5"></i>
                  <h5 class="fw-bold mb-0 text-warning">Proxy Checker</h5>
                </div>
                <span class="badge bg-dark border border-warning text-warning px-2 py-1 small">HTTP / SOCKS</span>
              </div>
              <p class="text-secondary small mb-2">
                Dukungan format: <code>HOST:PORT</code>, <code>HOST:PORT:USER:PASS</code>, <code>USER:PASS:HOST:PORT</code>, atau <code>scheme://...</code>
              </p>

              <!-- Proxy Textarea Input -->
              <div class="mb-2 flex-grow-1 d-flex flex-column">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small text-secondary fw-semibold mb-0">INPUT PROXY LIST</label>
                  <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-link text-warning p-0 text-decoration-none small" onclick="loadSampleProxies()">
                      <i class="fa-solid fa-lightbulb fa-xs me-1"></i>Sample
                    </button>
                    <button class="btn btn-sm btn-link text-secondary p-0 text-decoration-none small" onclick="clearProxyInput()">
                      <i class="fa-solid fa-trash-can fa-xs me-1"></i>Clear
                    </button>
                  </div>
                </div>
                <textarea id="proxyInput" class="form-control form-control-theme flex-grow-1" style="min-height: 140px;" placeholder="Contoh format:&#10;192.168.1.1:8080&#10;192.168.1.1:8080:username:password&#10;username:password:192.168.1.1:8080&#10;http://user:pass@192.168.1.1:8080"></textarea>
              </div>

              <!-- Options / Settings -->
              <div class="card p-2 mb-3 bg-dark border-secondary">
                <div class="row g-2">
                  <div class="col-6">
                    <label class="form-label small text-secondary mb-1">THREADS</label>
                    <input type="number" id="proxyConcurrency" class="form-control form-control-sm form-control-theme" value="5" min="1" max="20">
                  </div>
                  <div class="col-6">
                    <label class="form-label small text-secondary mb-1">TIMEOUT (s)</label>
                    <input type="number" id="proxyTimeout" class="form-control form-control-sm form-control-theme" value="15" min="2" max="60">
                  </div>
                  <div class="col-12">
                    <div class="form-check form-switch mt-1">
                      <input class="form-check-input" type="checkbox" id="checkScamalyticsToggle">
                      <label class="form-check-label small text-light" for="checkScamalyticsToggle">
                        Scamalytics Fraud Score Check <span class="badge bg-secondary text-warning" style="font-size: 0.65rem;">Deep</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="d-flex gap-2">
                <button id="btnStartProxy" class="btn btn-gold flex-grow-1 py-2 fw-semibold" onclick="startProxyChecking()">
                  <i class="fa-solid fa-play me-1"></i> Start Checking
                </button>
                <button id="btnStopProxy" class="btn btn-outline-danger px-3 py-2" onclick="stopProxyChecking()" disabled>
                  <i class="fa-solid fa-stop me-1"></i> Stop
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
                    <div class="text-secondary small fw-semibold" style="font-size: 0.7rem;">TOTAL</div>
                    <div id="proxyStatTotal" class="fs-5 fw-bold text-light">0</div>
                  </div>
                </div>
                <div class="col-sm-2 col-4">
                  <div class="p-2 text-center rounded bg-dark border border-success">
                    <div class="text-success small fw-semibold" style="font-size: 0.7rem;">LIVE</div>
                    <div id="proxyStatLive" class="fs-5 fw-bold text-success">0</div>
                  </div>
                </div>
                <div class="col-sm-2 col-4">
                  <div class="p-2 text-center rounded bg-dark border border-danger">
                    <div class="text-danger small fw-semibold" style="font-size: 0.7rem;">DEAD</div>
                    <div id="proxyStatDead" class="fs-5 fw-bold text-danger">0</div>
                  </div>
                </div>
                <div class="col-sm-3 col-6">
                  <div class="p-2 text-center rounded bg-dark border border-warning">
                    <div class="text-warning small fw-semibold" style="font-size: 0.7rem;">AVG LATENCY</div>
                    <div id="proxyStatLatency" class="fs-5 fw-bold text-warning">-</div>
                  </div>
                </div>
                <div class="col-sm-3 col-6">
                  <div class="p-2 text-center rounded bg-dark border border-info">
                    <div class="text-info small fw-semibold" style="font-size: 0.7rem;">LOW FRAUD (&lt;25)</div>
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
                  <button type="button" class="btn btn-outline-warning active" id="filterProxyAll" onclick="setProxyFilter('all')">All (<span id="countFilterAll">0</span>)</button>
                  <button type="button" class="btn btn-outline-success" id="filterProxyLive" onclick="setProxyFilter('live')">Live (<span id="countFilterLive">0</span>)</button>
                  <button type="button" class="btn btn-outline-danger" id="filterProxyDead" onclick="setProxyFilter('dead')">Dead (<span id="countFilterDead">0</span>)</button>
                  <button type="button" class="btn btn-outline-info" id="filterProxyClean" onclick="setProxyFilter('clean')">Low Fraud (<span id="countFilterClean">0</span>)</button>
                </div>

                <div class="d-flex gap-2 align-items-center">
                  <div class="input-group input-group-sm" style="max-width: 170px;">
                    <span class="input-group-text bg-dark border-secondary text-secondary"><i class="fa-solid fa-magnifying-glass"></i></span>
                    <input type="text" id="proxySearchInput" class="form-control form-control-sm form-control-theme" placeholder="Cari IP / Negara..." oninput="renderProxyTable()">
                  </div>

                  <!-- Export Dropdown -->
                  <div class="dropdown">
                    <button class="btn btn-sm btn-gold dropdown-toggle" type="button" data-bs-toggle="dropdown">
                      <i class="fa-solid fa-download me-1"></i> Export
                    </button>
                    <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end border-warning shadow">
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="copyLiveProxies('raw')"><i class="fa-regular fa-copy me-2 text-warning"></i>Copy Live (Original Format)</a></li>
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="copyLiveProxies('ipport')"><i class="fa-solid fa-network-wired me-2 text-warning"></i>Copy Live (HOST:PORT)</a></li>
                      <li><hr class="dropdown-divider border-secondary"></li>
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="downloadLiveProxiesTxt()"><i class="fa-regular fa-file-lines me-2 text-warning"></i>Download Live (.TXT)</a></li>
                      <li><a class="dropdown-item" href="javascript:void(0)" onclick="downloadProxyReportJson()"><i class="fa-solid fa-code me-2 text-warning"></i>Download Full Report (.JSON)</a></li>
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
                      <th>PROXY</th>
                      <th style="width: 80px;">STATUS</th>
                      <th style="width: 85px;">PING</th>
                      <th>EXIT IP &amp; LOCATION</th>
                      <th>ISP / ORG</th>
                      <th>FRAUD RISK</th>
                      <th style="width: 50px;">ACT</th>
                    </tr>
                  </thead>
                  <tbody id="proxyTableBody">
                    <tr>
                      <td colspan="8" class="text-center py-5 text-secondary">
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
          <h5 class="modal-title fw-bold text-warning"><i class="fa-solid fa-circle-info me-2"></i>Proxy Diagnostic Details</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" id="proxyDetailModalBody">
          <!-- Dynamic details content -->
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Tutup</button>
        </div>
      </div>
    </div>
  </div>

  <div class="modal fade" id="addAccountModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content card-theme border-warning text-light">
        <div class="modal-header border-secondary">
          <h5 class="modal-title fw-bold text-warning"><i class="fa-solid fa-user-plus me-2"></i>Add Outlook / Hotmail Accounts</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label small text-secondary fw-semibold">UPLOAD FILE .TXT (Bulk Import)</label>
            <input type="file" id="modalFileInput" class="form-control form-control-sm form-control-theme" accept=".txt,.csv" onchange="handleModalFileSelect(event)">
          </div>
          <label class="form-label small text-secondary fw-semibold">ATAU PASTE TOKENS (email|pass|refresh_token|client_id atau token saja)</label>
          <textarea id="modalAccountInput" class="form-control form-control-theme" rows="6" placeholder="user@hotmail.com|password|M.R3_BAY...|9e5f94bc-e8a4-4e73-b8be-63364c29d753"></textarea>
          
          <div class="mt-3">
            <label class="form-label small text-secondary fw-semibold">PROXY (Opsional: http://user:pass@host:port)</label>
            <input type="text" id="modalProxyInput" class="form-control form-control-theme" placeholder="Kosongkan jika direct">
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Batal</button>
          <button type="button" class="btn btn-gold" onclick="submitNewOutlookAccounts()">
            <i class="fa-solid fa-check me-1"></i> Import & Check
          </button>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    window.switchTab = function(tabName) {
      const allTabs = ['mail', 'capcut', '2fa', 'proxy'];
      allTabs.forEach(name => {
        const btn = document.getElementById('btn-tab-' + name);
        const pane = document.getElementById('tab-' + name);
        if (btn) {
          if (name === tabName) {
            btn.classList.add('active');
          } else {
            btn.classList.remove('active');
          }
        }
        if (pane) {
          if (name === tabName) {
            pane.classList.add('active');
            pane.style.setProperty('display', 'flex', 'important');
          } else {
            pane.classList.remove('active');
            pane.style.setProperty('display', 'none', 'important');
          }
        }
      });
    };
    function switchTab(tabName) {
      window.switchTab(tabName);
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

    function clearBulk2fa() {
      const inEl = document.getElementById('bulk2faInput');
      const outEl = document.getElementById('bulk2faOutput');
      const cntEl = document.getElementById('bulk2faCount');
      if (inEl) inEl.value = '';
      if (outEl) outEl.value = '';
      if (cntEl) cntEl.textContent = '0 generated';
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
      let secret = (input ? input.value : '').trim();
      if (!secret) {
        resetSingle2fa();
        return alert('Silakan masukkan 2FA Secret Key!');
      }

      // Extract secret if user pasted combo line (email|pass|secret)
      const parts = secret.split(/[:|\s\t,;]+/);
      if (parts.length > 1) {
        for (const p of parts) {
          if (p.length >= 10 && !p.includes('@')) {
            secret = p;
            break;
          }
        }
      }
      secret = secret.replace(/[\s\-]+/g, '').toUpperCase();

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
          alert('Secret Key tidak valid atau gagal digenerate!');
        }
      } catch (err) {
        resetSingle2fa();
        display.textContent = 'ERROR';
        copyBtn.disabled = true;
        alert('Gagal mengambil kode 2FA: ' + err.message);
      }
    }

    function copySingle2fa() {
      if (!currentSingle2faCode || currentSingle2faCode === '------') return;
      navigator.clipboard.writeText(currentSingle2faCode).then(() => {
        const btn = document.getElementById('btnCopySingle2fa');
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check me-1 text-success"></i> Disalin!';
        setTimeout(() => { btn.innerHTML = orig; }, 1500);
      });
    }

    async function generateBulk2fa() {
      const input = document.getElementById('bulk2faInput');
      const rawText = (input ? input.value : '').trim();
      if (!rawText) return alert('Silakan masukkan list secret / combo!');

      const lines = (rawText || '').split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l);
      if (lines.length === 0) return;

      const btn = document.getElementById('btnRunBulk2fa');
      const origBtn = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Memproses...';

      const parsedItems = [];
      const secretList = [];

      for (const line of lines) {
        let parts = [];
        if (line.includes('|')) parts = line.split('|').map(p => p.trim());
        else if (line.includes(':')) parts = line.split(':').map(p => p.trim());
        else if (line.includes('----')) parts = line.split('----').map(p => p.trim());
        else if (line.includes('\t')) parts = line.split('\t').map(p => p.trim());
        else parts = [line];

        let secret = "";
        let email = "";
        let pass = "";

        if (parts.length >= 3) {
          email = parts[0];
          pass = parts[1];
          secret = parts[2].replace(/[\s\-]+/g, '').toUpperCase();
        } else if (parts.length === 2) {
          if (parts[0].includes('@')) {
            email = parts[0];
            secret = parts[1].replace(/[\s\-]+/g, '').toUpperCase();
          } else {
            secret = parts[0].replace(/[\s\-]+/g, '').toUpperCase();
          }
        } else {
          secret = parts[0].replace(/[\s\-]+/g, '').toUpperCase();
        }

        parsedItems.push({ original: line, email, pass, secret });
        secretList.push(secret);
      }

      try {
        const batchSize = 100;
        const codeMap = {};

        for (let i = 0; i < secretList.length; i += batchSize) {
          const batch = secretList.slice(i, i + batchSize);
          const proxRes = await safeFetchJson('/api/2fa/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ secrets: batch })
          });

          if (proxRes && proxRes.data) {
            proxRes.data.forEach((item, idx) => {
              const sec = (item.secret || batch[idx] || "").toUpperCase();
              const code = item.code || item.token || "ERROR";
              codeMap[sec] = code;
            });
          }
        }

        // Build output
        let outLines = [];
        let successCount = 0;
        for (const item of parsedItems) {
          const code = codeMap[item.secret] || (item.secret ? "NOT_FOUND" : "NO_SECRET");
          if (code && code !== "ERROR" && code !== "NOT_FOUND" && code !== "NO_SECRET") {
            successCount++;
          }
          if (item.email && item.pass) {
            outLines.push(`${item.email}|${item.pass}|${item.secret}|${code}`);
          } else if (item.email) {
            outLines.push(`${item.email}|${item.secret}|${code}`);
          } else {
            outLines.push(`${item.secret} -> ${code}`);
          }
        }

        const outArea = document.getElementById('bulk2faOutput');
        if (outArea) outArea.value = outLines.join(String.fromCharCode(10));
        
        const countBadge = document.getElementById('bulk2faCount');
        if (countBadge) countBadge.textContent = `${successCount}/${parsedItems.length} generated`;

      } catch (err) {
        alert('Gagal bulk generate: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = origBtn;
      }
    }


    /* ================= PROXY CHECKER LOGIC ================= */
    let proxyList = [];
    let proxyResults = [];
    let proxyAbortController = null;
    let proxyFilterMode = 'all';

    function loadSampleProxies() {
      const sample = [
        '103.152.112.162:80',
        '103.125.40.52:8080',
        '45.114.130.138:8080',
        '185.199.229.156:7492:sampleuser:samplepass',
        'sampleuser:samplepass:198.51.100.1:8080'
      ].join(String.fromCharCode(10));
      document.getElementById('proxyInput').value = sample;
    }

    function clearProxyInput() {
      document.getElementById('proxyInput').value = '';
    }

    function setProxyFilter(mode) {
      proxyFilterMode = mode;
      ['all', 'live', 'dead', 'clean'].forEach(m => {
        const b = document.getElementById(`filterProxy${m.charAt(0).toUpperCase() + m.slice(1)}`);
        if (b) b.classList.toggle('active', m === mode);
      });
      renderProxyTable();
    }

    async function startProxyChecking() {
      const rawText = document.getElementById('proxyInput').value.trim();
      if (!rawText) return alert('Silakan masukkan list proxy!');

      const lines = (rawText || '').split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l && !l.startsWith('#'));
      if (lines.length === 0) return alert('Tidak ada proxy yang valid untuk dicek.');

      const concurrency = Math.min(20, Math.max(1, parseInt(document.getElementById('proxyConcurrency').value) || 5));
      const timeout = Math.min(60, Math.max(2, parseInt(document.getElementById('proxyTimeout').value) || 15));
      const checkScamalytics = document.getElementById('checkScamalyticsToggle').checked;

      proxyList = lines;
      proxyResults = [];
      proxyAbortController = new AbortController();

      document.getElementById('btnStartProxy').disabled = true;
      document.getElementById('btnStopProxy').disabled = false;
      document.getElementById('proxyProgressBar').style.width = '0%';

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
          document.getElementById('proxyProgressBar').style.width = pct + '%';
          updateProxyStats();
          renderProxyTable();
        }
      }

      const workers = [];
      for (let w = 0; w < Math.min(concurrency, total); w++) {
        workers.push(worker());
      }

      await Promise.all(workers);

      document.getElementById('btnStartProxy').disabled = false;
      document.getElementById('btnStopProxy').disabled = true;
      document.getElementById('proxyProgressBar').style.width = '100%';
    }

    function stopProxyChecking() {
      if (proxyAbortController) {
        proxyAbortController.abort();
      }
      document.getElementById('btnStartProxy').disabled = false;
      document.getElementById('btnStopProxy').disabled = true;
    }

    function updateProxyStats() {
      const total = proxyResults.length;
      const live = proxyResults.filter(r => r.live).length;
      const dead = proxyResults.filter(r => !r.live).length;
      const clean = proxyResults.filter(r => r.live && r.fraud_score !== null && r.fraud_score < 25).length;
      
      const liveItems = proxyResults.filter(r => r.live && r.latency_ms > 0);
      const avgLat = liveItems.length > 0 ? Math.round(liveItems.reduce((a, b) => a + b.latency_ms, 0) / liveItems.length) : '-';

      document.getElementById('proxyStatTotal').textContent = total;
      document.getElementById('proxyStatLive').textContent = live;
      document.getElementById('proxyStatDead').textContent = dead;
      document.getElementById('proxyStatLatency').textContent = avgLat !== '-' ? avgLat + 'ms' : '-';
      document.getElementById('proxyStatLowFraud').textContent = clean;

      document.getElementById('countFilterAll').textContent = total;
      document.getElementById('countFilterLive').textContent = live;
      document.getElementById('countFilterDead').textContent = dead;
      document.getElementById('countFilterClean').textContent = clean;
    }

    function renderProxyTable() {
      const tbody = document.getElementById('proxyTableBody');
      const search = (document.getElementById('proxySearchInput').value || '').toLowerCase().trim();

      if (proxyResults.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" class="text-center py-5 text-secondary">
              <i class="fa-solid fa-server fa-2x mb-2 d-block opacity-50"></i>
              Belum ada proxy yang diperiksa. Masukkan list proxy dan klik <b>Start Checking</b>.
            </td>
          </tr>
        `;
        return;
      }

      let filtered = proxyResults.filter(item => {
        if (proxyFilterMode === 'live' && !item.live) return false;
        if (proxyFilterMode === 'dead' && item.live) return false;
        if (proxyFilterMode === 'clean' && (!item.live || item.fraud_score === null || item.fraud_score >= 25)) return false;

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
              Tidak ada proxy yang cocok dengan filter atau pencarian.
            </td>
          </tr>
        `;
        return;
      }

      let html = '';
      filtered.forEach((r, idx) => {
        const isLive = r.live;
        const pingClass = r.latency_ms < 500 ? 'text-success' : (r.latency_ms < 1200 ? 'text-warning' : 'text-danger');
        
        let fraudBadge = '<span class="text-secondary small">-</span>';
        if (r.fraud_score !== undefined && r.fraud_score !== null) {
          const s = r.fraud_score;
          const scoreClass = s < 25 ? 'bg-success' : (s < 50 ? 'bg-warning text-dark' : 'bg-danger');
          fraudBadge = `<span class="badge ${scoreClass} fw-bold me-1">${s}</span><span class="small text-secondary">${escapeHtml(r.fraud_risk || '')}</span>`;
        }

        const countryText = r.country ? `${r.country} ${r.country_code ? '(' + r.country_code + ')' : ''}` : '-';
        const locText = r.city && r.city !== '-' ? `${r.city}, ${countryText}` : countryText;

        html += `
          <tr>
            <td class="text-secondary small font-monospace">${idx + 1}</td>
            <td class="font-monospace text-light">
              <span class="badge bg-dark border border-secondary text-warning me-1 small">${(r.scheme || 'http').toUpperCase()}</span>
              ${escapeHtml(r.display || r.raw)}
            </td>
            <td>
              ${isLive ? '<span class="badge bg-success"><i class="fa-solid fa-circle-check me-1"></i>LIVE</span>' : '<span class="badge bg-danger"><i class="fa-solid fa-circle-xmark me-1"></i>DEAD</span>'}
            </td>
            <td>
              ${isLive ? `<span class="font-monospace fw-bold ${pingClass}"><i class="fa-solid fa-bolt fa-xs me-1"></i>${r.latency_ms}ms</span>` : '<span class="text-secondary small">-</span>'}
            </td>
            <td>
              ${isLive ? `<div><span class="font-monospace fw-semibold text-warning">${escapeHtml(r.exit_ip || '-')}</span></div><div class="small text-secondary">${escapeHtml(locText)}</div>` : `<span class="text-danger small" title="${escapeHtml(r.error || '')}">${escapeHtml(r.error || 'Connection Failed')}</span>`}
            </td>
            <td class="small text-secondary" style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${escapeHtml(r.isp || r.org || '-')}
            </td>
            <td>
              ${fraudBadge}
            </td>
            <td>
              <button class="btn btn-sm btn-outline-warning p-1 px-2" onclick="showProxyDetailModal(${proxyResults.indexOf(r)})" title="Detail Diagnostik">
                <i class="fa-solid fa-eye fa-xs"></i>
              </button>
            </td>
          </tr>
        `;
      });

      tbody.innerHTML = html;
    }

    function showProxyDetailModal(index) {
      const r = proxyResults[index];
      if (!r) return;
      const modalBody = document.getElementById('proxyDetailModalBody');

      let scamalyticsHtml = '';
      if (r.fraud_score !== undefined && r.fraud_score !== null) {
        scamalyticsHtml = `
          <div class="card bg-dark border-secondary p-3 mt-3">
            <h6 class="fw-bold text-warning mb-2"><i class="fa-solid fa-shield-halved me-1"></i> Scamalytics Report</h6>
            <div class="row g-2 small">
              <div class="col-6"><span class="text-secondary">Fraud Score:</span> <b class="${r.fraud_score < 25 ? 'text-success' : (r.fraud_score < 50 ? 'text-warning' : 'text-danger')}">${r.fraud_score}/100</b></div>
              <div class="col-6"><span class="text-secondary">Fraud Risk:</span> <b>${escapeHtml(r.fraud_risk || '-')}</b></div>
              <div class="col-6"><span class="text-secondary">Residential:</span> <b>${escapeHtml(r.residential || 'no')}</b></div>
              <div class="col-6"><span class="text-secondary">Datacenter:</span> <b>${escapeHtml(r.datacenter || 'no')}</b></div>
              <div class="col-12"><span class="text-secondary">Blacklist Hits:</span> <b>${r.blacklist_hits && r.blacklist_hits.length > 0 ? r.blacklist_hits.join(', ') : 'None'}</b></div>
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
            <tr><td class="text-secondary" style="width: 35%;">Proxy Display</td><td class="font-monospace text-warning">${escapeHtml(r.display || r.raw)}</td></tr>
            <tr><td class="text-secondary">Scheme / Host</td><td>${escapeHtml(r.scheme || 'http')}://${escapeHtml(r.host || '')}:${escapeHtml(r.port || '')}</td></tr>
            <tr><td class="text-secondary">Public Exit IP</td><td class="font-monospace fw-bold text-info">${escapeHtml(r.exit_ip || '-')}</td></tr>
            <tr><td class="text-secondary">Country / Region</td><td>${escapeHtml(r.country || '-')} ${r.country_code ? '(' + r.country_code + ')' : ''} ${r.region ? '• ' + r.region : ''}</td></tr>
            <tr><td class="text-secondary">City</td><td>${escapeHtml(r.city || '-')}</td></tr>
            <tr><td class="text-secondary">ISP / Operator</td><td>${escapeHtml(r.isp || '-')}</td></tr>
            <tr><td class="text-secondary">Organization / AS</td><td>${escapeHtml(r.org || '-')} ${r.as ? '• ' + r.as : ''}</td></tr>
            ${!r.live && r.error ? `<tr><td class="text-danger">Error Detail</td><td class="text-danger">${escapeHtml(r.error)}</td></tr>` : ''}
          </table>

          ${scamalyticsHtml}
        </div>
      `;

      const modal = new bootstrap.Modal(document.getElementById('proxyDetailModal'));
      modal.show();
    }

    function copyLiveProxies(format) {
      const live = proxyResults.filter(r => r.live);
      if (live.length === 0) return alert('Tidak ada proxy LIVE untuk disalin.');

      let lines = [];
      if (format === 'ipport') {
        lines = live.map(r => `${r.host}:${r.port}`);
      } else {
        lines = live.map(r => r.raw || r.display);
      }

      navigator.clipboard.writeText(lines.join(String.fromCharCode(10))).then(() => {
        alert(`Berhasil menyalin ${live.length} proxy LIVE!`);
      });
    }

    function downloadLiveProxiesTxt() {
      const live = proxyResults.filter(r => r.live);
      if (live.length === 0) return alert('Tidak ada proxy LIVE untuk diunduh.');
      const content = live.map(r => r.raw || r.display).join(String.fromCharCode(10));
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `live_proxies_${Date.now()}.txt`;
      link.click();
    }

    function downloadProxyReportJson() {
      if (proxyResults.length === 0) return alert('Belum ada data untuk diekspor.');
      const content = JSON.stringify(proxyResults, null, 2);
      const blob = new Blob([content], { type: 'application/json;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `proxy_report_${Date.now()}.json`;
      link.click();
    }


    function copyField(elementId) {
      const el = document.getElementById(elementId);
      if (!el.value.trim()) return;
      navigator.clipboard.writeText(el.value).then(() => alert('Disalin ke clipboard!'));
    }

    function downloadField(elementId, filename) {
      const content = document.getElementById(elementId).value;
      if (!content.trim()) return alert('Field masih kosong.');
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
        throw new Error(`Respon server tidak valid (${res.status}): ` + (text.slice(0, 120).replace(/<[^>]+>/g, '').trim() || 'Error internal server'));
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

        const key = (email || token.slice(0, 30)) + '_' + token.slice(-20);
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
      navigator.clipboard.writeText(otp).then(() => {
        alert(`Kode OTP disalin: ${otp}`);
      });
    }

    function saveOutlookAccountsStorage() {
      try {
        localStorage.setItem('chenstore_outlook_accounts', JSON.stringify(outlookAccounts));
      } catch(e) {}
    }

    function loadOutlookAccountsStorage() {
      try {
        const raw = localStorage.getItem('chenstore_outlook_accounts');
        if (raw) {
          outlookAccounts = JSON.parse(raw) || [];
          if (outlookAccounts.length > 0) {
            renderAccountsList();
            if (window.innerWidth > 991) {
              selectOutlookAccount(0);
            }
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
        btn.innerHTML = showAllAccounts ? '<i class="fa-solid fa-filter me-1"></i>Mode Cari Saja' : '<i class="fa-solid fa-eye me-1"></i>Tampilkan Semua';
      }
      if (status) {
        status.textContent = showAllAccounts ? 'Mode: Semua Akun' : 'Mode: Cari Email';
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
      document.getElementById('tmAccountCount').textContent = outlookAccounts.length;

      const btn = document.getElementById('btnToggleShowAll');
      const status = document.getElementById('tmAccountModeStatus');
      if (btn) {
        btn.innerHTML = showAllAccounts ? '<i class="fa-solid fa-filter me-1"></i>Mode Cari Saja' : '<i class="fa-solid fa-eye me-1"></i>Tampilkan Semua';
      }
      if (status) {
        status.textContent = showAllAccounts ? 'Mode: Semua Akun' : 'Mode: Cari Email';
      }

      if (outlookAccounts.length === 0) {
        container.innerHTML = `<div class="text-center text-muted py-5 small">Belum ada akun.<br>Upload file <b>.TXT</b> atau klik <b>Add</b>.</div>`;
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
                <i class="fa-solid fa-circle-check me-1 text-success"></i> AKUN AKTIF:
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
              </div>
            </div>
          `;
        }

        container.innerHTML = `
          ${activeAccHtml}
          <div class="text-center text-muted py-4 px-2 small">
            <i class="fa-solid fa-magnifying-glass fa-2x mb-2 text-warning opacity-75"></i>
            <div class="text-light fw-semibold mb-1">Cari Akun Lain</div>
            <div class="text-secondary mb-3" style="font-size: 0.74rem;">
              Ketik email di kolom pencarian di atas untuk memilih akun.<br>
              <span class="badge bg-dark border border-warning text-warning mt-1">${outlookAccounts.length} Akun Tersedia</span>
            </div>
            <button class="btn btn-sm btn-outline-gold px-3 py-1" style="font-size: 0.75rem;" onclick="toggleShowAllAccounts()">
              <i class="fa-solid fa-eye me-1"></i> Tampilkan Semua (${outlookAccounts.length})
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
            Tidak ada akun yang cocok dengan "<b>${escapeHtml(search)}</b>"<br>
            <button class="btn btn-sm btn-link text-warning mt-2 small" onclick="toggleShowAllAccounts()">Tampilkan semua akun</button>
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
            <button class="btn btn-sm btn-link text-secondary p-0 px-1 opacity-50 hover-opacity-100" title="Hapus akun ini" onclick="deleteOutlookAccount(${idx}, event)">
              <i class="fa-solid fa-xmark fa-sm text-danger"></i>
            </button>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    function handleTxtFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async function(e) {
        const text = e.target.result;
        if (!text) return alert('File kosong!');
        await importAccountsFromText(text);
        event.target.value = '';
      };
      reader.readAsText(file);
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
      container.innerHTML = `<div class="text-center text-muted py-5 small"><i class="fa-solid fa-spinner fa-spin me-2 text-warning"></i>Mengekstrak & memeriksa akun...</div>`;

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
          return alert('Format tidak dikenali / token tidak ditemukan! Pastikan format baris berisi email & refresh token.');
        }

        let currentIndex = 0;
        let addedCount = 0;

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
              outlookAccounts.push(data);
              addedCount++;
              saveOutlookAccountsStorage();
              renderAccountsList();
              if (selectedAccountIndex === -1 && window.innerWidth > 991) {
                selectOutlookAccount(0);
              }
            } catch (e) {
              outlookAccounts.push({
                ok: false,
                email: item.email || 'Error',
                error: e.message,
                refresh_token: item.refresh_token,
                client_id: item.client_id
              });
              addedCount++;
              saveOutlookAccountsStorage();
              renderAccountsList();
              if (selectedAccountIndex === -1 && window.innerWidth > 991) {
                selectOutlookAccount(0);
              }
            }
          }
        }

        const pool = [];
        for (let i = 0; i < Math.min(8, items.length); i++) {
          pool.push(worker());
        }
        await Promise.all(pool);
        saveOutlookAccountsStorage();

      } catch (err) {
        alert('Gagal memproses file akun: ' + err.message);
        renderAccountsList();
      }
    }

    function deleteOutlookAccount(idx, event) {
      if (event) event.stopPropagation();
      const acc = outlookAccounts[idx];
      const emailName = acc ? acc.email : 'akun ini';
      if (confirm(`Hapus ${emailName} dari daftar?`)) {
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
          document.getElementById('tmActiveEmailLabel').textContent = 'Pilih Akun';
          document.getElementById('tmConnectionBadge').className = 'badge bg-dark border border-secondary text-secondary px-2 py-1';
          document.getElementById('tmConnectionBadge').innerHTML = '● Standby';
          document.getElementById('tmInboxTitle').innerHTML = '<i class="fa-regular fa-folder-open me-1"></i> INBOX (0)';
          document.getElementById('tmMessagesContainer').innerHTML = `<div class="text-center text-muted py-5 small">Pilih akun di sebelah kiri untuk melihat pesan inbox.</div>`;
          document.getElementById('tmReaderContent').innerHTML = `<div class="text-center text-muted my-auto"><i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i><h5 class="text-light">Belum ada email yang dipilih</h5></div>`;
        }
      }
    }

    async function submitNewOutlookAccounts() {
      const inputEl = document.getElementById('modalAccountInput');
      const proxyEl = document.getElementById('modalProxyInput');
      const text = inputEl ? inputEl.value.trim() : '';
      const proxy = proxyEl ? proxyEl.value.trim() : '';
      if (!text) return alert('Silakan masukkan token / akun atau upload file .txt!');

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
      if (confirm('Hapus semua daftar akun Mail Checker?')) {
        outlookAccounts = [];
        selectedAccountIndex = -1;
        currentInboxMessages = [];
        try { localStorage.removeItem('chenstore_outlook_accounts'); } catch(e) {}
        renderAccountsList();
        setMailView('accounts');
        document.getElementById('tmInboxTitle').innerHTML = '<i class="fa-regular fa-folder-open me-1"></i> INBOX (0)';
        document.getElementById('tmMessagesContainer').innerHTML = `<div class="text-center text-muted py-5 small">Pilih akun di sebelah kiri untuk melihat pesan inbox.</div>`;
        document.getElementById('tmReaderContent').innerHTML = `<div class="text-center text-muted my-auto"><i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i><h5 class="text-light">Belum ada email yang dipilih</h5></div>`;
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
        badge.innerHTML = '● Connected';
        await loadInboxMessages(acc);
      } else {
        badge.className = 'badge bg-danger text-light px-2 py-1';
        badge.innerHTML = '● Disconnected';
        document.getElementById('tmMessagesContainer').innerHTML = `<div class="text-center py-5 small text-danger"><i class="fa-solid fa-circle-exclamation fa-2x mb-2 text-danger"></i><br>Tidak dapat memuat inbox.<br><small class="text-secondary">${acc.error || 'Akun DEAD / Token tidak valid'}</small></div>`;
        document.getElementById('tmReaderContent').innerHTML = `
          <div class="text-center text-muted my-auto">
            <i class="fa-solid fa-triangle-exclamation fa-3x mb-3 text-danger"></i>
            <h5 class="text-danger">Akun Disconnected / DEAD</h5>
            <p class="small text-secondary px-3">${acc.error || 'Token tidak valid, kedaluwarsa, atau rusak.'}</p>
          </div>
        `;
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
        container.innerHTML = `<div class="text-center text-muted py-5 small">Inbox kosong.</div>`;
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

      document.getElementById('tmInboxTitle').innerHTML = `<i class="fa-regular fa-folder-open me-1"></i> INBOX (${filtered.length}/${currentInboxMessages.length})`;

      if (filtered.length === 0) {
        container.innerHTML = `<div class="text-center text-muted py-5 small">Tidak ada pesan yang cocok dengan filter.</div>`;
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
              ${escapeHtml(msg.preview || 'Tidak ada preview')}
            </div>
            ${otp ? `
              <div class="mt-2 d-flex align-items-center gap-1">
                <span class="badge bg-warning text-dark fw-bold font-monospace py-1 px-2"><i class="fa-solid fa-key me-1"></i>OTP: ${otp}</span>
                <button class="btn btn-xs btn-outline-warning py-0 px-2 fw-semibold" onclick="copyOtpDirect('${otp}', event)">Salin</button>
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
          container.innerHTML = `<div class="text-center text-danger py-5 small">${data.error || 'Gagal memuat pesan'}</div>`;
          return;
        }

        currentInboxMessages = data.messages || [];
        renderCurrentMessages();

      } catch (err) {
        container.innerHTML = `<div class="text-center text-danger py-5 small">${err.message}</div>`;
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
          reader.innerHTML = `<div class="text-center text-danger my-auto">${data.error || 'Gagal membaca email'}</div>`;
          return;
        }

        const otp = extractOtpCode(data.subject, '', data.body);
        let otpHtml = '';
        if (otp) {
          otpHtml = `
            <div class="otp-highlight-card mb-3">
              <div>
                <div class="small text-warning fw-bold text-uppercase"><i class="fa-solid fa-key me-1"></i> KODE VERIFIKASI / OTP TERDETEKSI</div>
                <div class="otp-code-text">${otp}</div>
              </div>
              <button class="btn btn-gold px-3 py-2 fw-bold shadow-sm" onclick="copyOtpDirect('${otp}', event)">
                <i class="fa-regular fa-copy me-1"></i> Salin OTP
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

          <div class="flex-grow-1 d-flex">
            <iframe class="tm-email-iframe shadow" srcdoc="${escapeHtml(data.body)}"></iframe>
          </div>
        `;
      } catch (err) {
        reader.innerHTML = `<div class="text-center text-danger my-auto">${err.message}</div>`;
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
      if (selectedAccountIndex >= 0) {
        const email = outlookAccounts[selectedAccountIndex].email;
        if (email) {
          navigator.clipboard.writeText(email).then(() => alert('Email disalin: ' + email));
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
        countEl.textContent = 'Total: ' + lines.length + ' akun';
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

    async function startCapcutChecking() {
      const text = ccAccountsInput.value.trim();
      const proxy = document.getElementById('ccProxyInput').value.trim();
      const workers = parseInt(document.getElementById('ccWorkersInput').value) || 6;
      const retries = parseInt(document.getElementById('ccRetriesInput').value) || 6;

      if (!text) return alert('Silakan masukkan daftar akun CapCut!');

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
          alert('Tidak ada akun valid yang ditemukan!');
          document.getElementById('btnStartCapcut').disabled = false;
          document.getElementById('btnStopCapcut').disabled = true;
          return;
        }

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
        if (err.name !== 'AbortError') alert('Error: ' + err.message);
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

    // Load saved accounts on startup and attach tab handlers
    document.addEventListener('DOMContentLoaded', () => {
      ['mail', 'capcut', '2fa', 'proxy'].forEach(name => {
        const b = document.getElementById('btn-tab-' + name);
        if (b) {
          b.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(name);
          });
        }
      });

      // Cleanup any stuck modal backdrops
      document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
      document.body.classList.remove('modal-open');

      loadOutlookAccountsStorage();
    });
  </script>
</body>
</html>
"""

# ==================== FLASK ROUTES ====================

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
        elif action == "parse_accounts" or "mode" in payload:
            return api_parse_accounts()
        elif action == "check_capcut" or "accounts_text" in payload:
            return api_check_capcut()
        elif action == "check_outlook":
            return api_check_outlook()
        
    default_proxy = os.environ.get("CAPCUT_PROXY", "")
    return render_template_string(HTML_TEMPLATE, default_proxy=default_proxy)


@app.route("/logo.png")
def serve_logo():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "logo.png")
    if os.path.exists(logo_path):
        return send_from_directory(base_dir, "logo.png")
    return ("", 204)

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
    unresolved_secrets = []

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
            unresolved_secrets.append(clean_s)

    # Fallback to twofa.co for any unparseable / custom secrets
    if unresolved_secrets:
        try:
            query = ",".join(unresolved_secrets[:40])
            url = f"https://twofa.co/api/{query}"
            headers = {"User-Agent": UA}
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                res_data = r.json()
                if isinstance(res_data, dict):
                    c = res_data.get("code") or res_data.get("token") or ""
                    results.append({
                        "secret": res_data.get("secret", unresolved_secrets[0]),
                        "code": str(c),
                        "error": res_data.get("error", "")
                    })
                elif isinstance(res_data, list):
                    for item in res_data:
                        c = item.get("code") or item.get("token") or ""
                        results.append({
                            "secret": item.get("secret", ""),
                            "code": str(c),
                            "error": item.get("error", "")
                        })
        except Exception:
            for uns in unresolved_secrets:
                results.append({
                    "secret": uns,
                    "code": "",
                    "error": "Invalid base32 secret"
                })

    return jsonify({"ok": True, "data": results})

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
