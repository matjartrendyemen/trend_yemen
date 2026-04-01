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
          h1 {
            margin: 0 0 8px;
          }
          p {
            margin: 0 0 20px;
            color: #666;
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
          }
          .card h3 {
            margin: 0 0 10px;
            font-size: 18px;
          }
          .meta {
            font-size: 14px;
            color: #555;
            margin-bottom: 6px;
          }
          .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
            margin: 6px 0 10px;
            border: 1px solid #ccc;
            background: #f2f2f2;
          }
          .preview {
            width: 100%;
            aspect-ratio: 1 / 1;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid #ddd;
            background: #eee;
            margin: 10px 0;
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
            margin: 10px 0;
            font-size: 14px;
          }
          a {
            color: #0b57d0;
            text-decoration: none;
          }
          a:hover {
            text-decoration: underline;
          }
        </style>
      </head>
      <body>
        <h1>Trend Yemen Admin UI</h1>
        <p>Simple admin view powered by <code>/admin/overview</code></p>

        <div id="status">Loading products...</div>
        <div id="error"></div>
        <div id="grid"></div>

        <script>
          async function loadProducts() {
            const statusEl = document.getElementById("status");
            const errorEl = document.getElementById("error");
            const gridEl = document.getElementById("grid");

            errorEl.style.display = "none";
            errorEl.textContent = "";
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
                const readinessStatus = (product.readiness && product.readiness.status) ? product.readiness.status : "invalid";
                const imageUrl = product.final_image_url || product.source_image_url || "";
                const detailUrl = "/admin/product?row_id=" + encodeURIComponent(rowId);

                const imageHtml = imageUrl
                  ? `<img class="preview" src="${imageUrl}" alt="${productName.replace(/"/g, '&quot;')}" onerror="this.outerHTML='<div class=&quot;placeholder&quot;>No image</div>'" />`
                  : `<div class="placeholder">No image</div>`;

                return `
                  <div class="card">
                    <h3>${productName}</h3>
                    <div class="meta"><strong>Row ID:</strong> ${rowId || "—"}</div>
                    <div class="meta"><strong>Category:</strong> ${categoryId}</div>
                    <div class="meta"><strong>Processing:</strong> ${processingStatus}</div>
                    <div class="badge">${readinessStatus}</div>
                    ${imageHtml}
                    <div><a href="${detailUrl}" target="_blank">View product JSON</a></div>
                  </div>
                `;
              }).join("");

            } catch (error) {
              statusEl.textContent = "Failed to load products";
              errorEl.style.display = "block";
              errorEl.textContent = error.message || "Unknown error";
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
