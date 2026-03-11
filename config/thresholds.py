# config/thresholds.py

# If agent confidence drops below this, human input is auto-requested
CONFIDENCE_THRESHOLD = 60

# Per-agent minimum confidence (can be tuned individually)
AGENT_CONFIDENCE_THRESHOLDS = {
    "bank_statement": 65,
    "itr": 60,
    "payslip": 60,
    "cibil": 70,       # CIBIL is critical — higher bar
    "property": 55,    # Property docs vary a lot — more lenient
    "summary": 75,     # Final summary must be reliable
}
