"""
Core pipeline logic — shared by the CLI (main.py) and the API (api.py).
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Callable, Optional

from crewai import Crew

from agents import create_agents
from config.thresholds import AGENT_CONFIDENCE_THRESHOLDS
from tasks import create_tasks
from tools.human_input_tool import ask_human
from tools.pdf_parser import load_documents

logger = logging.getLogger("loan_pipeline")

_DOC_TO_AGENT: dict[str, str] = {
    "bank_statement": "bank",
    "itr":            "itr",
    "payslip":        "payslip",
    "cibil":          "cibil",
    "property":       "property",
}


# ---------------------------------------------------------------------------
# Pure helpers (easily unit-tested)
# ---------------------------------------------------------------------------

def format_docs(doc_list: list) -> str:
    """Format a list of {filename, content} dicts into a single string block."""
    if not doc_list:
        return "No documents of this type provided."
    parts = [f"### File: {doc['filename']}\n{doc['content']}" for doc in doc_list]
    return "\n\n---\n\n".join(parts)


def save_agent_report(agent_name: str, content: str, agents_report_folder: str) -> None:
    """Write <agent_name>_report.md to the given folder."""
    os.makedirs(agents_report_folder, exist_ok=True)
    filepath = os.path.join(agents_report_folder, f"{agent_name}_report.md")
    with open(filepath, "w") as f:
        f.write(content)
    logger.info("Saved agent report: %s", filepath)


def check_confidence(agent_name: str, output, crew_inputs: dict) -> dict:
    """
    Inspect the pydantic output's confidence_score.
    If below threshold, invoke ask_human and store the response in crew_inputs
    so downstream agents can reference the clarification.
    """
    threshold = AGENT_CONFIDENCE_THRESHOLDS.get(agent_name, 60)
    pydantic_output = output.pydantic
    if pydantic_output is None:
        logger.warning("%s: no structured pydantic output — skipping confidence check", agent_name)
        return crew_inputs

    score = pydantic_output.confidence_score
    reason = pydantic_output.confidence_reason
    logger.info("%s confidence: %d/100 — %s", agent_name, score, reason)

    if score < threshold:
        logger.warning(
            "%s: confidence %d below threshold %d — requesting human input",
            agent_name, score, threshold,
        )
        question = (
            f"The {agent_name} agent has low confidence ({score}/100).\n"
            f"Reason: {reason}\n\n"
            "Please provide any additional information that could help:"
        )
        human_response = ask_human.run(question)
        crew_inputs[f"{agent_name}_human_clarification"] = human_response
        logger.info("%s: human clarification recorded", agent_name)
    else:
        logger.info("%s: confidence acceptable — proceeding", agent_name)

    return crew_inputs


# ---------------------------------------------------------------------------
# Async agent runners
# ---------------------------------------------------------------------------

async def _run_analysis_agent(doc_key: str, inputs: dict) -> tuple[str, object]:
    """
    Spin up a fresh Crew for one document type.
    Returns (doc_key, CrewOutput | Exception).
    Each call creates its own agent/task instances to avoid shared mutable state.
    """
    agents = create_agents()
    tasks = create_tasks(agents)
    agent_key = _DOC_TO_AGENT[doc_key]
    crew = Crew(agents=[agents[agent_key]], tasks=[tasks[doc_key]], verbose=False)
    try:
        result = await crew.kickoff_async(inputs=inputs)
        logger.info("%s agent: completed", doc_key)
        return doc_key, result
    except Exception as exc:
        logger.error("%s agent: failed — %s", doc_key, exc, exc_info=True)
        return doc_key, exc


async def _run_all_analysis_agents(inputs: dict, classified_docs: dict) -> dict:
    """Run all available doc-type agents concurrently."""
    doc_keys = [
        k for k in ("bank_statement", "itr", "payslip", "cibil", "property")
        if classified_docs.get(k)
    ]
    if not doc_keys:
        logger.warning("No documents available for any analysis agent")
        return {}

    logger.info("Running %d agents concurrently: %s", len(doc_keys), doc_keys)
    raw = await asyncio.gather(
        *[_run_analysis_agent(key, dict(inputs)) for key in doc_keys],
        return_exceptions=False,
    )
    return dict(raw)


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

async def run_pipeline(
    docs_folder: str = "data/documents",
    reports_folder: str = "data/reports",
    on_progress: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Execute the full loan underwriting pipeline.

    Args:
        docs_folder:   Directory containing input PDFs.
        reports_folder: Directory for output reports.
        on_progress:   Optional callback(message) called at each major stage.

    Returns:
        Absolute path of the saved final report markdown file.

    Raises:
        FileNotFoundError: If docs_folder does not exist.
        RuntimeError:      If the report generation step fails.
    """
    agents_folder = os.path.join(reports_folder, "agents")
    os.makedirs(agents_folder, exist_ok=True)
    os.makedirs(reports_folder, exist_ok=True)

    def _progress(msg: str) -> None:
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    if not os.path.isdir(docs_folder):
        raise FileNotFoundError(f"Documents folder not found: {docs_folder}")

    # ── Step 1: Classify documents ─────────────────────────────────────────
    _progress("Loading and classifying documents…")
    classified_docs = load_documents(docs_folder)
    doc_summary = {k: len(v) for k, v in classified_docs.items() if v and k != "unknown"}
    _progress(f"Documents classified: {doc_summary}")

    # ── Step 2: Build LLM input strings ───────────────────────────────────
    inputs: dict = {
        "bank_statement_docs": format_docs(classified_docs["bank_statement"]),
        "itr_docs":            format_docs(classified_docs["itr"]),
        "payslip_docs":        format_docs(classified_docs["payslip"]),
        "cibil_docs":          format_docs(classified_docs["cibil"]),
        "property_docs":       format_docs(classified_docs["property"]),
    }

    # ── Step 3: Parallel analysis agents ──────────────────────────────────
    _progress("Running specialist analysis agents in parallel…")
    agent_results = await _run_all_analysis_agents(inputs, classified_docs)

    _default: dict[str, str] = {
        "bank_statement": "No bank statement documents provided.",
        "itr":            "No ITR documents provided.",
        "payslip":        "No payslip documents provided.",
        "cibil":          "No CIBIL/credit report documents provided.",
        "property":       "No property documents provided.",
    }

    analyses: dict[str, str] = {}
    for doc_key, default_msg in _default.items():
        result = agent_results.get(doc_key)
        if result is None:
            analyses[doc_key] = default_msg
        elif isinstance(result, Exception):
            logger.error("%s: using fallback — %s", doc_key, result)
            analyses[doc_key] = f"Analysis failed: {result}"
        else:
            inputs = check_confidence(doc_key, result, inputs)
            analyses[doc_key] = str(result)
            save_agent_report(doc_key, analyses[doc_key], agents_folder)
            _progress(f"{doc_key}: analysis complete")

    # ── Step 4: Summary agent ─────────────────────────────────────────────
    _progress("Running summary agent…")
    summary_inputs = {
        **inputs,
        "bank_analysis":     analyses["bank_statement"],
        "itr_analysis":      analyses["itr"],
        "payslip_analysis":  analyses["payslip"],
        "cibil_analysis":    analyses["cibil"],
        "property_analysis": analyses["property"],
    }

    summary_result = None
    summary_analysis: str
    try:
        agents = create_agents()
        tasks = create_tasks(agents)
        summary_crew = Crew(agents=[agents["summary"]], tasks=[tasks["summary"]], verbose=False)
        summary_result = await summary_crew.kickoff_async(inputs=summary_inputs)
        inputs = check_confidence("summary", summary_result, {**summary_inputs})
        summary_analysis = str(summary_result)
        save_agent_report("summary", summary_analysis, agents_folder)
    except Exception as exc:
        logger.error("Summary agent failed: %s", exc, exc_info=True)
        summary_analysis = f"Summary generation failed: {exc}"

    # ── Step 5: Report formatter agent ────────────────────────────────────
    _progress("Generating final loan report…")
    report_inputs = {**summary_inputs, "summary_analysis": summary_analysis}

    try:
        agents = create_agents()
        tasks = create_tasks(agents)
        report_crew = Crew(agents=[agents["report"]], tasks=[tasks["report"]], verbose=False)
        final_result = await report_crew.kickoff_async(inputs=report_inputs)
    except Exception as exc:
        raise RuntimeError(f"Report generation failed: {exc}") from exc

    final_content = str(final_result)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_report_path = os.path.join(reports_folder, f"loan_report_{timestamp}.md")
    with open(final_report_path, "w") as f:
        f.write(final_content)

    _progress(f"Complete — report saved to {final_report_path}")
    return final_report_path
