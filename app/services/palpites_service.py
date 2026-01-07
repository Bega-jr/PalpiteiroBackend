from datetime import date
from app.services.supabase_service import get_supabase

# =====================================================
# SERVIÇO DE PALPITES (LEITURA INTELIGENTE 2026)
# Fonte da verdade: Supabase - Tabela: palpites_validos
# =====================================================

def obter_palpite_fixo_publico():
    """
    Busca o palpite de índice 0 (Fixo) mais recente disponível no banco.
    """
    try:
        supabase = get_supabase()
        
        # Filtra pelo índice do palpite fixo (0) e ordena pela data mais recente
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("indice_palpite", 0)
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        if not resp.data:
            print("⚠️ Nenhum palpite fixo encontrado no banco.")
            return None

        # Como usamos .limit(1), pegamos o primeiro item da lista
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
    Busca os palpites estatísticos (índices 1-10) da última data 
    que possua registros no banco de dados.
    """
    try:
        supabase = get_supabase()
        
        # 1. Busca qual é a data mais recente que possui qualquer palpite
        ultima_data_resp = (
            supabase.table("palpites_validos")
            .select("data_referencia")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
        
        if not ultima_data_resp.data:
            print("⚠️ Nenhum registro de palpite encontrado para determinar a data.")
            return []
            
        ultima_data = ultima_data_resp.data[0]["data_referencia"]
        print(f"📅 Carregando palpites estatísticos da data: {ultima_data}")

        # 2. Busca todos os palpites (exceto o fixo) para essa data específica
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("data_referencia", ultima_data)
            .gt("indice_palpite", 0)  # Índices 1 a 10
            .order("indice_palpite", desc=False)
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
