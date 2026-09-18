"""Adlandırılmış, birden fazla profil ve versiyon geçmişi yönetimi.

Farklı sektörler/pozisyonlar için ayrı profiller tutmayı sağlar
(ör. `yazilim`, `saglik`). Her kayıtta önceki hal otomatik olarak
data/profile_history/<isim>/ altına zaman damgalı yedeklenir, böylece
istenirse eski bir sürüme dönülebilir.

CLI araçları (cv_generator, job_search, cover_letter, cv_tailor,
cv_rewrite) zaten `--profile <dosya>` şeklinde doğrudan bir JSON yolu
kabul ediyor; bu modül yalnızca hangi dosyanın hangi profile ait
olduğunu ve geçmişini yönetir — CLI'larda değişiklik gerekmez.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

PROFILES_DIR = Path("data/profiles")
HISTORY_DIR = Path("data/profile_history")
LEGACY_PROFILE_PATH = Path("data/profile.json")
DEFAULT_PROFILE_NAME = "varsayılan"

_SAFE_NAME_RE = re.compile(r"[^\w\-]+", re.UNICODE)


def _safe_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("Profil adı boş olamaz.")
    return _SAFE_NAME_RE.sub("_", name)


def profile_path(name: str) -> Path:
    return PROFILES_DIR / f"{_safe_name(name)}.json"


def ensure_migrated() -> None:
    """Eski tek-profil düzeninden (data/profile.json) yeni çoklu-profil
    düzenine tek seferlik geçiş yapar."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    if not any(PROFILES_DIR.glob("*.json")) and LEGACY_PROFILE_PATH.exists():
        shutil.copy(LEGACY_PROFILE_PATH, profile_path(DEFAULT_PROFILE_NAME))


def list_profiles() -> list[str]:
    ensure_migrated()
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def load_profile_text(name: str) -> str | None:
    path = profile_path(name)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def save_profile(name: str, data: dict) -> None:
    path = profile_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        hist_dir = HISTORY_DIR / _safe_name(name)
        hist_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        shutil.copy(path, hist_dir / f"{stamp}.json")

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_profile(name: str) -> bool:
    path = profile_path(name)
    if not path.exists():
        return False
    path.unlink()
    return True


def list_history(name: str) -> list[str]:
    """Verilen profilin geçmiş sürümlerini, en yeniden en eskiye, zaman
    damgası (dosya adı) olarak döner."""
    hist_dir = HISTORY_DIR / _safe_name(name)
    if not hist_dir.exists():
        return []
    return sorted((p.stem for p in hist_dir.glob("*.json")), reverse=True)


def load_history_text(name: str, stamp: str) -> str | None:
    path = HISTORY_DIR / _safe_name(name) / f"{stamp}.json"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
