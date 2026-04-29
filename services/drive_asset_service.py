import io
import mimetypes
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class DriveAssetService:
    SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    SUPPORTED_VIDEO_EXTENSIONS = {".mp4"}
    DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
    PRODUCT_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

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
        root_folder_id = self._resolve_drive_folder_id()
        product_folder_id = self._ensure_product_folder(
            drive=drive,
            root_folder_id=root_folder_id,
            product_code=normalized_product_code,
        )
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
            parent_folder_id=product_folder_id,
        )

        drive_file_id = str(committed_file.get("id") or "").strip()
        if not drive_file_id:
            raise RuntimeError("Drive upload did not return file id")

        uploaded_file_parent_id = ""
        parents = committed_file.get("parents")
        if isinstance(parents, list) and parents:
            uploaded_file_parent_id = str(parents[0] or "").strip()

        try:
            drive.permissions().create(
                fileId=drive_file_id,
                body={"type": "anyone", "role": "reader"},
                fields="id",
                supportsAllDrives=True,
            ).execute()
        except Exception:
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
            "root_folder_id": root_folder_id,
            "product_folder_id": product_folder_id,
            "uploaded_file_parent_id": uploaded_file_parent_id,
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
        token_file = self._resolve_oauth_token_file()
        if not token_file.exists() or not token_file.is_file():
            raise ValueError(
                "Drive OAuth token is missing. Run local OAuth bootstrap first. "
                f"Expected token file: {token_file}"
            )

        try:
            credentials = Credentials.from_authorized_user_file(
                str(token_file),
                scopes=self.DRIVE_SCOPES,
            )
        except Exception as exc:
            raise ValueError(
                "Drive OAuth token is invalid. Re-run local OAuth bootstrap. "
                f"Token file: {token_file}. Details: {exc}"
            ) from exc

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    token_file.write_text(credentials.to_json(), encoding="utf-8")
                except Exception as exc:
                    raise ValueError(
                        "Drive OAuth token refresh failed. Re-run local OAuth bootstrap. "
                        f"Token file: {token_file}. Details: {exc}"
                    ) from exc
            else:
                raise ValueError(
                    "Drive OAuth token is missing or invalid. Run local OAuth bootstrap first. "
                    f"Expected token file: {token_file}"
                )

        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def _resolve_oauth_token_file(self) -> Path:
        raw_path = str(os.getenv("GOOGLE_DRIVE_OAUTH_TOKEN_FILE", "") or "").strip()
        if raw_path:
            return Path(raw_path)
        return Path("token.drive.oauth.json")

    def _resolve_drive_folder_id(self) -> str:
        value = str(os.getenv("DRIVE_FOLDER_ID", "") or "").strip()
        if not value:
            raise ValueError("DRIVE_FOLDER_ID is missing")
        return value

    def _ensure_product_folder(self, *, drive, root_folder_id: str, product_code: str) -> str:
        safe_product_code = self._sanitize_product_code(product_code)
        escaped_name = safe_product_code.replace("'", "\\'")
        query = (
            f"name = '{escaped_name}' and "
            f"mimeType = '{self.PRODUCT_FOLDER_MIME_TYPE}' and "
            f"'{root_folder_id}' in parents and trashed = false"
        )

        try:
            response = drive.files().list(
                q=query,
                spaces="drive",
                fields="files(id,name,parents)",
                pageSize=1,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
        except Exception as exc:
            raise RuntimeError(
                f"Drive product folder lookup failed inside DRIVE_FOLDER_ID={root_folder_id}: {exc}"
            ) from exc

        files = response.get("files") or []
        if files:
            folder_id = str(files[0].get("id") or "").strip()
            if folder_id:
                return folder_id

        metadata = {
            "name": safe_product_code,
            "mimeType": self.PRODUCT_FOLDER_MIME_TYPE,
            "parents": [root_folder_id],
        }

        try:
            created = drive.files().create(
                body=metadata,
                fields="id,name,parents",
                supportsAllDrives=True,
            ).execute()
        except Exception as exc:
            raise RuntimeError(
                f"Drive product folder creation failed under DRIVE_FOLDER_ID={root_folder_id} for product_code={safe_product_code}: {exc}"
            ) from exc

        folder_id = str(created.get("id") or "").strip()
        if not folder_id:
            raise RuntimeError(
                f"Drive product folder creation did not return folder id for product_code={safe_product_code}"
            )
        return folder_id

    def _sanitize_product_code(self, product_code: str) -> str:
        safe_product_code = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "_"
            for ch in str(product_code or "").strip()
        ).strip("_")
        return safe_product_code or "product"

    def _build_committed_filename(self, *, product_code: str, media_type: str, extension: str) -> str:
        safe_product_code = self._sanitize_product_code(product_code)
        prefix = "primary_video" if media_type == "video" else "primary_image"
        return f"{safe_product_code}__{prefix}__001{extension}"

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

        try:
            return drive.files().create(
                body=metadata,
                media_body=media,
                fields="id,name,mimeType,parents",
                supportsAllDrives=True,
            ).execute()
        except Exception as exc:
            raise RuntimeError(
                f"Drive file upload failed for filename={filename} parent_folder_id={parent_folder_id or 'ROOT'}: {exc}"
            ) from exc

    def _build_preview_url(self, drive_file_id: str) -> str:
        return f"https://drive.google.com/uc?export=view&id={drive_file_id}"

    def _build_drive_url(self, drive_file_id: str) -> str:
        return f"https://drive.google.com/file/d/{drive_file_id}/view?usp=sharing"

    def _fallback_mime_type(self, media_type: str) -> str:
        return "video/mp4" if media_type == "video" else "image/jpeg"
