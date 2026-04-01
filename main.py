import os
import threading
from flask import Flask, jsonify, request

from core.orchestrator import MasterOrchestrator
from storage.sheets_store import SheetsStore
from services.admin_read_service import AdminReadService

app = Flask(__name__)

orchestrator = MasterOrchestrator()
sheets = SheetsStore()
admin_read_service = AdminReadService()

_orchestrator_thread = None
_orchestrator_lock = threading.Lock()
_orchestrator_started = threading.Event()


@app.route("/")
@app.route("/health")
def health():
    is_running = (
        _orchestrator_thread is not None
        and _orchestrator_thread.is_alive()
        and _orchestrator_started.is_set()
    )

    return jsonify({
        "status": "ok",
        "service": "trend-yemen-backend",
        "orchestrator_running": is_running
    })


@app.route("/stats")
def stats():
    rows = sheets.sheet.get_all_records()

    counts = {
        "Pending": 0,
        "Processing": 0,
        "Completed": 0,
        "Failed": 0
    }

    for row in rows:
        status = str(row.get("ProcessingStatus", "")).strip()
        if status in counts:
            counts[status] += 1

    return jsonify(counts)


@app.route("/retry_failed", methods=["POST"])
def retry_failed():
    rows = sheets.sheet.get_all_records()
    status_col = sheets.col_map.get("ProcessingStatus")

    if not status_col:
        return jsonify({
            "status": "error",
            "message": "ProcessingStatus column not found"
        }), 400

    updated = 0

    for idx, row in enumerate(rows, start=2):
        status = str(row.get("ProcessingStatus", "")).strip()
        if status == "Failed":
            sheets.sheet.update_cell(idx, status_col, "Pending")
            updated += 1

    return jsonify({
        "status": "ok",
        "message": "retry completed",
        "updated": updated
    })


@app.route("/retry_row", methods=["POST"])
def retry_row():
    row_id = request.args.get("id", "").strip()

    if not row_id:
        return jsonify({"status": "error", "message": "Missing id"}), 400

    row_index = sheets._get_row_index_by_id(row_id)
    if not row_index:
        return jsonify({"status": "error", "message": "Row not found"}), 404

    status_col = sheets.col_map.get("ProcessingStatus")
    sheets.sheet.update_cell(row_index, status_col, "Pending")

    return jsonify({
        "status": "ok",
        "row_id": row_id
    })


@app.route("/delete_row", methods=["POST"])
def delete_row():
    row_id = request.args.get("id", "").strip()

    if not row_id:
        return jsonify({"status": "error", "message": "Missing id"}), 400

    row_index = sheets._get_row_index_by_id(row_id)
    if not row_index:
        return jsonify({"status": "error", "message": "Row not found"}), 404

    sheets.sheet.delete_rows(row_index)

    return jsonify({
        "status": "ok",
        "row_id": row_id
    })


@app.route("/list_products")
def list_products():
    rows = sheets.sheet.get_all_records()
    last_20 = rows[-20:] if len(rows) >= 20 else rows

    return jsonify({
        "status": "ok",
        "count": len(last_20),
        "products": last_20
    })


@app.route("/admin/overview", methods=["GET"])
def admin_overview():
    try:
        records = admin_read_service.get_all_admin_records()
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/product")
def admin_product():
    row_id = request.args.get("row_id", "").strip()

    if not row_id:
        return jsonify({
            "status": "error",
            "message": "Missing row_id"
        }), 400

    records = admin_read_service.get_all_admin_records()
    record = next((item for item in records if item.get("row_id") == row_id), None)

    if not record:
        return jsonify({
            "status": "error",
            "message": "Admin product not found"
        }), 404

    return jsonify(record)


@app.route("/admin/ui")
def admin_ui():
    return """
    <!doctype html>
    <html lang="en" dir="ltr">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <title>Trend Yemen Admin UI</title>
        <style>
          * { box-sizing: border-box; }

          body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f7f7f7;
            color: #222;
          }

          h1 {
            margin: 0 0 8px;
          }

          p {
            margin: 0 0 20px;
            color: #666;
          }

          #topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 14px;
          }

          #status {
            margin-bottom: 16px;
            color: #555;
          }

          #error {
            display: none;
            margin-bottom: 16px;
            padding: 10px 12px;
            background: #ffe5e5;
            border: 1px solid #ffb3b3;
            color: #a40000;
            border-radius: 8px;
            white-space: pre-wrap;
            word-break: break-word;
          }

          #grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
          }

          .card {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 8px;
          }

          .card-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 10px;
          }

          .card h3 {
            margin: 0;
            font-size: 18px;
            line-height: 1.25;
          }

          .meta {
            font-size: 14px;
            color: #444;
          }

          .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
            border: 1px solid transparent;
            white-space: nowrap;
          }

          .badge-ready {
            background: #e6f6ea;
            color: #18794e;
            border-color: #b7e3c4;
          }

          .badge-needs-review {
            background: #fff4d6;
            color: #9a6700;
            border-color: #f1d38a;
          }

          .badge-invalid {
            background: #fde8e8;
            color: #b42318;
            border-color: #f5b7b1;
          }

          .badge-unknown {
            background: #ececec;
            color: #555;
            border-color: #ddd;
          }

          .preview {
            width: 100%;
            aspect-ratio: 1 / 1;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid #ddd;
            background: #eee;
            margin: 4px 0;
          }

          .placeholder {
            width: 100%;
            aspect-ratio: 1 / 1;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            border: 1px solid #ddd;
            background: #eee;
            color: #777;
            margin: 4px 0;
            font-size: 14px;
          }

          .section-title {
            font-size: 14px;
            font-weight: bold;
            margin-top: 4px;
          }

          .muted {
            color: #666;
            font-size: 14px;
          }

          .error-box {
            background: #fff1f0;
            border: 1px solid #f3c2be;
            color: #a94442;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            word-break: break-word;
          }

          .links {
            display: flex;
            flex-direction: column;
            gap: 6px;
          }

          .actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 6px;
          }

          button {
            border: 1px solid #ccc;
            background: #fff;
            color: #222;
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
          }

          button:hover {
            background: #f2f2f2;
          }

          button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }

          a {
            color: #0b57d0;
            text-decoration: none;
            word-break: break-all;
            font-size: 14px;
          }

          a:hover {
            text-decoration: underline;
          }

          ul {
            margin: 6px 0 0 18px;
            padding: 0;
          }

          li {
            margin: 2px 0;
          }
        </style>
      </head>
      <body>
        <div id="topbar">
          <div>
            <h1>Trend Yemen Admin UI</h1>
            <p>Simple admin view powered by <code>/admin/overview</code></p>
          </div>
          <button onclick="loadProducts()">Refresh</button>
        </div>

        <div id="status">Loading products...</div>
        <div id="error"></div>
        <div id="grid"></div>

        <script>
          function normalizeImageUrl(url) {
            if (!url) return "";

            const value = String(url).trim();

            const filePathMatch = value.match(/drive\\.google\\.com\\/file\\/d\\/([a-zA-Z0-9_-]+)/);
            if (filePathMatch) {
              const fileId = filePathMatch[1];
              return `https://drive.google.com/uc?export=view&id=${fileId}`;
            }

            const queryIdMatch = value.match(/[?&]id=([a-zA-Z0-9_-]+)/);
            if (queryIdMatch) {
              const fileId = queryIdMatch[1];
              return `https://drive.google.com/uc?export=view&id=${fileId}`;
            }

            return value;
          }

          function escapeHtml(value) {
            return String(value ?? "")
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#39;");
          }

          function badgeClass(status) {
            const value = String(status || "").trim().toLowerCase();
            if (value === "ready") return "badge badge-ready";
            if (value === "needs_review") return "badge badge-needs-review";
            if (value === "invalid") return "badge badge-invalid";
            return "badge badge-unknown";
          }

          async function apiPost(path) {
            const response = await fetch(path, { method: "POST" });
            if (!response.ok) {
              const text = await response.text();
              throw new Error(text || ("Request failed: " + response.status));
            }
            return response.json();
          }

          async function retryRow(rowId) {
            if (!rowId) return;
            try {
              await apiPost("/retry_row?id=" + encodeURIComponent(rowId));
              await loadProducts();
            } catch (error) {
              showError(error.message || "Retry failed");
            }
          }

          async function deleteRow(rowId) {
            if (!rowId) return;
            const confirmed = confirm("Delete row " + rowId + "?");
            if (!confirmed) return;

            try {
              await apiPost("/delete_row?id=" + encodeURIComponent(rowId));
              await loadProducts();
            } catch (error) {
              showError(error.message || "Delete failed");
            }
          }

          function showError(message) {
            const errorEl = document.getElementById("error");
            if (!message) {
              errorEl.style.display = "none";
              errorEl.textContent = "";
              return;
            }
            errorEl.style.display = "block";
            errorEl.textContent = message;
          }

          async function loadProducts() {
            const statusEl = document.getElementById("status");
            const gridEl = document.getElementById("grid");

            showError("");
            gridEl.innerHTML = "";
            statusEl.textContent = "Loading products...";

            try {
              const response = await fetch("/admin/overview");
              if (!response.ok) {
                const text = await response.text();
                throw new Error(text || ("Request failed: " + response.status));
              }

              const products = await response.json();
              const records = Array.isArray(products) ? products : [];

              statusEl.textContent = records.length + " products loaded";

              if (!records.length) {
                gridEl.innerHTML = "<div>No products found</div>";
                return;
              }

              gridEl.innerHTML = records.map((product) => {
                const productName = product.product_name || "Untitled Product";
                const rowId = product.row_id || "";
                const categoryId = product.category_id || "—";
                const processingStatus = product.processing_status || "—";
                const readinessStatus = (product.readiness && product.readiness.status)
                  ? product.readiness.status
                  : "invalid";

                const smart = product.smart_encoding_inputs || {};
                const missingFields = Array.isArray(smart.missing_fields) ? smart.missing_fields : [];

                const rawFinalUrl = product.final_image_url || "";
                const rawSourceUrl = product.source_image_url || "";

                const imageUrl = normalizeImageUrl(rawFinalUrl || rawSourceUrl);
                const detailUrl = "/admin/product?row_id=" + encodeURIComponent(rowId);

                const errorMessage = product.error_message || "";

                const imageHtml = imageUrl
                  ? `<img class="preview" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(productName)}"
                        onerror="this.outerHTML='<div class=&quot;placeholder&quot;>No image</div>'" />`
                  : `<div class="placeholder">No image</div>`;

                const missingHtml = missingFields.length
                  ? `<ul>${missingFields.map(field => `<li>${escapeHtml(field)}</li>`).join("")}</ul>`
                  : `<div class="muted">No missing fields</div>`;

                const errorHtml = errorMessage
                  ? `<div class="error-box">${escapeHtml(errorMessage)}</div>`
                  : `<div class="muted">No error</div>`;

                return `
                  <div class="card">
                    <div class="card-head">
                      <h3>${escapeHtml(productName)}</h3>
                      <span class="${badgeClass(readinessStatus)}">${escapeHtml(readinessStatus)}</span>
                    </div>

                    <div class="meta"><strong>Row ID:</strong> ${escapeHtml(rowId || "—")}</div>
                    <div class="meta"><strong>Category:</strong> ${escapeHtml(categoryId)}</div>
                    <div class="meta"><strong>Processing:</strong> ${escapeHtml(processingStatus)}</div>

                    ${imageHtml}

                    <div class="section-title">Missing fields</div>
                    ${missingHtml}

                    <div class="section-title">Error message</div>
                    ${errorHtml}

                    <div class="links">
                      <a href="${escapeHtml(rawFinalUrl)}" target="_blank">Final image link</a>
                      <a href="${escapeHtml(rawSourceUrl)}" target="_blank">Source image link</a>
                      <a href="${escapeHtml(detailUrl)}" target="_blank">View product JSON</a>
                    </div>

                    <div class="actions">
                      <button onclick="retryRow('${escapeHtml(rowId)}')">Retry</button>
                      <button onclick="deleteRow('${escapeHtml(rowId)}')">Delete</button>
                    </div>
                  </div>
                `;
              }).join("");

            } catch (error) {
              statusEl.textContent = "Failed to load products";
              showError(error.message || "Unknown error");
            }
          }

          loadProducts();
        </script>
      </body>
    </html>
    """


def start_orchestrator():
    print("🚀 Starting Master Orchestrator...")
    _orchestrator_started.set()

    try:
        orchestrator.run()
    except Exception as e:
        print(f"❌ Orchestrator crashed: {e}")
    finally:
        _orchestrator_started.clear()


def start_background_services():
    global _orchestrator_thread

    with _orchestrator_lock:
        if _orchestrator_thread is not None and _orchestrator_thread.is_alive():
            print("⚠️ Orchestrator already running, skipping duplicate start")
            return _orchestrator_thread

        _orchestrator_thread = threading.Thread(
            target=start_orchestrator,
            name="master-orchestrator",
            daemon=True
        )
        _orchestrator_thread.start()
        print("✅ Background services started")
        return _orchestrator_thread


if __name__ == "__main__":
    print("🟢 Starting Trend Yemen Backend...")

    start_background_services()

    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
