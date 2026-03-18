# Loan Underwriting AI Agent System

An AI-powered loan underwriting system built with [CrewAI](https://crewai.com), [FastAPI](https://fastapi.tiangolo.com), and [Streamlit](https://streamlit.io). It accepts a set of financial PDFs, runs them through a team of specialized AI agents concurrently, and produces a structured markdown report with a final lending recommendation — accessible via a web UI, a REST API, or the command line.

---

## What It Does

Given a loan application's supporting documents, the system:

1. **Classifies** each PDF by document type automatically (by filename and content)
2. **Analyzes** all document types in parallel using specialized AI agents
3. **Cross-validates** findings across agents (income vs. bank credits, EMI vs. CIBIL entries)
4. **Gates on confidence** — if an agent's self-rated confidence drops below its threshold, it requests human clarification before proceeding
5. **Produces** a structured markdown report with a verdict: `APPROVE`, `CONDITIONAL APPROVE`, or `REJECT`

### Sample Output

```
## Consolidated Summary & Recommendation

| Metric               | Value      | Benchmark | Status |
|----------------------|------------|-----------|--------|
| CIBIL Score          | 785        | ≥ 700     | ✅     |
| FOIR                 | 25%        | ≤ 50%     | ✅     |
| Net Monthly Income   | ₹1,32,000  | —         | —      |
| Total EMI (existing) | ₹33,500    | —         | —      |
| Recommended Max EMI  | ₹66,000    | —         | —      |

Recommendation: CONDITIONAL APPROVE

Strong financial health with a stable income and high CIBIL score.
Conditional on submission of property documents for collateral verification.
```

---

## System Architecture

The system has three layers that share a single core pipeline:

```
┌─────────────────────────────────────────────────────────┐
│               Streamlit Web UI  (app.py)                │
│   File uploader → progress polling → tabbed report      │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP  (REST API)
┌────────────────────────▼────────────────────────────────┐
│              FastAPI Server  (api.py)                   │
│   /sessions/upload → /analyze → /status → /report      │
└────────────────────────┬────────────────────────────────┘
                         │ ThreadPoolExecutor + asyncio
┌────────────────────────▼────────────────────────────────┐
│           Core Pipeline  (pipeline.py)                  │
│                                                         │
│  PDF Classification  →  Parallel AI Agents              │
│                         ┌─────────────────────────┐     │
│                         │ BankAgent  │  ITRAgent  │     │
│                         │ PayslipAgent│ CIBILAgent│     │
│                         │ PropertyAgent           │     │
│                         └─────────────────────────┘     │
│                              ↓ asyncio.gather()         │
│  Confidence Gate  →  SummaryAgent  →  ReportAgent       │
│                              ↓                          │
│              loan_report_YYYYMMDD_HHMMSS.md             │
└─────────────────────────────────────────────────────────┘
```

### Pipeline Flow

1. PDFs placed in a folder are classified into types (bank statement, ITR, payslip, CIBIL, property)
2. Five specialist agents run concurrently via `asyncio.gather()` + `crew.kickoff_async()`
3. Each agent's confidence score is checked — below-threshold results trigger human input (or a graceful fallback in automated environments)
4. A summary agent consolidates all findings into a structured risk assessment
5. A report formatter produces the final professional markdown output

---

## Key Design Decisions

**Factory functions, not singletons.** `agents.py` and `tasks.py` expose `create_agents()` and `create_tasks(agents)` factory functions instead of module-level objects. CrewAI mutates `Agent` and `Task` objects during execution (sets `.output`, `.start_time`, internal counters), making shared instances unsafe for concurrent runs. Each async coroutine gets its own fresh instances.

**Async parallel execution.** The five analysis agents are independent of each other and run concurrently. Wall-clock time for a full 4-agent run is ~30 seconds vs. ~5 minutes sequential.

**Thread-isolated event loops for the API.** FastAPI's background tasks run inside the server's event loop. Calling `asyncio.run()` there would cause a "nested event loop" error. The API instead dispatches each pipeline run to a `ThreadPoolExecutor` worker, where `asyncio.new_event_loop().run_until_complete()` creates an isolated loop per job.

**Structured Pydantic outputs.** Every agent returns a validated Pydantic model with typed fields. This makes the summary agent's cross-validation deterministic and enables the API to return structured JSON rather than raw text.

**TTY-aware human input.** In interactive terminal sessions, agents can ask for clarification via `input()`. In Docker or CI environments (no TTY), the tool detects this automatically and returns a graceful fallback — the pipeline never blocks.

---

## Project Structure

```
loan-agent-system/
├── main.py                     # CLI entry point
├── pipeline.py                 # Core reusable pipeline logic
├── api.py                      # FastAPI REST server
├── app.py                      # Streamlit web UI
├── agents.py                   # Agent factory — 7 Agent definitions
├── tasks.py                    # Task factory — 7 Task definitions
├── pdf_generator.py            # Synthetic test PDF generator
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env                        # API keys (not committed)
├── config/
│   └── thresholds.py           # Per-agent confidence thresholds
├── models/
│   └── outputs.py              # Pydantic output models
├── tools/
│   ├── pdf_parser.py           # PDF text extraction + classification
│   ├── search_tool.py          # Serper web search
│   ├── human_input_tool.py     # TTY-aware human clarification
│   └── financial_tools.py      # FOIR + average balance calculations
├── tests/
│   ├── conftest.py             # Shared pytest fixtures
│   ├── test_pdf_parser.py
│   ├── test_financial_tools.py
│   ├── test_human_input_tool.py
│   ├── test_pipeline_utils.py
│   └── test_api.py
└── data/
    ├── documents/              # Input PDFs
    └── reports/
        ├── agents/             # Per-agent intermediate reports
        ├── pipeline.log        # Structured run log
        └── loan_report_*.md    # Final timestamped reports
```

---

## File Reference

Every file in the project, its purpose, and what it contains:

---

### `pipeline.py`

**Purpose:** The single source of truth for the underwriting pipeline logic. Both the CLI (`main.py`) and the API (`api.py`) call this file — neither duplicates pipeline code.

**What's inside:**
- `format_docs(doc_list)` — formats a list of `{filename, content}` dicts into a single string block for LLM consumption
- `save_agent_report(agent_name, content, agents_report_folder)` — writes `<agent>_report.md` to a configurable folder path
- `check_confidence(agent_name, output, crew_inputs)` — reads `output.pydantic.confidence_score`, compares against `AGENT_CONFIDENCE_THRESHOLDS`, calls `ask_human` if below threshold, stores the response in `crew_inputs`
- `_run_analysis_agent(doc_key, inputs)` — async coroutine that creates fresh Agent + Task instances and calls `crew.kickoff_async()`
- `_run_all_analysis_agents(inputs, classified_docs)` — runs all available document-type agents concurrently via `asyncio.gather()`
- `run_pipeline(docs_folder, reports_folder, on_progress)` — the main async entry point; classifies documents, runs parallel agents, runs summary and report agents, saves the final report, returns the report file path

---

### `main.py`

**Purpose:** CLI entry point. A thin wrapper around `pipeline.py` for running the pipeline from the terminal.

**What's inside:**
- Loads `.env` with `python-dotenv`
- Sets up file + stdout logging with timestamps
- Calls `asyncio.run(run_pipeline("data/documents", "data/reports"))` when executed directly

---

### `api.py`

**Purpose:** FastAPI REST server that exposes the pipeline as a web service. Supports session-based PDF upload, asynchronous pipeline execution, and report retrieval.

**What's inside:**
- `_sessions` dict — in-memory session store (maps `session_id → state dict`)
- `_executor` — `ThreadPoolExecutor` with 4 workers for isolated pipeline runs
- `_run_pipeline_in_thread(session_id, docs_folder, reports_folder)` — creates a new `asyncio` event loop in a worker thread, runs `run_pipeline()`, updates `_sessions` with status and report path
- **`GET /health`** — liveness probe, returns `{"status": "ok"}`
- **`POST /sessions/upload`** — accepts multiple PDF file uploads, creates a UUID session, saves files to `data/sessions/<session_id>/documents/`, returns `session_id`
- **`POST /sessions/{session_id}/analyze`** — validates session state, sets status to `"running"`, dispatches `_run_pipeline_in_thread` as a background task
- **`GET /sessions/{session_id}/status`** — returns current status, progress log, current step, timestamps, and any error message
- **`GET /sessions/{session_id}/report`** — returns the full report text as JSON once the pipeline completes; 404 if not yet complete
- **`GET /sessions/{session_id}/report/download`** — returns the `.md` file as a `FileResponse` download
- **`DELETE /sessions/{session_id}`** — removes session folder from disk and clears the in-memory record

---

### `app.py`

**Purpose:** Streamlit web application. Provides a browser-based UI for uploading documents, watching the pipeline run, and reading the final report.

**What's inside:**
- **Sidebar** — multi-file PDF uploader, "Run Analysis" button, "New Analysis" reset button, session ID display
- **Upload flow** — on button click, POSTs files to `/sessions/upload`, then POSTs to `/sessions/{id}/analyze`, stores `session_id` in `st.session_state`
- **Progress polling** — a `while True` loop with `time.sleep(3)` that GETs `/sessions/{id}/status`, maps stage names to a progress bar percentage, displays the live pipeline log, and calls `st.rerun()` on completion
- **Report display** — tabbed view using `st.tabs()`: one tab per `## ` section of the markdown report, plus a raw report tab with a download button and a pipeline log tab
- `parse_sections(md)` — splits the markdown report on `## ` headings, returns `{heading: body}` dict used to build report tabs
- `recommendation_badge(rec)` — maps `APPROVE / CONDITIONAL_APPROVE / REJECT` to green/yellow/red emoji labels
- **Landing page** — shown before any session is created; explains the pipeline stages and typical runtime

---

### `agents.py`

**Purpose:** Defines all seven CrewAI agents as a factory function. Called fresh for every pipeline run to avoid shared mutable state.

**What's inside:**
- `_make_llm()` — creates an `LLM` instance using `OPENAI_MODEL` env var (defaults to `openai/gpt-4o-mini`) at temperature 0.2
- `create_agents()` — instantiates and returns a dict of seven agents:
  - `bank` — Bank Statement Analyst: extracts salary credits, EMIs, FOIR, flags unusual transactions
  - `itr` — ITR & Tax Analyst: verifies income across assessment years, checks TDS compliance
  - `payslip` — Payslip Verification Specialist: validates salary structure, deductions, employer legitimacy
  - `cibil` — CIBIL & Credit Risk Analyst: assesses credit score (300–900 scale), DPD history, active loans
  - `property` — Property Document Analyst: checks title chain, encumbrances, RERA registration, LTV
  - `summary` — Loan Underwriting Decision Specialist: synthesises all findings into APPROVE/REJECT
  - `report` — Report Formatter: converts raw analysis into structured markdown
- All agents have `max_iter=5` and `max_execution_time=300` to prevent infinite loops

---

### `tasks.py`

**Purpose:** Defines all seven CrewAI tasks as a factory function. Receives agent instances as input so each task is bound to a specific (fresh) agent.

**What's inside:**
- `create_tasks(agents)` — returns a dict of seven tasks:
  - `bank_statement` — instructs the bank agent to extract 6-month salary credits, FOIR, EMI debits, bounced transactions; mandates confidence scoring
  - `itr` — instructs the ITR agent to extract year-wise gross income, TDS, income source breakdown
  - `payslip` — instructs the payslip agent to extract salary components, deductions, cross-check against bank credits
  - `cibil` — instructs the CIBIL agent to extract score, DPD history, active loans, hard inquiry count
  - `property` — instructs the property agent to extract title chain, registration details, LTV feasibility
  - `summary` — receives all five agent analyses via template variables, produces structured recommendation
  - `report` — compiles all analyses and summary into a final formatted markdown report
- Each task has `output_pydantic` set to the corresponding model from `models/outputs.py` (except the report task)

---

### `models/outputs.py`

**Purpose:** Pydantic models for all agent structured outputs. Enforces typed, validated data from every agent instead of free-form text.

**What's inside:**
- `RiskLevel` enum — `LOW | MEDIUM | HIGH | CRITICAL`
- `RecommendationStatus` enum — `APPROVE | CONDITIONAL_APPROVE | REJECT | INSUFFICIENT_DATA`
- `ContradictionSeverity` enum — `LOW | MEDIUM | HIGH`
- `ConfidenceMixin` — base model adding `confidence_score` (int 0–100) and `confidence_reason` (str) to all agent outputs
- `MonthlySalaryEntry` — `{month, amount}` used inside `BankStatementOutput`
- `BankStatementOutput(ConfidenceMixin)` — salary credits list, avg balance, FOIR %, bounced count, overdraft flag, risk level, key flags, summary
- `YearlyIncomeEntry` — `{assessment_year, gross_income, net_taxable_income, tds_deducted}`
- `ITROutput(ConfidenceMixin)` — yearly income list, primary income source, stability assessment, risk level
- `PayslipOutput(ConfidenceMixin)` — employer, designation, gross/net salary, PF, TDS, variable pay %, consistency flag
- `ActiveLoanEntry` — `{lender, loan_type, outstanding_amount, emi_amount, dpd_history}`
- `CIBILOutput(ConfidenceMixin)` — CIBIL score, active loans list, utilization %, settled/written-off counts, hard inquiry count, DPD flag
- `PropertyOutput(ConfidenceMixin)` — property type, address, owner names, registration details, RERA flag, LTV feasibility
- `SummaryOutput(ConfidenceMixin)` — net income, FOIR, CIBIL score, positive/negative/risk factors, per-domain risk levels, final recommendation + justification + conditions
- `Contradiction` / `ValidationReport` — models for cross-agent contradiction detection (defined, not yet wired into the live pipeline)

---

### `config/thresholds.py`

**Purpose:** Central configuration for confidence gating thresholds.

**What's inside:**
- `CONFIDENCE_THRESHOLD = 60` — global fallback
- `AGENT_CONFIDENCE_THRESHOLDS` dict — per-agent thresholds:

| Agent | Threshold | Rationale |
|-------|-----------|-----------|
| `bank_statement` | 65 | Core income verification |
| `itr` | 60 | Supplementary income confirmation |
| `payslip` | 60 | Often only one month available |
| `cibil` | 70 | Most critical risk signal |
| `property` | 55 | Documents vary widely in format |
| `summary` | 75 | Final decision must be reliable |

---

### `tools/pdf_parser.py`

**Purpose:** Reads PDFs and classifies them by document type.

**What's inside:**
- `parse_pdf(file_path)` — uses `pdfplumber` to extract all text from a PDF, page by page
- `classify_document(filename, content)` — first matches against filename keywords (bank/itr/payslip/cibil/property), falls back to content keyword detection if no filename match
- `load_documents(folder)` — iterates all `.pdf` files in a folder, parses each with `parse_pdf`, classifies each with `classify_document`, returns a dict: `{doc_type: [{filename, content}, ...]}`

---

### `tools/search_tool.py`

**Purpose:** Gives agents the ability to search the web for RBI guidelines, CIBIL thresholds, and lending norms.

**What's inside:**
- `web_search(query)` — `@tool`-decorated function that POSTs to `https://google.serper.dev/search` with the `SERPER_API_KEY`, extracts the top 5 organic result titles/snippets/links, and returns them as a formatted string. Returns a graceful message if the API key is not set.

---

### `tools/human_input_tool.py`

**Purpose:** Lets agents ask the human operator for clarification when critical data is missing or ambiguous.

**What's inside:**
- `ask_human(question)` — `@tool`-decorated function:
  - Checks `sys.stdin.isatty()` — if not a TTY (Docker, CI, subprocess), returns `"No interactive terminal available. Proceeding with available document data only."` without blocking
  - If TTY: prints the question and calls `input()`, wrapped in `try/except EOFError` for safety
  - Empty input returns `"No answer provided."`

---

### `tools/financial_tools.py`

**Purpose:** Utility calculations available as CrewAI tools.

**What's inside:**
- `calculate_foir(monthly_income, emi)` — returns `round((emi / monthly_income) * 100, 2)`; returns `0` if income is zero (division guard)
- `average_balance(balances)` — returns `sum(balances) / len(balances)`; returns `0` for empty list

---

### `pdf_generator.py`

**Purpose:** Generates a set of realistic synthetic loan application PDFs for testing. Writes directly to `data/documents/`.

**What's inside:**
- `user_profile` dict — consistent persona (Arjun K. Verma, TechGlobal Solutions, ₹1,32,000/month net)
- `_add_watermark(c)` — draws a "SAMPLE POC" diagonal watermark on each page
- `generate_payslip(data, filename)` — October 2023 payslip with basic/HRA/allowances, PF and TDS deductions
- `generate_bank_statement(data, filename)` — 6-month statement (May–October 2023) with monthly salary credits and recurring EMI debits (home loan ₹25,000, car loan ₹8,500); uses `c.showPage()` for multi-page output
- `generate_itr(data, filename)` — two assessment years (2022-23 and 2023-24) showing 11% income growth
- `generate_credit_report(data, filename)` — CIBIL score 785, three active accounts (home loan, car loan, credit card), all with no overdue

---

### `Dockerfile`

**Purpose:** Single Docker image used by both the API and Streamlit services (command is overridden per service in `docker-compose.yml`).

**What's inside:**
- Base: `python:3.11-slim`
- System deps: `tesseract-ocr` (for future OCR support), `libglib2.0-0`, `libsm6`, `libxext6` (PDF/image library dependencies)
- Copies `requirements.txt` first (layer cached unless dependencies change), then installs with `pip`
- Copies all application code
- Pre-creates `/data/sessions`, `/data/documents`, `/data/reports/agents` directories
- Exposes ports 8000 (API) and 8501 (Streamlit) — actual binding is controlled by `docker-compose.yml`
- No default `CMD` — each service provides its own command

---

### `docker-compose.yml`

**Purpose:** Orchestrates both services with a shared persistent volume and Docker internal networking.

**What's inside:**
- `api` service — runs `uvicorn api:app --host 0.0.0.0 --port 8000 --reload`, mounts `loan_data` volume at `/data`, passes all API keys from `.env`, includes a healthcheck (`GET /health`)
- `streamlit` service — runs `streamlit run app.py ...`, depends on `api` (waits for healthy status), sets `API_BASE_URL=http://api:8000` (Docker DNS resolves `api` to the API container)
- `loan_data` named volume — shared between the API container's session and report files; Streamlit never reads files directly, only via HTTP
- `loan_net` bridge network — isolates both services from the host network while allowing them to communicate by service name

---

### `tests/conftest.py`

**Purpose:** Shared pytest fixtures available to all test files without import.

**What's inside:**
- `mock_crew_output` fixture — a `MagicMock` with `.pydantic.confidence_score = 80` and `.pydantic.confidence_reason` set; represents a passing agent output
- `low_confidence_crew_output` fixture — same structure but `confidence_score = 30`; triggers human input in `check_confidence`
- `sample_docs` fixture — a list of two `{filename, content}` dicts for testing `format_docs`

---

### `tests/test_pdf_parser.py`

**Purpose:** 17 tests covering document classification and document loading.

**What's inside:**
- `TestClassifyByFilename` (12 tests) — one test per document type (bank, itr, payslip, cibil, property, unknown) and for variant keyword spellings (`account`, `salary_slip`, `sale_deed`, etc.)
- `TestClassifyByContent` (6 tests) — verifies content-based fallback for each doc type when filename doesn't match; also verifies filename takes priority over content when both match
- `test_load_documents_*` (5 tests) — mocks `pdfplumber.open` to avoid needing real PDFs; tests correct bucket assignment, empty folder, unknown-type routing, content extraction, and non-PDF file exclusion

---

### `tests/test_financial_tools.py`

**Purpose:** 12 tests covering FOIR and average balance calculations.

**What's inside:**
- `TestCalculateFoir` (7 tests) — standard case (40%), zero income guard, zero EMI, rounding to 2 decimal places, FOIR above 50%, full income as EMI (100%), EMI exceeding income (>100%)
- `TestAverageBalance` (5 tests) — standard three-value case, empty list, single value, mixed values, large balances

---

### `tests/test_human_input_tool.py`

**Purpose:** 6 tests covering all execution paths of the `ask_human` tool.

**What's inside:**
- `TestAskHumanNonInteractive` (2 tests) — patches `sys.stdin.isatty` to return `False`; verifies fallback message is returned and `input()` is never called
- `TestAskHumanInteractive` (4 tests) — patches `isatty` to `True`; verifies user input is returned, empty input returns `"No answer provided."`, EOFError returns fallback, input is stripped of whitespace

---

### `tests/test_pipeline_utils.py`

**Purpose:** 16 tests covering the three utility functions extracted into `pipeline.py`.

**What's inside:**
- `TestFormatDocs` (5 tests) — empty list, single doc, multiple docs with `---` separator, exact content preservation, return type
- `TestSaveAgentReport` (4 tests) — file creation in specified folder, content written exactly, directory auto-creation, file overwrite behaviour
- `TestCheckConfidence` (7 tests) — above threshold (no `ask_human` call), below threshold (human called, key stored), clarification key named after agent, existing inputs preserved, `None` pydantic output handled, summary agent threshold (75) tested for pass and fail

---

### `tests/test_api.py`

**Purpose:** 23 tests covering all six FastAPI endpoints.

**What's inside:**
- Uses `fastapi.testclient.TestClient` — synchronous HTTP client, no real network needed
- `autouse` fixture clears `_sessions` dict before and after every test for isolation
- `TestUpload` (5 tests) — single file, multiple files, non-PDF rejection, unique session IDs, files written to disk
- `TestAnalyze` (4 tests) — returns running status, 404 on unknown session, 409 if already running, 409 if already complete
- `TestStatus` (4 tests) — pending after upload, presence of required fields, 404 on unknown session, reflects manual state changes
- `TestReport` (4 tests) — 404 when pending, report content returned on completion, 404 for missing file on disk, 404 on unknown session
- `TestDownload` (2 tests) — file bytes returned on completion, 404 when pending
- `TestDelete` (3 tests) — session removed from dict, 404 on unknown session, folder deleted from disk

---

## Getting Started

### Prerequisites

- Python 3.10+ (3.11 recommended)
- [OpenAI API key](https://platform.openai.com/api-keys)
- [Serper API key](https://serper.dev) — free tier; used by agents for RBI guideline lookups
- Docker + Docker Compose (for the containerised setup only)

---

### 1. Clone and Install

```bash
git clone <repo-url>
cd loan-agent-system
pip install -r requirements.txt
```

---

### 2. Configure Environment

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
CREWAI_TRACING_ENABLED=false

# Optional — override the LLM (default: gpt-4o-mini)
# OPENAI_MODEL=openai/gpt-4o
```

---

### 3. Generate Test Documents

The built-in PDF generator creates a complete 6-month sample application:

```bash
python pdf_generator.py
# Writes to data/documents/:
#   bank_statement.pdf  — 6 months of salary credits + EMI debits
#   itr.pdf             — two assessment years (2022-23, 2023-24)
#   payslip.pdf         — October 2023 with full deduction breakdown
#   credit_report.pdf   — CIBIL score 785, three active accounts
```

Or drop your own PDFs into `data/documents/`. Files are classified automatically:

| Document Type | Matched by filename keyword |
|---------------|-----------------------------|
| Bank Statement | `bank`, `statement`, `account` |
| ITR | `itr`, `income_tax`, `tax_return` |
| Payslip | `payslip`, `salary_slip`, `pay_stub`, `payroll` |
| CIBIL / Credit Report | `cibil`, `credit_report`, `credit_score`, `equifax` |
| Property Document | `property`, `sale_deed`, `agreement`, `flat`, `house` |

---

### 4a. Run via Command Line

```bash
python main.py
```

**Output locations:**

| File | Description |
|------|-------------|
| `data/reports/loan_report_YYYYMMDD_HHMMSS.md` | Final consolidated report |
| `data/reports/agents/{agent}_report.md` | Individual agent reports |
| `data/reports/pipeline.log` | Timestamped run log |

Typical runtime: **~30 seconds** for a 4-document application (agents run in parallel).

---

### 4b. Run via Web UI (Streamlit + FastAPI)

Start both services in separate terminals:

```bash
# Terminal 1 — API server
uvicorn api:app --reload --port 8000

# Terminal 2 — Streamlit UI
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

**API interactive docs:** http://localhost:8000/docs

**UI workflow:**
1. Upload one or more PDFs in the sidebar
2. Click **Run Analysis**
3. Watch the live progress bar as agents run in parallel
4. Read the tabbed report — one tab per report section
5. Download the `.md` report file

---

### 4c. Run via Docker Compose

```bash
# Build images and start both services
docker-compose up --build

# Run in the background
docker-compose up --build -d

# Stop
docker-compose down
```

Services started:

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | FastAPI — REST endpoints |
| API Docs | http://localhost:8000/docs | Auto-generated Swagger UI |
| Streamlit | http://localhost:8501 | Web UI |

Session data (uploaded PDFs and reports) is stored in the `loan_data` Docker volume and persists across container restarts.

---

### 5. Run Tests

```bash
# Run all 80 tests
pytest tests/ -v

# Run a specific file
pytest tests/test_api.py -v
pytest tests/test_pipeline_utils.py -v

# Run a specific test
pytest tests/test_financial_tools.py::TestCalculateFoir::test_zero_income_returns_zero -v
```

All tests run in ~2 seconds with no API keys required (CrewAI and OpenAI are fully mocked).

**Test coverage by file:**

| Test File | Tests | What is covered |
|-----------|-------|-----------------|
| `test_pdf_parser.py` | 17 | Document classification by filename + content, `load_documents()` |
| `test_financial_tools.py` | 12 | FOIR calculation, average balance, edge cases |
| `test_human_input_tool.py` | 6 | TTY detection, EOF handling, empty input, whitespace stripping |
| `test_pipeline_utils.py` | 16 | `format_docs`, `save_agent_report`, `check_confidence` |
| `test_api.py` | 23 | All 6 endpoints — upload, analyze, status, report, download, delete |

---

## REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe |
| `POST` | `/sessions/upload` | Upload PDFs, create session |
| `POST` | `/sessions/{id}/analyze` | Start the pipeline |
| `GET` | `/sessions/{id}/status` | Poll progress |
| `GET` | `/sessions/{id}/report` | Get completed report as JSON |
| `GET` | `/sessions/{id}/report/download` | Download report as `.md` file |
| `DELETE` | `/sessions/{id}` | Clean up session |

**Session lifecycle:**

```
upload → pending → (analyze) → running → complete
                                       → failed
```

---

## Data Models

All agent outputs are validated Pydantic models:

```
ConfidenceMixin              — confidence_score (0–100) + confidence_reason
├── BankStatementOutput      — salary credits, avg balance, FOIR %, bounced count, overdraft flag
├── ITROutput                — yearly income entries, income source, stability verdict
├── PayslipOutput            — gross/net salary, deductions, consistency flag
├── CIBILOutput              — score, active loans list, DPD flag, hard inquiry count
├── PropertyOutput           — title chain, registration, RERA flag, LTV feasibility
└── SummaryOutput            — positive/negative/risk factors, per-domain risk levels, recommendation

ValidationReport             — cross-agent contradiction detection (defined, not yet wired)
└── Contradiction            — field, agent_a vs agent_b, severity (LOW/MEDIUM/HIGH)

Enums
├── RiskLevel                — LOW | MEDIUM | HIGH | CRITICAL
└── RecommendationStatus     — APPROVE | CONDITIONAL_APPROVE | REJECT | INSUFFICIENT_DATA
```

---

## Future Scope

### Short-term

- **OCR support for scanned PDFs.** `pytesseract` is already in `requirements.txt`; wiring it into `pdf_parser.py` would handle scanned or photographed documents.
- **Property document generator.** `pdf_generator.py` does not yet produce a synthetic property document — adding one would enable end-to-end testing of all five analysis paths.
- **Multi-applicant batch mode.** A wrapper that iterates `data/documents/<applicant_id>/` and generates per-applicant reports.

### Medium-term

- **Database persistence.** Every `*Output` model exposes `.model_dump()` — ready to insert into SQLite or PostgreSQL. Enables re-submission history and trend analysis.
- **Cross-agent contradiction detection.** `ValidationReport` and `Contradiction` models are defined in `models/outputs.py` but not yet wired into the pipeline. Activating them in the summary agent would surface income mismatches as structured, severity-rated flags.
- **Configurable LLM per agent.** High-stakes agents (CIBIL, Summary) could use `gpt-4o` while the report formatter uses a cheaper model.
- **Redis session store.** Replacing the in-memory `_sessions` dict in `api.py` with Redis would make the API stateless and horizontally scalable.

### Long-term

- **Fine-tuned models.** Training a domain-specific model on historical approved/rejected applications to replace the general-purpose LLM for the summary agent.
- **Regulatory compliance layer.** A dedicated agent or rule-engine that checks every output against RBI Master Directions and flags non-compliant decisions.
- **Fraud signal detection.** Cross-referencing declared employer against MCA21 records, checking for synthetic salary patterns, and flagging metadata anomalies in uploaded documents.
- **Authentication and multi-tenancy.** Adding JWT-based auth to the API and scoping sessions by bank/organisation for production deployment.

---

## Disclaimer

This system is a research and automation aid. All lending decisions generated by this pipeline must be reviewed and approved by a qualified credit officer in accordance with applicable RBI guidelines and the lending institution's internal credit policy. The AI outputs are advisory only.
