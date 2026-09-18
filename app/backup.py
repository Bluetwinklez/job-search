"""Veritabanı ve profil yedekleme / geri yükleme (Backup & Restore) modülü."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any, Dict, List


def create_backup_zip(data_dir: Path = Path("data")) -> bytes:
    """data/ dizinindeki veritabanı, profil ve geçmiş dosyalarını zip arşivine paketler."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if not data_dir.exists():
            return buffer.getvalue()

        # jobs.db
        db_file = data_dir / "jobs.db"
        if db_file.exists() and db_file.is_file():
            zf.write(db_file, arcname="jobs.db")

        # profiles/ klasörü
        profiles_dir = data_dir / "profiles"
        if profiles_dir.exists() and profiles_dir.is_dir():
            for pfile in profiles_dir.glob("*.json"):
                zf.write(pfile, arcname=f"profiles/{pfile.name}")

        # profile_history/ klasörü
        history_dir = data_dir / "profile_history"
        if history_dir.exists() and history_dir.is_dir():
            for hfile in history_dir.rglob("*.json"):
                rel_path = hfile.relative_to(data_dir)
                zf.write(hfile, arcname=str(rel_path).replace("\\", "/"))

        # profile.json (varsa)
        root_profile = data_dir / "profile.json"
        if root_profile.exists() and root_profile.is_file():
            zf.write(root_profile, arcname="profile.json")

    return buffer.getvalue()


def restore_backup_zip(zip_bytes: bytes, target_dir: Path = Path("data")) -> Dict[str, Any]:
    """Zip arşivindeki dosyaları güvenli şekilde target_dir içine geri yükler."""
    if not zip_bytes:
        return {"success": False, "error": "Boş yedek dosyası", "files_restored": []}

    target_dir.mkdir(parents=True, exist_ok=True)
    restored_files: List[str] = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            for member in zf.infolist():
                filename = member.filename
                # Güvenlik kontrolü: Zip Slip / Directory Traversal önleme
                if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
                    continue

                dest_path = target_dir / filename
                if member.is_dir():
                    dest_path.mkdir(parents=True, exist_ok=True)
                    continue

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(dest_path, "wb") as target:
                    target.write(source.read())
                restored_files.append(filename)

        return {
            "success": True,
            "error": None,
            "files_restored": restored_files,
        }
    except zipfile.BadZipFile:
        return {
            "success": False,
            "error": "Geçersiz veya bozuk ZIP dosyası",
            "files_restored": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "files_restored": restored_files,
        }
