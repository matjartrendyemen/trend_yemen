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
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width,initial-scale=1"/>
      <title>Admin Registry</title>
      <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, sans-serif; padding:20px; margin:0; background:#f5f5f5; color:#222; }

        .page-title { margin: 0 0 8px; }
        .page-subtitle { margin: 0 0 18px; color:#666; }

        .create-box,
        .list,
        .details {
          background:#fff;
          border:1px solid #ddd;
          border-radius:8px;
        }

        .create-box {
          padding:12px;
          margin-bottom:15px;
        }

        .toolbar {
          display:flex;
          gap:10px;
          flex-wrap:wrap;
          margin-bottom:15px;
        }

        input, select, button {
          padding:8px;
          border-radius:6px;
          border:1px solid #ccc;
          background:#fff;
        }

        button { cursor:pointer; }
        button:hover { background:#f0f0f0; }

        #create-form {
          display:flex;
          gap:10px;
          flex-wrap:wrap;
          align-items:center;
        }

        #create-result {
          margin-top:10px;
          white-space:pre-wrap;
          word-break:break-word;
          color:#444;
          font-size:14px;
        }

        .list-header {
          display:grid;
          grid-template-columns: 48px minmax(160px, 2fr) minmax(120px, 1fr) minmax(110px, 1fr) minmax(120px, 1fr) 90px;
          gap:10px;
          padding:10px 8px;
          border-bottom:1px solid #eee;
          font-size:13px;
          font-weight:bold;
          color:#666;
          background:#fafafa;
        }

        .row {
          display:grid;
          grid-template-columns: 48px minmax(160px, 2fr) minmax(120px, 1fr) minmax(110px, 1fr) minmax(120px, 1fr) 90px;
          gap:10px;
          align-items:center;
          padding:8px;
          border-bottom:1px solid #eee;
          cursor:pointer;
        }

        .row:hover { background:#f0f0f0; }
        .row.selected { background:#dbe9ff; }

        .thumb {
          width:40px;
          height:40px;
          object-fit:cover;
          border-radius:6px;
          border:1px solid #ccc;
          background:#eee;
          display:block;
        }

        .thumb-fallback {
          width:40px;
          height:40px;
          border-radius:6px;
          border:1px solid #ccc;
          background:#eee;
          color:#777;
          font-size:11px;
          display:flex;
          align-items:center;
          justify-content:center;
        }

        .cell-muted {
          color:#666;
          font-size:13px;
        }

        .details {
          margin-top:15px;
          padding:12px;
        }

        .details h3 {
          margin-top:0;
          margin-bottom:10px;
        }

        .details-grid {
          display:grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap:10px;
          margin-bottom:12px;
        }

        .details-box {
          background:#fafafa;
          border:1px solid #eee;
          border-radius:6px;
          padding:10px;
          font-size:14px;
        }

        .links, .actions {
          display:flex;
          gap:10px;
          flex-wrap:wrap;
          margin-top:10px;
        }

        .error-box {
          padding:10px;
          background:#fff1f0;
          border:1px solid #f3c2be;
          color:#a94442;
          border-radius:6px;
          margin-top:10px;
          white-space:pre-wrap;
          word-break:break-word;
        }

        .hidden { display:none; }
      </style>
    </head>
    <body>
      <h1 class="page-title">Admin Registry</h1>
      <p class="page-subtitle">Control center with compact product registry and on-demand details.</p>

      <div class="create-box">
        <form id="create-form">
          <input id="image-input" type="file" accept="image/*" required />
          <input id="price-input" type="number" step="any" min="0" placeholder="Price (YER)" required />
          <button type="submit">Create Product</button>
        </form>
        <div id="create-result"></div>
      </div>

      <div class="toolbar">
        <input id="search" placeholder="Search by product name"/>
        <select id="category"></select>
        <select id="status">
          <option value="">All Status</option>
          <option>Pending</option>
          <option>Processing</option>
          <option>Completed</option>
          <option>Failed</option>
        </select>
        <button onclick="toggleAll()">Show All</button>
        <button onclick="load()">Refresh</button>
      </div>

      <div id="error" class="error-box hidden"></div>

      <div id="list" class="list"></div>
      <div id="details" class="details" style="display:none;"></div>

      <script>
        let DATA = [];
        let SELECTED = null;
        let SHOW_ALL = false;

        function escapeHtml(value){
          return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
        }

        function norm(u){
          if(!u) return "";

          const value = String(u).trim();

          if(value.startsWith("/admin/seed_image")) return value;
          if(value.includes("/admin/seed_image/")) return value;

          return "";
        }

        function showError(message){
          const box = document.getElementById("error");
          if(!message){
            box.classList.add("hidden");
            box.textContent = "";
            return;
          }
          box.classList.remove("hidden");
          box.textContent = message;
        }

        function buildCat(){
          let cats = [...new Set(DATA.map(x => x.category_id).filter(Boolean))];
          let el = document.getElementById("category");
          el.innerHTML = "<option value=''>All Categories</option>" +
            cats.map(c => "<option>" + escapeHtml(c) + "</option>").join("");
        }

        function toggleAll(){
          SHOW_ALL = !SHOW_ALL;
          render();
        }

        function renderThumb(url){
          const normalized = norm(url);
          if(!normalized){
            return '<div class="thumb-fallback">No img</div>';
          }

          return '<img class="thumb" src="' + escapeHtml(normalized) + '" onerror="this.outerHTML=\\'<div class=&quot;thumb-fallback&quot;>No img</div>\\'"/>';
        }

        function render(){
          let s = document.getElementById("search").value.toLowerCase();
          let c = document.getElementById("category").value;
          let st = document.getElementById("status").value;

          let list = DATA.filter(p => {
            if(s && !(p.product_name || "").toLowerCase().includes(s)) return false;
            if(c && p.category_id !== c) return false;
            if(st && p.processing_status !== st) return false;
            return true;
          });

          if(!SHOW_ALL) list = list.slice(0, 50);

          const header = `
            <div class="list-header">
              <div>Image</div>
              <div>Name</div>
              <div>Category</div>
              <div>Status</div>
              <div>Readiness</div>
              <div>Row ID</div>
            </div>
          `;

          document.getElementById("list").innerHTML = header + list.map(p => `
            <div class="row ${SELECTED === p.row_id ? "selected" : ""}" onclick="selectRow('${escapeHtml(p.row_id)}')">
              <div>${renderThumb(p.source_image_url)}</div>
              <div>${escapeHtml(p.product_name || "—")}</div>
              <div class="cell-muted">${escapeHtml(p.category_id || "—")}</div>
              <div class="cell-muted">${escapeHtml(p.processing_status || "—")}</div>
              <div class="cell-muted">${escapeHtml((p.readiness || {}).status || "—")}</div>
              <div class="cell-muted">${escapeHtml(p.row_id || "—")}</div>
            </div>
          `).join("");

          if(SELECTED && !DATA.find(x => x.row_id === SELECTED)){
            document.getElementById("details").style.display = "none";
          }
        }

        function selectRow(id){
          SELECTED = id;
          render();

          let p = DATA.find(x => x.row_id === id);
          if(!p) return;

          const readiness = (p.readiness || {}).status || "—";
          const missingFields = ((p.smart_encoding_inputs || {}).missing_fields || []).join(", ") || "—";
          const sourceLink = p.source_image_url || "";
          const finalLink = p.final_image_url || "";
          const sourcePreview = norm(sourceLink);

          document.getElementById("details").style.display = "block";
          document.getElementById("details").innerHTML = `
            <h3>${escapeHtml(p.product_name || "Untitled Product")}</h3>

            <div class="details-grid">
              <div class="details-box"><strong>Row ID:</strong><br>${escapeHtml(p.row_id || "—")}</div>
              <div class="details-box"><strong>Category:</strong><br>${escapeHtml(p.category_id || "—")}</div>
              <div class="details-box"><strong>Status:</strong><br>${escapeHtml(p.processing_status || "—")}</div>
              <div class="details-box"><strong>Readiness:</strong><br>${escapeHtml(readiness)}</div>
              <div class="details-box"><strong>Missing fields:</strong><br>${escapeHtml(missingFields)}</div>
              <div class="details-box"><strong>Error:</strong><br>${escapeHtml(p.error_message || "—")}</div>
            </div>

            <div>
              ${sourcePreview
                ? '<img class="thumb" style="width:96px;height:96px;" src="' + escapeHtml(sourcePreview) + '" onerror="this.outerHTML=\\'<div class=&quot;thumb-fallback&quot; style=&quot;width:96px;height:96px;&quot;>No img</div>\\'"/>'
                : '<div class="thumb-fallback" style="width:96px;height:96px;">No img</div>'
              }
            </div>

            <div class="links">
              ${sourceLink ? '<a href="' + escapeHtml(sourceLink) + '" target="_blank">Source link</a>' : ''}
              ${finalLink ? '<a href="' + escapeHtml(finalLink) + '" target="_blank">Final link</a>' : ''}
              <a href="/admin/product?row_id=${escapeHtml(p.row_id)}" target="_blank">JSON</a>
            </div>

            <div class="actions">
              <button onclick="retry('${escapeHtml(p.row_id)}')">Retry</button>
              <button onclick="del('${escapeHtml(p.row_id)}')">Delete</button>
            </div>
          `;
        }

        function retry(id){
          fetch("/retry_row?id=" + encodeURIComponent(id), {method:"POST"})
            .then(load)
            .catch(err => showError(err.message || "Retry failed"));
        }

        function del(id){
          if(!confirm("Delete?")) return;
          fetch("/delete_row?id=" + encodeURIComponent(id), {method:"POST"})
            .then(load)
            .catch(err => showError(err.message || "Delete failed"));
        }

        async function createProduct(event){
          event.preventDefault();

          const imageInput = document.getElementById("image-input");
          const priceInput = document.getElementById("price-input");
          const resultEl = document.getElementById("create-result");

          const file = imageInput.files[0];
          const price = (priceInput.value || "").trim();

          if(!file){
            resultEl.textContent = "Please choose an image file";
            return;
          }

          if(!price){
            resultEl.textContent = "Please enter price";
            return;
          }

          const formData = new FormData();
          formData.append("image", file);
          formData.append("price", price);

          resultEl.textContent = "Creating product...";

          try {
            const response = await fetch("/admin/create_product", {
              method: "POST",
              body: formData
            });

            const data = await response.json();

            if(!response.ok){
              throw new Error(data.message || "Create product failed");
            }

            resultEl.textContent =
              "Created successfully\\n" +
              "row_id: " + (data.row_id || "") + "\\n" +
              "status: " + (data.status || "") + "\\n" +
              "image_url: " + (data.image_url || "");

            imageInput.value = "";
            priceInput.value = "";
            await load();
          } catch (error){
            resultEl.textContent = error.message || "Create product failed";
          }
        }

        async function load(){
          showError("");
          try {
            const response = await fetch("/admin/overview");
            if(!response.ok){
              const text = await response.text();
              throw new Error(text || ("Request failed: " + response.status));
            }

            const d = await response.json();
            DATA = Array.isArray(d) ? d : [];
            buildCat();
            render();

            if(SELECTED){
              const found = DATA.find(x => x.row_id === SELECTED);
              if(found){
                selectRow(SELECTED);
              }
            }
          } catch (error){
            showError(error.message || "Failed to load registry");
          }
        }

        document.getElementById("search").oninput = render;
        document.getElementById("category").onchange = render;
        document.getElementById("status").onchange = render;
        document.getElementById("create-form").addEventListener("submit", createProduct);

        load();
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
