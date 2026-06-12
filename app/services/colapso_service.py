import json
from app.services.supabase_service import get_supabase

def detectar_colapso_estrategico():
    print("🧬 [Colapso] Iniciando análise de fadiga de padrões...")
    supabase = get_supabase()
    
    # 1. Busca os metadados das últimas execuções de validação para auditar o comportamento
    try:
        historico_validacao = (
            supabase.table("meta_validacao_execucoes")
            .select("concurso_referencia, status_validacao, alertas")
            .order("concurso_referencia", desc=True)
            .limit(10)
            .execute()
            .data
        )
    except Exception as e:
        print(f"⚠️ Erro ao acessar meta_validacao_execucoes: {e}")
        return False

    if not historico_validacao:
        print("ℹ️ Dados insuficientes em meta_validacao_execucoes para mapear colapso.")
        return True

    # 2. Lógica de detecção: Se houver mais de 3 rejeições seguidas por risco/overlap,
    # indica um colapso iminente da janela de dezenas atual.
    rejeicoes = sum(1 for x in historico_validacao if x["status_validacao"] != "OK")
    print(f"📊 Varredura Concluída: {rejeicoes} anomalias detectadas nos últimos 10 concursos.")

    # 3. Alerta de Colapso Estratégico Contextual
    if rejeicoes >= 4:
        print("🚨 ALERTADO: Tendência latente de colapso de padrões antigos identificada!")
        # Aqui o sistema sinaliza que o mercado mudou bruscamente
        # Em versões futuras, você pode salvar esses IDs em uma tabela de quarentena.
    else:
        print("✅ Estabilidade sistêmica confirmada. Nenhum padrão de elite em colapso.")
        
    return True
