from app.services.conferencia_service import conferir_jogos_do_dia
import os

if __name__ == "__main__":
    print("Iniciando conferência de jogos...")
    resultado = conferir_jogos_do_dia()
    print(resultado)
