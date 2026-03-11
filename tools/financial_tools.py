from crewai.tools import tool

@tool
def calculate_foir(monthly_income: float, emi: float) -> float:
    """Calculate Fixed Obligation to Income Ratio"""
    if monthly_income == 0:
        return 0
    return round((emi / monthly_income) * 100, 2)

@tool
def average_balance(balances: list) -> float:
    """Calculate average bank balance"""
    if not balances:
        return 0
    return sum(balances) / len(balances)