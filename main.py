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
          body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f7f7f7;
            color: #222;
          }
          .page {
            max-width: 1200px;
            margin: 0 auto;
          }
          h1 {
            margin: 0 0 8px;
            font-size: 28px;
          }
          .sub {
            margin: 0 0 20px;
            color: #666;
          }
          .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
          }
          #status {
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
          }
          #grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
          }
          .card {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 12px;
            padding: 14px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
          }
          .title-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
            margin-bottom: 10px;
          }
          .product-name {
            margin: 0;
            font-size: 18px;
            line-height: 1.35;
          }
          .badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
            border: 1px solid #ccc;
            white-space: nowrap;
          }
          .badge.ready {
            background: #e8f7ec;
            color: #0f7a2d;
            border-color: #b7e0c1;
          }
          .badge.needs_review {
            background: #fff5d6;
            color: #9a6b00;
            border-color: #f1d37a;
          }
          .badge.invalid {
            background: #fdeaea;
            color: #b42318;
            border-color: #f3b3b3;
          }
          .meta {
            font-size: 14px;
            color: #444;
            margin-bottom: 6px;
          }
          .meta strong {
            color: #222;
          }
          .preview {
            width: 100%;
            aspect-ratio: 1 / 1;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid #ddd;
            background: #eee;
            margin: 12px 0;
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
            margin: 12px 0;
            font-size: 14px;
          }
          .section-label {
            font-size: 13px;
            font-weight: bold;
            color: #333;
            margin-top: 10px;
            margin-bottom: 6px;
          }
          .missing-list {
            margin: 0;
            padding-left: 18px;
            color: #555;
            font-size: 14px;
          }
          .muted {
            color: #666;
            font-size: 14px;
          }
          .error-message {
            margin-top: 6px;
            padding: 8px 10px;
            border-radius: 8px;
            background: #fff4f4;
            border: 1px solid #f1c0c0;
            color: #9f1d1d;
            font-size: 13px;
            word-break: break-word;
          }
          .links {
            margin-top: 10px;
            display: grid;
            gap: 6px;
          }
          .small-link {
            font-size: 13px;
            color: #0b57d0;
            text-decoration: none;
            word-break: break-all;
          }
          .small-link:hover {
            text-decoration: underline;
          }
          .actions {
            display: flex;
            gap: 8px;
            margin-top: 14px;
          }
          button {
            border: 1px solid #ccc;
            background: #fafafa;
            color: #222;
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
          }
          button:hover {
            background: #f0f0f0;
          }
          button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }
          .empty {
            padding: 30px 0;
            color: #666;
          }
        </style>
      </head>
      <body>
        <div class="page">
          <h1>Trend Yemen Admin UI</h1>
          <p class="sub">Simple admin view powered by <code>/admin/overview</code></p>

          <div class="topbar">
            <div id="status">Loading products...</div>
            <button id="refreshBtn" type="button">Refresh</button>
          </div>

          <div id="error"></div>
          <div id="grid"></div>
        </div>

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

          function setError(message = "") {
            const errorEl = document.getElementById("error");
            if (!message) {
              errorEl.style.display = "none";
              errorEl.textContent = "";
              return;
            }
            errorEl.style.display = "block";
            errorEl.textContent = message;
          }

          function badgeClass(status) {
            if (status === "ready") return "badge ready";
            if (status === "needs_review") return "badge needs_review";
            return "badge invalid";
          }

          async function fetchOverview() {
            const response = await fetch("/admin/overview");
            if (!response.ok) {
              const text = await response.text();
              throw new Error(text || ("Request failed: " + response.status));
            }
            return response.json();
          }

          async function postAction(url) {
            const response = await fetch(url, { method: "POST" });
            if (!response.ok) {
              const text = await response.text();
              throw new Error(text || ("Request failed: " + response.status));
            }
            return response.json();
          }

          async function retryRow(rowId) {
            if (!rowId) return;
            try {
              setError("");
              await postAction("/retry_row?id=" + encodeURIComponent(rowId));
              await loadProducts();
            } catch (error) {
              setError(error.message || "Failed to retry row");
            }
          }

          async function deleteRow(rowId) {
            if (!rowId) return;
            const confirmed = confirm("Delete row " + rowId + "?");
            if (!confirmed) return;

            try {
              setError("");
              await postAction("/delete_row?id=" + encodeURIComponent(rowId));
              await loadProducts();
            } catch (error) {
              setError(error.message || "Failed to delete row");
            }
          }

          function renderProducts(records) {
            const gridEl = document.getElementById("grid");
            const statusEl = document.getElementById("status");

            statusEl.textContent = records.length + " products loaded";

            if (!records.length) {
              gridEl.innerHTML = '<div class="empty">No products found</div>';
              return;
            }

            gridEl.innerHTML = records.map((product) => {
              const productName = product.product_name || "Untitled Product";
              const rowId = product.row_id || "";
              const categoryId = product.category_id || "—";
              const processingStatus = product.processing_status || "—";
              const readinessStatus = (product.readiness && product.readiness.status) ? product.readiness.status : "invalid";
              const finalImageUrl = product.final_image_url || "";
              const sourceImageUrl = product.source_image_url || "";
              const previewRaw = finalImageUrl || sourceImageUrl || "";
              const previewUrl = normalizeImageUrl(previewRaw);
              const detailUrl = "/admin/product?row_id=" + encodeURIComponent(rowId);
              const missingFields = (product.smart_encoding_inputs && Array.isArray(product.smart_encoding_inputs.missing_fields))
                ? product.smart_encoding_inputs.missing_fields
                : [];
              const errorMessage = product.error_message || "";

              const imageHtml = previewUrl
                ? `<img class="preview" src="${escapeHtml(previewUrl)}" alt="${escapeHtml(productName)}" onerror="this.outerHTML='<div class=&quot;placeholder&quot;>No image</div>'" />`
                : `<div class="placeholder">No image</div>`;

              const missingHtml = missingFields.length
                ? `<ul class="missing-list">${missingFields.map((field) => `<li>${escapeHtml(field)}</li>`).join("")}</ul>`
                : `<div class="muted">No missing fields</div>`;

              const errorHtml = errorMessage
                ? `<div class="section-label">Error message</div><div class="error-message">${escapeHtml(errorMessage)}</div>`
                : "";

              const finalLinkHtml = finalImageUrl
                ? `<a class="small-link" href="${escapeHtml(finalImageUrl)}" target="_blank" rel="noreferrer">Final image link</a>`
                : `<span class="muted">Final image link: —</span>`;

              const sourceLinkHtml = sourceImageUrl
                ? `<a class="small-link" href="${escapeHtml(sourceImageUrl)}" target="_blank" rel="noreferrer">Source image link</a>`
                : `<span class="muted">Source image link: —</span>`;

              return `
                <div class="card">
                  <div class="title-row">
                    <h3 class="product-name">${escapeHtml(productName)}</h3>
                    <span class="${badgeClass(readinessStatus)}">${escapeHtml(readinessStatus)}</span>
                  </div>

                  <div class="meta"><strong>Row ID:</strong> ${escapeHtml(rowId || "—")}</div>
                  <div class="meta"><strong>Category:</strong> ${escapeHtml(categoryId)}</div>
                  <div class="meta"><strong>Processing:</strong> ${escapeHtml(processingStatus)}</div>

                  ${imageHtml}

                  <div class="section-label">Missing fields</div>
                  ${missingHtml}

                  ${errorHtml}

                  <div class="links">
                    ${finalLinkHtml}
                    ${sourceLinkHtml}
                    <a class="small-link" href="${escapeHtml(detailUrl)}" target="_blank">View product JSON</a>
                  </div>

                  <div class="actions">
                    <button type="button" onclick="retryRow('${escapeHtml(rowId)}')">Retry</button>
                    <button type="button" onclick="deleteRow('${escapeHtml(rowId)}')">Delete</button>
                  </div>
                </div>
              `;
            }).join("");
          }

          async function loadProducts() {
            const gridEl = document.getElementById("grid");
            const statusEl = document.getElementById("status");

            setError("");
            gridEl.innerHTML = "";
            statusEl.textContent = "Loading products...";

            try {
              const records = await fetchOverview();
              renderProducts(Array.isArray(records) ? records : []);
            } catch (error) {
              statusEl.textContent = "Failed to load products";
              setError(error.message || "Unknown error");
            }
          }

          document.getElementById("refreshBtn").addEventListener("click", loadProducts);
          window.retryRow = retryRow;
          window.deleteRow = deleteRow;

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
