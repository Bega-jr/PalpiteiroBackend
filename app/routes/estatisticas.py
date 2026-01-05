from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

def safe_float(valor, default=0.0):
    """Converte valores do banco (que podem ser string) para float com segurança."""
    try:
        if valor is None: return default
        return float(valor)
    except (ValueError, TypeError):
        return default

@router.get("/")
def get_estatisticas():
    hoje = date.today().isoformat()

    try:
        # 1. Busca estatísticas por número
        response_numeros = (
            supabase.table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .eq("data_referencia", hoje)
            .execute()
        )

        numeros = response_numeros.data or []

        if not numeros:
            # Fallback para o último dia disponível (limit 25 para pegar os 25 números)
            fallback = (
                supabase.table("estatisticas_numeros")
                .select("numero, frequencia, atraso, score, data_referencia")
                .order("data_referencia", desc=True)
                .limit(25)
                .execute()
            )
            numeros = fallback.data or []
            if numeros:
                hoje = numeros[0].get("data_referencia", hoje)

        # 2. Busca resumo diário
        # .single() pode gerar erro se não achar nada, usamos .limit(1) para segurança
        response_diario = (
            supabase.table("estatisticas_diarias_v2")
            .select("*")
            .eq("data_referencia", hoje)
            .limit(1)
            .execute()
        )

        # Se não houver dados de hoje, tenta pegar o último registro disponível
        if not response_diario.data:
            response_diario = (
                supabase.table("estatisticas_diarias_v2")
                .select("*")
                .order("data_referencia", desc=True)
                .limit(1)
                .execute()
            )

        diario = response_diario.data[0] if response_diario.data else {}

        # 3. Tratamento de listas (numeros_atrasados pode vir como string ou lista)
        faltam = diario.get("numeros_atrasados", [])
        if isinstance(faltam, str): # Caso o banco retorne como string por erro de tipo
            import json
            try: faltam = json.loads(faltam)
            except: faltam = []

        return {
            "estatisticas": numeros,
            "analise": {
                # Usamos safe_float porque seu banco está salvando números como strings
                "soma_media": round(safe_float(diario.get("media_soma")), 2),
                "pares_media": round(safe_float(diario.get("media_pares"), 7.2), 2),
                "impares_media": round(safe_float(diario.get("media_impares"), 7.8), 2),
                "primos_media": round(safe_float(diario.get("media_primos")), 2),
                "data_referencia": hoje,
            },
            "ciclo": {
                "faltam": faltam if faltam else diario.get("numeros_frios", []),
                "total_faltam": len(faltam) if faltam else len(diario.get("numeros_frios", [])),
            },
        }

    except Exception as e:
        print(f"❌ Erro no endpoint /estatisticas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
