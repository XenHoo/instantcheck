"""Outlook Commander: portable, single-file Textual application."""
import asyncio, os, re, sys, tempfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote

import httpx, msal
from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, ListItem, ListView, Select, Static

# Configuration and runtime location -------------------------------------------------
CLIENT_PRESETS = {"1": {"id": "9e5f94bc-e8a4-4e73-b8be-63364c29d753", "name": "Mozilla Thunderbird"}}
SCOPES = ["Mail.Read", "Mail.ReadBasic", "User.Read"]
AUTHORITY = "https://login.microsoftonline.com/consumers"
INBOX_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
ERROR_MESSAGES = {
    "AADSTS70000": "Token is invalid, expired, or corrupted. Generate a new token.",
    "AADSTS700016": "Client ID was not found in Azure AD.",
    "AADSTS700038": "Client ID is invalid or contains a typo.",
    "AADSTS90023": "The app does not have permission to access this resource.",
    "AADSTS50173": "Token expired. Refresh or generate a new token.",
    "AADSTS900232": "The app is not allowed for this account type.",
}

def runtime_directory() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

DATA_DIRECTORY = runtime_directory()
EMAIL_LIST_FILE, TOKEN_FILE = str(DATA_DIRECTORY / "email_list.txt"), str(DATA_DIRECTORY / "accounts_with_tokens.txt")

# Storage ---------------------------------------------------------------------------
def valid_email(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value))

def valid_token(value: str) -> bool:
    return value.startswith("M.")

def valid_client_id(value: str) -> bool:
    return bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", value))

def load_email_list(filepath: str) -> List[Dict[str, str]]:
    if not os.path.exists(filepath): return []
    rows = []
    with open(filepath, encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("|")
            if parts and not line.lstrip().startswith("#") and valid_email(parts[0].strip()):
                rows.append({"email": parts[0].strip(), "password": parts[1].strip() if len(parts) > 1 else ""})
    return rows

def load_accounts(filepath: str) -> List[Dict[str, str]]:
    if not os.path.exists(filepath): return []
    rows = []
    with open(filepath, encoding="utf-8") as file:
        for line in file:
            parts = [part.strip() for part in line.strip().split("|")]
            if len(parts) == 4: email, password, token, client_id = parts
            elif len(parts) == 3: email, token, client_id = parts; password = ""
            else: continue
            if valid_email(email) and valid_token(token) and valid_client_id(client_id):
                rows.append({"email": email, "password": password, "refresh_token": token, "client_id": client_id, "status": "unknown", "status_msg": ""})
    return rows

def atomic_write(filepath: str, lines: List[str]) -> bool:
    path = None
    try:
        descriptor, path = tempfile.mkstemp(prefix=".tokens-", dir=os.path.dirname(os.path.abspath(filepath)), text=True)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file: file.writelines(lines)
        os.replace(path, filepath); return True
    except (OSError, UnicodeError):
        if path and os.path.exists(path):
            try: os.remove(path)
            except OSError: pass
        return False

def upsert_token(filepath: str, email: str, password: str, token: str, client_id: str) -> bool:
    lines, found = [], False
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as file:
            for line in file:
                values = line.strip().split("|")
                if not line.strip() or line.startswith("#") or values[0].strip().lower() != email.lower(): lines.append(line); continue
                if found: continue
                old_password = values[1] if len(values) == 4 else ""
                password = password or old_password
                lines.append(f"{email}|{password}|{token}|{client_id}\n" if password else f"{email}|{token}|{client_id}\n"); found = True
    if not found: lines.append(f"{email}|{password}|{token}|{client_id}\n" if password else f"{email}|{token}|{client_id}\n")
    return atomic_write(filepath, lines)

def rotate_token(filepath: str, email: str, token: str) -> bool:
    if not os.path.exists(filepath): return False
    lines, found = [], False
    with open(filepath, encoding="utf-8") as file:
        for line in file:
            values = line.strip().split("|")
            if line.strip() and not line.lstrip().startswith("#") and values[0].strip().lower() == email.lower() and len(values) in {3, 4}:
                lines.append(f"{values[0]}|{values[1]}|{token}|{values[3]}\n" if len(values) == 4 else f"{values[0]}|{token}|{values[2]}\n"); found = True
            else: lines.append(line)
    return atomic_write(filepath, lines) if found else False

def ensure_data_files(email_file: str, token_file: str) -> None:
    for path, header in ((email_file, "# Input format: email or email|password\n"), (token_file, "# Token format: email|password|refresh_token|client_id\n")):
        if not os.path.exists(path):
            try:
                with open(path, "w", encoding="utf-8") as file: file.write(header)
            except OSError: pass

# Parsing, proxy, Microsoft API ------------------------------------------------------
class HTMLToText(HTMLParser):
    def __init__(self) -> None: super().__init__(); self.parts: List[str] = []; self.skip = 0
    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if self.skip:
            if tag in {"script", "style", "head"}: self.skip += 1
        elif tag in {"script", "style", "head"}: self.skip = 1
        elif tag in {"p", "br", "div", "tr"}: self.parts.append("\n")
        elif tag == "li": self.parts.append("\n• ")
    def handle_endtag(self, tag: str) -> None:
        if self.skip:
            if tag in {"script", "style", "head"}: self.skip -= 1
        elif tag in {"p", "div", "table"}: self.parts.append("\n")
    def handle_data(self, data: str) -> None:
        if not self.skip: self.parts.append(data)
    def text(self) -> str:
        value = re.sub(r"[\u200b\u200c\u200d\ufeff\u00a0]", "", "".join(self.parts))
        value = re.sub(r"[ \t]+", " ", value); value = re.sub(r"\n[ \t]+|[ \t]+\n", "\n", value); value = re.sub(r"\n{3,}", "\n\n", value)
        return "\n".join(line.strip() for line in value.splitlines()).strip()

def plain_html(value: str) -> str:
    parser = HTMLToText(); parser.feed(value or ""); return parser.text()

def parse_proxy(value: str, protocol: str) -> Tuple[Optional[str], Optional[str]]:
    raw = re.sub(r"^(http|https|socks5|socks4)://", "", value.strip(), flags=re.I)
    if not raw or "@" not in raw: return None, "Authentication is required: user:pass@host:port or host:port@user:pass."
    parts = raw.split("@")
    if len(parts) != 2: return None, "Use user:pass@host:port or host:port@user:pass."
    host_pattern = r"^([a-zA-Z0-9.-]+):(\d{1,5})$"; first, second = re.match(host_pattern, parts[0]), re.match(host_pattern, parts[1])
    # Prefer the conventional user:pass@host:port form when both halves happen
    # to match host:port (for example when the password contains only digits).
    if second: host, port, auth = second.group(1), second.group(2), parts[0]
    elif first: host, port, auth = first.group(1), first.group(2), parts[1]
    else: return None, "Could not parse proxy."
    credentials = auth.split(":", 1)
    if len(credentials) != 2 or not all(credentials): return None, "Invalid authentication format."
    if not 1 <= int(port) <= 65535: return None, f"Port {port} is outside 1-65535."
    scheme = "socks5" if protocol.lower() == "socks5" else "http"
    return f"{scheme}://{quote(credentials[0], safe='')}:{quote(credentials[1], safe='')}@{host}:{port}", None

async def test_proxy(proxy: str) -> Tuple[bool, str]:
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=20) as client: response = await client.get("https://login.microsoftonline.com")
        return (True, f"🟢 Proxy connected and active (HTTP {response.status_code})") if response.status_code in {200,302,400,401,403} else (False, f"🔴 Unexpected proxy response (HTTP {response.status_code})")
    except Exception as error: return False, f"🔴 Proxy error: {str(error)[:80]}"

def friendly_error(error: str) -> str:
    for code, message in ERROR_MESSAGES.items():
        if code in error: return f"[{code}] {message}"
    normalized = error.replace("ERROR_", "HTTP ")
    if "HTTP 400" in normalized: return f"Bad Request: {error}"[:120]
    if "HTTP 401" in normalized: return "Unauthorized - token is invalid or expired"
    if "HTTP 403" in normalized: return "Forbidden - access denied"
    if "HTTP 404" in normalized: return "Not Found - resource does not exist"
    return normalized[:120] or "Unknown error"

async def access_token(refresh: str, client_id: str, email: str, token_file: str, proxy: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    data = {"grant_type":"refresh_token", "client_id":client_id, "refresh_token":refresh, "scope":"https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/User.Read"}
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=60 if proxy else 30) as client: response = await client.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", data=data)
        prefix = "Proxy request failed: " if proxy else ""
        try: body = response.json()
        except ValueError: return None, None, f"{prefix}HTTP {response.status_code}: invalid token response"
        if not isinstance(body, dict): return None, None, f"{prefix}HTTP {response.status_code}: invalid token response"
        if response.status_code != 200:
            detail = body.get("error_description") or body.get("error") or response.text[:200]
            return None, None, f"{prefix}HTTP {response.status_code}: {detail}"
        if not body.get("access_token"):
            detail = body.get("error_description") or body.get("error") or "access_token was not returned"
            return None, None, f"HTTP 200: {detail}"
        new_refresh = body.get("refresh_token") or refresh
        if new_refresh != refresh: rotate_token(token_file, email, new_refresh)
        return body["access_token"], new_refresh, None
    except (httpx.HTTPError, ValueError) as error: return None, None, ("Proxy connection failed: " if proxy else "") + str(error)

async def inbox(token: str, days: Optional[int], top: int, proxy: Optional[str]) -> Union[List[Dict[str, Any]], str]:
    params = {"$orderby":"receivedDateTime desc", "$top":str(max(1,min(100,top))), "$select":"id,subject,from,receivedDateTime,body,bodyPreview,isRead"}
    if days: params["$filter"] = f"receivedDateTime ge {(datetime.now(timezone.utc)-timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=60 if proxy else 30) as client: response = await client.get(INBOX_MESSAGES_URL, headers={"Authorization":f"Bearer {token}"}, params=params)
        try: body = response.json()
        except ValueError: body = None
        if response.status_code == 200:
            if not isinstance(body, dict) or not isinstance(body.get("value", []), list): return "ERROR_RESPONSE: Invalid Microsoft Graph response."
            return body.get("value", [])
        detail = response.text[:200]
        if isinstance(body, dict):
            graph_error = body.get("error")
            if isinstance(graph_error, dict): detail = str(graph_error.get("message") or detail)
        error = f"ERROR_{response.status_code}: {detail}"
        return f"ERROR_PROXY: {error}" if proxy else error
    except httpx.HTTPError as error: return f"ERROR_{'PROXY' if proxy else 'NET'}: {error}"

def start_device_flow(client_id: str) -> Tuple[Optional[msal.PublicClientApplication], Optional[Dict[str, Any]], Optional[str]]:
    try:
        client = msal.PublicClientApplication(client_id, authority=AUTHORITY); flow = client.initiate_device_flow(scopes=SCOPES)
        return (client, flow, None) if "user_code" in flow else (None, None, str(flow))
    except Exception as error: return None, None, str(error)

def finish_device_flow(client: msal.PublicClientApplication, flow: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    try:
        result = client.acquire_token_by_device_flow(flow)
        return result.get("refresh_token"), None if result.get("refresh_token") else str(result.get("error_description") or "No refresh token was returned")
    except Exception as error: return None, str(error)

# UI widgets -------------------------------------------------------------------------
class AccountSelected(Message):
    def __init__(self, account: Dict[str, Any]) -> None: self.account = account; super().__init__()
class EmailSelected(Message):
    def __init__(self, item: Dict[str, Any]) -> None: self.item = item; super().__init__()

class AccountItem(ListItem):
    def __init__(self, account: Dict[str, Any]) -> None:
        self.account = account; icon = "🟢" if account["status"] == "active" else "🔴" if account["status"] in {"expired","error"} else "⚪"
        super().__init__(Label(f"{icon} {escape(account['email'])}\n[dim]{account['status'].title()}[/]"))

class AccountSidebar(Widget):
    DEFAULT_CSS = """
    AccountSidebar { width: 32; dock: left; border-right: heavy $accent; background: $surface; }
    AccountSidebar Input { margin: 1 1 0 1; }
    AccountSidebar ListView { height: 1fr; margin: 1; }
    """
    def __init__(self, accounts: List[Dict[str, Any]], **kwargs: Any) -> None: super().__init__(**kwargs); self.accounts = accounts
    def compose(self) -> ComposeResult: yield Input(placeholder="🔍 Search accounts...", id="account_search"); yield ListView(id="account_list")
    def on_mount(self) -> None: self.update_accounts(self.accounts)
    def update_accounts(self, accounts: List[Dict[str, Any]]) -> None:
        self.accounts = accounts; query = self.query_one("#account_search", Input).value.lower().strip() if self.is_mounted else ""
        view = self.query_one("#account_list", ListView); view.clear(); shown = [a for a in accounts if not query or query in a["email"].lower()]
        for account in shown: view.append(AccountItem(account))
        if not shown: view.append(ListItem(Label("No valid accounts found.")))
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "account_search": self.update_accounts(self.accounts)
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, AccountItem): self.post_message(AccountSelected(event.item.account))

def local_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception: return value or "?"

class MailTable(Widget):
    DEFAULT_CSS = """
    MailTable { height: 1fr; border-bottom: solid $accent; }
    MailTable Input { margin: 1 1 0 1; }
    MailTable DataTable { height: 1fr; margin: 1; }
    #mail_status { color: $text-muted; text-align: center; padding: 1; height: auto; }
    """
    def __init__(self, **kwargs: Any) -> None: super().__init__(**kwargs); self.items: List[Dict[str,Any]]=[]; self.filtered: List[Dict[str,Any]]=[]
    def compose(self) -> ComposeResult: yield Input(placeholder="🔍 Search subject or sender...",id="mail_search"); yield Static("No emails loaded.",id="mail_status"); yield DataTable(id="mail_table",cursor_type="row")
    def on_mount(self) -> None: self.query_one("#mail_table",DataTable).add_columns("No","Subject","From","Received (Local)")
    @staticmethod
    def sender(item: Dict[str,Any]) -> str:
        sender = item.get("from")
        if not isinstance(sender, dict): return ""
        address = sender.get("emailAddress")
        if not isinstance(address, dict): return ""
        value = address.get("address")
        return value if isinstance(value, str) else ""
    def set_items(self, items: List[Dict[str,Any]], status: Optional[str]=None) -> None:
        self.items=items; table=self.query_one("#mail_table",DataTable); table.clear(); query=self.query_one("#mail_search",Input).value.lower().strip()
        self.filtered=[x for x in items if not query or query in str(x.get("subject") or "").lower() or query in self.sender(x).lower()]
        state=self.query_one("#mail_status",Static); state.update(status or ("No matching emails." if query else "No emails loaded.")); state.display=not bool(self.filtered)
        for index,item in enumerate(self.filtered,1): table.add_row(str(index),str(item.get("subject") or "(no subject)")[:50],self.sender(item)[:30] or "?",local_time(str(item.get("receivedDateTime") or "?"))[:16],key=str(index-1))
    def on_input_changed(self,event:Input.Changed)->None:
        if event.input.id=="mail_search": self.set_items(self.items)
    def on_data_table_row_selected(self,event:DataTable.RowSelected)->None:
        try:self.post_message(EmailSelected(self.filtered[int(event.row_key.value)]))
        except (ValueError,TypeError,IndexError):pass

class MailViewer(Widget):
    DEFAULT_CSS="""
    MailViewer { height: 1fr; padding: 0 1 1 1; background: $surface; }
    #mail_meta { padding: 0 1; background: $panel; border: solid $accent; margin-bottom: 0; height: auto; }
    #mail_body { height: 1fr; border: solid $secondary; padding: 1; margin-top: 0; background: $surface-darken-1; }
    """
    def compose(self)->ComposeResult:
        yield Static("Select an email from the inbox to read its content.",id="mail_meta")
        with VerticalScroll(id="mail_body"): yield Static("",id="mail_text",markup=False)
    def clear(self)->None:self.query_one("#mail_meta",Static).update("Select an email from the inbox to read its content.");self.query_one("#mail_text",Static).update("")
    def show(self,item:Dict[str,Any],recipient:str)->None:
        sender=MailTable.sender(item) or "?"; subject=item.get("subject") or "(no subject)"; body=item.get("body") if isinstance(item.get("body"),dict) else {}; content=str(body.get("content") or "")
        received = local_time(str(item.get("receivedDateTime") or "?"))
        self.query_one("#mail_meta",Static).update(f"[bold cyan]Subject:[/] {escape(str(subject))}\n[bold cyan]From:[/] {escape(sender)} | [bold cyan]To:[/] {escape(recipient)}\n[bold cyan]Date:[/] {escape(received)}")
        self.query_one("#mail_text",Static).update(plain_html(content) if str(body.get("contentType","")).lower()=="html" else content or "(Empty message body)")

# Screens ---------------------------------------------------------------------------
class Alert(ModalScreen[None]):
    BINDINGS=[("escape","close","Close"),("enter","close","Close")]
    DEFAULT_CSS="""
    Alert { align: center middle; background: rgba(0, 0, 0, 0.7); }
    #alert_dialog { width: 60; max-width: 90%; height: auto; padding: 1 2; background: $panel; border: thick $warning; }
    #alert_title { text-style: bold; color: $warning; margin-bottom: 1; }
    #alert_message { margin-bottom: 1; } #alert_button_row { margin-top: 1; align: center middle; }
    #alert_button_row Button { min-width: 16; }
    """
    def __init__(self,title:str,message:str)->None:super().__init__();self.title,self.message=title,message
    def compose(self)->ComposeResult:
        with Vertical(id="alert_dialog"):
            yield Label(self.title,id="alert_title");yield Static(self.message,id="alert_message",markup=False)
            with Horizontal(id="alert_button_row"):yield Button("OK / Close [Esc]",id="close",variant="warning")
    def action_close(self)->None:self.dismiss(None)
    def on_button_pressed(self,event:Button.Pressed)->None:
        if event.button.id=="close":self.dismiss(None)

class DeviceFlow(ModalScreen[Optional[str]]):
    BINDINGS=[("escape","cancel","Cancel / Skip")]
    DEFAULT_CSS="""
    DeviceFlow { align: center middle; background: rgba(0, 0, 0, 0.7); }
    #dialog { width: 72; max-width: 90%; height: auto; max-height: 90%; padding: 1 2; background: $panel; border: thick $accent; }
    .verification-uri { color: $accent; background: $surface; padding: 0 1; margin: 0 0 1 0; height: auto; max-height: 4; overflow-y: auto; }
    .user-code { background: $warning-muted; color: $warning; text-align: center; text-style: bold; padding: 0 1; margin: 1 0; height: 3; }
    .step { margin-bottom: 0; } #status_hint { color: $accent; margin-top: 1; text-style: bold; }
    #button_row { dock: bottom; height: 3; align: center middle; margin-bottom: 1; } #button_row Button { margin: 0 1; min-width: 26; }
    """
    def __init__(self,email:str,flow:Dict[str,Any])->None:super().__init__();self.email,self.flow=email,flow
    def compose(self)->ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"[bold cyan]LOGIN AUTHORIZATION FOR:[/] {escape(self.email)}",id="title")
            yield Label("1. Open this URL in your browser:",classes="step");yield Static(str(self.flow.get("verification_uri")or"Unavailable"),classes="verification-uri",markup=False)
            yield Label("2. Enter this code:",classes="step");yield Static(str(self.flow.get("user_code")or"Unavailable"),classes="user-code",markup=False)
            yield Label("3. Sign in and accept the requested permissions.",classes="step");yield Label("⌛ Waiting for browser authorization...",id="status_hint")
            with Horizontal(id="button_row"):yield Button("[Esc] Cancel / Skip",id="cancel",variant="error")
    def action_cancel(self)->None:self.dismiss(None)
    def on_button_pressed(self,event:Button.Pressed)->None:
        if event.button.id=="cancel":self.dismiss(None)

class Home(Screen):
    BINDINGS=[("q","quit","Quit"),("g","generate","Generate Tokens"),("e","dashboard","Manage Email")]
    DEFAULT_CSS="""
    Home { layout: vertical; padding: 0; }
    #home_content { height: 1fr; padding: 1 2; }
    .section-box { margin-bottom: 1; padding: 1; background: $surface; border: solid $secondary; height: auto; }
    .section-title { text-style: bold; color: $accent; margin-bottom: 1; }
    .field-label { margin-top: 1; text-style: bold; }
    #actions_row { height: auto; layout: horizontal; margin-top: 1; }
    #actions_row Button { width: 1fr; min-width: 24; margin-right: 1; }
    #proxy_row { height: auto; align: left middle; margin-top: 1; }
    #proxy_row Button { margin-left: 1; } #proxy_status { margin-top: 1; }
    """
    def compose(self)->ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="home_content"):
            with Vertical(classes="section-box"):
                yield Label("🚀 MAIN NAVIGATION",classes="section-title")
                with Horizontal(id="actions_row"):
                    yield Button("🚀 Manage Email (Open Dashboard)",id="dashboard",variant="primary")
                    yield Button("🔑 Generate New Token",id="generate",variant="success")
                    yield Button("📁 Create / Refresh Files",id="files")
            with Vertical(classes="section-box"):
                yield Label("⚙️ EMAIL FETCH SETTINGS",classes="section-title")
                yield Label("Email retrieval mode:",classes="field-label")
                yield Select([("Latest email count (10 - 100)","top"),("Date range (last 1 - 30 days)","days")],id="mode",value="top")
                yield Label("Limit / value (for example: 50 emails or 14 days):",classes="field-label")
                yield Input(value="50",placeholder="Enter a number (10-100 or 1-30)",id="limit")
            with Vertical(classes="section-box"):
                yield Label("🛡️ PROXY SETTINGS (Optional)",classes="section-title")
                yield Label("Proxy protocol:",classes="field-label")
                yield Select([("HTTP / HTTPS proxy","http"),("SOCKS5 proxy","socks5")],id="protocol",value="http")
                yield Label("Proxy string (user:pass@host:port or host:port@user:pass):",classes="field-label")
                yield Input(placeholder="user:pass@1.2.3.4:8080 (authentication is required)",id="proxy")
                with Horizontal(id="proxy_row"): yield Button("🧪 Test Proxy Connection",id="test_proxy",variant="warning")
                yield Static("⚪ Proxy status: Inactive (direct connection)",id="proxy_status",markup=False)
        yield Footer()
    def on_mount(self)->None:
        ensure_data_files(self.app.email_file,self.app.token_file);self.update_layout(self.size.width)
    def on_resize(self,event:Resize)->None:self.update_layout(event.size.width)
    def update_layout(self,width:int)->None:
        try:
            actions=self.query_one("#actions_row",Horizontal);actions.styles.layout="vertical" if width<=100 else "horizontal"
            for button in actions.query(Button):button.styles.width="100%" if width<=100 else "1fr"
            proxy=self.query_one("#proxy_row",Horizontal);proxy.styles.layout="vertical" if width<=100 else "horizontal";proxy.query_one(Button).styles.width="100%" if width<=100 else "auto"
        except Exception:pass
    def on_button_pressed(self,event:Button.Pressed)->None:
        if event.button.id=="dashboard":self.open_dashboard()
        elif event.button.id=="generate":self.app.open_generator()
        elif event.button.id=="files":ensure_data_files(self.app.email_file,self.app.token_file);self.notify(f"Data files are ready in {self.app.data_directory}.")
        elif event.button.id=="test_proxy":self.run_worker(self.proxy_worker(),thread=False)
    async def proxy_worker(self)->None:
        value=self.query_one("#proxy",Input).value;status=self.query_one("#proxy_status",Static)
        if not value.strip():status.update("⚪ Proxy status: Inactive (direct connection)");return
        status.update("⏳ Testing proxy connection to Microsoft...")
        proxy,error=parse_proxy(value,str(self.query_one("#protocol",Select).value))
        if error:status.update(f"🔴 Proxy error: {error}");return
        _,message=await test_proxy(str(proxy));status.update(message)
    def open_dashboard(self)->None:
        if not load_accounts(self.app.token_file):self.app.push_screen(Alert("❌ Access Denied","Generate a valid token first."));return
        try:value=int(self.query_one("#limit",Input).value)
        except ValueError:self.app.push_screen(Alert("🔴 Invalid Value","Enter a numeric email limit."));return
        mode=str(self.query_one("#mode",Select).value)
        if (mode=="top" and not 10<=value<=100) or (mode=="days" and not 1<=value<=30):self.app.push_screen(Alert("🔴 Value Out Of Range","Use 10-100 emails or 1-30 days."));return
        proxy,error=parse_proxy(self.query_one("#proxy",Input).value,str(self.query_one("#protocol",Select).value))
        if error and self.query_one("#proxy",Input).value.strip():self.app.push_screen(Alert("🔴 Invalid Proxy",error));return
        self.app.mode,self.app.limit,self.app.proxy=mode,value,proxy;self.app.switch_screen("dashboard")
    def action_generate(self)->None:self.app.open_generator()
    def action_dashboard(self)->None:self.open_dashboard()

class Generator(ModalScreen[Optional[Tuple[str,str,str]]]):
    BINDINGS=[("escape","cancel","Cancel")]
    DEFAULT_CSS="""
    Generator { align: center middle; background: rgba(0, 0, 0, 0.7); }
    #gen_dialog { width: 66; max-width: 90%; height: auto; max-height: 90%; padding: 1 2; background: $panel; border: thick $accent; }
    .field-label { margin-top: 1; text-style: bold; } #gen_button_row { height: auto; margin-top: 1; align: center middle; }
    #gen_button_row Button { width: 1fr; min-width: 20; margin: 0 1; }
    """
    def compose(self)->ComposeResult:
        token_name=Path(self.app.token_file).name;files=sorted(x for x in Path(self.app.data_directory).glob("*.txt") if x.name!=token_name);options=[(x.name,str(x))for x in files]or[("No .txt files found","none")];selected=options[0][1]
        with Vertical(id="gen_dialog"):
            yield Label("[bold cyan]GENERATE NEW REFRESH TOKENS[/bold cyan]")
            yield Label("1. Select input email file:",classes="field-label");yield Select(options,id="file",value=selected)
            yield Label("2. Select target email account:",classes="field-label");yield Select(self.emails(selected),id="email",value=self.emails(selected)[0][1])
            yield Label("3. Select Client ID preset:",classes="field-label");yield Select([(x["name"],x["id"])for x in CLIENT_PRESETS.values()],id="client",value=next(iter(CLIENT_PRESETS.values()))["id"])
            yield Static("")
            with Horizontal(id="gen_button_row"):
                yield Button("[Esc] Cancel",id="cancel",variant="error");yield Button("Start Generating",id="start",variant="success")
    def emails(self,path:str)->List[Tuple[str,str]]:
        items=load_email_list(path)if path and path!="none"else[];return [(f"All accounts ({len(items)} emails)","ALL")]+[(x["email"],x["email"])for x in items]if items else[("No valid emails found","none")]
    def on_mount(self)->None:self.update_layout(self.size.width)
    def on_resize(self,event:Resize)->None:self.update_layout(event.size.width)
    def update_layout(self,width:int)->None:
        try:
            row=self.query_one("#gen_button_row",Horizontal)
            row.styles.layout="vertical" if width<=80 else "horizontal"
            for button in row.query(Button):button.styles.width="100%" if width<=80 else "1fr"
        except Exception:pass
    def on_select_changed(self,event:Select.Changed)->None:
        if event.select.id=="file":options=self.emails(str(event.value));select=self.query_one("#email",Select);select.set_options(options);select.value=options[0][1]
    def action_cancel(self)->None:self.dismiss(None)
    def on_button_pressed(self,event:Button.Pressed)->None:
        if event.button.id=="cancel":self.dismiss(None)
        elif event.button.id=="start":
            file,email,client=(self.query_one(f"#{x}",Select).value for x in("file","email","client"))
            if file!="none"and email!="none":self.dismiss((str(file),str(client),str(email)))
            else:self.notify("Select an input file, account, and client ID first.",severity="warning")

class Dashboard(Screen):
    BINDINGS=[("h","home","Home"),("r","refresh","Refresh"),("g","generate","Generate Tokens"),("l","reload","Reload Accounts")]
    DEFAULT_CSS="""
    Dashboard { layout: horizontal; }
    #dashboard_main_content { height: 1fr; width: 1fr; }
    #mails { height: 2fr; min-height: 8; }
    #viewer { height: 3fr; min-height: 8; }
    #status { dock: bottom; height: 1; background: $primary; color: $text; padding: 0 1; }
    """
    def compose(self)->ComposeResult:
        yield Header(show_clock=True);yield AccountSidebar([],id="accounts")
        with Vertical(id="dashboard_main_content"):yield MailTable(id="mails");yield MailViewer(id="viewer")
        yield Static("Ready",id="status",markup=False);yield Footer()
    def on_mount(self)->None:self.update_layout(self.size.width,self.size.height);self.app.reload_accounts()
    def on_resize(self,event:Resize)->None:self.update_layout(event.size.width,event.size.height)
    def update_layout(self,width:int,height:int)->None:
        try:
            self.query_one("#accounts",AccountSidebar).styles.width=24 if width<=80 else 32
            self.query_one("#mails",MailTable).styles.height="1fr" if height<=30 else "2fr"
            self.query_one("#viewer",MailViewer).styles.height="1fr" if height<=30 else "3fr"
        except Exception:pass
    def action_home(self)->None:self.app.switch_screen("home")
    def action_refresh(self)->None:self.app.refresh_inbox()
    def action_generate(self)->None:self.app.open_generator()
    def action_reload(self)->None:self.app.reload_accounts()

# Application -----------------------------------------------------------------------
class OutlookCommander(App):
    TITLE="OUTLOOK COMMANDER";SUB_TITLE="Multi-Account Email Management Tool";SCREENS={"home":Home,"dashboard":Dashboard};BINDINGS=[("q","quit","Quit")]
    def __init__(self)->None:
        super().__init__();self.data_directory=str(DATA_DIRECTORY);self.email_file,self.token_file=EMAIL_LIST_FILE,TOKEN_FILE;self.accounts:List[Dict[str,Any]]=[];self.current:Optional[Dict[str,Any]]=None;self.current_access_token:Optional[str]=None;self.mode="top";self.limit=50;self.proxy:Optional[str]=None;self.request_id=0
    def on_mount(self)->None:ensure_data_files(self.email_file,self.token_file);self.push_screen("home")
    def status(self,text:str)->None:
        try:self.get_screen("dashboard").query_one("#status",Static).update(text)
        except Exception:pass
    def reload_accounts(self)->None:
        self.accounts=load_accounts(self.token_file);old=self.current["email"].lower()if self.current else"";self.current=next((x for x in self.accounts if x["email"].lower()==old),None);self.current_access_token=None
        try:self.get_screen("dashboard").query_one("#accounts",AccountSidebar).update_accounts(self.accounts);self.get_screen("dashboard").query_one("#mails",MailTable).set_items([]);self.get_screen("dashboard").query_one("#viewer",MailViewer).clear()
        except Exception:pass
        self.status(f"Loaded {len(self.accounts)} account(s).")
    def on_account_selected(self,message:AccountSelected)->None:
        self.request_id+=1;self.current=message.account;self.current_access_token=None
        try:self.get_screen("dashboard").query_one("#mails",MailTable).set_items([],"Loading inbox...");self.get_screen("dashboard").query_one("#viewer",MailViewer).clear()
        except Exception:pass
        self.run_worker(self.fetch(message.account,self.request_id),thread=False)
    async def fetch(self,account:Dict[str,Any],request_id:int)->None:
        token,new_token,error=await access_token(account["refresh_token"],account["client_id"],account["email"],self.token_file,self.proxy)
        if new_token:account["refresh_token"]=new_token
        if self.current is not account or request_id!=self.request_id:return
        if not token:
            account["status"]="error"if(error or"").startswith("Proxy ")else"expired";account["status_msg"]=friendly_error(error or"Authentication failed")
            try:self.get_screen("dashboard").query_one("#accounts",AccountSidebar).update_accounts(self.accounts)
            except Exception:pass
            self.status(f"🔴 Auth Error for {account['email']}: {account['status_msg']}");return
        account["status"]="active";self.current_access_token=token
        try:self.get_screen("dashboard").query_one("#accounts",AccountSidebar).update_accounts(self.accounts)
        except Exception:pass
        self.status(f"Fetching emails for {account['email']}...");items=await inbox(token,self.limit if self.mode=="days"else None,self.limit if self.mode=="top"else 100,self.proxy)
        if self.current is not account or request_id!=self.request_id:return
        if isinstance(items,str):self.get_screen("dashboard").query_one("#mails",MailTable).set_items([],"Unable to load inbox.");self.status(f"🔴 Error: {friendly_error(items)}")
        else:
            self.get_screen("dashboard").query_one("#mails",MailTable).set_items(items)
            connection="Proxy Active"if self.proxy else"Direct"
            self.status(f"🟢 Active | Inbox loaded for {account['email']} ({len(items)} emails) [{connection}]")
    def on_email_selected(self,message:EmailSelected)->None:
        if self.current:self.get_screen("dashboard").query_one("#viewer",MailViewer).show(message.item,self.current["email"])
    def refresh_inbox(self)->None:
        if self.current:self.request_id+=1;self.run_worker(self.fetch(self.current,self.request_id),thread=False)
        else:self.status("Select an account first.")
    def open_generator(self)->None:
        def handle(result:Optional[Tuple[str,str,str]])->None:
            if result:self.run_worker(self.generate(*result),thread=False)
        self.push_screen(Generator(),handle)
    async def generate(self,filepath:str,client_id:str,target:str)->None:
        accounts=load_email_list(filepath);accounts=[x for x in accounts if target=="ALL"or x["email"].lower()==target.lower()]
        if not accounts:self.notify("No valid accounts found.",severity="error");return
        success=0
        for account in accounts:
            client,flow,error=start_device_flow(client_id)
            if not client or not flow:self.notify(f"Device flow failed for {account['email']}: {error}",severity="error");continue
            task=asyncio.create_task(asyncio.to_thread(finish_device_flow,client,flow));closed=asyncio.get_running_loop().create_future();modal=DeviceFlow(account["email"],flow);self.push_screen(modal,lambda result:not closed.done()and closed.set_result(result))
            while not task.done()and not closed.done():await asyncio.sleep(.4)
            if closed.done()and closed.result()is None:
                flow["expires_at"]=0;task.cancel();self.notify(f"Skipped: {account['email']}",severity="warning");continue
            if not closed.done():modal.dismiss("auto")
            try:refresh,error=await task
            except Exception as exception:refresh,error=None,str(exception)
            if refresh:
                if upsert_token(self.token_file,account["email"],account["password"],refresh,client_id):success+=1;self.notify(f"🟢 Token created for {account['email']}.")
                else:self.notify(f"🔴 Failed to save the token for {account['email']}.",severity="error")
            else:self.notify(f"🔴 Login failed for {account['email']}: {error}",severity="error")
        self.notify(f"Token generation complete: {success}/{len(accounts)} succeeded.",title="Generation Complete",severity="information"if success else"error");self.reload_accounts()

def main()->None:
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
    OutlookCommander().run()
if __name__=="__main__":
    try:main()
    except KeyboardInterrupt:print("\nProgram stopped by user.")
