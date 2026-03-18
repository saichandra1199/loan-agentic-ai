"""
Streamlit web interface for the Loan Underwriting AI system.

Requires the FastAPI backend (api.py) to be running.
Set API_BASE_URL environment variable if the API is not on localhost:8000.
"""
import os
import time

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Loan Underwriting AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
for key, default in {
    "session_id": None,
    "status": None,
    "report_ready": False,
    "report_data": None,
    "last_status_data": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_post(path: str, **kwargs):
    try:
        return requests.post(f"{API_BASE}{path}", timeout=30, **kwargs)
    except requests.ConnectionError:
        st.error("Cannot reach the API server. Make sure it is running.")
        st.stop()


def api_get(path: str, **kwargs):
    try:
        return requests.get(f"{API_BASE}{path}", timeout=10, **kwargs)
    except requests.ConnectionError:
        st.error("Cannot reach the API server. Make sure it is running.")
        st.stop()


def recommendation_badge(rec: str) -> str:
    colours = {
        "APPROVE":             "🟢",
        "CONDITIONAL_APPROVE": "🟡",
        "REJECT":              "🔴",
    }
    label = rec.replace("_", " ")
    return f"{colours.get(rec, '⚪')} **{label}**"


def parse_sections(md: str) -> dict[str, str]:
    """Split markdown into {heading: body} sections on '## ' boundaries."""
    sections: dict[str, str] = {}
    current_heading = "Overview"
    current_lines: list[str] = []
    for line in md.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections


# ---------------------------------------------------------------------------
# Sidebar — upload
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🏦 Loan Underwriting AI")
    st.caption("AI-powered credit analysis for loan applications")
    st.divider()

    st.subheader("📂 Upload Documents")
    st.markdown(
        """
        **Accepted document types**
        - Bank Statements
        - ITR / Income Tax Returns
        - Payslips / Salary Slips
        - CIBIL / Credit Reports
        - Property Documents
        """
    )

    uploaded_files = st.file_uploader(
        "Drop PDF files here",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    run_disabled = not uploaded_files or st.session_state.status == "running"
    run_clicked = st.button(
        "🚀 Run Analysis",
        type="primary",
        disabled=run_disabled,
        use_container_width=True,
    )

    if st.session_state.session_id:
        st.divider()
        st.caption(f"Session `{st.session_state.session_id[:8]}…`")
        if st.button("🔄 New Analysis", use_container_width=True):
            for k in ("session_id", "status", "report_ready", "report_data", "last_status_data"):
                st.session_state[k] = None if k not in ("report_ready",) else False
            st.session_state["last_status_data"] = {}
            st.rerun()

    st.divider()
    st.caption("Powered by CrewAI + GPT-4o-mini")


# ---------------------------------------------------------------------------
# Main area — upload & trigger
# ---------------------------------------------------------------------------
if run_clicked and uploaded_files:
    with st.spinner("Uploading documents…"):
        files = [
            ("files", (f.name, f.read(), "application/pdf"))
            for f in uploaded_files
        ]
        resp = api_post("/sessions/upload", files=files)
        if resp.status_code != 200:
            st.error(f"Upload failed: {resp.text}")
            st.stop()
        session_id = resp.json()["session_id"]
        st.session_state.session_id = session_id

    with st.spinner("Starting analysis…"):
        resp = api_post(f"/sessions/{session_id}/analyze")
        if resp.status_code not in (200, 202):
            st.error(f"Failed to start analysis: {resp.text}")
            st.stop()
        st.session_state.status = "running"

    st.rerun()


# ---------------------------------------------------------------------------
# Main area — progress polling
# ---------------------------------------------------------------------------
if st.session_state.session_id and st.session_state.status == "running":
    session_id = st.session_state.session_id

    st.subheader("⏳ Analysing loan documents…")

    # Stage → (label, progress %)
    STAGE_MAP = {
        "Loading":    ("📂 Loading & classifying documents", 10),
        "Running":    ("🤖 Running specialist agents in parallel", 45),
        "summary":    ("🔍 Generating underwriting summary", 75),
        "Generating": ("📝 Writing final report", 90),
        "Complete":   ("✅ Analysis complete", 100),
    }

    progress_bar = st.progress(0)
    step_label = st.empty()
    log_area = st.empty()

    while True:
        resp = api_get(f"/sessions/{session_id}/status")
        data = resp.json()
        st.session_state.last_status_data = data
        current = data.get("current_step", "")

        # Match stage
        label, pct = "⏳ Processing…", 5
        for key, (lbl, p) in STAGE_MAP.items():
            if key.lower() in current.lower():
                label, pct = lbl, p
                break

        progress_bar.progress(pct / 100)
        step_label.info(label)

        log_lines = data.get("progress", [])
        if log_lines:
            log_area.text_area("Pipeline log", value="\n".join(log_lines), height=150)

        if data["status"] == "complete":
            st.session_state.status = "complete"
            st.session_state.report_ready = True
            st.rerun()

        if data["status"] == "failed":
            st.session_state.status = "failed"
            st.error(f"Analysis failed: {data.get('error', 'Unknown error')}")
            st.stop()

        time.sleep(3)


# ---------------------------------------------------------------------------
# Main area — failed state
# ---------------------------------------------------------------------------
if st.session_state.status == "failed":
    data = st.session_state.last_status_data
    st.error(f"Pipeline failed: {data.get('error', 'Unknown error')}")
    with st.expander("Pipeline log"):
        for line in data.get("progress", []):
            st.text(line)


# ---------------------------------------------------------------------------
# Main area — completed report
# ---------------------------------------------------------------------------
if st.session_state.report_ready and st.session_state.session_id:
    session_id = st.session_state.session_id

    if not st.session_state.report_data:
        with st.spinner("Loading report…"):
            resp = api_get(f"/sessions/{session_id}/report")
            if resp.status_code == 200:
                st.session_state.report_data = resp.json()
            else:
                st.error("Could not load the report from the server.")
                st.stop()

    report_data = st.session_state.report_data
    report_md = report_data.get("content", "")

    # Extract recommendation from report text for the banner
    rec_line = next((l for l in report_md.splitlines() if "Recommendation:" in l), "")
    if "APPROVE" in rec_line and "CONDITIONAL" not in rec_line:
        rec_key = "APPROVE"
    elif "CONDITIONAL" in rec_line:
        rec_key = "CONDITIONAL_APPROVE"
    elif "REJECT" in rec_line:
        rec_key = "REJECT"
    else:
        rec_key = ""

    st.success("✅ Analysis Complete")
    if rec_key:
        st.markdown(f"### Recommendation: {recommendation_badge(rec_key)}", unsafe_allow_html=True)

    st.divider()

    # Tabs
    sections = parse_sections(report_md)
    tab_names = list(sections.keys()) if sections else ["Full Report"]

    # Always add a raw report tab and a log tab
    all_tabs = st.tabs(tab_names + ["📄 Raw Report", "📜 Log"])
    section_items = list(sections.items())

    for i, tab in enumerate(all_tabs[:-2]):
        with tab:
            _, body = section_items[i]
            st.markdown(body)

    with all_tabs[-2]:
        dl_col, _ = st.columns([1, 3])
        with dl_col:
            st.download_button(
                label="⬇️ Download .md",
                data=report_md,
                file_name=f"loan_report_{session_id[:8]}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        st.markdown(report_md)

    with all_tabs[-1]:
        last = st.session_state.last_status_data
        for line in last.get("progress", []):
            st.text(line)


# ---------------------------------------------------------------------------
# Landing state (no session yet)
# ---------------------------------------------------------------------------
if not st.session_state.session_id:
    st.title("Welcome to Loan Underwriting AI")
    st.markdown(
        """
        This system automates the analysis of loan applications using a team of
        specialized AI agents. Upload your applicant's financial documents in the
        sidebar to get started.

        **Pipeline stages**
        1. 📂 Document classification (bank statement, ITR, payslip, CIBIL, property)
        2. 🤖 Parallel AI analysis — 5 specialist agents run concurrently
        3. 🔍 Cross-validation and consolidated underwriting summary
        4. 📝 Professional markdown report with APPROVE / CONDITIONAL APPROVE / REJECT verdict

        **Typical runtime:** ~30 seconds for a full 4-document application.
        """
    )
    st.info("⬅️ Upload PDF documents in the sidebar to begin.")
