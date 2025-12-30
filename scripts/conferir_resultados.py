import os
import sys
# Adiciona a raiz ao path para encontrar o módulo app
sys.path.append(os.getcwd())

from app.services.conferencia_service import conferir_jogos_do_dia

if __name__ == "__main__":
    print("Iniciando conferência automática...")
    resultado = conferir_jogos_do_dia()
    print(resultado)
