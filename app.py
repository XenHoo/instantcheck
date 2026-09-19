"""Unified Multi-Checker Web Dashboard: CapCut & Outlook Mail Checker.
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, Response, render_template_string, request, jsonify

import capcut_check
import capcut_cli
import outlook_check

app = Flask(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>All-in-One Multi Checker (CapCut & Outlook)</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #0b1329;
      color: #f1f5f9;
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    .card {
      background-color: #151f38;
      border: 1px solid #243456;
      border-radius: 12px;
    }
    .form-control {
      background-color: #0b1329;
      border: 1px solid #243456;
      color: #f8fafc;
      border-radius: 8px;
    }
    .form-control:focus {
      background-color: #0b1329;
      border-color: #38bdf8;
      color: #f8fafc;
      box-shadow: 0 0 0 0.25rem rgba(56, 189, 248, 0.2);
    }
    .result-box {
      background-color: #0b1329;
      border: 1px solid #243456;
      color: #f8fafc;
      font-family: monospace;
      font-size: 0.85rem;
      border-radius: 8px;
      resize: vertical;
      min-height: 170px;
    }
    .badge-counter {
      font-size: 0.9rem;
      padding: 4px 10px;
      border-radius: 20px;
    }
    .nav-pills .nav-link {
      color: #94a3b8;
      font-weight: 600;
      border-radius: 10px;
      padding: 10px 20px;
      border: 1px solid transparent;
      transition: all 0.2s;
    }
    .nav-pills .nav-link:hover {
      color: #f8fafc;
      background-color: #1e293b;
    }
    .nav-pills .nav-link.active {
      background: linear-gradient(135deg, #0284c7, #06b6d4);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
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
    <div class="d-flex flex-wrap align-items-center justify-content-between mb-4 pb-3 border-bottom border-secondary gap-3">
      <div class="d-flex align-items-center gap-3">
        <i class="fa-solid fa-layer-group text-info fa-2x"></i>
        <div>
          <h3 class="mb-0 fw-bold">Multi Account Checker Dashboard</h3>
          <small class="text-secondary">Pusat Pengecekan Akun CapCut & Outlook Mail Realtime</small>
        </div>
      </div>
      <!-- Tab Navigation -->
      <ul class="nav nav-pills" id="checkerTabs" role="tablist">
        <li class="nav-item" role="presentation">
          <button class="nav-link active" id="capcut-tab" data-bs-toggle="pill" data-bs-target="#capcut-pane" type="button" role="tab">
            <i class="fa-solid fa-film me-2"></i>CapCut Checker
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="outlook-tab" data-bs-toggle="pill" data-bs-target="#outlook-pane" type="button" role="tab">
            <i class="fa-solid fa-envelope me-2"></i>Outlook / Mail Checker
          </button>
        </li>
      </ul>
    </div>

    <!-- Tab Contents -->
    <div class="tab-content" id="checkerTabsContent">
      
      <!-- ================= CAPCUT CHECKER TAB ================= -->
      <div class="tab-pane fade show active" id="capcut-pane" role="tabpanel">
        <div class="row g-4">
          <!-- Input Column -->
          <div class="col-lg-5">
            <div class="card p-3 shadow-sm h-100">
              <h5 class="fw-bold mb-3"><i class="fa-solid fa-list-check me-2 text-primary"></i>Input Akun CapCut</h5>
              
              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold">DAFTAR AKUN (email:pass, email|pass, dll)</label>
                <textarea id="accountsInput" class="form-control" rows="8" placeholder="user1@example.com:password123&#10;user2@example.com|password456"></textarea>
                <div class="d-flex justify-content-between mt-1">
                  <small id="accountCount" class="text-muted">Total: 0 akun</small>
                  <button class="btn btn-sm btn-link text-decoration-none p-0 text-danger" onclick="document.getElementById('accountsInput').value=''; updateCapcutCount();">Clear</button>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold">RESIDENTIAL PROXY URL (Wajib)</label>
                <input type="text" id="proxyInput" class="form-control" placeholder="http://user-session-{sess}:pass@gate.provider.com:7000" value="{{ default_proxy }}">
                <small class="text-muted" style="font-size: 0.75rem;">Gunakan token <code>{sess}</code> untuk rotasi IP otomatis.</small>
              </div>

              <div class="row g-2 mb-3">
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold">THREADS</label>
                  <input type="number" id="workersInput" class="form-control" value="6" min="1" max="25">
                </div>
                <div class="col-6">
                  <label class="form-label text-secondary small fw-semibold">IP RETRIES</label>
                  <input type="number" id="retriesInput" class="form-control" value="6" min="1" max="15">
                </div>
              </div>

              <div class="d-flex gap-2">
                <button id="btnStart" class="btn btn-custom-start flex-grow-1 py-2" onclick="startCapcutChecking()">
                  <i class="fa-solid fa-play me-2"></i>Mulai Check CapCut
                </button>
                <button id="btnStop" class="btn btn-danger py-2" onclick="stopCapcutChecking()" disabled>
                  <i class="fa-solid fa-stop me-2"></i>Stop
                </button>
              </div>

              <!-- Progress bar -->
              <div class="mt-4">
                <div class="d-flex justify-content-between small text-secondary mb-1">
                  <span>Progress</span>
                  <span id="progressText">0 / 0 (0%)</span>
                </div>
                <div class="progress" style="height: 8px; background-color: #0b1329;">
                  <div id="progressBar" class="progress-bar bg-info" style="width: 0%;"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Output Column -->
          <div class="col-lg-7">
            <div class="card p-3 shadow-sm">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold mb-0"><i class="fa-solid fa-square-poll-vertical me-2 text-success"></i>Hasil CapCut</h5>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-outline-light" onclick="downloadCapcutAll('csv')">
                    <i class="fa-solid fa-file-csv me-1"></i>CSV
                  </button>
                  <button class="btn btn-sm btn-outline-light" onclick="downloadCapcutAll('txt')">
                    <i class="fa-solid fa-file-lines me-1"></i>TXT
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
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('proResult', 'capcut_pro_accounts.txt')">
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
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('freeResult', 'capcut_free_accounts.txt')">
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
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('dieResult', 'capcut_die_accounts.txt')">
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

      <!-- ================= OUTLOOK / MAIL CHECKER TAB ================= -->
      <div class="tab-pane fade" id="outlook-pane" role="tabpanel">
        <div class="row g-4">
          <!-- Input Column -->
          <div class="col-lg-5">
            <div class="card p-3 shadow-sm h-100">
              <h5 class="fw-bold mb-3"><i class="fa-solid fa-envelope-open-text me-2 text-info"></i>Input Token Outlook</h5>
              
              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold">DAFTAR TOKEN (email|password|refresh_token|client_id atau token saja)</label>
                <textarea id="outlookInput" class="form-control" rows="8" placeholder="user@hotmail.com|password|M.R3_BAY...|9e5f94bc-e8a4-4e73-b8be-63364c29d753"></textarea>
                <div class="d-flex justify-content-between mt-1">
                  <small id="outlookCount" class="text-muted">Total: 0 token</small>
                  <button class="btn btn-sm btn-link text-decoration-none p-0 text-danger" onclick="document.getElementById('outlookInput').value=''; updateOutlookCount();">Clear</button>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold">PROXY (Opsional: http://user:pass@host:port)</label>
                <input type="text" id="outlookProxyInput" class="form-control" placeholder="http://user:pass@host:port (Kosongkan jika direct)">
              </div>

              <div class="mb-3">
                <label class="form-label text-secondary small fw-semibold">THREADS / CONCURRENCY</label>
                <input type="number" id="outlookWorkersInput" class="form-control" value="8" min="1" max="30">
              </div>

              <div class="d-flex gap-2">
                <button id="btnStartOutlook" class="btn btn-custom-start flex-grow-1 py-2" onclick="startOutlookChecking()">
                  <i class="fa-solid fa-play me-2"></i>Mulai Check Mail
                </button>
                <button id="btnStopOutlook" class="btn btn-danger py-2" onclick="stopOutlookChecking()" disabled>
                  <i class="fa-solid fa-stop me-2"></i>Stop
                </button>
              </div>

              <!-- Progress bar -->
              <div class="mt-4">
                <div class="d-flex justify-content-between small text-secondary mb-1">
                  <span>Progress</span>
                  <span id="outlookProgressText">0 / 0 (0%)</span>
                </div>
                <div class="progress" style="height: 8px; background-color: #0b1329;">
                  <div id="outlookProgressBar" class="progress-bar bg-info" style="width: 0%;"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Output Column -->
          <div class="col-lg-7">
            <div class="card p-3 shadow-sm">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold mb-0"><i class="fa-solid fa-inbox me-2 text-info"></i>Hasil Outlook Mail</h5>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-outline-light" onclick="downloadOutlookAll('csv')">
                    <i class="fa-solid fa-file-csv me-1"></i>CSV
                  </button>
                  <button class="btn btn-sm btn-outline-light" onclick="downloadOutlookAll('txt')">
                    <i class="fa-solid fa-file-lines me-1"></i>TXT
                  </button>
                </div>
              </div>

              <!-- LIVE Result Box -->
              <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-success">
                    <i class="fa-solid fa-circle-check me-1"></i>LIVE / ACTIVE MAIL
                    <span id="outlookLiveCount" class="badge bg-success badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('outlookLiveResult')">
                      <i class="fa-solid fa-copy me-1"></i>Copy
                    </button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('outlookLiveResult', 'outlook_live_accounts.txt')">
                      <i class="fa-solid fa-download me-1"></i>Save
                    </button>
                  </div>
                </div>
                <textarea id="outlookLiveResult" class="form-control result-box border-success" style="min-height: 250px;" readonly placeholder="Akun Outlook LIVE akan muncul di sini beserta ringkasan email..."></textarea>
              </div>

              <!-- DEAD / ERROR Result Box -->
              <div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="fw-bold text-danger">
                    <i class="fa-solid fa-circle-xmark me-1"></i>EXPIRED / DEAD TOKEN
                    <span id="outlookDeadCount" class="badge bg-danger badge-counter ms-1">0</span>
                  </span>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="copyField('outlookDeadResult')">
                      <i class="fa-solid fa-copy me-1"></i>Copy
                    </button>
                    <button class="btn btn-sm btn-outline-secondary text-light" onclick="downloadField('outlookDeadResult', 'outlook_dead_accounts.txt')">
                      <i class="fa-solid fa-download me-1"></i>Save
                    </button>
                  </div>
                </div>
                <textarea id="outlookDeadResult" class="form-control result-box border-danger" style="min-height: 200px;" readonly placeholder="Token mati/expired akan muncul di sini..."></textarea>
              </div>

            </div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    /* =================== UTILITIES =================== */
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

    /* =================== CAPCUT CHECKER =================== */
    let capcutAbortController = null;
    let capcutRecords = [];

    const accountsInput = document.getElementById('accountsInput');
    accountsInput.addEventListener('input', updateCapcutCount);

    function updateCapcutCount() {
      const lines = accountsInput.value.trim().split('\\n').filter(l => l.trim().length > 0);
      document.getElementById('accountCount').textContent = `Total: ${lines.length} akun`;
    }

    function downloadCapcutAll(format) {
      if (capcutRecords.length === 0) return alert('Belum ada hasil untuk didownload.');
      let content = '', filename = '', mimeType = '';

      if (format === 'csv') {
        content = 'email,password,status,plan,expiry,user_id,error\\n';
        for (const r of capcutRecords) {
          content += `"${r.email}","${r.password}","${r.status}","${r.plan || ''}","${r.expiry || ''}","${r.user_id || ''}","${r.error || ''}"\\n`;
        }
        filename = 'capcut_results.csv';
        mimeType = 'text/csv;charset=utf-8;';
      } else {
        for (const r of capcutRecords) {
          const uidStr = r.user_id ? ` | UID: ${r.user_id}` : '';
          const planStr = r.is_pro ? ` | Exp: ${r.expiry}` : ' | Free Plan';
          content += `${r.email}:${r.password}${uidStr}${r.ok ? planStr : ' [' + (r.error||'DEAD') + ']'}\\n`;
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

    async function startCapcutChecking() {
      const text = accountsInput.value.trim();
      const proxy = document.getElementById('proxyInput').value.trim();
      const workers = parseInt(document.getElementById('workersInput').value) || 6;
      const retries = parseInt(document.getElementById('retriesInput').value) || 6;

      if (!text) return alert('Silakan masukkan daftar akun CapCut!');

      document.getElementById('proResult').value = '';
      document.getElementById('freeResult').value = '';
      document.getElementById('dieResult').value = '';
      document.getElementById('proCount').textContent = '0';
      document.getElementById('freeCount').textContent = '0';
      document.getElementById('dieCount').textContent = '0';
      capcutRecords = [];

      let countPro = 0, countFree = 0, countDie = 0, checked = 0;
      document.getElementById('btnStart').disabled = true;
      document.getElementById('btnStop').disabled = false;
      capcutAbortController = new AbortController();

      try {
        const response = await fetch('/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ accounts_text: text, proxy: proxy, workers: workers, retries: retries }),
          signal: capcutAbortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\n');
          buffer = lines.pop();

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

                const total = data.total;
                const percent = Math.round((checked / total) * 100);
                document.getElementById('progressText').textContent = `${checked} / ${total} (${percent}%)`;
                document.getElementById('progressBar').style.width = `${percent}%`;
              }
            } catch (e) {}
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') alert('Error: ' + err.message);
      } finally {
        document.getElementById('btnStart').disabled = false;
        document.getElementById('btnStop').disabled = true;
      }
    }

    function stopCapcutChecking() {
      if (capcutAbortController) capcutAbortController.abort();
      document.getElementById('btnStart').disabled = false;
      document.getElementById('btnStop').disabled = true;
    }

    /* =================== OUTLOOK MAIL CHECKER =================== */
    let outlookAbortController = null;
    let outlookRecords = [];

    const outlookInput = document.getElementById('outlookInput');
    outlookInput.addEventListener('input', updateOutlookCount);

    function updateOutlookCount() {
      const lines = outlookInput.value.trim().split('\\n').filter(l => l.trim().length > 0);
      document.getElementById('outlookCount').textContent = `Total: ${lines.length} token`;
    }

    function downloadOutlookAll(format) {
      if (outlookRecords.length === 0) return alert('Belum ada hasil untuk didownload.');
      let content = '', filename = '', mimeType = '';

      if (format === 'csv') {
        content = 'email,password,status,refresh_token,client_id,latest_subject,latest_from,latest_date,error\\n';
        for (const r of outlookRecords) {
          content += `"${r.email}","${r.password}","${r.status}","${r.refresh_token}","${r.client_id}","${r.latest_subject || ''}","${r.latest_from || ''}","${r.latest_date || ''}","${r.error || ''}"\\n`;
        }
        filename = 'outlook_results.csv';
        mimeType = 'text/csv;charset=utf-8;';
      } else {
        for (const r of outlookRecords) {
          if (r.ok) {
            content += `${r.email}|${r.password}|${r.refresh_token}|${r.client_id} | LIVE | Latest: ${r.latest_subject || '-'}\\n`;
          } else {
            content += `${r.email}|${r.refresh_token} | DEAD [${r.error}]\\n`;
          }
        }
        filename = 'outlook_results.txt';
        mimeType = 'text/plain;charset=utf-8;';
      }

      const blob = new Blob([content], { type: mimeType });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    }

    async function startOutlookChecking() {
      const text = outlookInput.value.trim();
      const proxy = document.getElementById('outlookProxyInput').value.trim();
      const workers = parseInt(document.getElementById('outlookWorkersInput').value) || 8;

      if (!text) return alert('Silakan masukkan token/akun Outlook!');

      document.getElementById('outlookLiveResult').value = '';
      document.getElementById('outlookDeadResult').value = '';
      document.getElementById('outlookLiveCount').textContent = '0';
      document.getElementById('outlookDeadCount').textContent = '0';
      outlookRecords = [];

      let countLive = 0, countDead = 0, checked = 0;
      document.getElementById('btnStartOutlook').disabled = true;
      document.getElementById('btnStopOutlook').disabled = false;
      outlookAbortController = new AbortController();

      try {
        const response = await fetch('/api/check_outlook', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ accounts_text: text, proxy: proxy, workers: workers }),
          signal: outlookAbortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\n');
          buffer = lines.pop();

          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              const data = JSON.parse(line);
              if (data.type === 'init') {
                document.getElementById('outlookProgressText').textContent = `0 / ${data.total} (0%)`;
                document.getElementById('outlookProgressBar').style.width = '0%';
                continue;
              }
              if (data.type === 'result') {
                checked++;
                const r = data.data;
                outlookRecords.push(r);

                if (r.ok) {
                  countLive++;
                  document.getElementById('outlookLiveCount').textContent = countLive;
                  const mailInfo = r.latest_subject ? ` | Mail: "${r.latest_subject}" from ${r.latest_from}` : ' | Inbox: (Kosong)';
                  document.getElementById('outlookLiveResult').value += `${r.email}${r.password ? ':'+r.password : ''}${mailInfo}\\n`;
                } else {
                  countDead++;
                  document.getElementById('outlookDeadCount').textContent = countDead;
                  document.getElementById('outlookDeadResult').value += `${r.email} [${r.error}]\\n`;
                }

                const total = data.total;
                const percent = Math.round((checked / total) * 100);
                document.getElementById('outlookProgressText').textContent = `${checked} / ${total} (${percent}%)`;
                document.getElementById('outlookProgressBar').style.width = `${percent}%`;
              }
            } catch (e) {}
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') alert('Error: ' + err.message);
      } finally {
        document.getElementById('btnStartOutlook').disabled = false;
        document.getElementById('btnStopOutlook').disabled = true;
      }
    }

    function stopOutlookChecking() {
      if (outlookAbortController) outlookAbortController.abort();
      document.getElementById('btnStartOutlook').disabled = false;
      document.getElementById('btnStopOutlook').disabled = true;
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    default_proxy = os.environ.get("CAPCUT_PROXY", "")
    return render_template_string(HTML_TEMPLATE, default_proxy=default_proxy)


# CapCut Check API
@app.route("/api/check", methods=["POST"])
def api_check_capcut():
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


# Outlook / Hotmail Check API
@app.route("/api/check_outlook", methods=["POST"])
def api_check_outlook():
    payload = request.get_json(force=True)
    accounts_text = payload.get("accounts_text", "")
    proxy_url = payload.get("proxy", "").strip() or None
    workers = int(payload.get("workers", 8))

    items = outlook_check.parse_outlook_lines(accounts_text)
    total = len(items)

    def generate():
        yield json.dumps({"type": "init", "total": total}) + "\n"
        if total == 0:
            return

        def _do_check_outlook(item):
            res = outlook_check.check_outlook_account(
                email=item["email"],
                password=item["password"],
                refresh_token=item["refresh_token"],
                client_id=item["client_id"],
                proxy=proxy_url
            )
            res["refresh_token"] = item["refresh_token"]
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Multi-Checker Web on http://0.0.0.0:{port} ...")
    app.run(host="0.0.0.0", port=port, debug=False)
