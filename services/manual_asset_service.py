import os
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional


class ManualAssetService:
    """Local-only manual asset intake.

    - Saves files locally under a structured temp directory
    - Builds read-only refs suitable for ManualAssetsJSON
    - Does not write to Sheets or Drive
    """

    def __init__(self, base_dir: Path, url_builder: Callable[[str], str]):
        self.base_dir = Path(base_dir)
        self.url_builder = url_builder
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _clean(value) -> str:
        return str(value or "").strip()

    def _safe_row_dir(self, row_id: str) -> Path:
        safe_row_id = "".join(ch for ch in self._clean(row_id) if ch.isalnum() or ch in {"-", "_"})
        safe_row_id = safe_row_id or "row"
        row_dir = self.base_dir / safe_row_id
        row_dir.mkdir(parents=True, exist_ok=True)
        return row_dir

    def _save_bytes_atomic(self, row_dir: Path, original_filename: str, file_bytes: bytes) -> Dict[str, str]:
        if not file_bytes:
            raise ValueError("Empty file payload")

        extension = Path(self._clean(original_filename)).suffix.lower()
        if not extension:
            raise ValueError("Missing file extension")

        final_name = f"{uuid.uuid4().hex}{extension}"
        temp_name = f".{final_name}.tmp"

        temp_path = row_dir / temp_name
        final_path = row_dir / final_name

        try:
            with open(temp_path, "wb") as fh:
                fh.write(file_bytes)
                fh.flush()
                os.fsync(fh.fileno())

            os.replace(temp_path, final_path)

            if not final_path.exists() or not final_path.is_file():
                raise RuntimeError("Manual asset file was not saved")

            if final_path.stat().st_size <= 0:
                raise RuntimeError("Manual asset file is empty after save")

            relative_path = f"{row_dir.name}/{final_name}"
            return {
                "final_path": str(final_path),
                "relative_path": relative_path,
                "url": self.url_builder(relative_path),
            }
        except Exception:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            try:
                if final_path.exists():
                    final_path.unlink()
            except Exception:
                pass
            raise

    def _count_existing_type(self, existing_assets: List[dict], asset_type: str) -> int:
        count = 0
        for item in existing_assets or []:
            if not isinstance(item, dict):
                continue
            if self._clean(item.get("type")).lower() == asset_type.lower():
                count += 1
        return count

    def save_assets(
        self,
        *,
        row_id: str,
        images: List[dict],
        video: Optional[dict] = None,
        existing_assets: Optional[List[dict]] = None,
    ) -> List[dict]:
        existing_assets = existing_assets or []
        row_dir = self._safe_row_dir(row_id)
        saved_assets: List[dict] = []

        image_start_index = self._count_existing_type(existing_assets, "image") + 1
        created_paths: List[str] = []

        try:
            for offset, image in enumerate(images or [], start=0):
                saved = self._save_bytes_atomic(
                    row_dir=row_dir,
                    original_filename=image["filename"],
                    file_bytes=image["bytes"],
                )
                created_paths.append(saved["final_path"])
                image_index = image_start_index + offset
                saved_assets.append({
                    "source_family": "manual",
                    "source_name": "manual",
                    "source_tag": "manual_ref",
                    "type": "image",
                    "role": "additional",
                    "priority": 3,
                    "rank": 300 + image_index,
                    "url": saved["url"],
                    "label": f"Manual Image {image_index}",
                    "relative_path": saved["relative_path"],
                    "size_bytes": image.get("size_bytes", 0),
                })

            if video:
                saved = self._save_bytes_atomic(
                    row_dir=row_dir,
                    original_filename=video["filename"],
                    file_bytes=video["bytes"],
                )
                created_paths.append(saved["final_path"])
                saved_assets.append({
                    "source_family": "manual",
                    "source_name": "manual",
                    "source_tag": "manual_ref",
                    "type": "video",
                    "role": "video",
                    "priority": 2,
                    "rank": 250,
                    "url": saved["url"],
                    "label": "Manual Video",
                    "relative_path": saved["relative_path"],
                    "size_bytes": video.get("size_bytes", 0),
                })

            return saved_assets
        except Exception:
            self.cleanup_saved_assets(saved_assets)
            raise

    def cleanup_saved_assets(self, saved_assets: List[dict]) -> None:
        for asset in saved_assets or []:
            if not isinstance(asset, dict):
                continue
            relative_path = self._clean(asset.get("relative_path"))
            if not relative_path:
                continue
            file_path = self.base_dir / relative_path
            try:
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
            except Exception:
                pass
