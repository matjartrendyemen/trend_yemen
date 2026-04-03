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
      <title>Admin Registry</title>
      <style>
        body { font-family: Arial; padding:20px; background:#f5f5f5; }
        .toolbar { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px; }
        input, select, button { padding:8px; border-radius:6px; border:1px solid #ccc; }

        .list { background:#fff; border-radius:8px; border:1px solid #ddd; }
        .row {
          display:flex; gap:10px; align-items:center;
          padding:8px; border-bottom:1px solid #eee;
          cursor:pointer;
        }
        .row:hover { background:#f0f0f0; }
        .row.selected { background:#dbe9ff; }

        .thumb { width:40px; height:40px; object-fit:cover; border-radius:6px; border:1px solid #ccc; }

        .details {
          margin-top:15px; background:#fff;
          border:1px solid #ddd; border-radius:8px;
          padding:12px;
        }
      </style>
    </head>
    <body>

      <div class="toolbar">
        <input id="search" placeholder="Search"/>
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

      <div id="list" class="list"></div>
      <div id="details" class="details" style="display:none;"></div>

      <script>
        let DATA=[], SELECTED=null, SHOW_ALL=false;

        function norm(u){
          if(!u) return "";
          let m=u.match(/id=([a-zA-Z0-9_-]+)/);
          return m ? "https://drive.google.com/uc?export=view&id="+m[1] : u;
        }

        function load(){
          fetch("/admin/overview").then(r=>r.json()).then(d=>{
            DATA=d;
            buildCat();
            render();
          });
        }

        function buildCat(){
          let cats=[...new Set(DATA.map(x=>x.category_id).filter(Boolean))];
          let el=document.getElementById("category");
          el.innerHTML="<option value=''>All</option>"+cats.map(c=>"<option>"+c+"</option>").join("");
        }

        function toggleAll(){ SHOW_ALL=!SHOW_ALL; render(); }

        function render(){
          let s=document.getElementById("search").value.toLowerCase();
          let c=document.getElementById("category").value;
          let st=document.getElementById("status").value;

          let list=DATA.filter(p=>{
            if(s && !(p.product_name||"").toLowerCase().includes(s)) return false;
            if(c && p.category_id!==c) return false;
            if(st && p.processing_status!==st) return false;
            return true;
          });

          if(!SHOW_ALL) list=list.slice(0,50);

          document.getElementById("list").innerHTML = list.map(p=>`
            <div class="row ${SELECTED===p.row_id?"selected":""}" onclick="selectRow('${p.row_id}')">
              <img class="thumb" src="${norm(p.source_image_url)}"/>
              <div>${p.product_name||"—"}</div>
              <div>${p.category_id||"—"}</div>
              <div>${p.processing_status||"—"}</div>
              <div>${(p.readiness||{}).status||"—"}</div>
              <div>${p.row_id}</div>
            </div>
          `).join("");
        }

        function selectRow(id){
          SELECTED=id; render();
          let p=DATA.find(x=>x.row_id===id);
          if(!p) return;

          document.getElementById("details").style.display="block";
          document.getElementById("details").innerHTML=`
            <h3>${p.product_name}</h3>
            <div>Row: ${p.row_id}</div>
            <div>Status: ${p.processing_status}</div>
            <div>Category: ${p.category_id}</div>
            <div>Readiness: ${(p.readiness||{}).status}</div>
            <div>Error: ${p.error_message||"—"}</div>
            <div>Missing: ${(p.smart_encoding_inputs?.missing_fields||[]).join(", ")}</div>
            <div>
              <a href="${p.source_image_url}" target="_blank">Source</a> |
              <a href="${p.final_image_url}" target="_blank">Final</a> |
              <a href="/admin/product?row_id=${p.row_id}" target="_blank">JSON</a>
            </div>
            <div>
              <button onclick="retry('${p.row_id}')">Retry</button>
              <button onclick="del('${p.row_id}')">Delete</button>
            </div>
          `;
        }

        function retry(id){ fetch("/retry_row?id="+id,{method:"POST"}).then(load); }
        function del(id){
          if(!confirm("Delete?")) return;
          fetch("/delete_row?id="+id,{method:"POST"}).then(load);
        }

        document.getElementById("search").oninput=render;
        document.getElementById("category").onchange=render;
        document.getElementById("status").onchange=render;

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
