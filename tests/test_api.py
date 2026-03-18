"""Tests for api.py — FastAPI endpoint behaviour."""
import io
import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api import _sessions, app

client = TestClient(app, raise_server_exceptions=True)

# Minimal valid-looking PDF bytes (not a real PDF — just enough to pass filename check)
FAKE_PDF = b"%PDF-1.4 fake content"


@pytest.fixture(autouse=True)
def clear_sessions():
    """Isolate each test by clearing in-memory session state."""
    _sessions.clear()
    yield
    _sessions.clear()


def upload_one(filename: str = "bank_statement.pdf") -> str:
    """Helper: upload one fake PDF and return its session_id."""
    resp = client.post(
        "/sessions/upload",
        files=[("files", (filename, io.BytesIO(FAKE_PDF), "application/pdf"))],
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_upload_single_pdf_creates_session(self):
        resp = client.post(
            "/sessions/upload",
            files=[("files", ("bank_statement.pdf", io.BytesIO(FAKE_PDF), "application/pdf"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "bank_statement.pdf" in data["files"]

    def test_upload_multiple_pdfs(self):
        files = [
            ("files", ("bank.pdf",   io.BytesIO(FAKE_PDF), "application/pdf")),
            ("files", ("payslip.pdf", io.BytesIO(FAKE_PDF), "application/pdf")),
        ]
        resp = client.post("/sessions/upload", files=files)
        assert resp.status_code == 200
        assert len(resp.json()["files"]) == 2

    def test_upload_non_pdf_returns_400(self):
        resp = client.post(
            "/sessions/upload",
            files=[("files", ("notes.txt", io.BytesIO(b"text"), "text/plain"))],
        )
        assert resp.status_code == 400

    def test_upload_creates_unique_session_ids(self):
        s1 = upload_one("a.pdf")
        s2 = upload_one("b.pdf")
        assert s1 != s2

    def test_upload_saves_files_to_disk(self, tmp_path):
        """Files should be written to the session docs directory."""
        with patch("api.BASE_DATA_DIR", str(tmp_path)):
            resp = client.post(
                "/sessions/upload",
                files=[("files", ("itr.pdf", io.BytesIO(FAKE_PDF), "application/pdf"))],
            )
        session_id = resp.json()["session_id"]
        dest = tmp_path / "sessions" / session_id / "documents" / "itr.pdf"
        assert dest.exists()


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------

class TestAnalyze:
    def test_analyze_returns_running(self):
        session_id = upload_one()
        with patch("api._run_pipeline_in_thread"):
            resp = client.post(f"/sessions/{session_id}/analyze")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_analyze_unknown_session_returns_404(self):
        resp = client.post("/sessions/nonexistent/analyze")
        assert resp.status_code == 404

    def test_analyze_already_running_returns_409(self):
        session_id = upload_one()
        _sessions[session_id]["status"] = "running"
        resp = client.post(f"/sessions/{session_id}/analyze")
        assert resp.status_code == 409

    def test_analyze_already_complete_returns_409(self):
        session_id = upload_one()
        _sessions[session_id]["status"] = "complete"
        resp = client.post(f"/sessions/{session_id}/analyze")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_pending_after_upload(self):
        session_id = upload_one()
        resp = client.get(f"/sessions/{session_id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_status_contains_progress_fields(self):
        session_id = upload_one()
        data = client.get(f"/sessions/{session_id}/status").json()
        assert "progress" in data
        assert "current_step" in data
        assert "files" in data

    def test_status_unknown_session_returns_404(self):
        resp = client.get("/sessions/no-such-session/status")
        assert resp.status_code == 404

    def test_status_reflects_manual_state_change(self):
        session_id = upload_one()
        _sessions[session_id]["status"] = "running"
        _sessions[session_id]["current_step"] = "Running agents…"
        data = client.get(f"/sessions/{session_id}/status").json()
        assert data["status"] == "running"
        assert data["current_step"] == "Running agents…"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class TestReport:
    def test_report_not_available_when_pending(self):
        session_id = upload_one()
        resp = client.get(f"/sessions/{session_id}/report")
        assert resp.status_code == 404

    def test_report_returns_content_when_complete(self, tmp_path):
        session_id = str(uuid.uuid4())
        report_file = tmp_path / "loan_report.md"
        report_file.write_text("# Loan Report\nRecommendation: APPROVE")

        _sessions[session_id] = {
            "status":       "complete",
            "report_path":  str(report_file),
            "files":        ["bank_statement.pdf"],
            "progress":     [],
            "current_step": "Complete",
            "error":        None,
            "created_at":   "2026-01-01T00:00:00+00:00",
            "started_at":   "2026-01-01T00:01:00+00:00",
            "completed_at": "2026-01-01T00:02:00+00:00",
        }

        resp = client.get(f"/sessions/{session_id}/report")
        assert resp.status_code == 200
        body = resp.json()
        assert "# Loan Report" in body["content"]
        assert body["session_id"] == session_id

    def test_report_returns_404_for_missing_file(self):
        session_id = str(uuid.uuid4())
        _sessions[session_id] = {
            "status":       "complete",
            "report_path":  "/nonexistent/path/report.md",
            "files":        [],
            "progress":     [],
            "current_step": "",
            "error":        None,
            "created_at":   "",
            "started_at":   "",
            "completed_at": "",
        }
        resp = client.get(f"/sessions/{session_id}/report")
        assert resp.status_code == 404

    def test_report_unknown_session_returns_404(self):
        resp = client.get("/sessions/ghost/report")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

class TestDownload:
    def test_download_returns_file(self, tmp_path):
        session_id = str(uuid.uuid4())
        report_file = tmp_path / "loan_report.md"
        report_file.write_text("# Report Content")

        _sessions[session_id] = {
            "status":       "complete",
            "report_path":  str(report_file),
            "files":        [],
            "progress":     [],
            "current_step": "",
            "error":        None,
            "created_at":   "",
            "started_at":   "",
            "completed_at": "",
        }

        resp = client.get(f"/sessions/{session_id}/report/download")
        assert resp.status_code == 200
        assert b"# Report Content" in resp.content

    def test_download_not_available_when_pending(self):
        session_id = upload_one()
        resp = client.get(f"/sessions/{session_id}/report/download")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_removes_session(self):
        session_id = upload_one()
        resp = client.delete(f"/sessions/{session_id}")
        assert resp.status_code == 204
        assert session_id not in _sessions

    def test_delete_unknown_session_returns_404(self):
        resp = client.delete("/sessions/phantom")
        assert resp.status_code == 404

    def test_delete_cleans_up_files(self, tmp_path):
        with patch("api.BASE_DATA_DIR", str(tmp_path)):
            # Create a session via upload
            resp = client.post(
                "/sessions/upload",
                files=[("files", ("payslip.pdf", io.BytesIO(FAKE_PDF), "application/pdf"))],
            )
            session_id = resp.json()["session_id"]

            session_dir = tmp_path / "sessions" / session_id
            assert session_dir.exists()

            client.delete(f"/sessions/{session_id}")
            assert not session_dir.exists()
