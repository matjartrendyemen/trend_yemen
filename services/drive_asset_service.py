import io
import json
import mimetypes
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class DriveAssetService:
    SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    SUPPORTED_VIDEO_EXTENSIONS = {".mp4"}

    def __init__(self, seed_base_dir: str | Path):
        self.seed_base_dir = Path(seed_base_dir)

    def commit_primary_asset(
        self,
        *,
        row_id: str,
        product_code: str,
        media_url: str,
        media_type: str,
        source_family: str = "",
        source_name: str = "",
        source_tag: str = "",
    ) -> Dict[str, Any]:
        normalized_row_id = str(row_id or "").strip()
        normalized_product_code = str(product_code or "").strip() or normalized_row_id
        normalized_media_url = str(media_url or "").strip()
        normalized_media_type = str(media_type or "").strip().lower() or "image"

        if not normalized_row_id:
            raise ValueError("Missing row_id")

        if not normalized_media_url:
            raise ValueError("Missing final media URL")

        if normalized_media_type not in {"image", "video"}:
            raise ValueError("Unsupported media type for commit")

        source_bytes, source_filename, mime_type = self._read_source_bytes(
            media_url=normalized_media_url,
            media_type=normalized_media_type,
        )

        extension = Path(source_filename).suffix.lower()
        if normalized_media_type == "image" and extension not in self.SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError("Unsupported image asset for commit")
        if normalized_media_type == "video" and extension not in self.SUPPORTED_VIDEO_EXTENSIONS:
            raise ValueError("Unsupported video asset for commit")

        drive = self._build_drive_client()
        folder_id = self._resolve_drive_folder_id()
        committed_filename = self._build_committed_filename(
            product_code=normalized_product_code,
            media_type=normalized_media_type,
            extension=extension,
        )
        committed_file = self._upload_bytes_to_drive(
            drive=drive,
            filename=committed_filename,
            mime_type=mime_type,
            content=source_bytes,
            parent_folder_id=folder_id,
        )

        drive_file_id = str(committed_file.get("id") or "").strip()
        if not drive_file_id:
            raise RuntimeError("Drive upload did not return file id")

        try:
            drive.permissions().create(
                fileId=drive_file_id,
                body={"type": "anyone", "role": "reader"},
                fields="id",
            ).execute()
        except Exception:
            # Permission failures should not corrupt ownership writes.
            # Preview/open may still work if the Drive defaults are already permissive.
            pass

        role = "primary_video" if normalized_media_type == "video" else "primary_image"
        preview_url = self._build_preview_url(drive_file_id)
        drive_url = self._build_drive_url(drive_file_id)

        owned_asset_entry = {
            "asset_id": uuid.uuid4().hex,
            "product_code": normalized_product_code,
            "kind": normalized_media_type,
            "role": role,
            "source_family": str(source_family or "").strip() or "unknown",
            "source_name": str(source_name or "").strip() or "unknown",
            "source_tag": str(source_tag or "").strip() or "unknown_source",
            "original_url": normalized_media_url,
            "storage_status": "committed",
            "drive_file_id": drive_file_id,
            "drive_url": drive_url,
            "preview_url": preview_url,
            "mime_type": mime_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }

        return {
            "asset_id": owned_asset_entry["asset_id"],
            "owned_asset_entry": owned_asset_entry,
            "drive_file_id": drive_file_id,
            "drive_url": drive_url,
            "preview_url": preview_url,
            "mime_type": mime_type,
            "kind": normalized_media_type,
            "role": role,
            "filename": committed_filename,
        }

    def _read_source_bytes(self, *, media_url: str, media_type: str) -> tuple[bytes, str, str]:
        local_path = self._resolve_local_path_from_url(media_url)
        if local_path:
            if not local_path.exists() or not local_path.is_file():
                raise ValueError("Local asset file not found for commit")

            file_bytes = local_path.read_bytes()
            if not file_bytes:
                raise ValueError("Local asset file is empty")

            filename = local_path.name
            mime_type = mimetypes.guess_type(filename)[0] or self._fallback_mime_type(media_type)
            return file_bytes, filename, mime_type

        request = urllib.request.Request(
            media_url,
            headers={
                "User-Agent": "TrendYemenAssetOwnership/1.0",
            },
        )

        with urllib.request.urlopen(request, timeout=25) as response:
            file_bytes = response.read()
            if not file_bytes:
                raise ValueError("Downloaded asset is empty")

            content_type = str(response.headers.get("Content-Type") or "").split(";")[0].strip()
            filename = self._infer_filename_from_url(media_url, media_type)
            mime_type = content_type or mimetypes.guess_type(filename)[0] or self._fallback_mime_type(media_type)
            return file_bytes, filename, mime_type

    def _resolve_local_path_from_url(self, media_url: str) -> Path | None:
        parsed = urllib.parse.urlparse(str(media_url or "").strip())
        path = parsed.path or ""

        marker = "/admin/seed_image/"
        if marker not in path:
            return None

        relative_part = path.split(marker, 1)[1]
        relative_part = urllib.parse.unquote(relative_part).lstrip("/")
        if not relative_part:
            return None

        candidate = (self.seed_base_dir / relative_part).resolve()
        seed_root = self.seed_base_dir.resolve()

        try:
            candidate.relative_to(seed_root)
        except Exception:
            return None

        return candidate

    def _infer_filename_from_url(self, media_url: str, media_type: str) -> str:
        parsed = urllib.parse.urlparse(str(media_url or "").strip())
        path = urllib.parse.unquote(parsed.path or "")
        filename = Path(path).name.strip()

        if filename and Path(filename).suffix:
            return filename

        extension = ".mp4" if media_type == "video" else ".jpg"
        return f"asset{extension}"

    def _build_drive_client(self):
        creds_raw = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_raw:
            raise ValueError("GOOGLE_CREDENTIALS is missing")

        credentials_info = json.loads(creds_raw)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def _resolve_drive_folder_id(self) -> str:
        for env_name in (
            "OWNED_ASSETS_DRIVE_FOLDER_ID",
            "GOOGLE_DRIVE_FOLDER_ID",
            "DRIVE_FOLDER_ID",
        ):
            value = str(os.getenv(env_name, "") or "").strip()
            if value:
                return value
        return ""

    def _build_committed_filename(self, *, product_code: str, media_type: str, extension: str) -> str:
        safe_product_code = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "_"
            for ch in str(product_code or "").strip()
        ).strip("_") or "product"
        prefix = "primary-video" if media_type == "video" else "primary-image"
        return f"{safe_product_code}__{prefix}{extension}"

    def _upload_bytes_to_drive(
        self,
        *,
        drive,
        filename: str,
        mime_type: str,
        content: bytes,
        parent_folder_id: str = "",
    ) -> Dict[str, Any]:
        metadata = {"name": filename}
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]

        media = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype=mime_type,
            resumable=False,
        )

        return drive.files().create(
            body=metadata,
            media_body=media,
            fields="id,name,mimeType",
            supportsAllDrives=True,
        ).execute()

    def _build_preview_url(self, drive_file_id: str) -> str:
        return f"https://drive.google.com/uc?export=view&id={drive_file_id}"

    def _build_drive_url(self, drive_file_id: str) -> str:
        return f"https://drive.google.com/file/d/{drive_file_id}/view?usp=sharing"

    def _fallback_mime_type(self, media_type: str) -> str:
        return "video/mp4" if media_type == "video" else "image/jpeg"
