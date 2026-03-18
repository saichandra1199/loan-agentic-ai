"""Tests for tools/financial_tools.py — FOIR and balance calculations."""
import pytest
from tools.financial_tools import calculate_foir, average_balance


# ---------------------------------------------------------------------------
# calculate_foir
# ---------------------------------------------------------------------------

class TestCalculateFoir:
    def test_standard_case(self):
        result = calculate_foir.func(monthly_income=100000.0, emi=40000.0)
        assert result == 40.0

    def test_zero_income_returns_zero(self):
        """Guard against division-by-zero."""
        result = calculate_foir.func(monthly_income=0.0, emi=5000.0)
        assert result == 0

    def test_zero_emi(self):
        result = calculate_foir.func(monthly_income=100000.0, emi=0.0)
        assert result == 0.0

    def test_rounds_to_two_decimal_places(self):
        result = calculate_foir.func(monthly_income=132000.0, emi=33500.0)
        expected = round((33500 / 132000) * 100, 2)
        assert result == expected

    def test_foir_above_50_percent(self):
        """High FOIR — should still compute correctly, flagging is done elsewhere."""
        result = calculate_foir.func(monthly_income=80000.0, emi=50000.0)
        assert result == round((50000 / 80000) * 100, 2)

    def test_full_income_as_emi(self):
        result = calculate_foir.func(monthly_income=50000.0, emi=50000.0)
        assert result == 100.0

    def test_income_less_than_emi(self):
        """FOIR > 100 is theoretically possible with multiple loans."""
        result = calculate_foir.func(monthly_income=30000.0, emi=40000.0)
        assert result > 100.0


# ---------------------------------------------------------------------------
# average_balance
# ---------------------------------------------------------------------------

class TestAverageBalance:
    def test_standard_case(self):
        result = average_balance.func(balances=[100000.0, 200000.0, 300000.0])
        assert result == 200000.0

    def test_empty_list_returns_zero(self):
        result = average_balance.func(balances=[])
        assert result == 0

    def test_single_value(self):
        result = average_balance.func(balances=[75000.0])
        assert result == 75000.0

    def test_mixed_values(self):
        result = average_balance.func(balances=[50000.0, 60000.0, 40000.0])
        assert result == pytest.approx(50000.0)

    def test_large_balances(self):
        result = average_balance.func(balances=[1_000_000.0, 2_000_000.0])
        assert result == 1_500_000.0
