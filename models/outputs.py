from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationStatus(str, Enum):
    APPROVE = "APPROVE"
    CONDITIONAL_APPROVE = "CONDITIONAL_APPROVE"
    REJECT = "REJECT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# -----------------------------------
# Shared confidence mixin
# -----------------------------------
class ConfidenceMixin(BaseModel):
    confidence_score: int = Field(
        description=(
            "Self-rated confidence in this analysis, 0-100. "
            "90-100: All data present and clear. "
            "70-89: Minor gaps but analysis is solid. "
            "50-69: Significant gaps, some assumptions made. "
            "Below 50: Critical data missing, analysis unreliable."
        )
    )
    confidence_reason: str = Field(
        description="1-2 sentences explaining the confidence score — what was missing or unclear."
    )


# -----------------------------------
# Bank Statement Output
# -----------------------------------
class MonthlySalaryEntry(BaseModel):
    month: str
    amount: float


class BankStatementOutput(ConfidenceMixin):
    applicant_name: Optional[str] = None
    account_number_masked: Optional[str] = None
    monthly_salary_credits: List[MonthlySalaryEntry] = Field(default_factory=list)
    average_monthly_balance: Optional[float] = None
    total_monthly_emi_debits: Optional[float] = None
    foir_percentage: Optional[float] = None
    bounced_transactions_count: int = Field(0)
    large_unexplained_credits: List[str] = Field(default_factory=list)
    overdraft_used: bool = Field(False)
    risk_level: RiskLevel
    key_flags: List[str] = Field(default_factory=list)
    summary: str


# -----------------------------------
# ITR Output
# -----------------------------------
class YearlyIncomeEntry(BaseModel):
    assessment_year: str
    gross_income: float
    net_taxable_income: float
    tds_deducted: Optional[float] = None


class ITROutput(ConfidenceMixin):
    applicant_name: Optional[str] = None
    pan_number_masked: Optional[str] = None
    yearly_income: List[YearlyIncomeEntry] = Field(default_factory=list)
    primary_income_source: str
    income_stability: str
    income_matches_bank_credits: Optional[bool] = None
    risk_level: RiskLevel
    key_flags: List[str] = Field(default_factory=list)
    summary: str


# -----------------------------------
# Payslip Output
# -----------------------------------
class PayslipOutput(ConfidenceMixin):
    employer_name: Optional[str] = None
    employee_designation: Optional[str] = None
    gross_monthly_salary: Optional[float] = None
    net_take_home_salary: Optional[float] = None
    pf_deducted: Optional[float] = None
    tds_deducted: Optional[float] = None
    variable_pay_percentage: Optional[float] = None
    salary_consistent_across_months: Optional[bool] = None
    months_analyzed: int = Field(0)
    risk_level: RiskLevel
    key_flags: List[str] = Field(default_factory=list)
    summary: str


# -----------------------------------
# CIBIL Output
# -----------------------------------
class ActiveLoanEntry(BaseModel):
    lender: str
    loan_type: str
    outstanding_amount: Optional[float] = None
    emi_amount: Optional[float] = None
    dpd_history: str


class CIBILOutput(ConfidenceMixin):
    cibil_score: Optional[int] = None
    score_category: Optional[str] = None
    active_loans: List[ActiveLoanEntry] = Field(default_factory=list)
    total_outstanding_debt: Optional[float] = None
    credit_card_utilization_pct: Optional[float] = None
    settled_accounts_count: int = Field(0)
    written_off_accounts_count: int = Field(0)
    hard_inquiries_last_6_months: int = Field(0)
    any_dpd_in_last_12_months: bool = Field(False)
    risk_level: RiskLevel
    key_flags: List[str] = Field(default_factory=list)
    summary: str


# -----------------------------------
# Property Output
# -----------------------------------
class PropertyOutput(ConfidenceMixin):
    property_type: Optional[str] = None
    property_address: Optional[str] = None
    area_sqft: Optional[float] = None
    owner_names: List[str] = Field(default_factory=list)
    registration_number: Optional[str] = None
    registration_date: Optional[str] = None
    rera_registered: Optional[bool] = None
    rera_number: Optional[str] = None
    encumbrance_free: Optional[bool] = None
    declared_value_inr: Optional[float] = None
    estimated_ltv_feasible: Optional[bool] = None
    risk_level: RiskLevel
    key_flags: List[str] = Field(default_factory=list)
    summary: str


# -----------------------------------
# Summary Output
# -----------------------------------
class SummaryOutput(ConfidenceMixin):
    applicant_name: Optional[str] = None
    net_monthly_income: Optional[float] = None
    total_existing_emi: Optional[float] = None
    foir_percentage: Optional[float] = None
    cibil_score: Optional[int] = None
    recommended_max_emi: Optional[float] = None
    positive_factors: List[str] = Field(default_factory=list)
    negative_factors: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    bank_risk: Optional[RiskLevel] = None
    income_risk: Optional[RiskLevel] = None
    credit_risk: Optional[RiskLevel] = None
    property_risk: Optional[RiskLevel] = None
    overall_risk: RiskLevel
    recommendation: RecommendationStatus
    recommendation_justification: str
    conditions: List[str] = Field(default_factory=list)

# Add to models/outputs.py

class ContradictionSeverity(str, Enum):
    LOW = "LOW"        # Minor discrepancy, worth noting
    MEDIUM = "MEDIUM"  # Needs clarification before approval
    HIGH = "HIGH"      # Serious mismatch, likely reject or investigate


class Contradiction(BaseModel):
    field: str = Field(description="What was being compared e.g. 'Monthly Income'")
    agent_a: str = Field(description="First agent name e.g. 'ITR'")
    value_a: str = Field(description="Value reported by agent A")
    agent_b: str = Field(description="Second agent name e.g. 'Bank Statement'")
    value_b: str = Field(description="Value reported by agent B")
    severity: ContradictionSeverity
    explanation: str = Field(description="1-2 sentences explaining the contradiction")


class ValidationReport(ConfidenceMixin):
    contradictions: List[Contradiction] = Field(default_factory=list)
    total_contradictions: int = Field(0)
    high_severity_count: int = Field(0)
    medium_severity_count: int = Field(0)
    low_severity_count: int = Field(0)
    income_consistent: bool = Field(description="Is income consistent across ITR, payslip and bank?")
    emi_consistent: bool = Field(description="Are EMI figures consistent across CIBIL and bank?")
    employer_consistent: bool = Field(description="Is employer consistent across payslip and bank credits?")
    validation_passed: bool = Field(description="True only if zero HIGH severity contradictions found")
    summary: str