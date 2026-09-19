import sys
import os
import traceback

# Add directories to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
curr_dir = os.path.abspath(os.path.dirname(__file__))
cwd = os.getcwd()

for p in [root_dir, curr_dir, cwd, '/var/task', '/var/task/api']:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from app import app
except Exception as e:
    err_trace = traceback.format_exc()
    from flask import Flask, Response
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    def catch_all(path):
        return Response(
            f"<h2>Vercel Python Import Error</h2><pre style='background:#222;color:#f88;padding:15px;border-radius:6px;'>{err_trace}</pre><p><b>sys.path:</b> {sys.path}</p><p><b>Files in cwd:</b> {os.listdir(cwd) if os.path.exists(cwd) else 'N/A'}</p>",
            status=500,
            mimetype="text/html"
        )
