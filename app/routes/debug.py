from fastapi import APIRouter
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
XLSX = DATA_DIR / "lotofacil.xlsx"
CSV = DATA_DIR / "lotofacil.csv"


@router.get("/debug/data")
def debug_data():
    return {
        "data_dir_exists": DATA_DIR.exists(),
        "xlsx_exists": XLSX.exists(),
        "csv_exists": CSV.exists(),
        "csv_size_bytes": CSV.stat().st_size if CSV.exists() else 0,
        "xlsx_mtime": XLSX.stat().st_mtime if XLSX.exists() else None,
        "csv_mtime": CSV.stat().st_mtime if CSV.exists() else None,
        "cwd": str(Path.cwd())
    }
