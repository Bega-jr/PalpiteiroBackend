from babel.numbers import format_currency
from babel.dates import format_date
from datetime import datetime

def format_brl(valor: float) -> str:
    return format_currency(valor, "BRL", locale="pt_BR")

def format_data_br(data) -> str:
    if isinstance(data, str):
        data = datetime.strptime(data, "%d/%m/%Y")
    return format_date(data, format="full", locale="pt_BR")

def format_dezena(n: int) -> str:
    return f"{n:02d}"
