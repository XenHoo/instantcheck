"""Flask Web App for CapCut Account Checker.

Runs a web UI with realtime streaming checking, separate result fields
(Live/PRO, Free, Die/Error), copy buttons, and optional CSV/TXT download.
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, Response, render_template_string, request, jsonify

import capcut_check
import capcut_cli

app = Flask(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CapCut Account Checker</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #0f172a;
      color: #f1f5f9;
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    .card {
      background-color: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
    }
    .form-control {
      background-color: #0f172a;
      border: 1px solid #334155;
      color: #f8fafc;
      border-radius: 8px;
    }
    .form-control:focus {
      background-color: #0f172a;
      border-color: #38bdf8;
      color: #f8fafc;
      box-shadow: 0 0 0 0.25rem rgba(56, 189, 248, 0.2);
    }
    .result-box {
      background-color: #0f172a;
      border: 1px solid #334155;
      color: #f8fafc;
      font-family: monospace;
      font-size: 0.85rem;
      border-radius: 8px;
      resize: vertical;
      min-height: 180px;
    }
    .badge-counter {
      font-size: 0.9rem;
      padding: 4px 10px;
      border-radius: 20px;
    }
    .btn-custom-start {
      background: linear-gradient(135deg, #0284c7, #06b6d4);
      color: white;
      font-weight: 600;
      border: none;
    }
    .btn-custom-start:hover {
      background: linear-gradient(135deg, #0369a1, #0891b2);
      color: white;
    }
  </style>
</head>
<body class="py-4">
  <div class="container-fluid px-lg-5">
    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom border-secondary">
      <div class="d-flex align-items-center gap-3">
        <i class="fa-solid fa-film text-info fa-2x"></i>
        <div>
          <h3 class="mb-0 fw-bold">CapCut Account Checker</h3>
          <small class="text-secondary">Cek status akun CapCut (PRO / Free / Expiry) secara realtime</small>
        </div>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="row g-4">
      <!-- Input Column -->
      <div class="col-lg-5">
        <div class="card p-3 shadow-sm h-100">
          <h5 class="fw-bold mb-3"><i class="fa-solid fa-list-check me-2 text-primary"></i>Input Data</h5>
          
          <div class="mb-3">
            <label class="form-label text-secondary small fw-semibold">DAFTAR AKUN (Format: email:pass, email|pass, dll)</label>
            <textarea id="accountsInput" class="form-control" rows="8" placeholder="user1@example.com:password123&#10;user2@example.com|password456"></textarea>
            <div class="d-flex justify-content-between mt-1">
              <small id="accountCount" class="text-muted">Total: 0 akun</small>
              <button class="btn btn-sm btn-link text-decoration-none p-0 text-danger" onclick="document.getElementById('accountsInput').value=''; updateCount();">Clear</button>
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label text-secondary small fw-semibold">RESIDENTIAL PROXY URL (Wajib)</label>
            <input type="text" id="proxyInput" class="form-control" placeholder="http://user-session-{sess}:pass@gate.provider.com:7000" value="{{ default_proxy }}">
            <small class="text-muted" style="font-size: 0.75rem;">Gunakan token <code>{sess}</code> untuk rotasi IP otomatis per request.</small>
          </div>

          <div class="row g-2 mb-3">
            <div class="col-6">
              <label class="form-label text-secondary small fw-semibold">THREADS / WORKERS</label>
              <input type="number" id="workersInput" class="form-control" value="6" min="1" max="20">
            </div>
            <div class="col-6">
              <label class="form-label text-secondary small fw-semibold">IP RETRIES</label>
              <input type="number" id="retriesInput" class="form-control" value="6" min="1" max="15">
            </div>
          </div>

          <div class="d-flex gap-2">
            <button id="btnStart" class="btn btn-custom-start flex-grow-1 py-2" onclick="startChecking()">
              <i class="fa-solid fa-play me-2"></i>Mulai Check
            </button>
            <button id="btnStop" class="btn btn-danger py-2" onclick="stopChecking()" disabled>
              <i class="fa-solid fa-stop me-2"></i>Stop
            </button>
          </div>

          <!-- Progress bar -->
          <div class="mt-4">
            <div class="d-flex justify-content-between small text-secondary mb-1">
              <span>Progress</span>
              <span id="progressText">0 / 0 (0%)</span>
            </div>
            <div class="progress" style="height: 8px; background-color: #0f172a;">
              <div id="progressBar" class="progress-bar bg-info" style="width: 0%;"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Output Column -->
      <div class="col-lg-7">
        <div class="card p-3 shadow-sm">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="fw-bold mb-0"><i class="fa-solid fa-square-poll-vertical me-2 text-success"></i>Hasil Pengecekan</h5>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-light" onclick="downloadAll('csv')">
                <i class="fa-solid fa-file-csv me-1"></i>Download CSV
              </button>
              <button class="btn btn-sm btn-outline-light" onclick="downloadAll('txt')">
                <i class="fa-solid fa-file-lines me-1"></i>Download TXT
              </button>
            </div>
          </div>

          <!-- PRO Result Box -->
          <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <span class="fw-bold text-success">
                <i class="fa-solid fa-crown me-1"></i>PRO / VIP 
                <span id="proCount" class="badge bg-success badge-counter ms-1">0</span>
              </span>
              <div class="btn-group btn-group-sm">
                <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('proResult')">
                  <i class="fa-solid fa-copy me-1"></i>Copy
                </button>
                <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('proResult', 'pro_accounts.txt')">
                  <i class="fa-solid fa-download me-1"></i>Save
                </button>
              </div>
            </div>
            <textarea id="proResult" class="form-control result-box border-success" readonly placeholder="Akun PRO akan muncul di sini..."></textarea>
          </div>

          <!-- FREE Result Box -->
          <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <span class="fw-bold text-primary">
                <i class="fa-solid fa-user me-1"></i>FREE / REGULAR
                <span id="freeCount" class="badge bg-primary badge-counter ms-1">0</span>
              </span>
              <div class="btn-group btn-group-sm">
                <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('freeResult')">
                  <i class="fa-solid fa-copy me-1"></i>Copy
                </button>
                <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('freeResult', 'free_accounts.txt')">
                  <i class="fa-solid fa-download me-1"></i>Save
                </button>
              </div>
            </div>
            <textarea id="freeResult" class="form-control result-box border-primary" readonly placeholder="Akun FREE akan muncul di sini..."></textarea>
          </div>

          <!-- DIE / ERROR Result Box -->
          <div>
            <div class="d-flex justify-content-between align-items-center mb-1">
              <span class="fw-bold text-danger">
                <i class="fa-solid fa-circle-xmark me-1"></i>DEAD / ERROR
                <span id="dieCount" class="badge bg-danger badge-counter ms-1">0</span>
              </span>
              <div class="btn-group btn-group-sm">
                <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('dieResult')">
                  <i class="fa-solid fa-copy me-1"></i>Copy
                </button>
                <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('dieResult', 'die_accounts.txt')">
                  <i class="fa-solid fa-download me-1"></i>Save
                </button>
              </div>
            </div>
            <textarea id="dieResult" class="form-control result-box border-danger" readonly placeholder="Akun Gagal/Invalid akan muncul di sini..."></textarea>
          </div>

        </div>
      </div>
    </div>
  </div>

  <script>
    let abortController = null;
    let allRecords = [];

    const accountsInput = document.getElementById('accountsInput');
    accountsInput.addEventListener('input', updateCount);

    function updateCount() {
      const lines = accountsInput.value.trim().split('\\n').filter(l => l.trim().length > 0);
      document.getElementById('accountCount').textContent = `Total: ${lines.length} akun`;
    }

    function copyField(elementId) {
      const el = document.getElementById(elementId);
      if (!el.value.trim()) return;
      navigator.clipboard.writeText(el.value).then(() => {
        alert('Disalin ke clipboard!');
      });
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

    function downloadAll(format) {
      if (allRecords.length === 0) return alert('Belum ada hasil untuk didownload.');
      
      let content = '';
      let filename = '';
      let mimeType = '';

      if (format === 'csv') {
        content = 'email,password,status,plan,expiry,user_id,error\\n';
        for (const r of allRecords) {
          content += `"${r.email}","${r.password}","${r.status}","${r.plan || ''}","${r.expiry || ''}","${r.user_id || ''}","${r.error || ''}"\\n`;
        }
        filename = 'capcut_results.csv';
        mimeType = 'text/csv;charset=utf-8;';
      } else {
        for (const r of allRecords) {
          const uidStr = r.user_id ? ` | UID: ${r.user_id}` : '';
          content += `${r.email}:${r.password} | ${r.status}${uidStr} | ${r.expiry || r.error || ''}\\n`;
        }
        filename = 'capcut_results.txt';
        mimeType = 'text/plain;charset=utf-8;';
      }

      const blob = new Blob([content], { type: mimeType });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    }

    async function startChecking() {
      const text = accountsInput.value.trim();
      const proxy = document.getElementById('proxyInput').value.trim();
      const workers = parseInt(document.getElementById('workersInput').value) || 6;
      const retries = parseInt(document.getElementById('retriesInput').value) || 6;

      if (!text) {
        return alert('Silakan masukkan daftar akun terlebih dahulu!');
      }

      // Reset state & fields
      document.getElementById('proResult').value = '';
      document.getElementById('freeResult').value = '';
      document.getElementById('dieResult').value = '';
      document.getElementById('proCount').textContent = '0';
      document.getElementById('freeCount').textContent = '0';
      document.getElementById('dieCount').textContent = '0';
      allRecords = [];

      let countPro = 0;
      let countFree = 0;
      let countDie = 0;
      let checked = 0;

      document.getElementById('btnStart').disabled = true;
      document.getElementById('btnStop').disabled = false;

      abortController = new AbortController();

      try {
        const response = await fetch('/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            accounts_text: text,
            proxy: proxy,
            workers: workers,
            retries: retries
          }),
          signal: abortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\n');
          buffer = lines.pop(); // keep partial chunk

          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              const data = JSON.parse(line);
              
              if (data.type === 'init') {
                document.getElementById('progressText').textContent = `0 / ${data.total} (0%)`;
                document.getElementById('progressBar').style.width = '0%';
                continue;
              }

              if (data.type === 'result') {
                checked++;
                const r = data.data;
                allRecords.push(r);

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

                // Update progress
                const total = data.total;
                const percent = Math.round((checked / total) * 100);
                document.getElementById('progressText').textContent = `${checked} / ${total} (${percent}%)`;
                document.getElementById('progressBar').style.width = `${percent}%`;
              }
            } catch (e) {
              console.error('Error parsing stream line:', e);
            }
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          alert('Terjadi kesalahan saat memeriksa akun: ' + err.message);
        }
      } finally {
        document.getElementById('btnStart').disabled = false;
        document.getElementById('btnStop').disabled = true;
      }
    }

    function stopChecking() {
      if (abortController) {
        abortController.abort();
      }
      document.getElementById('btnStart').disabled = false;
      document.getElementById('btnStop').disabled = true;
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    default_proxy = os.environ.get("CAPCUT_PROXY", "")
    return render_template_string(HTML_TEMPLATE, default_proxy=default_proxy)

@app.route("/api/check", methods=["POST"])
def api_check():
    payload = request.get_json(force=True)
    accounts_text = payload.get("accounts_text", "")
    proxy_url = payload.get("proxy", "").strip() or os.environ.get("CAPCUT_PROXY", "")
    workers = int(payload.get("workers", 6))
    retries = int(payload.get("retries", 6))

    accounts = capcut_cli.parse_accounts(accounts_text)
    total = len(accounts)

    def generate():
        yield json.dumps({"type": "init", "total": total}) + "\n"
        if total == 0:
            return

        def _do_check(item):
            email, pw = item
            res = capcut_check.check_capcut_account(
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting CapCut Web Checker on http://0.0.0.0:{port} ...")
    app.run(host="0.0.0.0", port=port, debug=False)
