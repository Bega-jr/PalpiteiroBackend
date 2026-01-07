from datetime import date
from app.services.supabase_service import get_supabase

# =====================================================
# SERVIÇO DE PALPITES (LEITURA DIRETA DO SUPABASE)
# Conforme Script Unificado 2026
# =====================================================

def obter_palpite_fixo_publico():
    """
    Busca o palpite de índice 0 (Fixo) gerado pelo processamento diário.
    """
    try:
        supabase = get_supabase()
        hoje = date.today().isoformat()
        
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .order("data_referencia", desc=True)
            .limit(1) # No caso do fixo
            .eq("indice_palpite", 0)  # Identificador do Fixo no script unificado
            .execute()
        )

        if not resp.data:
            return None

        registro = resp.data[0]
        return {
            "status": "ok",
            "data_referencia": registro.get("data_referencia"),
            "numeros": registro.get("numeros"),
            "metricas": registro.get("metricas", {})
        }
    except Exception as e:
        print(f"❌ Erro ao ler palpite fixo no Supabase: {e}")
        return None

def obter_palpites_estatisticos_publico():
    """
    Busca os palpites de índice 1 a 10 gerados pelo processamento diário.
    """
    try:
        supabase = get_supabase()
        hoje = date.today().isoformat()
        
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("data_referencia", hoje)
            .gt("indice_palpite", 0)  # Pega apenas os estatísticos (índices > 0)
            .order("indice_palpite")
            .execute()
        )

        if not resp.data:
            return []

        palpites = []
        for r in resp.data:
            palpites.append({
                "indice": r.get("indice_palpite"),
                "numeros": r.get("numeros"),
                "tipo": r.get("tipo"),
                "score": r.get("metricas", {}).get("score", 0.85),
                "soma": r.get("soma_total"),
                "pares": r.get("pares")
            })
        
        return palpites
    except Exception as e:
        print(f"❌ Erro ao ler palpites estatísticos no Supabase: {e}")
        return []
