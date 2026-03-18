"""
FastAPI application — REST interface for the loan underwriting pipeline.

Endpoints:
  POST   /sessions/upload              Upload PDFs, create a session
  POST   /sessions/{id}/analyze        Start the pipeline (background thread)
  GET    /sessions/{id}/status         Poll pipeline progress
  GET    /sessions/{id}/report         Retrieve the completed report
  GET    /sessions/{id}/report/download Download the .md report file
  DELETE /sessions/{id}                Clean up session data
"""
import asyncio
import logging
import os
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from pipeline import run_pipeline

load_dotenv()

logger = logging.getLogger("loan_api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

BASE_DATA_DIR = os.getenv("DATA_DIR", "data")

app = FastAPI(
    title="Loan Underwriting AI",
    description="AI-powered loan underwriting pipeline — upload financial PDFs, get a credit decision.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store — replace with Redis for multi-worker production deployments.
_sessions: dict[str, dict[str, Any]] = {}

# Dedicated thread pool so pipeline coroutines run in isolated event loops.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pipeline")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _session_docs_dir(session_id: str) -> str:
    return os.path.join(BASE_DATA_DIR, "sessions", session_id, "documents")


def _session_reports_dir(session_id: str) -> str:
    return os.path.join(BASE_DATA_DIR, "sessions", session_id, "reports")


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return _sessions[session_id]


def _run_pipeline_in_thread(session_id: str, docs_folder: str, reports_folder: str) -> None:
    """
    Execute the async pipeline inside a dedicated event loop on a worker thread.
    This avoids "cannot run nested event loop" errors when called from FastAPI's
    background task system (which itself runs in an asyncio event loop).
    """
    session = _sessions[session_id]

    def on_progress(msg: str) -> None:
        session["progress"].append(msg)
        session["current_step"] = msg

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        report_path = loop.run_until_complete(
            run_pipeline(docs_folder, reports_folder, on_progress)
        )
        session.update({
            "status":       "complete",
            "report_path":  report_path,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Session %s completed — report: %s", session_id, report_path)
    except Exception as exc:
        logger.exception("Pipeline failed for session %s", session_id)
        session.update({
            "status":       "failed",
            "error":        str(exc),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health():
    """Liveness probe."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/sessions/upload", status_code=200, tags=["sessions"])
async def upload_documents(files: list[UploadFile] = File(...)):
    """
    Upload one or more PDF documents and create a new analysis session.
    Returns the session_id to use in subsequent calls.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file must be uploaded")

    session_id = str(uuid.uuid4())
    docs_dir = _session_docs_dir(session_id)
    os.makedirs(docs_dir, exist_ok=True)

    saved: list[str] = []
    for file in files:
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are accepted. Received: {file.filename}",
            )
        dest = os.path.join(docs_dir, file.filename)
        Path(dest).write_bytes(await file.read())
        saved.append(file.filename)

    _sessions[session_id] = {
        "session_id":   session_id,
        "status":       "pending",
        "files":        saved,
        "docs_folder":  docs_dir,
        "reports_folder": _session_reports_dir(session_id),
        "progress":     [],
        "current_step": "",
        "report_path":  None,
        "error":        None,
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "started_at":   None,
        "completed_at": None,
    }

    logger.info("Session %s created — %d file(s): %s", session_id, len(saved), saved)
    return {"session_id": session_id, "files": saved}


@app.post("/sessions/{session_id}/analyze", status_code=200, tags=["sessions"])
async def start_analysis(session_id: str, background_tasks: BackgroundTasks):
    """
    Start the underwriting pipeline for a session.
    The pipeline runs in a background thread and updates session status.
    """
    session = _get_session(session_id)

    if session["status"] == "running":
        raise HTTPException(status_code=409, detail="Analysis is already running for this session")
    if session["status"] == "complete":
        raise HTTPException(status_code=409, detail="Analysis already completed — create a new session to re-run")

    session["status"] = "running"
    session["started_at"] = datetime.now(timezone.utc).isoformat()

    background_tasks.add_task(
        _executor.submit,
        _run_pipeline_in_thread,
        session_id,
        session["docs_folder"],
        session["reports_folder"],
    )

    return {"session_id": session_id, "status": "running"}


@app.get("/sessions/{session_id}/status", tags=["sessions"])
async def get_status(session_id: str):
    """Poll the pipeline progress for a session."""
    session = _get_session(session_id)
    return {
        "session_id":    session_id,
        "status":        session["status"],
        "files":         session["files"],
        "current_step":  session["current_step"],
        "progress":      session["progress"],
        "error":         session["error"],
        "created_at":    session["created_at"],
        "started_at":    session["started_at"],
        "completed_at":  session["completed_at"],
    }


@app.get("/sessions/{session_id}/report", tags=["sessions"])
async def get_report(session_id: str):
    """
    Retrieve the completed analysis report as text.
    Returns 404 if the session is not yet complete.
    """
    session = _get_session(session_id)
    if session["status"] != "complete":
        raise HTTPException(
            status_code=404,
            detail=f"Report not available — current status: {session['status']}",
        )

    report_path = session["report_path"]
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    content = Path(report_path).read_text()
    return {"session_id": session_id, "content": content, "report_path": report_path}


@app.get("/sessions/{session_id}/report/download", tags=["sessions"])
async def download_report(session_id: str):
    """Download the final report as a markdown file."""
    session = _get_session(session_id)
    if session["status"] != "complete":
        raise HTTPException(status_code=404, detail="Report not yet available")

    report_path = session["report_path"]
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        path=report_path,
        media_type="text/markdown",
        filename=f"loan_report_{session_id[:8]}.md",
    )


@app.delete("/sessions/{session_id}", status_code=204, tags=["sessions"])
async def delete_session(session_id: str):
    """Clean up all documents and reports for a session."""
    _get_session(session_id)

    session_dir = os.path.join(BASE_DATA_DIR, "sessions", session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)

    _sessions.pop(session_id, None)
