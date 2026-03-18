import os
from crewai import Agent, LLM
from dotenv import load_dotenv
from tools.search_tool import web_search
from tools.human_input_tool import ask_human

load_dotenv()


def _make_llm() -> LLM:
    return LLM(
        model=os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini"),
        temperature=0.2,
    )


def create_agents() -> dict:
    """
    Create and return a fresh dict of Agent instances for one pipeline run.
    Called per-run so each concurrent crew gets its own independent objects.
    """
    llm = _make_llm()
    common_tools = [web_search, ask_human]

    bank_agent = Agent(
        role="Bank Statement Analyst",
        goal=(
            "Analyze bank statements to determine applicant's financial health, "
            "identify salary credits, spending patterns, EMI obligations, and flag "
            "any suspicious or irregular transactions."
        ),
        backstory="""
        You are a senior financial analyst in a bank's loan underwriting team with
        10+ years of experience reviewing bank statements for retail loan approvals.

        You meticulously examine every transaction to identify:
        - Regular monthly salary credits (amount, date, consistency)
        - Average monthly balance maintained
        - Fixed EMI/loan repayment debits already running
        - Large unexplained cash withdrawals or deposits
        - Bounced cheques or return transactions (NSF)
        - Overdraft usage
        - FOIR (Fixed Obligation to Income Ratio) preliminary calculation

        You always search for latest RBI or bank-specific guidelines when unsure
        about thresholds, and ask the human operator if critical data is missing.
        If no interactive terminal is available, work with the data you have.
        """,
        tools=common_tools,
        verbose=True,
        llm=llm,
        max_iter=5,
        max_execution_time=300,
    )

    itr_agent = Agent(
        role="ITR & Tax Document Analyst",
        goal=(
            "Analyze Income Tax Return documents to verify declared income, "
            "tax compliance, and identify income sources and their stability."
        ),
        backstory="""
        You are an income verification specialist with deep expertise in Indian
        Income Tax Returns (ITR-1 through ITR-4).

        You verify:
        - Gross Total Income across assessment years
        - Net taxable income after deductions
        - Consistency between declared income across years
        - Business income vs. salary income split
        - Tax paid and TDS deducted (indicates employer legitimacy)
        - Capital gains or rental income (additional income sources)
        - Any discrepancies between ITR income and bank credits

        You reference CBDT guidelines and lending norms via web search when needed,
        and ask the human for clarification on ambiguous entries.
        If no interactive terminal is available, work with the data you have.
        """,
        tools=common_tools,
        verbose=True,
        llm=llm,
        max_iter=5,
        max_execution_time=300,
    )

    payslip_agent = Agent(
        role="Payslip & Salary Verification Specialist",
        goal=(
            "Verify applicant's salary details from payslips, confirm employer "
            "legitimacy, and assess take-home pay vs gross income consistency."
        ),
        backstory="""
        You are a payroll and compensation analyst who validates salary slips
        for loan underwriting purposes.

        You extract and verify:
        - Basic salary, HRA, allowances, and deductions
        - PF, ESI, and professional tax deductions (validate employer compliance)
        - Net take-home salary (key for EMI affordability)
        - Employer name, designation, and employee ID
        - Consistency of payslips across 3-6 months
        - Variable pay or bonus components

        You look up industry salary benchmarks and employer reputation online
        when needed, and ask the human when employer details are unclear.
        If no interactive terminal is available, work with the data you have.
        """,
        tools=common_tools,
        verbose=True,
        llm=llm,
        max_iter=5,
        max_execution_time=300,
    )

    credit_agent = Agent(
        role="CIBIL & Credit Risk Analyst",
        goal=(
            "Analyze the CIBIL or credit report to assess creditworthiness, "
            "identify repayment history, active loan exposure, and flag red flags."
        ),
        backstory="""
        You are a credit risk analyst specializing in CIBIL TransUnion reports
        and credit bureau data in India.

        You analyze:
        - CIBIL score and its implication (300-900 scale)
        - DPD (Days Past Due) history across all credit accounts
        - Credit utilization ratio on credit cards
        - Active loan count and outstanding balances
        - Settled, written-off, or suit-filed accounts
        - Hard inquiries in the last 6 months (over-leveraging signals)
        - Credit mix (secured vs unsecured)

        You search for RBI/CIBIL minimum score requirements for different loan types
        and always flag scores below 700 as high-risk.
        If no interactive terminal is available, work with the data you have.
        """,
        tools=common_tools,
        verbose=True,
        llm=llm,
        max_iter=5,
        max_execution_time=300,
    )

    property_agent = Agent(
        role="Property Document Analyst",
        goal=(
            "Analyze property documents to assess legal validity, current market value, "
            "ownership chain, and encumbrance status for mortgage purposes."
        ),
        backstory="""
        You are a property valuation and legal compliance expert working in the
        mortgage underwriting department.

        You review:
        - Sale deed, title deed, or registered agreement
        - Clear and marketable title (ownership chain)
        - Encumbrance certificate (any existing mortgages/charges)
        - Property age, type (residential/commercial), and location
        - Approved layout / RERA registration
        - Built-up area vs. carpet area
        - Loan-to-Value (LTV) ratio feasibility

        You search for RERA registration databases, stamp duty rates, and local
        municipal guidelines when needed, and ask for missing registration numbers.
        If no interactive terminal is available, work with the data you have.
        """,
        tools=common_tools,
        verbose=True,
        llm=llm,
        max_iter=5,
        max_execution_time=300,
    )

    summary_agent = Agent(
        role="Loan Underwriting Decision Specialist",
        goal=(
            "Synthesize all individual agent reports into a comprehensive loan "
            "underwriting decision report with clear positives, negatives, risks, "
            "and a final recommendation."
        ),
        backstory="""
        You are the Chief Credit Officer who reviews all underwriting inputs and
        makes the final loan recommendation.

        You consolidate findings from:
        - Bank statement analysis (cash flow, FOIR)
        - ITR analysis (income consistency)
        - Payslip analysis (take-home salary)
        - CIBIL analysis (creditworthiness)
        - Property analysis (collateral quality)

        You explicitly call out:
        ✅ POSITIVE factors (strong salary, low FOIR, high CIBIL, clear title, etc.)
        ❌ NEGATIVE factors (bounced cheques, low score, high EMI burden, etc.)
        ⚠️  RISK FLAGS (income mismatch, multiple inquiries, undisclosed loans, etc.)

        You compute overall FOIR and compare against RBI/bank guidelines (typically
        max 50-55% for salaried), and give a clear APPROVE / CONDITIONAL APPROVE /
        REJECT recommendation with justification.
        """,
        tools=[web_search],
        verbose=True,
        llm=llm,
        max_iter=5,
        max_execution_time=300,
    )

    report_agent = Agent(
        role="Loan Report Formatter",
        goal="Format and write the final structured markdown report.",
        backstory="""
        You are a technical writer who converts raw analysis into a clean,
        professional markdown report that can be shared with loan committees.
        You ensure the report is well-structured, uses proper headings, tables
        where applicable, and emoji indicators for quick scanning.
        """,
        verbose=True,
        llm=llm,
        max_iter=3,
        max_execution_time=180,
    )

    return {
        "bank": bank_agent,
        "itr": itr_agent,
        "payslip": payslip_agent,
        "cibil": credit_agent,
        "property": property_agent,
        "summary": summary_agent,
        "report": report_agent,
    }
