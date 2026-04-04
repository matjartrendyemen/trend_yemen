import os
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

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

SEED_IMAGE_DIR = Path(tempfile.gettempdir()) / "trend_yemen_seed_images"
SEED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


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


@app.route("/admin/seed_image/<path:filename>")
def admin_seed_image(filename):
    return send_from_directory(SEED_IMAGE_DIR, filename)


@app.route("/admin/create_product", methods=["POST"])
def admin_create_product():
    image = request.files.get("image")
    price_raw = request.form.get("price", "").strip()

    if image is None or not image.filename:
        return jsonify({
            "status": "error",
            "message": "Missing image file"
        }), 400

    if not str(image.mimetype or "").startswith("image/"):
        return jsonify({
            "status": "error",
            "message": "Uploaded file must be an image"
        }), 400

    if not price_raw:
        return jsonify({
            "status": "error",
            "message": "Missing price"
        }), 400

    try:
        normalized_price = price_raw.replace(",", "").strip()
        price_number = float(normalized_price)

        if price_number <= 0:
            raise ValueError()

        price_value = (
            str(int(price_number))
            if price_number.is_integer()
            else str(price_number)
        )
    except Exception:
        return jsonify({
            "status": "error",
            "message": "Invalid price"
        }), 400

    try:
        image_bytes = image.read()
        if not image_bytes:
            return jsonify({
                "status": "error",
                "message": "Empty image file"
            }), 400

        extension = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4().hex}{extension}"
        file_path = SEED_IMAGE_DIR / filename

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        image_url = request.host_url.rstrip("/") + f"/admin/seed_image/{filename}"

        created = sheets.append_pending_product(
            image_url=image_url,
            price=price_value,
        )

        return jsonify({
            "row_id": created["row_id"],
            "image_url": created["image_url"],
            "status": created["status"],
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


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

          .page {
            max-width: 1360px;
            margin: 0 auto;
          }

          h1 {
            margin: 0 0 8px;
          }

          p {
            margin: 0;
            color: #666;
          }

          .topbar {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 18px;
          }

          .toolbar-actions {
            display: flex;
            gap: 8px;
            align-items: center;
          }

          #status {
            margin-bottom: 14px;
            color: #555;
            font-size: 14px;
          }

          #error {
            display: none;
            margin-bottom: 14px;
            padding: 10px 12px;
            background: #ffe5e5;
            border: 1px solid #ffb3b3;
            color: #a40000;
            border-radius: 8px;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .registry-shell {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 12px;
            overflow: hidden;
          }

          .table-wrap {
            overflow-x: auto;
          }

          table {
            width: 100%;
            border-collapse: collapse;
            min-width: 980px;
          }

          thead {
            background: #f3f4f6;
          }

          th, td {
            padding: 12px 10px;
            border-bottom: 1px solid #ececec;
            text-align: left;
            vertical-align: middle;
            font-size: 14px;
          }

          th {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #555;
            white-space: nowrap;
          }

          tbody tr:hover {
            background: #fafafa;
          }

          .cell-preview {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 220px;
          }

          .thumb,
          .thumb-placeholder {
            width: 46px;
            height: 46px;
            border-radius: 8px;
            border: 1px solid #ddd;
            background: #f0f0f0;
            flex: 0 0 auto;
          }

          .thumb {
            object-fit: cover;
          }

          .thumb-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #777;
            font-size: 11px;
          }

          .preview-text {
            display: flex;
            flex-direction: column;
            gap: 4px;
            min-width: 0;
          }

          .preview-title {
            font-weight: bold;
            color: #222;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 240px;
          }

          .preview-sub {
            color: #666;
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 240px;
          }

          .badge {
            display: inline-flex;
            align-items: center;
            border: 1px solid #d7d7d7;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 12px;
            white-space: nowrap;
            background: #f5f5f5;
            color: #444;
          }

          .badge-pending {
            background: #fff7db;
            border-color: #f0ddb0;
            color: #8a6300;
          }

          .badge-processing {
            background: #e8f1ff;
            border-color: #c8dafc;
            color: #175cd3;
          }

          .badge-completed {
            background: #e8f7ec;
            border-color: #c4e7ce;
            color: #18794e;
          }

          .badge-failed {
            background: #ffeaea;
            border-color: #f5c2c2;
            color: #b42318;
          }

          .badge-unknown {
            background: #f3f3f3;
            border-color: #ddd;
            color: #555;
          }

          .muted {
            color: #777;
          }

          .num {
            white-space: nowrap;
          }

          .actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            white-space: nowrap;
          }

          button,
          .link-button {
            border: 1px solid #ccc;
            background: #fff;
            color: #222;
            border-radius: 8px;
            padding: 7px 10px;
            cursor: pointer;
            font-size: 13px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
          }

          button:hover,
          .link-button:hover {
            background: #f3f3f3;
          }

          button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }

          .empty-state {
            padding: 28px 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
          }
        </style>
      </head>
      <body>
        <div class="page">
          <div class="topbar">
            <div>
              <h1>Trend Yemen Admin UI</h1>
              <p>Compact registry view powered by <code>/admin/overview</code></p>
            </div>

            <div class="toolbar-actions">
              <button id="refreshBtn" type="button">Refresh</button>
            </div>
          </div>

          <div id="status">Loading registry...</div>
          <div id="error"></div>

          <div class="registry-shell">
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Row ID</th>
                    <th>Preview</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Price</th>
                    <th>Last Updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody id="registryBody">
                  <tr>
                    <td colspan="7" class="empty-state">Loading registry...</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <script>
          function escapeHtml(value) {
            return String(value ?? "")
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#39;");
          }

          function normalizeImageUrl(url) {
            if (!url) return "";

            const value = String(url).trim();

            const filePathMatch = value.match(/drive\\.google\\.com\\/file\\/d\\/([a-zA-Z0-9_-]+)/);
            if (filePathMatch) {
              const fileId = filePathMatch[1];
              return "https://drive.google.com/uc?export=view&id=" + fileId;
            }

            const queryIdMatch = value.match(/[?&]id=([a-zA-Z0-9_-]+)/);
            if (queryIdMatch) {
              const fileId = queryIdMatch[1];
              return "https://drive.google.com/uc?export=view&id=" + fileId;
            }

            return value;
          }

          function getPreviewUrl(record) {
            return normalizeImageUrl(
              record.final_image_url ||
              record.source_image_url ||
              record.image_url ||
              ""
            );
          }

          function getPreviewLabel(record) {
            return (
              record.product_name ||
              record.title ||
              record.name ||
              record.row_id ||
              "Untitled"
            );
          }

          function getPreviewSub(record) {
            const source = record.final_image_url
              ? "Final image"
              : record.source_image_url
              ? "Source image"
              : record.image_url
              ? "Image"
              : "No image";

            return source;
          }

          function getCategoryValue(record) {
            return (
              record.category_id ||
              record.category ||
              "—"
            );
          }

          function getStatusValue(record) {
            return (
              record.processing_status ||
              record.status ||
              "—"
            );
          }

          function getPriceValue(record) {
            const value = (
              record.price ??
              record.price_yer ??
              record.price_value ??
              ""
            );

            if (value === null || value === undefined || String(value).trim() === "") {
              return "—";
            }

            return String(value);
          }

          function getLastUpdatedValue(record) {
            return (
              record.last_updated ||
              record.updated_at ||
              record.modified_at ||
              record.created_at ||
              "—"
            );
          }

          function getStatusClass(status) {
            const normalized = String(status || "").trim().toLowerCase();

            if (normalized === "pending") return "badge badge-pending";
            if (normalized === "processing") return "badge badge-processing";
            if (normalized === "completed") return "badge badge-completed";
            if (normalized === "failed") return "badge badge-failed";

            return "badge badge-unknown";
          }

          function setStatus(text) {
            document.getElementById("status").textContent = text;
          }

          function clearError() {
            const errorEl = document.getElementById("error");
            errorEl.style.display = "none";
            errorEl.textContent = "";
          }

          function showError(text) {
            const errorEl = document.getElementById("error");
            errorEl.style.display = "block";
            errorEl.textContent = text || "Unknown error";
          }

          function renderEmpty(message) {
            const body = document.getElementById("registryBody");
            body.innerHTML = `
              <tr>
                <td colspan="7" class="empty-state">${escapeHtml(message)}</td>
              </tr>
            `;
          }

          function renderRows(records) {
            const body = document.getElementById("registryBody");

            if (!Array.isArray(records) || !records.length) {
              renderEmpty("No records found");
              return;
            }

            body.innerHTML = records.map((record) => {
              const rowId = record.row_id || "—";
              const previewUrl = getPreviewUrl(record);
              const previewLabel = getPreviewLabel(record);
              const previewSub = getPreviewSub(record);
              const category = getCategoryValue(record);
              const status = getStatusValue(record);
              const price = getPriceValue(record);
              const lastUpdated = getLastUpdatedValue(record);
              const jsonUrl = "/admin/product?row_id=" + encodeURIComponent(record.row_id || "");

              const previewHtml = previewUrl
                ? `<img class="thumb" src="${escapeHtml(previewUrl)}" alt="${escapeHtml(previewLabel)}" onerror="this.outerHTML='&lt;div class=&quot;thumb-placeholder&quot;&gt;No image&lt;/div&gt;'" />`
                : `<div class="thumb-placeholder">No image</div>`;

              const retryDisabled = record.row_id ? "" : "disabled";
              const deleteDisabled = record.row_id ? "" : "disabled";
              const jsonDisabled = record.row_id ? "" : "aria-disabled=\\"true\\"";

              return `
                <tr>
                  <td class="num">${escapeHtml(rowId)}</td>
                  <td>
                    <div class="cell-preview">
                      ${previewHtml}
                      <div class="preview-text">
                        <div class="preview-title">${escapeHtml(previewLabel)}</div>
                        <div class="preview-sub">${escapeHtml(previewSub)}</div>
                      </div>
                    </div>
                  </td>
                  <td>${escapeHtml(category)}</td>
                  <td><span class="${getStatusClass(status)}">${escapeHtml(status)}</span></td>
                  <td>${escapeHtml(price)}</td>
                  <td>${escapeHtml(lastUpdated)}</td>
                  <td>
                    <div class="actions">
                      <button type="button" onclick="retryRow('${escapeHtml(String(record.row_id || ""))}')" ${retryDisabled}>Retry</button>
                      <button type="button" onclick="deleteRow('${escapeHtml(String(record.row_id || ""))}')" ${deleteDisabled}>Delete</button>
                      <a class="link-button" href="${escapeHtml(jsonUrl)}" target="_blank" ${jsonDisabled}>View JSON</a>
                    </div>
                  </td>
                </tr>
              `;
            }).join("");
          }

          async function fetchJson(url, options) {
            const response = await fetch(url, options);

            if (!response.ok) {
              const text = await response.text();
              throw new Error(text || ("Request failed: " + response.status));
            }

            return response.json();
          }

          async function loadRegistry() {
            clearError();
            setStatus("Loading registry...");
            renderEmpty("Loading registry...");

            try {
              const data = await fetchJson("/admin/overview");
              const records = Array.isArray(data) ? data : [];

              renderRows(records);
              setStatus(records.length + " records loaded");
            } catch (error) {
              renderEmpty("Unable to load registry");
              setStatus("Failed to load registry");
              showError(error.message || "Unknown error");
            }
          }

          async function retryRow(rowId) {
            if (!rowId) return;

            clearError();
            setStatus("Retrying row " + rowId + "...");

            try {
              await fetchJson("/retry_row?id=" + encodeURIComponent(rowId), {
                method: "POST"
              });
              await loadRegistry();
            } catch (error) {
              setStatus("Failed to retry row");
              showError(error.message || "Unknown error");
            }
          }

          async function deleteRow(rowId) {
            if (!rowId) return;

            const confirmed = confirm("Delete row " + rowId + "?");
            if (!confirmed) return;

            clearError();
            setStatus("Deleting row " + rowId + "...");

            try {
              await fetchJson("/delete_row?id=" + encodeURIComponent(rowId), {
                method: "POST"
              });
              await loadRegistry();
            } catch (error) {
              setStatus("Failed to delete row");
              showError(error.message || "Unknown error");
            }
          }

          document.getElementById("refreshBtn").addEventListener("click", loadRegistry);

          window.retryRow = retryRow;
          window.deleteRow = deleteRow;

          loadRegistry();
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
