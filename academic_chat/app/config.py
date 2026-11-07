import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    # Windows desktop processes can predate a user-level environment change.
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
                if value:
                    return str(value)
        except (OSError, ImportError):
            pass
    return default


def db_path() -> Path:
    return Path(setting("ACADEMIC_DB_PATH", str(DATA / "academic.db")))


def chroma_path() -> str:
    return setting("CHROMA_PATH", str(DATA / "chroma"))


def threshold() -> float:
    value = float(setting("VECTOR_SCORE_THRESHOLD", "0.38"))
    if not 0 <= value <= 1:
        raise ValueError("VECTOR_SCORE_THRESHOLD must be between 0 and 1")
    return value
