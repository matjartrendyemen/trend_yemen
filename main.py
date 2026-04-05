import os
import tempfile
import threading
import uuid
import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from core.orchestrator import MasterOrchestrator
from storage.sheets_store import SheetsStore
from services.admin_read_service import AdminReadService
from services.media_matching_service import MediaMatchingService

app = Flask(__name__)

orchestrator = MasterOrchestrator()
sheets = SheetsStore()
admin_read_service = AdminReadService()
media_matching_service = MediaMatchingService(sheets)

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


@app.route("/admin/match_media", methods=["POST"])
def admin_match_media():
    row_id = request.args.get("id", "").strip()

    if not row_id:
        return jsonify({
            "status": "error",
            "message": "Missing id"
        }), 400

    records = admin_read_service.get_all_admin_records()
    record = next((item for item in records if item.get("row_id") == row_id), None)

    if not record:
        return jsonify({
            "status": "error",
            "message": "Row not found"
        }), 404

    try:
        result = media_matching_service.generate_candidates_for_row(
            row_id=row_id,
            product_name=record.get("product_name", "") or record.get("title", "") or record.get("name", ""),
            category_id=record.get("category_id", "") or record.get("category", ""),
        )
        return jsonify({
            "status": "ok",
            "row_id": row_id,
            "matched_count": result.get("matched_count", 0),
            "matched_status": result.get("matched_status", "ready")
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/admin/select_final_media", methods=["POST"])
def admin_select_final_media():
    row_id = request.args.get("id", "").strip()
    media_url = request.args.get("media_url", "").strip()
    media_type = request.args.get("media_type", "image").strip() or "image"

    if not row_id:
        return jsonify({
            "status": "error",
            "message": "Missing id"
        }), 400

    if not media_url:
        return jsonify({
            "status": "error",
            "message": "Missing media_url"
        }), 400

    records = admin_read_service.get_all_admin_records()
    record = next((item for item in records if item.get("row_id") == row_id), None)

    if not record:
        return jsonify({
            "status": "error",
            "message": "Row not found"
        }), 404

    try:
        sheets.update_media_fields(
            row_id,
            {
                "FinalPrimaryMediaType": media_type,
                "FinalPrimaryMediaURL": media_url,
                "FinalMediaStatus": "selected",
            },
        )

        return jsonify({
            "status": "ok",
            "row_id": row_id,
            "final_media_url": media_url,
            "final_media_status": "selected",
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


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
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f6f7f9;
            color: #1f2937;
          }

          .page {
            max-width: 1480px;
            margin: 0 auto;
            padding: 20px;
          }

          .topbar {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 16px;
          }

          .topbar h1 {
            margin: 0 0 6px;
            font-size: 28px;
          }

          .topbar p {
            margin: 0;
            color: #6b7280;
            font-size: 14px;
          }

          .toolbar-actions {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
          }

          .toolbar {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 12px;
          }

          .toolbar input,
          .toolbar select,
          .create-form input[type="file"],
          .create-form input[type="text"] {
            height: 38px;
            padding: 0 12px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            background: #ffffff;
            color: #111827;
            font-size: 14px;
          }

          .toolbar input {
            min-width: 260px;
            flex: 1 1 260px;
          }

          .toolbar select {
            min-width: 170px;
          }

          button,
          .json-link,
          .action-link {
            border: 1px solid #d1d5db;
            background: #ffffff;
            color: #111827;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
          }

          button:hover,
          .json-link:hover,
          .action-link:hover {
            background: #f3f4f6;
          }

          button:disabled,
          .is-busy {
            opacity: 0.7;
            cursor: wait;
          }

          .action-danger {
            color: #b91c1c;
            border-color: #fecaca;
            background: #fffafa;
          }

          .action-danger:hover {
            background: #fef2f2;
          }

          .action-primary {
            border-color: #bfdbfe;
            background: #eff6ff;
            color: #1d4ed8;
          }

          .action-primary:hover {
            background: #dbeafe;
          }

          .action-secondary {
            border-color: #d1fae5;
            background: #ecfdf5;
            color: #065f46;
          }

          .action-secondary:hover {
            background: #d1fae5;
          }

          .action-selected {
            border-color: #bfdbfe;
            background: #dbeafe;
            color: #1d4ed8;
            font-weight: bold;
          }

          #status {
            margin-bottom: 12px;
            color: #4b5563;
            font-size: 14px;
          }

          #error {
            display: none;
            margin-bottom: 12px;
            padding: 12px;
            border-radius: 10px;
            border: 1px solid #fecaca;
            background: #fef2f2;
            color: #b91c1c;
            white-space: pre-wrap;
            word-break: break-word;
            font-size: 14px;
          }

          #flash {
            display: none;
            margin-bottom: 12px;
            padding: 12px;
            border-radius: 10px;
            border: 1px solid #d1fae5;
            background: #ecfdf5;
            color: #065f46;
            white-space: pre-wrap;
            word-break: break-word;
            font-size: 14px;
          }

          .layout {
            display: grid;
            grid-template-columns: minmax(0, 1.8fr) minmax(320px, 0.9fr);
            gap: 16px;
            align-items: start;
          }

          .card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            overflow: hidden;
          }

          .card-head {
            padding: 14px 16px;
            border-bottom: 1px solid #eef0f2;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            flex-wrap: wrap;
          }

          .card-head h2 {
            margin: 0;
            font-size: 16px;
          }

          .card-head p {
            margin: 4px 0 0;
            color: #6b7280;
            font-size: 13px;
          }

          .create-form {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            padding: 16px;
          }

          .create-form input[type="file"] {
            padding: 8px 10px;
            height: auto;
            min-height: 38px;
            width: 100%;
            max-width: 320px;
          }

          .create-form input[type="text"] {
            min-width: 180px;
            flex: 0 1 200px;
          }

          .create-hint {
            padding: 0 16px 16px;
            color: #6b7280;
            font-size: 12px;
          }

          .table-wrap {
            overflow-x: auto;
          }

          table {
            width: 100%;
            border-collapse: collapse;
            min-width: 1140px;
          }

          thead {
            background: #f9fafb;
          }

          th,
          td {
            padding: 12px 10px;
            border-bottom: 1px solid #eef0f2;
            text-align: left;
            vertical-align: middle;
          }

          th {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #6b7280;
            white-space: nowrap;
          }

          td {
            font-size: 14px;
            color: #111827;
          }

          tbody tr {
            cursor: pointer;
            transition: background 0.15s ease, box-shadow 0.15s ease;
          }

          tbody tr:hover {
            background: #f9fafb;
          }

          tbody tr.is-selected {
            background: #eaf2ff;
            box-shadow: inset 3px 0 0 #2563eb;
          }

          .image-cell {
            width: 72px;
          }

          .thumb,
          .thumb-placeholder {
            width: 48px;
            height: 48px;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
            background: #f3f4f6;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            color: #6b7280;
            font-size: 11px;
          }

          .thumb {
            object-fit: cover;
          }

          .name-cell {
            min-width: 220px;
          }

          .truncate {
            max-width: 220px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 4px 10px;
            border-radius: 999px;
            border: 1px solid #d1d5db;
            font-size: 12px;
            white-space: nowrap;
            background: #f9fafb;
            color: #374151;
          }

          .badge-pending {
            background: #fff7db;
            border-color: #f3dfab;
            color: #8a6300;
          }

          .badge-processing {
            background: #e8f0ff;
            border-color: #cbdcff;
            color: #1d4ed8;
          }

          .badge-completed {
            background: #e9f8ee;
            border-color: #cdebd7;
            color: #15803d;
          }

          .badge-failed {
            background: #fef0f0;
            border-color: #fecaca;
            color: #b91c1c;
          }

          .row-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
          }

          .row-actions button,
          .row-actions a {
            padding: 6px 10px;
            font-size: 12px;
          }

          .empty-state {
            padding: 28px 20px;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
          }

          .details-panel {
            min-height: 180px;
          }

          .details-header {
            padding: 16px 16px 12px;
            border-bottom: 1px solid #eef0f2;
          }

          .details-header h2 {
            margin: 0 0 6px;
            font-size: 18px;
          }

          .details-header p {
            margin: 0;
            color: #6b7280;
            font-size: 13px;
          }

          .details-body {
            padding: 16px;
          }

          .details-empty {
            color: #6b7280;
            font-size: 14px;
          }

          .detail-image {
            width: 100%;
            max-height: 260px;
            object-fit: cover;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            background: #f3f4f6;
            margin-bottom: 14px;
          }

          .detail-grid {
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 10px 12px;
            align-items: start;
          }

          .detail-label {
            color: #6b7280;
            font-size: 13px;
          }

          .detail-value {
            color: #111827;
            font-size: 14px;
            word-break: break-word;
          }

          .detail-actions {
            display: flex;
            gap: 8px;
            margin-top: 16px;
            flex-wrap: wrap;
          }

          .matched-media-block {
            margin-top: 18px;
            padding-top: 16px;
            border-top: 1px solid #eef0f2;
          }

          .matched-media-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 12px;
          }

          .matched-media-head h3 {
            margin: 0;
            font-size: 15px;
          }

          .matched-media-head p {
            margin: 0;
            color: #6b7280;
            font-size: 13px;
          }

          .matched-media-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 12px;
          }

          .candidate-card {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            background: #fff;
            overflow: hidden;
          }

          .candidate-card.is-final {
            border-color: #60a5fa;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
          }

          .candidate-preview {
            width: 100%;
            height: 120px;
            object-fit: cover;
            display: block;
            background: #f3f4f6;
            border-bottom: 1px solid #eef0f2;
          }

          .candidate-preview-placeholder {
            width: 100%;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f3f4f6;
            color: #6b7280;
            font-size: 12px;
            border-bottom: 1px solid #eef0f2;
          }

          .candidate-body {
            padding: 10px;
          }

          .candidate-rank {
            font-size: 12px;
            font-weight: bold;
            color: #1d4ed8;
            margin-bottom: 6px;
          }

          .candidate-label {
            font-size: 13px;
            color: #111827;
            margin-bottom: 6px;
            word-break: break-word;
          }

          .candidate-meta {
            font-size: 12px;
            color: #6b7280;
            display: grid;
            gap: 4px;
          }

          .candidate-link {
            margin-top: 8px;
            display: inline-flex;
            font-size: 12px;
            text-decoration: none;
            color: #065f46;
          }

          .candidate-link:hover {
            text-decoration: underline;
          }

          .candidate-actions {
            margin-top: 10px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
          }

          .candidate-actions button {
            padding: 6px 10px;
            font-size: 12px;
          }

          .matched-empty {
            color: #6b7280;
            font-size: 13px;
            padding: 6px 0 2px;
          }

          @media (max-width: 1100px) {
            .layout {
              grid-template-columns: 1fr;
            }
          }
        </style>
      </head>
      <body>
        <div class="page">
          <div class="topbar">
            <div>
              <h1>Trend Yemen Admin UI</h1>
              <p>Registry table with search, filters, details panel, row actions, and light admin improvements</p>
            </div>
            <div class="toolbar-actions">
              <button id="refreshBtn" type="button">Refresh</button>
            </div>
          </div>

          <div class="card" style="margin-bottom: 16px;">
            <div class="card-head">
              <div>
                <h2>Create Product</h2>
                <p>Seed image stays temporary. Existing flow remains unchanged.</p>
              </div>
            </div>
            <form id="createProductForm" class="create-form">
              <input id="createImageInput" name="image" type="file" accept="image/*" required />
              <input id="createPriceInput" name="price" type="text" placeholder="Price (YER)" required />
              <button id="createBtn" type="submit" class="action-primary">Create Product</button>
            </form>
            <div class="create-hint">Uses the existing <code>/admin/create_product</code> endpoint.</div>
          </div>

          <div class="toolbar">
            <input id="searchInput" type="text" placeholder="Search by name, row ID, category, status, or price" />
            <select id="categoryFilter">
              <option value="__all__">All Categories</option>
            </select>
            <select id="statusFilter">
              <option value="__all__">All Statuses</option>
            </select>
            <button id="resetFiltersBtn" type="button">Reset</button>
          </div>

          <div id="flash"></div>
          <div id="status">Loading registry...</div>
          <div id="error"></div>

          <div class="layout">
            <div class="card">
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Image</th>
                      <th>Name</th>
                      <th>Category</th>
                      <th>Status</th>
                      <th>Price</th>
                      <th>Row ID</th>
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

            <div class="card details-panel">
              <div class="details-header">
                <h2>Details</h2>
                <p>Click a row to view product details.</p>
              </div>
              <div class="details-body" id="detailsPanel">
                <div class="details-empty">No row selected.</div>
              </div>
            </div>
          </div>
        </div>

        <script>
          let registryRecords = [];
          let filteredRecords = [];
          let selectedRowId = "";
          let flashTimer = null;

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

          function getFinalPrimaryMediaUrl(record) {
            return normalizeImageUrl(
              record.final_primary_media_url ||
              record.FinalPrimaryMediaURL ||
              ""
            );
          }

          function getImageUrl(record) {
            return getFinalPrimaryMediaUrl(record) || normalizeImageUrl(
              record.final_image_url ||
              record.source_image_url ||
              record.image_url ||
              ""
            );
          }

          function getName(record) {
            return (
              record.product_name ||
              record.title ||
              record.name ||
              "Untitled"
            );
          }

          function getCategory(record) {
            return (
              record.category_id ||
              record.category ||
              "—"
            );
          }

          function getStatus(record) {
            return (
              record.processing_status ||
              record.status ||
              "—"
            );
          }

          function getPrice(record) {
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

          function getRowId(record) {
            return record.row_id || "—";
          }

          function getLastUpdated(record) {
            return (
              record.last_updated ||
              record.updated_at ||
              record.modified_at ||
              record.created_at ||
              "—"
            );
          }

          function getMatchedMediaStatus(record) {
            return (
              record.matched_media_status ||
              record.MatchedMediaStatus ||
              "not_started"
            );
          }

          function getMatchedMediaCount(record) {
            const value = record.matched_media_count ?? record.MatchedMediaCount ?? "";
            if (value === null || value === undefined || String(value).trim() === "") {
              return "0";
            }
            return String(value);
          }

          function getMatchedAt(record) {
            return (
              record.matched_at ||
              record.MatchedAt ||
              "—"
            );
          }

          function getFinalMediaStatus(record) {
            return (
              record.final_media_status ||
              record.FinalMediaStatus ||
              "not_set"
            );
          }

          function parseMatchedMedia(record) {
            const raw = (
              record.matched_media_json ||
              record.MatchedMediaJSON ||
              ""
            );

            if (!raw) return [];

            try {
              const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
              return Array.isArray(parsed) ? parsed : [];
            } catch (error) {
              return [];
            }
          }

          function getCandidateUrl(candidate) {
            return normalizeImageUrl(candidate.url || "");
          }

          function isFinalCandidate(record, candidate) {
            const finalUrl = getFinalPrimaryMediaUrl(record);
            const candidateUrl = getCandidateUrl(candidate);
            return !!finalUrl && !!candidateUrl && finalUrl === candidateUrl;
          }

          function getStatusClass(status) {
            const normalized = String(status || "").trim().toLowerCase();

            if (normalized === "pending") return "badge badge-pending";
            if (normalized === "processing") return "badge badge-processing";
            if (normalized === "completed") return "badge badge-completed";
            if (normalized === "failed") return "badge badge-failed";

            return "badge";
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

          function showFlash(text) {
            const flashEl = document.getElementById("flash");
            flashEl.style.display = "block";
            flashEl.textContent = text || "";
            if (flashTimer) {
              clearTimeout(flashTimer);
            }
            flashTimer = window.setTimeout(() => {
              flashEl.style.display = "none";
              flashEl.textContent = "";
            }, 2600);
          }

          function renderEmpty(message) {
            const body = document.getElementById("registryBody");
            body.innerHTML = `
              <tr>
                <td colspan="7" class="empty-state">${escapeHtml(message)}</td>
              </tr>
            `;
          }

          function renderMatchedMedia(record) {
            const matchedCandidates = parseMatchedMedia(record);
            const matchedCount = getMatchedMediaCount(record);
            const matchedStatus = getMatchedMediaStatus(record);

            if (!matchedCandidates.length) {
              return `
                <div class="matched-media-block">
                  <div class="matched-media-head">
                    <div>
                      <h3>Matched Media</h3>
                      <p>Status: ${escapeHtml(matchedStatus)} · Count: ${escapeHtml(matchedCount)}</p>
                    </div>
                  </div>
                  <div class="matched-empty">No matched media candidates yet.</div>
                </div>
              `;
            }

            const itemsHtml = matchedCandidates.map((candidate, index) => {
              const rank = candidate.rank || (index + 1);
              const label = candidate.label || "Candidate";
              const score = candidate.score !== undefined && candidate.score !== null ? String(candidate.score) : "—";
              const type = candidate.type || "image";
              const sourceTag = candidate.source_tag || "unknown";
              const url = getCandidateUrl(candidate);
              const selected = isFinalCandidate(record, candidate);

              const previewHtml = url
                ? `<img class="candidate-preview" src="${escapeHtml(url)}" alt="${escapeHtml(label)}" onerror="this.outerHTML='&lt;div class=&quot;candidate-preview-placeholder&quot;&gt;Preview unavailable&lt;/div&gt;'" />`
                : `<div class="candidate-preview-placeholder">No preview</div>`;

              const previewLink = url
                ? `<a class="candidate-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open preview</a>`
                : ``;

              const selectBtnClass = selected ? "action-selected" : "action-secondary";
              const selectBtnLabel = selected ? "Selected" : "Select";
              const selectBtnDisabled = selected ? "disabled" : "";

              return `
                <div class="candidate-card ${selected ? "is-final" : ""}">
                  ${previewHtml}
                  <div class="candidate-body">
                    <div class="candidate-rank">Rank #${escapeHtml(rank)}</div>
                    <div class="candidate-label">${escapeHtml(label)}</div>
                    <div class="candidate-meta">
                      <div>Score: ${escapeHtml(score)}</div>
                      <div>Type: ${escapeHtml(type)}</div>
                      <div>Source: ${escapeHtml(sourceTag)}</div>
                    </div>
                    ${previewLink}
                    <div class="candidate-actions">
                      <button type="button" class="${selectBtnClass}" ${selectBtnDisabled} onclick="selectFinalMediaAction('${escapeHtml(getRowId(record))}', '${escapeHtml(url)}', '${escapeHtml(type)}', this)">
                        ${selectBtnLabel}
                      </button>
                    </div>
                  </div>
                </div>
              `;
            }).join("");

            return `
              <div class="matched-media-block">
                <div class="matched-media-head">
                  <div>
                    <h3>Matched Media</h3>
                    <p>Status: ${escapeHtml(matchedStatus)} · Count: ${escapeHtml(matchedCount)}</p>
                  </div>
                </div>
                <div class="matched-media-grid">
                  ${itemsHtml}
                </div>
              </div>
            `;
          }

          function renderDetails(record) {
            const panel = document.getElementById("detailsPanel");

            if (!record) {
              panel.innerHTML = '<div class="details-empty">No row selected.</div>';
              return;
            }

            const imageUrl = getImageUrl(record);
            const name = getName(record);
            const category = getCategory(record);
            const status = getStatus(record);
            const price = getPrice(record);
            const rowId = getRowId(record);
            const lastUpdated = getLastUpdated(record);
            const jsonUrl = "/admin/product?row_id=" + encodeURIComponent(rowId);
            const matchedStatus = getMatchedMediaStatus(record);
            const matchedCount = getMatchedMediaCount(record);
            const matchedAt = getMatchedAt(record);
            const finalMediaStatus = getFinalMediaStatus(record);

            const imageHtml = imageUrl
              ? `<img class="detail-image" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(name)}" onerror="this.style.display='none'" />`
              : "";

            panel.innerHTML = `
              ${imageHtml}
              <div class="detail-grid">
                <div class="detail-label">Name</div>
                <div class="detail-value">${escapeHtml(name)}</div>

                <div class="detail-label">Category</div>
                <div class="detail-value">${escapeHtml(category)}</div>

                <div class="detail-label">Status</div>
                <div class="detail-value"><span class="${getStatusClass(status)}">${escapeHtml(status)}</span></div>

                <div class="detail-label">Price</div>
                <div class="detail-value">${escapeHtml(price)}</div>

                <div class="detail-label">Row ID</div>
                <div class="detail-value">${escapeHtml(rowId)}</div>

                <div class="detail-label">Last Updated</div>
                <div class="detail-value">${escapeHtml(lastUpdated)}</div>

                <div class="detail-label">Matched Media</div>
                <div class="detail-value">${escapeHtml(matchedStatus)} (${escapeHtml(matchedCount)})</div>

                <div class="detail-label">Matched At</div>
                <div class="detail-value">${escapeHtml(matchedAt)}</div>

                <div class="detail-label">Final Media</div>
                <div class="detail-value">${escapeHtml(finalMediaStatus)}</div>
              </div>

              <div class="detail-actions">
                <button type="button" class="action-secondary" onclick="matchMediaAction('${escapeHtml(String(rowId))}', this)">Match Media</button>
                <button type="button" onclick="retryRowAction('${escapeHtml(String(rowId))}', this)">Retry</button>
                <button type="button" class="action-danger" onclick="deleteRowAction('${escapeHtml(String(rowId))}', this)">Delete</button>
                <a class="json-link" href="${escapeHtml(jsonUrl)}" target="_blank">View JSON</a>
              </div>

              ${renderMatchedMedia(record)}
            `;
          }

          function populateFilters(records) {
            const categoryFilter = document.getElementById("categoryFilter");
            const statusFilter = document.getElementById("statusFilter");

            const currentCategory = categoryFilter.value || "__all__";
            const currentStatus = statusFilter.value || "__all__";

            const categories = Array.from(new Set(
              (records || [])
                .map((record) => String(getCategory(record)).trim())
                .filter((value) => value && value !== "—")
            )).sort((a, b) => a.localeCompare(b));

            const statuses = Array.from(new Set(
              (records || [])
                .map((record) => String(getStatus(record)).trim())
                .filter((value) => value && value !== "—")
            )).sort((a, b) => a.localeCompare(b));

            categoryFilter.innerHTML = '<option value="__all__">All Categories</option>' +
              categories.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");

            statusFilter.innerHTML = '<option value="__all__">All Statuses</option>' +
              statuses.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");

            categoryFilter.value = categories.includes(currentCategory) ? currentCategory : "__all__";
            statusFilter.value = statuses.includes(currentStatus) ? currentStatus : "__all__";
          }

          function applyFilters() {
            const searchValue = document.getElementById("searchInput").value.trim().toLowerCase();
            const categoryValue = document.getElementById("categoryFilter").value;
            const statusValue = document.getElementById("statusFilter").value;

            filteredRecords = registryRecords.filter((record) => {
              const name = String(getName(record)).toLowerCase();
              const category = String(getCategory(record));
              const status = String(getStatus(record));
              const price = String(getPrice(record)).toLowerCase();
              const rowId = String(getRowId(record)).toLowerCase();

              const matchesSearch = !searchValue || [
                name,
                category.toLowerCase(),
                status.toLowerCase(),
                price,
                rowId
              ].some((value) => value.includes(searchValue));

              const matchesCategory = categoryValue === "__all__" || category === categoryValue;
              const matchesStatus = statusValue === "__all__" || status === statusValue;

              return matchesSearch && matchesCategory && matchesStatus;
            });

            renderRows(filteredRecords);

            if (!registryRecords.length) {
              setStatus("0 records loaded");
              return;
            }

            if (!filteredRecords.length) {
              setStatus("No matching results");
              return;
            }

            setStatus(filteredRecords.length + " of " + registryRecords.length + " records shown");
          }

          function selectRow(rowId) {
            selectedRowId = rowId || "";

            const selectedRecord = filteredRecords.find((item) => (item.row_id || "") === selectedRowId) || null;
            renderDetails(selectedRecord);

            document.querySelectorAll("#registryBody tr[data-row-id]").forEach((row) => {
              if (row.getAttribute("data-row-id") === selectedRowId) {
                row.classList.add("is-selected");
              } else {
                row.classList.remove("is-selected");
              }
            });
          }

          function renderRows(records) {
            filteredRecords = Array.isArray(records) ? records : [];
            const body = document.getElementById("registryBody");

            if (!filteredRecords.length) {
              const hasFilters = (
                document.getElementById("searchInput").value.trim() ||
                document.getElementById("categoryFilter").value !== "__all__" ||
                document.getElementById("statusFilter").value !== "__all__"
              );

              renderEmpty(hasFilters ? "No matching results" : "No records found");
              renderDetails(null);
              selectedRowId = "";
              return;
            }

            body.innerHTML = filteredRecords.map((record) => {
              const imageUrl = getImageUrl(record);
              const name = getName(record);
              const category = getCategory(record);
              const status = getStatus(record);
              const price = getPrice(record);
              const rowId = getRowId(record);
              const jsonUrl = "/admin/product?row_id=" + encodeURIComponent(rowId);

              const imageHtml = imageUrl
                ? `<img class="thumb" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(name)}" onerror="this.outerHTML='&lt;div class=&quot;thumb-placeholder&quot;&gt;No image&lt;/div&gt;'" />`
                : `<div class="thumb-placeholder">No image</div>`;

              return `
                <tr data-row-id="${escapeHtml(String(record.row_id || ""))}" onclick="selectRow('${escapeHtml(String(record.row_id || ""))}')">
                  <td class="image-cell">${imageHtml}</td>
                  <td class="name-cell"><div class="truncate">${escapeHtml(name)}</div></td>
                  <td><div class="truncate">${escapeHtml(category)}</div></td>
                  <td><span class="${getStatusClass(status)}">${escapeHtml(status)}</span></td>
                  <td>${escapeHtml(price)}</td>
                  <td><div class="truncate">${escapeHtml(rowId)}</div></td>
                  <td>
                    <div class="row-actions">
                      <button type="button" class="action-secondary" onclick="event.stopPropagation(); matchMediaAction('${escapeHtml(String(rowId))}', this)">Match Media</button>
                      <button type="button" onclick="event.stopPropagation(); retryRowAction('${escapeHtml(String(rowId))}', this)">Retry</button>
                      <button type="button" class="action-danger" onclick="event.stopPropagation(); deleteRowAction('${escapeHtml(String(rowId))}', this)">Delete</button>
                      <a class="action-link" href="${escapeHtml(jsonUrl)}" target="_blank" onclick="event.stopPropagation()">View JSON</a>
                    </div>
                  </td>
                </tr>
              `;
            }).join("");

            const existing = filteredRecords.find((item) => (item.row_id || "") === selectedRowId);
            if (existing) {
              selectRow(selectedRowId);
            } else {
              selectRow(filteredRecords[0].row_id || "");
            }
          }

          async function fetchJson(url, options) {
            const response = await fetch(url, options);

            if (!response.ok) {
              const text = await response.text();
              throw new Error(text || ("Request failed: " + response.status));
            }

            return response.json();
          }

          function setButtonBusy(button, busyText) {
            if (!button) return null;
            const snapshot = {
              text: button.textContent,
              disabled: button.disabled
            };
            button.disabled = true;
            button.classList.add("is-busy");
            if (busyText) {
              button.textContent = busyText;
            }
            return snapshot;
          }

          function restoreButton(button, snapshot) {
            if (!button || !snapshot) return;
            button.disabled = snapshot.disabled;
            button.classList.remove("is-busy");
            button.textContent = snapshot.text;
          }

          async function loadRegistry(options) {
            const keepSelection = options && options.keepSelection;
            const preferredRowId = options && options.preferredRowId;

            clearError();
            setStatus("Loading registry...");
            renderEmpty("Loading registry...");
            renderDetails(null);

            try {
              const data = await fetchJson("/admin/overview");
              registryRecords = Array.isArray(data) ? data : [];

              populateFilters(registryRecords);
              applyFilters();

              if (keepSelection && preferredRowId) {
                const target = filteredRecords.find((item) => (item.row_id || "") === preferredRowId);
                if (target) {
                  selectRow(preferredRowId);
                }
              }
            } catch (error) {
              registryRecords = [];
              filteredRecords = [];
              selectedRowId = "";
              renderEmpty("Unable to load registry");
              renderDetails(null);
              setStatus("Failed to load registry");
              showError(error.message || "Unknown error");
            }
          }

          function resetFilters() {
            document.getElementById("searchInput").value = "";
            document.getElementById("categoryFilter").value = "__all__";
            document.getElementById("statusFilter").value = "__all__";
            applyFilters();
          }

          async function retryRowAction(rowId, buttonEl) {
            if (!rowId || rowId === "—") return;

            clearError();
            const buttonState = setButtonBusy(buttonEl, "Retrying...");
            setStatus("Retrying row " + rowId + "...");

            try {
              await fetchJson("/retry_row?id=" + encodeURIComponent(rowId), {
                method: "POST"
              });

              selectedRowId = rowId;
              await loadRegistry({
                keepSelection: true,
                preferredRowId: rowId
              });

              showFlash("Row " + rowId + " moved to Pending");
              setStatus("Row " + rowId + " retried");
            } catch (error) {
              showError(error.message || "Unknown error");
              setStatus("Retry failed");
            } finally {
              restoreButton(buttonEl, buttonState);
            }
          }

          async function deleteRowAction(rowId, buttonEl) {
            if (!rowId || rowId === "—") return;

            if (!window.confirm("Delete row " + rowId + "?")) {
              return;
            }

            clearError();
            const buttonState = setButtonBusy(buttonEl, "Deleting...");
            setStatus("Deleting row " + rowId + "...");

            try {
              await fetchJson("/delete_row?id=" + encodeURIComponent(rowId), {
                method: "POST"
              });

              if (selectedRowId === rowId) {
                selectedRowId = "";
              }

              await loadRegistry();
              showFlash("Row " + rowId + " deleted");
              setStatus("Row " + rowId + " deleted");
            } catch (error) {
              showError(error.message || "Unknown error");
              setStatus("Delete failed");
            } finally {
              restoreButton(buttonEl, buttonState);
            }
          }

          async function matchMediaAction(rowId, buttonEl) {
            if (!rowId || rowId === "—") return;

            clearError();
            const buttonState = setButtonBusy(buttonEl, "Matching...");
            setStatus("Matching media for row " + rowId + "...");

            try {
              const result = await fetchJson("/admin/match_media?id=" + encodeURIComponent(rowId), {
                method: "POST"
              });

              selectedRowId = rowId;
              await loadRegistry({
                keepSelection: true,
                preferredRowId: rowId
              });

              showFlash("Media matched for row " + rowId + " (" + String(result.matched_count || 0) + " candidates)");
              setStatus("Media matching completed");
            } catch (error) {
              showError(error.message || "Unknown error");
              setStatus("Media matching failed");
            } finally {
              restoreButton(buttonEl, buttonState);
            }
          }

          async function selectFinalMediaAction(rowId, mediaUrl, mediaType, buttonEl) {
            if (!rowId || !mediaUrl) return;

            clearError();
            const buttonState = setButtonBusy(buttonEl, "Selecting...");
            setStatus("Selecting final media for row " + rowId + "...");

            try {
              await fetchJson(
                "/admin/select_final_media?id=" + encodeURIComponent(rowId) +
                "&media_url=" + encodeURIComponent(mediaUrl) +
                "&media_type=" + encodeURIComponent(mediaType || "image"),
                {
                  method: "POST"
                }
              );

              selectedRowId = rowId;
              await loadRegistry({
                keepSelection: true,
                preferredRowId: rowId
              });

              showFlash("Final media selected for row " + rowId);
              setStatus("Final media selected");
            } catch (error) {
              showError(error.message || "Unknown error");
              setStatus("Final media selection failed");
            } finally {
              restoreButton(buttonEl, buttonState);
            }
          }

          async function createProductAction(event) {
            event.preventDefault();

            clearError();

            const form = document.getElementById("createProductForm");
            const imageInput = document.getElementById("createImageInput");
            const priceInput = document.getElementById("createPriceInput");
            const createBtn = document.getElementById("createBtn");

            if (!imageInput.files || !imageInput.files.length) {
              showError("Please choose an image");
              return;
            }

            if (!priceInput.value.trim()) {
              showError("Please enter a price");
              return;
            }

            const buttonState = setButtonBusy(createBtn, "Creating...");
            setStatus("Creating product...");

            try {
              const formData = new FormData(form);

              const response = await fetch("/admin/create_product", {
                method: "POST",
                body: formData
              });

              const data = await response.json().catch(() => ({}));

              if (!response.ok) {
                throw new Error(data.message || data.error || ("Request failed: " + response.status));
              }

              form.reset();
              selectedRowId = data.row_id || "";
              await loadRegistry({
                keepSelection: true,
                preferredRowId: selectedRowId
              });

              showFlash("Product created: " + (data.row_id || "new row"));
              setStatus("Product created successfully");
            } catch (error) {
              showError(error.message || "Unknown error");
              setStatus("Create product failed");
            } finally {
              restoreButton(createBtn, buttonState);
            }
          }

          document.getElementById("refreshBtn").addEventListener("click", function() {
            loadRegistry({
              keepSelection: true,
              preferredRowId: selectedRowId
            });
          });
          document.getElementById("resetFiltersBtn").addEventListener("click", resetFilters);
          document.getElementById("searchInput").addEventListener("input", applyFilters);
          document.getElementById("categoryFilter").addEventListener("change", applyFilters);
          document.getElementById("statusFilter").addEventListener("change", applyFilters);
          document.getElementById("createProductForm").addEventListener("submit", createProductAction);

          window.selectRow = selectRow;
          window.retryRowAction = retryRowAction;
          window.deleteRowAction = deleteRowAction;
          window.matchMediaAction = matchMediaAction;
          window.selectFinalMediaAction = selectFinalMediaAction;

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
