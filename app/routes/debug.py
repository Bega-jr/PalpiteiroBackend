from fastapi import APIRouter
from pathlib import Path
import os
from datetime import date
from app.core.supabase import supabase

router = APIRouter(prefix="/debug", tags=["Debug"])

# ============================================================
# 1️⃣ DEBUG DE AMBIENTE (ENV / SUPABASE)
# ============================================================

@router.get("/env")
def debug_env():
    return {
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_KEY": bool(os.getenv("SUPABASE_KEY")),
        "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "não definido"),
    }


# ============================================================
# 2️⃣ DEBUG DE FILESYSTEM / DATA
# ============================================================

@router.get("/data")
def debug_data():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    csv = data_dir / "lotofacil.csv"
    xlsx = data_dir / "lotofacil.xlsx"

    return {
        "base_dir": str(base_dir),
        "cwd": str(Path.cwd()),
        "data_dir_exists": data_dir.exists(),
        "csv_exists": csv.exists(),
        "xlsx_exists": xlsx.exists(),
        "csv_size_bytes": csv.stat().st_size if csv.exists() else 0,
        "csv_mtime": csv.stat().st_mtime if csv.exists() else None,
        "xlsx_mtime": xlsx.stat().st_mtime if xlsx.exists() else None,
    }


# ============================================================
# 3️⃣ DEBUG DE CONEXÃO COM SUPABASE
# ============================================================

@router.get("/supabase")
def debug_supabase():
    try:
        resp = supabase.table("estatisticas_numeros") \
            .select("numero") \
            .limit(1) \
            .execute()

        return {
            "status": "ok",
            "rows_returned": len(resp.data),
            "erro": None
        }

    except Exception as e:
        return {
            "status": "erro",
            "rows_returned": 0,
            "erro": str(e)
        }


# ============================================================
# 4️⃣ DEBUG DE DADOS ATUAIS (ESTATÍSTICAS)
# ============================================================

@router.get("/estatisticas")
def debug_estatisticas():
    hoje = date.today().isoformat()

    try:
        numeros = supabase.table("estatisticas_numeros") \
            .select("numero, frequencia, atraso, score, data_referencia") \
            .order("data_referencia", desc=True) \
            .limit(5) \
            .execute().data

        diaria = supabase.table("estatisticas_diarias_v2") \
            .select("*") \
            .order("data_referencia", desc=True) \
            .limit(1) \
            .execute().data

        return {
            "status": "ok",
            "estatisticas_numeros_exemplo": numeros,
            "estatisticas_diarias_exemplo": diaria
        }

    except Exception as e:
        return {
            "status": "erro",
            "erro": str(e)
        }


# ============================================================
# 5️⃣ DEBUG GERAL (RESUMO ÚNICO)
# ============================================================

@router.get("/full")
def debug_full():
    return {
        "env": debug_env(),
        "data": debug_data(),
        "supabase": debug_supabase(),
        "estatisticas": debug_estatisticas()
    }
