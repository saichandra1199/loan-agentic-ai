import os
from datetime import datetime
from crewai import Crew, Process
from dotenv import load_dotenv
from agents import (
    bank_agent, itr_agent, payslip_agent,
    credit_agent, property_agent, summary_agent, report_agent
)
from tasks import (
    bank_task, itr_task, payslip_task,
    credit_task, property_task, summary_task, report_task
)

from config.thresholds import AGENT_CONFIDENCE_THRESHOLDS
from tools.human_input_tool import ask_human
from tools.pdf_parser import load_documents

load_dotenv()

DOCS_FOLDER = "data/documents"
REPORTS_FOLDER = "data/reports"
AGENTS_REPORT_FOLDER = "data/reports/agents"


def check_confidence(agent_name: str, output, crew_inputs: dict) -> dict:
    """
    Check agent confidence score. If below threshold, ask human
    for additional info and store it back in inputs for downstream agents.
    """
    threshold = AGENT_CONFIDENCE_THRESHOLDS.get(agent_name, 60)
    score = output.confidence_score
    reason = output.confidence_reason

    print(f"\n  🎯 {agent_name} confidence: {score}/100")
    print(f"  💬 Reason: {reason}")

    if score < threshold:
        print(f"\n  ⚠️  Confidence below threshold ({threshold}). Requesting human input...")
        question = (
            f"The {agent_name} agent has low confidence ({score}/100).\n"
            f"Reason: {reason}\n\n"
            f"Please provide any additional information that could help:"
        )
        human_response = ask_human.run(question)

        # Store human clarification so downstream agents can use it
        key = f"{agent_name}_human_clarification"
        crew_inputs[key] = human_response
        print(f"  ✅ Human input recorded for {agent_name}")
    else:
        print(f"  ✅ Confidence acceptable — proceeding")

    return crew_inputs


def save_agent_report(agent_name: str, content: str):
    """Save individual agent report to disk."""
    os.makedirs(AGENTS_REPORT_FOLDER, exist_ok=True)
    filepath = os.path.join(AGENTS_REPORT_FOLDER, f"{agent_name}_report.md")
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  💾 Saved: {filepath}")


def format_docs(doc_list: list) -> str:
    """Format list of documents into a single string with separators."""
    if not doc_list:
        return "No documents of this type provided."
    parts = []
    for doc in doc_list:
        parts.append(f"### File: {doc['filename']}\n{doc['content']}")
    return "\n\n---\n\n".join(parts)


def run_pipeline():
    print("\n" + "="*60)
    print("🏦 LOAN UNDERWRITING AI PIPELINE")
    print("="*60)

    # Step 1: Load and classify documents
    print("\n📂 Loading and classifying documents...")
    classified_docs = load_documents(DOCS_FOLDER)

    for doc_type, docs in classified_docs.items():
        if docs:
            print(f"  ✅ {doc_type}: {len(docs)} file(s)")
        else:
            print(f"  ⚠️  {doc_type}: No files found")

    # Step 2: Format document content for each agent
    inputs = {
        "bank_statement_docs": format_docs(classified_docs["bank_statement"]),
        "itr_docs": format_docs(classified_docs["itr"]),
        "payslip_docs": format_docs(classified_docs["payslip"]),
        "cibil_docs": format_docs(classified_docs["cibil"]),
        "property_docs": format_docs(classified_docs["property"]),
    }

    # Step 3: Run individual analysis agents sequentially
    print("\n🤖 Running specialist analysis agents...\n")

    # Bank Statement Analysis
    if classified_docs["bank_statement"]:
        print("📊 Analyzing bank statements...")
        bank_crew = Crew(agents=[bank_agent], tasks=[bank_task], verbose=True)
        bank_result = bank_crew.kickoff(inputs=inputs)
        inputs = check_confidence("bank_statement", bank_result, inputs)
        bank_analysis = str(bank_result)
        save_agent_report("bank_statement", bank_analysis)
    else:
        bank_analysis = "No bank statement documents provided."
        print("⚠️  Skipping bank statement analysis (no files)")

    # ITR Analysis
    if classified_docs["itr"]:
        print("📋 Analyzing ITR documents...")
        itr_crew = Crew(agents=[itr_agent], tasks=[itr_task], verbose=True)
        itr_result = itr_crew.kickoff(inputs=inputs)
        inputs = check_confidence("itr", itr_result, inputs)
        itr_analysis = str(itr_result)
        save_agent_report("itr", itr_analysis)
    else:
        itr_analysis = "No ITR documents provided."
        print("⚠️  Skipping ITR analysis (no files)")

    # Payslip Analysis
    if classified_docs["payslip"]:
        print("💰 Analyzing payslips...")
        payslip_crew = Crew(agents=[payslip_agent], tasks=[payslip_task], verbose=True)
        payslip_result = payslip_crew.kickoff(inputs=inputs)
        inputs = check_confidence("payslip", payslip_result, inputs)
        payslip_analysis = str(payslip_result)
        save_agent_report("payslip", payslip_analysis)
    else:
        payslip_analysis = "No payslip documents provided."
        print("⚠️  Skipping payslip analysis (no files)")

    # CIBIL Analysis
    if classified_docs["cibil"]:
        print("📈 Analyzing CIBIL report...")
        credit_crew = Crew(agents=[credit_agent], tasks=[credit_task], verbose=True)
        credit_result = credit_crew.kickoff(inputs=inputs)
        inputs = check_confidence("cibil", credit_result, inputs)
        cibil_analysis = str(credit_result)
        save_agent_report("cibil", cibil_analysis)
    else:
        cibil_analysis = "No CIBIL/credit report documents provided."
        print("⚠️  Skipping CIBIL analysis (no files)")

    # Property Analysis
    if classified_docs["property"]:
        print("🏠 Analyzing property documents...")
        property_crew = Crew(agents=[property_agent], tasks=[property_task], verbose=True)
        property_result = property_crew.kickoff(inputs=inputs)
        inputs = check_confidence("property", property_result, inputs)
        property_analysis = str(property_result)
        save_agent_report("property", property_analysis)
    else:
        property_analysis = "No property documents provided."
        print("⚠️  Skipping property analysis (no files)")

    # Step 4: Run summary agent with all analyses
    print("\n🔍 Running conclusive summary agent...")
    summary_inputs = {
        **inputs,
        "bank_analysis": bank_analysis,
        "itr_analysis": itr_analysis,
        "payslip_analysis": payslip_analysis,
        "cibil_analysis": cibil_analysis,
        "property_analysis": property_analysis,
    }

    summary_crew = Crew(agents=[summary_agent], tasks=[summary_task], verbose=True)
    summary_result = summary_crew.kickoff(inputs=summary_inputs)
    summary_analysis = str(summary_result)
    save_agent_report("summary", summary_analysis)

    # Step 5: Generate final formatted report
    print("\n📝 Generating final loan report...")
    report_inputs = {
        **summary_inputs,
        "summary_analysis": summary_analysis,
    }

    report_crew = Crew(agents=[report_agent], tasks=[report_task], verbose=True)
    final_result = report_crew.kickoff(inputs=report_inputs)

    # Step 6: Save final report
    os.makedirs(REPORTS_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_report_path = os.path.join(REPORTS_FOLDER, f"loan_report_{timestamp}.md")

    with open(final_report_path, "w") as f:
        f.write(str(final_result))

    print("\n" + "="*60)
    print("✅ LOAN ANALYSIS COMPLETE!")
    print("="*60)
    print(f"\n📄 Final Report: {final_report_path}")
    print(f"📁 Agent Reports: {AGENTS_REPORT_FOLDER}/")
    print("\nAgent Reports Generated:")
    for doc_type in ["bank_statement", "itr", "payslip", "cibil", "property", "summary"]:
        report_file = os.path.join(AGENTS_REPORT_FOLDER, f"{doc_type}_report.md")
        if os.path.exists(report_file):
            print(f"  ✅ {doc_type}_report.md")


if __name__ == "__main__":
    run_pipeline()