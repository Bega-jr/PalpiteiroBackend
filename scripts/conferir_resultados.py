import os
import sys
import time

# Adiciona o diretório atual ao sys.path para garantir que o módulo 'app' seja encontrado
sys.path.append(os.getcwd())

from app.services.conferencia_service import conferir_jogos_do_dia

def executar_conferencia():
    print("="*50)
    print(f"INICIANDO CONFERÊNCIA AUTOMÁTICA - {time.strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*50)
    
    try:
        # Chama a função que ajustamos: ela buscará o concurso 3585 (ou o mais recente)
        # na tabela lotofacil_concursos e conferirá os palpites_validos.
        resultado = conferir_jogos_do_dia()
        
        print(f"\n[STATUS]: {resultado}")
        
    except Exception as e:
        print(f"\n[ERRO CRÍTICO]: Falha ao executar a conferência: {str(e)}")
        # Log de erro adicional pode ser inserido aqui
        
    print("\n" + "="*50)
    print("PROCESSO FINALIZADO.")

if __name__ == "__main__":
    executar_conferencia()
