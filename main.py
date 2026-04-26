import os
import tempfile
import threading
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, url_for

from core.orchestrator import MasterOrchestrator
from storage.sheets_store import SheetsStore
from services.admin_read_service import AdminReadService
from services.content_output_service import ContentOutputService
from services.media_matching_service import MediaMatchingService

app = Flask(__name__)

orchestrator = MasterOrchestrator()
sheets = SheetsStore()
admin_read_service = AdminReadService()
media_matching_service = MediaMatchingService(sheets)
content_output_service = ContentOutputService(sheets)

_orchestrator_thread = None
_orchestrator_lock = threading.Lock()
_orchestrator_started = threading.Event()

SEED_IMAGE_DIR = Path(tempfile.gettempdir()) / "trend_yemen_seed_images"
SEED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_ADMIN_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _ensure_seed_image_dir():
    SEED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    return SEED_IMAGE_DIR


def _build_seed_image_url(filename):
    return url_for("admin_seed_image", filename=filename, _external=True)


def _error_response(message, status_code=400):
    return jsonify({
        "status": "error",
        "message": message
    }), status_code


def _has_allowed_admin_image_extension(filename):
    return Path(str(filename or "")).suffix.lower() in ALLOWED_ADMIN_IMAGE_EXTENSIONS


def _normalize_admin_price(price_raw):
    normalized = str(price_raw or "").replace(",", "").strip()

    if not normalized:
        raise ValueError("Missing price")

    value = Decimal(normalized)

    if value <= 0:
        raise ValueError("Price must be greater than zero")

    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))

    normalized_value = format(value.normalize(), "f")
    if "." in normalized_value:
        normalized_value = normalized_value.rstrip("0").rstrip(".")

    return normalized_value


def _remove_seed_image(file_path):
    try:
        if file_path and file_path.exists():
            file_path.unlink()
    except Exception:
        pass


def _save_seed_image_locally(image_bytes, original_filename):
    if not image_bytes:
        raise ValueError("Empty image file")

    seed_dir = _ensure_seed_image_dir()
    extension = Path(str(original_filename or "")).suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{extension}"

    temp_path = seed_dir / f".{filename}.tmp"
    final_path = seed_dir / filename

    try:
        with open(temp_path, "wb") as f:
            f.write(image_bytes)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, final_path)

        if not final_path.exists() or not final_path.is_file():
            raise RuntimeError("Seed image file was not saved")

        if final_path.stat().st_size <= 0:
            raise RuntimeError("Seed image file is empty after save")

        return filename, final_path

    except Exception:
        _remove_seed_image(temp_path)
        _remove_seed_image(final_path)
        raise


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

    records = admin_read_service.get_all_admin_records()
    record = next((item for item in records if item.get("row_id") == row_id), None)

    if not record:
        return jsonify({"status": "error", "message": "Row not found"}), 404

    processing_status = str(record.get("processing_status", "")).strip()
    enrichment_status = str(record.get("enrichment_status", "")).strip()
    retryable = bool(record.get("retryable"))

    if processing_status == "Pending":
        return jsonify({
            "status": "error",
            "message": "Retry is not allowed while row is Pending"
        }), 409

    if processing_status == "Processing":
        return jsonify({
            "status": "error",
            "message": "Retry is not allowed while row is Processing"
        }), 409

    if processing_status == "Completed":
        return jsonify({
            "status": "error",
            "message": "Retry is not allowed for Completed rows"
        }), 409

    if enrichment_status != "failed":
        return jsonify({
            "status": "error",
            "message": "Retry is allowed only for failed enrichment rows"
        }), 409

    if not retryable:
        return jsonify({
            "status": "error",
            "message": "Retry is not allowed for this failure classification"
        }), 409

    row_index = sheets._get_row_index_by_id(row_id)
    if not row_index:
        return jsonify({"status": "error", "message": "Row not found"}), 404

    status_col = sheets.col_map.get("ProcessingStatus")
    sheets.sheet.update_cell(row_index, status_col, "Pending")

    return jsonify({
        "status": "ok",
        "row_id": row_id
    })


@app.route("/admin/resolve_stuck", methods=["POST"])
def admin_resolve_stuck():
    row_id = request.args.get("id", "").strip()
    action = request.args.get("action", "").strip().lower()

    if not row_id:
        return jsonify({"status": "error", "message": "Missing id"}), 400

    if action not in {"reset_to_pending", "release_to_failed"}:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

    records = admin_read_service.get_all_admin_records()
    record = next((item for item in records if item.get("row_id") == row_id), None)

    if not record:
        return jsonify({"status": "error", "message": "Row not found"}), 404

    action_eligibility = record.get("action_eligibility") or {}

    if action == "reset_to_pending" and not action_eligibility.get("reset_to_pending"):
        return jsonify({
            "status": "error",
            "message": "Reset to Pending is allowed only for stuck eligible rows"
        }), 409

    if action == "release_to_failed" and not action_eligibility.get("release_to_failed"):
        return jsonify({
            "status": "error",
            "message": "Release to Failed is allowed only for stuck eligible rows"
        }), 409

    row_index = sheets._get_row_index_by_id(row_id)
    if not row_index:
        return jsonify({"status": "error", "message": "Row not found"}), 404

    status_col = sheets.col_map.get("ProcessingStatus")
    if not status_col:
        return jsonify({"status": "error", "message": "ProcessingStatus column not found"}), 400

    if action == "reset_to_pending":
        sheets.sheet.update_cell(row_index, status_col, "Pending")

        return jsonify({
            "status": "ok",
            "row_id": row_id,
            "resolved_status": "Pending",
            "action": action,
        })

    sheets.sheet.update_cell(row_index, status_col, "Failed")

    error_col = sheets.col_map.get("ErrorMessage")
    if error_col:
        sheets.sheet.update_cell(
            row_index,
            error_col,
            "Manually released from stuck Processing via Admin."
        )

    return jsonify({
        "status": "ok",
        "row_id": row_id,
        "resolved_status": "Failed",
        "action": action,
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
        result = media_matching_service.generate_candidates_for_product_record(record)
        return jsonify({
            "status": "ok",
            "row_id": result.get("row_id", row_id),
            "matched_count": result.get("matched_count", 0),
            "matched_status": result.get("matched_status", "ready")
        })
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
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


@app.route("/admin/generate_content", methods=["POST"])
def admin_generate_content():
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
        result = content_output_service.generate_for_row_id(row_id)
        return jsonify({
            "status": "ok",
            "row_id": result.get("row_id", row_id),
            "content_status": result.get("content_status", "ready"),
            "content_ready_at": result.get("content_ready_at", ""),
            "marketing_title": result.get("marketing_title", ""),
        })
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 409
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/admin/seed_image/<path:filename>")
def admin_seed_image(filename):
    _ensure_seed_image_dir()

    file_path = SEED_IMAGE_DIR / filename

    if not file_path.exists() or not file_path.is_file():
        return _error_response("Seed image not found", 404)

    if file_path.stat().st_size <= 0:
        return _error_response("Seed image file is empty", 404)

    return send_from_directory(SEED_IMAGE_DIR, filename)


@app.route("/admin/create_product", methods=["POST"])
def admin_create_product():
    content_type = str(request.content_type or "").lower()
    if "multipart/form-data" not in content_type:
        return _error_response("Content-Type must be multipart/form-data")

    image = request.files.get("image")
    price_raw = request.form.get("price", "")

    if image is None or not str(image.filename or "").strip():
        return _error_response("Missing image file")

    image_filename = str(image.filename).strip()
    image_mimetype = str(image.mimetype or "").strip().lower()

    if not _has_allowed_admin_image_extension(image_filename):
        return _error_response(
            "Unsupported image file type. Allowed: JPG, JPEG, PNG, WEBP, GIF, BMP"
        )

    if image_mimetype and not image_mimetype.startswith("image/"):
        return _error_response("Uploaded file must be an image")

    if not str(price_raw or "").strip():
        return _error_response("Missing price")

    try:
        price_value = _normalize_admin_price(price_raw)
    except (InvalidOperation, ValueError):
        return _error_response("Invalid price. Enter a positive number")

    file_path = None

    try:
        image_bytes = image.read()
        filename, file_path = _save_seed_image_locally(image_bytes, image_filename)

        if not file_path.exists() or not file_path.is_file():
            return _error_response("Failed to save seed image locally", 500)

        if file_path.stat().st_size <= 0:
            _remove_seed_image(file_path)
            return _error_response("Failed to save seed image locally", 500)

        image_url = _build_seed_image_url(filename)

        if not image_url:
            _remove_seed_image(file_path)
            return _error_response("Failed to build local seed image URL", 500)

        created = sheets.append_pending_product(
            image_url=image_url,
            price=price_value,
        )

        return jsonify({
            "row_id": created["row_id"],
            "image_url": created["image_url"],
            "status": created["status"],
        }), 201

    except ValueError as e:
        _remove_seed_image(file_path)
        return _error_response(str(e), 400)
    except Exception:
        _remove_seed_image(file_path)
        return _error_response("Failed to create product", 500)


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

          .badge-retryable-failed {
            background: #fff7db;
            border-color: #f3dfab;
            color: #8a6300;
          }

          .badge-stuck-processing {
            background: #fff7db;
            border-color: #f3dfab;
            color: #8a6300;
          }

          .badge-content-eligible {
            background: #eef2ff;
            border-color: #c7d2fe;
            color: #4338ca;
          }

          .badge-content-ready {
            background: #e9f8ee;
            border-color: #cdebd7;
            color: #15803d;
          }

          .badge-content-failed {
            background: #fef0f0;
            border-color: #fecaca;
            color: #b91c1c;
          }

          .badge-content-notready {
            background: #f9fafb;
            border-color: #e5e7eb;
            color: #6b7280;
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

          .row-meta {
            margin-top: 4px;
            font-size: 12px;
            color: #6b7280;
            line-height: 1.4;
          }

          .row-meta-warning {
            color: #8a6300;
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

          .matched-media-block,
          .content-block {
            margin-top: 18px;
            padding-top: 16px;
            border-top: 1px solid #eef0f2;
          }

          .matched-media-head,
          .content-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 12px;
          }

          .matched-media-head h3,
          .content-head h3 {
            margin: 0;
            font-size: 15px;
          }

          .matched-media-head p,
          .content-head p {
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

          .matched-empty,
          .content-empty {
            color: #6b7280;
            font-size: 13px;
            padding: 6px 0 2px;
          }

          .content-preview-grid {
            display: grid;
            gap: 12px;
          }

          .content-preview-item {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 12px;
            background: #fafafa;
          }

          .content-preview-item h4 {
            margin: 0 0 8px;
            font-size: 13px;
            color: #374151;
          }

          .content-preview-item p,
          .content-preview-item div {
            margin: 0;
            font-size: 13px;
            color: #111827;
            white-space: pre-wrap;
            word-break: break-word;
          }


          .workspace-block {
            margin-top: 18px;
            padding-top: 16px;
            border-top: 1px solid #eef0f2;
          }

          .workspace-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 12px;
          }

          .workspace-head h3 {
            margin: 0;
            font-size: 15px;
          }

          .workspace-head p {
            margin: 0;
            color: #6b7280;
            font-size: 13px;
          }

          .workspace-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
            gap: 12px;
          }

          .workspace-card {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            background: #ffffff;
            overflow: hidden;
          }

          .workspace-preview {
            width: 100%;
            height: 160px;
            background: #f3f4f6;
            border-bottom: 1px solid #eef0f2;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            color: #6b7280;
            font-size: 12px;
          }

          .workspace-preview img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
          }

          .workspace-video-placeholder {
            padding: 16px;
            text-align: center;
            line-height: 1.5;
          }

          .workspace-body {
            padding: 12px;
          }

          .workspace-label {
            font-size: 13px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 8px;
            word-break: break-word;
          }

          .workspace-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
          }

          .workspace-foot {
            font-size: 12px;
            color: #6b7280;
            line-height: 1.5;
            word-break: break-word;
          }

          .workspace-actions {
            margin-top: 10px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
          }

          .badge-source-original {
            background: #eef2ff;
            border-color: #c7d2fe;
            color: #4338ca;
          }

          .badge-source-cj {
            background: #ecfdf5;
            border-color: #a7f3d0;
            color: #065f46;
          }

          .badge-source-pexels {
            background: #fff7ed;
            border-color: #fed7aa;
            color: #9a3412;
          }

          .badge-source-manual {
            background: #f5f3ff;
            border-color: #ddd6fe;
            color: #6d28d9;
          }

          .badge-source-final {
            background: #eff6ff;
            border-color: #bfdbfe;
            color: #1d4ed8;
          }

          .badge-type-video {
            background: #fef2f2;
            border-color: #fecaca;
            color: #b91c1c;
          }

          .badge-is-final {
            background: #dbeafe;
            border-color: #93c5fd;
            color: #1d4ed8;
            font-weight: 700;
          }

          .workspace-link {
            font-size: 12px;
            color: #2563eb;
            text-decoration: none;
          }

          .workspace-link:hover {
            text-decoration: underline;
          }

          .workspace-empty {
            padding: 14px 12px;
            border: 1px dashed #d1d5db;
            border-radius: 12px;
            color: #6b7280;
            font-size: 13px;
            background: #fafafa;
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
            <form
              id="createProductForm"
              class="create-form"
              action="/admin/create_product"
              method="post"
              enctype="multipart/form-data"
            >
              <input
                id="createImageInput"
                name="image"
                type="file"
                accept=".jpg,.jpeg,.png,.webp,.gif,.bmp,image/*"
                required
              />
              <input
                id="createPriceInput"
                name="price"
                type="text"
                inputmode="decimal"
                placeholder="Price (YER)"
                required
              />
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


          function normalizeWorkspaceAssets(record) {
            const assets = Array.isArray(record?.product_workspace_assets)
              ? record.product_workspace_assets
              : [];

            return assets.filter((asset) => asset && asset.url);
          }

          function getWorkspaceSourceBadgeClass(asset) {
            const sourceTag = String(asset?.source_tag || "").toLowerCase();
            const sourceFamily = String(asset?.source_family || "").toLowerCase();

            if (sourceTag === "seed_media" || sourceFamily === "seed") {
              return "badge-source-original";
            }
            if (sourceTag === "cj_supplier" || sourceTag === "cj" || sourceFamily === "supplier") {
              return "badge-source-cj";
            }
            if (sourceTag === "pexels" || sourceFamily === "fallback") {
              return "badge-source-pexels";
            }
            if (sourceTag === "manual_ref" || sourceFamily === "manual") {
              return "badge-source-manual";
            }
            if (sourceTag === "final_selected" || sourceFamily === "final") {
              return "badge-source-final";
            }
            return "";
          }

          function renderWorkspaceAssetPreview(asset) {
            const type = String(asset?.type || "image").toLowerCase();
            const url = escapeHtml(asset?.url || "");
            const label = escapeHtml(asset?.label || "Workspace Asset");

            if (type === "video") {
              return `
                <div class="workspace-preview">
                  <div class="workspace-video-placeholder">
                    <div><strong>Video Preview</strong></div>
                    <div style="margin-top:6px;">No heavy player in this slice</div>
                  </div>
                </div>
              `;
            }

            return `
              <div class="workspace-preview">
                <img src="${url}" alt="${label}" loading="lazy" />
              </div>
            `;
          }

          function renderWorkspaceAssetCard(asset, record) {
            const sourceFamily = escapeHtml(asset?.source_family || "unknown");
            const sourceName = escapeHtml(asset?.source_name || "unknown");
            const sourceTag = escapeHtml(asset?.source_tag || "unknown_source");
            const type = escapeHtml(asset?.type || "image");
            const role = escapeHtml(asset?.role || "additional");
            const priority = escapeHtml(asset?.priority ?? "");
            const rank = escapeHtml(asset?.rank ?? "");
            const url = escapeHtml(asset?.url || "");
            const label = escapeHtml(asset?.label || "Workspace Asset");
            const rowId = escapeHtml(getRowId(record));
            const mediaType = escapeHtml(asset?.type || "image");
            const isFinal = Boolean(asset?.is_final);
            const sourceBadgeClass = getWorkspaceSourceBadgeClass(asset);
            const typeBadgeClass = type.toLowerCase() === "video" ? "badge-type-video" : "";

            return `
              <div class="workspace-card">
                ${renderWorkspaceAssetPreview(asset)}
                <div class="workspace-body">
                  <div class="workspace-label">${label}</div>

                  <div class="workspace-meta">
                    <span class="badge ${sourceBadgeClass}">${sourceName}</span>
                    <span class="badge ${typeBadgeClass}">${type}</span>
                    <span class="badge">${role}</span>
                    ${isFinal ? `<span class="badge badge-is-final">final</span>` : ``}
                  </div>

                  <div class="workspace-foot">
                    <div>source: ${sourceFamily} / ${sourceTag}</div>
                    <div>rank: ${rank || "-"} · priority: ${priority || "-"}</div>
                    <div style="margin-top:6px;">
                      <a class="workspace-link" href="${url}" target="_blank" rel="noreferrer">Open asset</a>
                    </div>
                  </div>

                  <div class="workspace-actions">
                    ${isFinal
                      ? `<button type="button" class="action-selected" disabled>Selected</button>`
                      : `<button type="button" class="action-secondary" onclick="selectFinalMediaAction('${rowId}', '${url}', '${mediaType}', this)">Select</button>`}
                  </div>
                </div>
              </div>
            `;
          }

          function renderProductWorkspace(record) {
            const assets = normalizeWorkspaceAssets(record);

            if (!assets.length) {
              return `
                <div class="workspace-block">
                  <div class="workspace-head">
                    <div>
                      <h3>Product Workspace</h3>
                      <p>Unified read-only preview of current product assets.</p>
                    </div>
                  </div>
                  <div class="workspace-empty">No workspace assets available for this product yet.</div>
                </div>
              `;
            }

            const imageAssets = assets.filter((asset) => String(asset?.type || "image").toLowerCase() !== "video");
            const videoAssets = assets.filter((asset) => String(asset?.type || "").toLowerCase() === "video");

            const renderGroup = (title, items) => {
              if (!items.length) return "";
              return `
                <div style="margin-top:12px;">
                  <div style="font-size:13px;color:#6b7280;margin-bottom:8px;">${title}</div>
                  <div class="workspace-grid">
                    ${items.map((asset) => renderWorkspaceAssetCard(asset, record)).join("")}
                  </div>
                </div>
              `;
            };

            return `
              <div class="workspace-block">
                <div class="workspace-head">
                  <div>
                    <h3>Product Workspace</h3>
                    <p>Read-only preview from product_workspace_assets.</p>
                  </div>
                </div>
                ${renderGroup("Images", imageAssets)}
                ${renderGroup("Videos", videoAssets)}
              </div>
            `;
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

          function getProcessingStatus(record) {
            return (
              record.processing_status ||
              record.status ||
              "—"
            );
          }

          function getStatus(record) {
            return (
              record.operational_status ||
              getProcessingStatus(record)
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

          function getOperationalStatus(record) {
            return record.operational_status || getStatus(record);
          }

          function getRetryabilityStatus(record) {
            return record.retryability_status || "not_applicable";
          }

          function getRetryGuidance(record) {
            return record.retry_guidance || "—";
          }

          function getFailureStage(record) {
            return record.failure_stage || "—";
          }

          function getFailureCategory(record) {
            return record.failure_category || "—";
          }

          function getFailureSummary(record) {
            return record.failure_summary || "—";
          }

          function getErrorMessage(record) {
            return record.error_message || "—";
          }

          function isRetryRecommended(record) {
            return Boolean(record.retry_recommended);
          }

          function isStuckProcessing(record) {
            return Boolean(record.is_stuck_processing);
          }

          function getProcessingAge(record) {
            return record.processing_age || "";
          }

          function getStuckReason(record) {
            return record.stuck_reason || "";
          }

          function isStuckActionEligible(record) {
            return Boolean(record.stuck_action_eligible);
          }

          function getActionEligibility(record) {
            return record.action_eligibility || {};
          }

          function canResetToPending(record) {
            return Boolean(getActionEligibility(record).reset_to_pending);
          }

          function canReleaseToFailed(record) {
            return Boolean(getActionEligibility(record).release_to_failed);
          }

          function canGenerateContent(record) {
            return Boolean(getActionEligibility(record).generate_content);
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

          function getContentStatus(record) {
            return record.content_status || "not_started";
          }

          function getContentReadiness(record) {
            return record.content_readiness || "not_ready";
          }

          function getContentReadyAt(record) {
            return record.content_ready_at || "—";
          }

          function getContentErrorMessage(record) {
            return record.content_error_message || "—";
          }

          function getMarketingTitle(record) {
            return record.marketing_title || "";
          }

          function getMarketingDescription(record) {
            return record.marketing_description || "";
          }

          function getSocialPost(record) {
            return record.social_post || "";
          }

          function getSeoKeywords(record) {
            return record.seo_keywords || "";
          }

          function getSeoHashtags(record) {
            return record.seo_hashtags || "";
          }

          function getContentEligibility(record) {
            return record.content_eligibility || {};
          }

          function getContentReadinessClass(readiness) {
            const normalized = String(readiness || "").toLowerCase();
            if (normalized === "ready") return "badge badge-content-ready";
            if (normalized === "failed") return "badge badge-content-failed";
            if (normalized === "eligible") return "badge badge-content-eligible";
            return "badge badge-content-notready";
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
            const normalized = String(status || "")
              .trim()
              .toLowerCase()
              .replace(/[\\s_-]+/g, "");

            if (normalized === "retryablefailed") return "badge badge-retryable-failed";
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

          const ALLOWED_CREATE_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"];

          function hasAllowedCreateImageExtension(fileName) {
            const value = String(fileName || "").toLowerCase();
            return ALLOWED_CREATE_IMAGE_EXTENSIONS.some((ext) => value.endsWith(ext));
          }

          function validateCreateProductInputs(imageInput, priceInput) {
            const file = imageInput.files && imageInput.files[0];

            if (!file) {
              return "Please choose an image";
            }

            const hasValidExtension = hasAllowedCreateImageExtension(file.name);
            const hasValidMimeType = !file.type || file.type.startsWith("image/");

            if (!hasValidExtension || !hasValidMimeType) {
              return "Please choose a valid image file (JPG, JPEG, PNG, WEBP, GIF, or BMP)";
            }

            const normalizedPrice = String(priceInput.value || "").replace(/,/g, "").trim();
            const priceNumber = Number(normalizedPrice);

            if (!normalizedPrice) {
              return "Please enter a price";
            }

            if (!Number.isFinite(priceNumber) || priceNumber <= 0) {
              return "Please enter a valid positive price";
            }

            return "";
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
              const role = candidate.role || "additional";
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
                      <div>Role: ${escapeHtml(role)}</div>
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

          function renderContentPreview(record) {
            const contentStatus = getContentStatus(record);
            const contentReadiness = getContentReadiness(record);
            const contentReadyAt = getContentReadyAt(record);
            const contentErrorMessage = getContentErrorMessage(record);
            const marketingTitle = getMarketingTitle(record);
            const marketingDescription = getMarketingDescription(record);
            const socialPost = getSocialPost(record);
            const seoKeywords = getSeoKeywords(record);
            const seoHashtags = getSeoHashtags(record);
            const eligibility = getContentEligibility(record);

            const previewItems = [];

            if (marketingTitle) {
              previewItems.push(`
                <div class="content-preview-item">
                  <h4>Marketing Title</h4>
                  <div>${escapeHtml(marketingTitle)}</div>
                </div>
              `);
            }

            if (marketingDescription) {
              previewItems.push(`
                <div class="content-preview-item">
                  <h4>Marketing Description</h4>
                  <div>${escapeHtml(marketingDescription)}</div>
                </div>
              `);
            }

            if (socialPost) {
              previewItems.push(`
                <div class="content-preview-item">
                  <h4>Social Post</h4>
                  <div>${escapeHtml(socialPost)}</div>
                </div>
              `);
            }

            if (seoKeywords) {
              previewItems.push(`
                <div class="content-preview-item">
                  <h4>SEO Keywords</h4>
                  <div>${escapeHtml(seoKeywords)}</div>
                </div>
              `);
            }

            if (seoHashtags) {
              previewItems.push(`
                <div class="content-preview-item">
                  <h4>SEO Hashtags</h4>
                  <div>${escapeHtml(seoHashtags)}</div>
                </div>
              `);
            }

            const eligibilityReason = eligibility.reason || "—";

            if (!previewItems.length) {
              return `
                <div class="content-block">
                  <div class="content-head">
                    <div>
                      <h3>Publish-Ready Content</h3>
                      <p>Status: ${escapeHtml(contentStatus)} · Readiness: ${escapeHtml(contentReadiness)}</p>
                    </div>
                  </div>
                  <div class="content-empty">No content output generated yet.</div>
                  <div class="row-meta">Eligibility: ${escapeHtml(eligibilityReason)}</div>
                  <div class="row-meta">Ready At: ${escapeHtml(contentReadyAt)}</div>
                  <div class="row-meta row-meta-warning">Error: ${escapeHtml(contentErrorMessage)}</div>
                </div>
              `;
            }

            return `
              <div class="content-block">
                <div class="content-head">
                  <div>
                    <h3>Publish-Ready Content</h3>
                    <p>Status: ${escapeHtml(contentStatus)} · Readiness: ${escapeHtml(contentReadiness)}</p>
                  </div>
                </div>
                <div class="row-meta">Eligibility: ${escapeHtml(eligibilityReason)}</div>
                <div class="row-meta">Ready At: ${escapeHtml(contentReadyAt)}</div>
                <div class="row-meta row-meta-warning">Error: ${escapeHtml(contentErrorMessage)}</div>
                <div class="content-preview-grid" style="margin-top: 12px;">
                  ${previewItems.join("")}
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
            const processingStatus = getProcessingStatus(record);
            const price = getPrice(record);
            const rowId = getRowId(record);
            const lastUpdated = getLastUpdated(record);
            const jsonUrl = "/admin/product?row_id=" + encodeURIComponent(rowId);
            const matchedStatus = getMatchedMediaStatus(record);
            const matchedCount = getMatchedMediaCount(record);
            const matchedAt = getMatchedAt(record);
            const finalMediaStatus = getFinalMediaStatus(record);

            const retryabilityStatus = getRetryabilityStatus(record);
            const retryGuidance = getRetryGuidance(record);
            const failureStage = getFailureStage(record);
            const failureCategory = getFailureCategory(record);
            const failureSummary = getFailureSummary(record);
            const errorMessage = getErrorMessage(record);
            const retryRecommended = isRetryRecommended(record) ? "Yes" : "No";

            const isStuck = isStuckProcessing(record);
            const processingAge = getProcessingAge(record);
            const stuckReason = getStuckReason(record);
            const stuckActionEligible = isStuckActionEligible(record) ? "Yes" : "No";

            const showResetToPending = canResetToPending(record);
            const showReleaseToFailed = canReleaseToFailed(record);
            const showGenerateContent = canGenerateContent(record);

            const contentStatus = getContentStatus(record);
            const contentReadiness = getContentReadiness(record);

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

                <div class="detail-label">Operational Status</div>
                <div class="detail-value"><span class="${getStatusClass(status)}">${escapeHtml(status)}</span></div>

                <div class="detail-label">Processing Status</div>
                <div class="detail-value"><span class="${getStatusClass(processingStatus)}">${escapeHtml(processingStatus)}</span></div>

                <div class="detail-label">Price</div>
                <div class="detail-value">${escapeHtml(price)}</div>

                <div class="detail-label">Row ID</div>
                <div class="detail-value">${escapeHtml(rowId)}</div>

                <div class="detail-label">Last Updated</div>
                <div class="detail-value">${escapeHtml(lastUpdated)}</div>

                <div class="detail-label">Processing Age</div>
                <div class="detail-value">${escapeHtml(processingAge || "—")}</div>

                <div class="detail-label">Stuck Processing</div>
                <div class="detail-value">${escapeHtml(isStuck ? "Yes" : "No")}</div>

                <div class="detail-label">Stuck Reason</div>
                <div class="detail-value">${escapeHtml(stuckReason || "—")}</div>

                <div class="detail-label">Stuck Action Eligible</div>
                <div class="detail-value">${escapeHtml(stuckActionEligible)}</div>

                <div class="detail-label">Retryability</div>
                <div class="detail-value">${escapeHtml(retryabilityStatus)}</div>

                <div class="detail-label">Retry Recommended</div>
                <div class="detail-value">${escapeHtml(retryRecommended)}</div>

                <div class="detail-label">Retry Guidance</div>
                <div class="detail-value">${escapeHtml(retryGuidance)}</div>

                <div class="detail-label">Failure Stage</div>
                <div class="detail-value">${escapeHtml(failureStage)}</div>

                <div class="detail-label">Failure Category</div>
                <div class="detail-value">${escapeHtml(failureCategory)}</div>

                <div class="detail-label">Failure Summary</div>
                <div class="detail-value">${escapeHtml(failureSummary)}</div>

                <div class="detail-label">Error Message</div>
                <div class="detail-value">${escapeHtml(errorMessage)}</div>

                <div class="detail-label">Matched Media</div>
                <div class="detail-value">${escapeHtml(matchedStatus)} (${escapeHtml(matchedCount)})</div>

                <div class="detail-label">Matched At</div>
                <div class="detail-value">${escapeHtml(matchedAt)}</div>

                <div class="detail-label">Final Media</div>
                <div class="detail-value">${escapeHtml(finalMediaStatus)}</div>

                <div class="detail-label">Content Status</div>
                <div class="detail-value"><span class="${getContentReadinessClass(contentReadiness)}">${escapeHtml(contentStatus)}</span></div>

                <div class="detail-label">Content Readiness</div>
                <div class="detail-value"><span class="${getContentReadinessClass(contentReadiness)}">${escapeHtml(contentReadiness)}</span></div>
              </div>

              <div class="detail-actions">
                <button type="button" class="action-secondary" onclick="matchMediaAction('${escapeHtml(String(rowId))}', this)">Match Media</button>
                <button type="button" onclick="retryRowAction('${escapeHtml(String(rowId))}', this)">Retry</button>
                ${showGenerateContent ? `<button type="button" class="action-primary" onclick="generateContentAction('${escapeHtml(String(rowId))}', this)">Generate Content</button>` : ``}
                ${showResetToPending ? `<button type="button" onclick="resolveStuckAction('${escapeHtml(String(rowId))}', 'reset_to_pending', this)">Reset to Pending</button>` : ``}
                ${showReleaseToFailed ? `<button type="button" class="action-danger" onclick="resolveStuckAction('${escapeHtml(String(rowId))}', 'release_to_failed', this)">Release to Failed</button>` : ``}
                <button type="button" class="action-danger" onclick="deleteRowAction('${escapeHtml(String(rowId))}', this)">Delete</button>
                <a class="json-link" href="${escapeHtml(jsonUrl)}" target="_blank">View JSON</a>
              </div>

              ${renderMatchedMedia(record)}
              ${renderProductWorkspace(record)}
              ${renderContentPreview(record)}
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
              const contentReadiness = getContentReadiness(record);
              const contentStatus = getContentStatus(record);

              const imageHtml = imageUrl
                ? `<img class="thumb" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(name)}" onerror="this.outerHTML='&lt;div class=&quot;thumb-placeholder&quot;&gt;No image&lt;/div&gt;'" />`
                : `<div class="thumb-placeholder">No image</div>`;

              const statusMetaHtml = isStuckProcessing(record)
                ? `
                  <div class="row-meta">
                    <span class="badge badge-stuck-processing">Stuck</span>
                    <span>${escapeHtml(getProcessingAge(record) || "—")}</span>
                  </div>
                  <div class="row-meta row-meta-warning">${escapeHtml(getStuckReason(record) || "")}</div>
                `
                : (
                    getStuckReason(record)
                      ? `<div class="row-meta row-meta-warning">${escapeHtml(getStuckReason(record))}</div>`
                      : (
                          getProcessingAge(record)
                            ? `<div class="row-meta">Age: ${escapeHtml(getProcessingAge(record))}</div>`
                            : ``
                        )
                  );

              const contentMetaHtml = `
                <div class="row-meta">
                  <span class="${getContentReadinessClass(contentReadiness)}">${escapeHtml(contentStatus)}</span>
                </div>
              `;

              return `
                <tr data-row-id="${escapeHtml(String(record.row_id || ""))}" onclick="selectRow('${escapeHtml(String(record.row_id || ""))}')">
                  <td class="image-cell">${imageHtml}</td>
                  <td class="name-cell"><div class="truncate">${escapeHtml(name)}</div></td>
                  <td><div class="truncate">${escapeHtml(category)}</div></td>
                  <td>
                    <span class="${getStatusClass(status)}">${escapeHtml(status)}</span>
                    ${statusMetaHtml}
                    ${contentMetaHtml}
                  </td>
                  <td>${escapeHtml(price)}</td>
                  <td><div class="truncate">${escapeHtml(rowId)}</div></td>
                  <td>
                    <div class="row-actions">
                      <button type="button" class="action-secondary" onclick="event.stopPropagation(); matchMediaAction('${escapeHtml(String(rowId))}', this)">Match Media</button>
                      <button type="button" onclick="event.stopPropagation(); retryRowAction('${escapeHtml(String(rowId))}', this)">Retry</button>
                      <button type="button" class="action-primary" onclick="event.stopPropagation(); generateContentAction('${escapeHtml(String(rowId))}', this)">Generate Content</button>
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

          async function resolveStuckAction(rowId, action, buttonEl) {
            if (!rowId || rowId === "—" || !action) return;

            const actionLabel = action === "reset_to_pending" ? "Resetting..." : "Releasing...";
            const successLabel = action === "reset_to_pending"
              ? "Row " + rowId + " reset to Pending"
              : "Row " + rowId + " released to Failed";

            clearError();
            const buttonState = setButtonBusy(buttonEl, actionLabel);
            setStatus(successLabel + "...");

            try {
              await fetchJson(
                "/admin/resolve_stuck?id=" + encodeURIComponent(rowId) +
                "&action=" + encodeURIComponent(action),
                {
                  method: "POST"
                }
              );

              selectedRowId = rowId;
              await loadRegistry({
                keepSelection: true,
                preferredRowId: rowId
              });

              showFlash(successLabel);
              setStatus(successLabel);
            } catch (error) {
              showError(error.message || "Unknown error");
              setStatus("Stuck resolve failed");
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

          async function generateContentAction(rowId, buttonEl) {
            if (!rowId || rowId === "—") return;

            clearError();
            const buttonState = setButtonBusy(buttonEl, "Generating...");
            setStatus("Generating content for row " + rowId + "...");

            try {
              const result = await fetchJson("/admin/generate_content?id=" + encodeURIComponent(rowId), {
                method: "POST"
              });

              selectedRowId = rowId;
              await loadRegistry({
                keepSelection: true,
                preferredRowId: rowId
              });

              showFlash("Content generated for row " + rowId);
              setStatus("Content generation completed");
            } catch (error) {
              showError(error.message || "Unknown error");
              setStatus("Content generation failed");
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

            const validationError = validateCreateProductInputs(imageInput, priceInput);
            if (validationError) {
              showError(validationError);
              setStatus("Create product failed");
              return;
            }

            const buttonState = setButtonBusy(createBtn, "Creating...");
            setStatus("Creating product...");

            try {
              const formData = new FormData(form);
              formData.set("price", priceInput.value.trim());

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
          window.resolveStuckAction = resolveStuckAction;
          window.deleteRowAction = deleteRowAction;
          window.matchMediaAction = matchMediaAction;
          window.selectFinalMediaAction = selectFinalMediaAction;
          window.generateContentAction = generateContentAction;

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
