from crewai import Task
from models.outputs import (
    BankStatementOutput, ITROutput, PayslipOutput,
    CIBILOutput, PropertyOutput, SummaryOutput,
)


def create_tasks(agents: dict) -> dict:
    """
    Create and return a fresh dict of Task instances bound to the given agents.
    Called per-run so each concurrent crew gets its own independent task objects.
    """

    bank_task = Task(
        description="""
Analyze the following bank statement document(s):

{bank_statement_docs}

Extract and report:
1. Monthly salary credit amounts and dates (last 6 months)
2. Average monthly balance
3. Total EMI/loan debits per month
4. FOIR calculation: (Total monthly fixed obligations / Net monthly income) × 100
5. Any bounced/returned transactions
6. Large unexplained cash deposits (>50% of salary)
7. Overdraft usage

If salary credits are inconsistent or EMI amounts are unclear, use the
ask_human tool to get clarification.

Use web_search to verify current RBI guidelines on acceptable FOIR limits
for home loans vs personal loans.

CONFIDENCE SCORING (mandatory):
Rate your confidence_score from 0-100 based on:
- Were all expected fields found in the document? (+points)
- Was the document legible and complete? (+points)
- Did you have to make assumptions due to missing data? (-points)
- Were there contradictions within the document? (-points)

Also write a confidence_reason explaining the score in 1-2 sentences.
If your confidence is below 60, explicitly note what information
would be needed to improve it.
""",
        agent=agents["bank"],
        expected_output="""
A detailed bank statement analysis report in markdown format covering:
- Income analysis table (month-wise salary credits)
- Balance analysis
- EMI obligations list
- FOIR calculation
- Red flags (if any)
- Summary verdict on financial health
""",
        output_pydantic=BankStatementOutput,
    )

    itr_task = Task(
        description="""
Analyze the following ITR (Income Tax Return) document(s):

{itr_docs}

Extract and report:
1. Assessment years covered
2. Gross total income per year
3. Net taxable income after deductions (80C, 80D, etc.)
4. Income sources breakdown (salary, business, rental, capital gains)
5. TDS deducted vs. tax paid (compliance check)
6. Income growth trend year-on-year
7. Any inconsistency with declared salary

Use ask_human if Assessment Year or income figures are unclear.
Use web_search to verify ITR income thresholds for different loan types.

CONFIDENCE SCORING (mandatory):
Rate your confidence_score from 0-100 based on:
- Were all expected fields found in the document? (+points)
- Was the document legible and complete? (+points)
- Did you have to make assumptions due to missing data? (-points)
- Were there contradictions within the document? (-points)

Also write a confidence_reason explaining the score in 1-2 sentences.
If your confidence is below 60, explicitly note what information
would be needed to improve it.
""",
        agent=agents["itr"],
        expected_output="""
An ITR analysis report covering:
- Year-wise income table
- Income source breakdown
- Tax compliance assessment
- Income stability verdict
- Flags for inconsistencies
""",
        output_pydantic=ITROutput,
    )

    payslip_task = Task(
        description="""
Analyze the following payslip document(s):

{payslip_docs}

Extract and report:
1. Employer name, employee ID, designation
2. Gross salary components (basic, HRA, allowances)
3. Deductions (PF, ESI, TDS, professional tax)
4. Net take-home salary per month
5. Consistency across multiple months
6. Variable pay percentage vs. fixed salary
7. Cross-check net salary against bank credits

Use ask_human if employer name or salary components are illegible.
Use web_search to verify employer legitimacy or look up industry benchmarks.

CONFIDENCE SCORING (mandatory):
Rate your confidence_score from 0-100 based on:
- Were all expected fields found in the document? (+points)
- Was the document legible and complete? (+points)
- Did you have to make assumptions due to missing data? (-points)
- Were there contradictions within the document? (-points)

Also write a confidence_reason explaining the score in 1-2 sentences.
If your confidence is below 60, explicitly note what information
would be needed to improve it.
""",
        agent=agents["payslip"],
        expected_output="""
A payslip analysis report covering:
- Salary breakdown table
- Employer verification notes
- Month-wise consistency check
- Take-home salary confirmation
- Anomaly flags
""",
        output_pydantic=PayslipOutput,
    )

    credit_task = Task(
        description="""
Analyze the following CIBIL/credit report document(s):

{cibil_docs}

Extract and report:
1. CIBIL score (flag if < 700 as risky, < 650 as high-risk)
2. All active credit accounts with outstanding balances
3. DPD (Days Past Due) history — any 30+/60+/90+ DPD entries
4. Credit card utilization ratio
5. Settled, written-off, or suit-filed accounts
6. Number of hard inquiries in last 6 months
7. Total credit exposure vs. declared income

Use web_search to look up minimum CIBIL score requirements for home/personal/auto loans
from major Indian banks (SBI, HDFC, ICICI).
Use ask_human if account numbers or DPD values are unclear.

CONFIDENCE SCORING (mandatory):
Rate your confidence_score from 0-100 based on:
- Were all expected fields found in the document? (+points)
- Was the document legible and complete? (+points)
- Did you have to make assumptions due to missing data? (-points)
- Were there contradictions within the document? (-points)

Also write a confidence_reason explaining the score in 1-2 sentences.
If your confidence is below 60, explicitly note what information
would be needed to improve it.
""",
        agent=agents["cibil"],
        expected_output="""
A credit risk report covering:
- CIBIL score with risk classification
- Active loans table
- DPD history
- Negative marks (settled/written-off)
- Inquiry analysis
- Overall creditworthiness verdict
""",
        output_pydantic=CIBILOutput,
    )

    property_task = Task(
        description="""
Analyze the following property document(s):

{property_docs}

Extract and report:
1. Property type (residential/commercial/land)
2. Property address and area (sq ft / sq m)
3. Owner name(s) and title chain
4. Registration details (date, registration number, sub-registrar office)
5. Any encumbrances or existing mortgages mentioned
6. RERA registration number (if applicable)
7. Estimated or declared property value
8. Loan-to-Value (LTV) feasibility based on value

If no property documents are provided, note "No property documents provided."
Use web_search to verify RERA registration or local stamp duty rates if needed.
Use ask_human for missing registration numbers or unclear ownership details.

CONFIDENCE SCORING (mandatory):
Rate your confidence_score from 0-100 based on:
- Were all expected fields found in the document? (+points)
- Was the document legible and complete? (+points)
- Did you have to make assumptions due to missing data? (-points)
- Were there contradictions within the document? (-points)

Also write a confidence_reason explaining the score in 1-2 sentences.
If your confidence is below 60, explicitly note what information
would be needed to improve it.
""",
        agent=agents["property"],
        expected_output="""
A property analysis report covering:
- Property details summary
- Title and ownership verification
- Encumbrance status
- LTV analysis
- Legal compliance flags
- Overall property suitability verdict
""",
        output_pydantic=PropertyOutput,
    )

    summary_task = Task(
        description="""
You have access to the complete analyses from all specialist agents:

BANK STATEMENT ANALYSIS:
{bank_analysis}

ITR ANALYSIS:
{itr_analysis}

PAYSLIP ANALYSIS:
{payslip_analysis}

CIBIL ANALYSIS:
{cibil_analysis}

PROPERTY ANALYSIS:
{property_analysis}

Create a comprehensive loan underwriting summary that includes:

## ✅ Positive Factors
List all strong points (high CIBIL, stable income, low FOIR, clear title, etc.)

## ❌ Negative Factors
List all weak points (low score, high FOIR, bounced cheques, DPD history, etc.)

## ⚠️ Risk Flags
List items needing further verification or monitoring

## 📊 Key Metrics Summary
| Metric | Value | Benchmark | Status |
|--------|-------|-----------|--------|
| CIBIL Score | X | ≥700 | ✅/❌ |
| FOIR | X% | ≤50% | ✅/❌ |
| Net Monthly Income | ₹X | - | - |
| Total EMI (existing) | ₹X | - | - |
| Proposed EMI capacity | ₹X | - | - |

## 🏦 Final Recommendation
APPROVE / CONDITIONAL APPROVE / REJECT

CONFIDENCE SCORING (mandatory):
Rate your confidence_score from 0-100 based on:
- Were all expected fields found in the document? (+points)
- Was the document legible and complete? (+points)
- Did you have to make assumptions due to missing data? (-points)
- Were there contradictions within the document? (-points)

Also write a confidence_reason explaining the score in 1-2 sentences.
If your confidence is below 60, explicitly note what information
would be needed to improve it.

Justification (3-5 sentences)

Use web_search to verify current lending guidelines if needed.
""",
        agent=agents["summary"],
        expected_output="""
A comprehensive loan underwriting decision report with:
- Structured positives and negatives
- Key metrics table
- Risk flags
- Clear final recommendation with justification
""",
        output_pydantic=SummaryOutput,
    )

    report_task = Task(
        description="""
Compile the complete final loan analysis report in professional markdown format.

Use all the analyses and the summary provided:

INDIVIDUAL ANALYSES:
{bank_analysis}
{itr_analysis}
{payslip_analysis}
{cibil_analysis}
{property_analysis}

CONCLUSIVE SUMMARY:
{summary_analysis}

Structure the final report as:

# 🏦 Loan Application Analysis Report
**Generated:** [date]
**Applicant:** [name if found, else "As per documents"]

---

## 1. 📄 Bank Statement Analysis
[bank analysis content]

---

## 2. 💼 ITR Analysis
[ITR analysis content]

---

## 3. 💰 Payslip Analysis
[payslip analysis content]

---

## 4. 📊 CIBIL / Credit Analysis
[credit analysis content]

---

## 5. 🏠 Property Analysis
[property analysis content]

---

## 6. 🔍 Consolidated Summary & Recommendation
[summary content]

---

*This report was generated by an AI-assisted loan underwriting system.
Final lending decisions must be reviewed and approved by a qualified
credit officer as per RBI guidelines.*
""",
        agent=agents["report"],
        expected_output="Complete formatted markdown loan analysis report",
    )

    return {
        "bank_statement": bank_task,
        "itr": itr_task,
        "payslip": payslip_task,
        "cibil": credit_task,
        "property": property_task,
        "summary": summary_task,
        "report": report_task,
    }
