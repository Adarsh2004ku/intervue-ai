import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from flask import Flask, jsonify, render_template_string, request


DEFAULT_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_TOKEN = os.getenv("TEST_AUTH_TOKEN", "token_adarsh")

app = Flask(__name__)


@dataclass
class RouteTest:
    name: str
    method: str
    path: str
    expected_status: tuple[int, ...] = (200,)
    json_body: dict[str, Any] | None = None
    auth: bool = False


ROUTE_TESTS = [
    RouteTest("Root", "GET", "/", expected_status=(200, 404)),
    RouteTest("OpenAPI schema", "GET", "/openapi.json"),
    RouteTest("Swagger docs", "GET", "/docs"),
    RouteTest("Health", "GET", "/health"),
    RouteTest("Health live", "GET", "/health/live"),
    RouteTest("Health ready", "GET", "/health/ready"),
    RouteTest("Auth users", "GET", "/auth/users"),
    RouteTest("Auth login adarsh", "POST", "/auth/login/adarsh"),
    RouteTest("Testing home", "GET", "/testing"),
    RouteTest("Testing ping", "GET", "/testing/ping"),
    RouteTest("Testing LLM", "GET", "/testing/llm"),
    RouteTest("Testing Redis", "GET", "/testing/redis"),
    RouteTest("Testing Supabase", "GET", "/testing/supabase"),
    RouteTest(
        "Interview start smoke",
        "POST",
        "/interview/start",
        json_body={"mode": "test"},
        auth=True,
    ),
    RouteTest("Interview get smoke", "GET", "/interview/test_interview_123"),
    RouteTest(
        "Interview answer smoke",
        "POST",
        "/interview/test_interview_123/answer",
        json_body={"answer": "This is a test answer."},
        auth=True,
    ),
    RouteTest("Report smoke", "GET", "/reports/test_interview_123"),
    RouteTest("Admin health", "GET", "/admin/health"),
    RouteTest("Admin stats", "GET", "/admin/stats", auth=True),
    RouteTest("Prometheus metrics", "GET", "/metrics", expected_status=(200, 404)),
]


def normalize_base_url(base_url: str) -> str:
    return base_url.strip().rstrip("/")


def make_request(base_url: str, test: RouteTest, token: str, timeout: float) -> dict[str, Any]:
    url = f"{normalize_base_url(base_url)}{test.path}"
    headers = {"Accept": "application/json"}
    body = None

    if test.auth:
        headers["Authorization"] = f"Bearer {token}"

    if test.json_body is not None:
        body = json.dumps(test.json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=test.method,
    )

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            status = response.status
            content_type = response.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
        content_type = exc.headers.get("content-type", "")
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "name": test.name,
            "method": test.method,
            "path": test.path,
            "url": url,
            "ok": False,
            "status": None,
            "expected": list(test.expected_status),
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
            "body": None,
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    text = raw.decode("utf-8", errors="replace")
    parsed_body: Any = text

    if "application/json" in content_type:
        try:
            parsed_body = json.loads(text)
        except json.JSONDecodeError:
            parsed_body = text

    return {
        "name": test.name,
        "method": test.method,
        "path": test.path,
        "url": url,
        "ok": status in test.expected_status,
        "status": status,
        "expected": list(test.expected_status),
        "elapsed_ms": elapsed_ms,
        "error": None,
        "body": parsed_body,
    }


def run_route_tests(base_url: str, token: str, timeout: float) -> dict[str, Any]:
    results = [
        make_request(base_url, test, token, timeout)
        for test in ROUTE_TESTS
    ]
    passed = sum(1 for result in results if result["ok"])

    return {
        "base_url": normalize_base_url(base_url),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
        "notes": [
            "Start FastAPI separately, for example: uvicorn backend.main:app --reload --port 8000",
            "WebSocket /ws/test is not exercised by this Flask app because it only uses standard HTTP checks.",
            "Resume upload is best tested manually from Swagger because it needs a real file upload.",
        ],
    }


@app.get("/")
def home():
    return render_template_string(
        PAGE_TEMPLATE,
        default_base_url=DEFAULT_BASE_URL,
        default_token=DEFAULT_TOKEN,
    )


@app.get("/api/routes")
def list_routes():
    return jsonify([
        {
            "name": test.name,
            "method": test.method,
            "path": test.path,
            "expected_status": test.expected_status,
            "auth": test.auth,
        }
        for test in ROUTE_TESTS
    ])


@app.post("/api/run-tests")
def run_tests():
    payload = request.get_json(silent=True) or {}
    base_url = payload.get("base_url") or DEFAULT_BASE_URL
    token = payload.get("token") or DEFAULT_TOKEN
    timeout = float(payload.get("timeout") or 8)
    return jsonify(run_route_tests(base_url, token, timeout))


PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Intervue.AI Route Tester</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #16202a;
      --muted: #65717f;
      --line: #dfe4ea;
      --good: #087f5b;
      --bad: #c92a2a;
      --warn: #9a6700;
      --accent: #145c9e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 18px 24px;
    }
    main {
      width: min(1180px, calc(100vw - 32px));
      margin: 24px auto 48px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }
    .subtle {
      color: var(--muted);
      margin-top: 6px;
      font-size: 14px;
    }
    .controls {
      display: grid;
      grid-template-columns: minmax(260px, 1fr) minmax(180px, 260px) auto;
      gap: 12px;
      align-items: end;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 18px;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
    }
    input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      color: var(--text);
      font: inherit;
      background: #fff;
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 11px 16px;
      font: inherit;
      font-weight: 700;
      color: #fff;
      background: var(--accent);
      cursor: pointer;
      min-height: 42px;
    }
    button:disabled {
      cursor: wait;
      opacity: .7;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .metric strong {
      display: block;
      font-size: 26px;
      margin-top: 4px;
    }
    .table-wrap {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    th, td {
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
      overflow-wrap: anywhere;
    }
    th {
      background: #fbfcfd;
      color: var(--muted);
      font-weight: 700;
      font-size: 12px;
      text-transform: uppercase;
    }
    tr:last-child td { border-bottom: 0; }
    .status {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 68px;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 800;
    }
    .pass { color: var(--good); background: #e6fcf5; }
    .fail { color: var(--bad); background: #fff5f5; }
    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 13px;
    }
    pre {
      margin: 8px 0 0;
      max-height: 140px;
      overflow: auto;
      white-space: pre-wrap;
      color: var(--muted);
      font-size: 12px;
    }
    .notes {
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    @media (max-width: 760px) {
      .controls, .summary { grid-template-columns: 1fr; }
      th:nth-child(5), td:nth-child(5) { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Intervue.AI Route Tester</h1>
    <div class="subtle">Run smoke checks against the FastAPI backend.</div>
  </header>
  <main>
    <section class="controls">
      <label>
        FastAPI base URL
        <input id="baseUrl" value="{{ default_base_url }}">
      </label>
      <label>
        Bearer token
        <input id="token" value="{{ default_token }}">
      </label>
      <button id="runBtn" type="button">Run Tests</button>
    </section>

    <section class="summary">
      <div class="metric">Total<strong id="total">0</strong></div>
      <div class="metric">Passed<strong id="passed">0</strong></div>
      <div class="metric">Failed<strong id="failed">0</strong></div>
      <div class="metric">Base<strong id="base">-</strong></div>
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width: 19%">Check</th>
            <th style="width: 9%">Method</th>
            <th style="width: 22%">Path</th>
            <th style="width: 9%">Status</th>
            <th style="width: 9%">Time</th>
            <th>Response</th>
          </tr>
        </thead>
        <tbody id="results">
          <tr><td colspan="6">Click Run Tests to begin.</td></tr>
        </tbody>
      </table>
    </section>
    <div id="notes" class="notes"></div>
  </main>

  <script>
    const runBtn = document.getElementById('runBtn');
    const results = document.getElementById('results');

    function setText(id, value) {
      document.getElementById(id).textContent = value;
    }

    function responseText(result) {
      if (result.error) return result.error;
      if (typeof result.body === 'string') return result.body.slice(0, 600);
      return JSON.stringify(result.body, null, 2).slice(0, 600);
    }

    function render(data) {
      setText('total', data.total);
      setText('passed', data.passed);
      setText('failed', data.failed);
      setText('base', data.base_url.replace(/^https?:\\/\\//, ''));
      results.innerHTML = '';
      for (const row of data.results) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${row.name}</td>
          <td><code>${row.method}</code></td>
          <td><code>${row.path}</code></td>
          <td><span class="status ${row.ok ? 'pass' : 'fail'}">${row.status || 'ERR'}</span></td>
          <td>${row.elapsed_ms} ms</td>
          <td><div>Expected: ${row.expected.join(', ')}</div><pre></pre></td>
        `;
        tr.querySelector('pre').textContent = responseText(row);
        results.appendChild(tr);
      }
      document.getElementById('notes').innerHTML = data.notes.map(note => `<div>${note}</div>`).join('');
    }

    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      runBtn.textContent = 'Running...';
      results.innerHTML = '<tr><td colspan="6">Running checks...</td></tr>';
      try {
        const response = await fetch('/api/run-tests', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            base_url: document.getElementById('baseUrl').value,
            token: document.getElementById('token').value
          })
        });
        render(await response.json());
      } catch (error) {
        results.innerHTML = `<tr><td colspan="6">${error.message}</td></tr>`;
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = 'Run Tests';
      }
    });
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)
