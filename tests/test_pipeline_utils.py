"""Tests for pipeline.py utility functions — format_docs, save_agent_report, check_confidence."""
import pytest
from unittest.mock import MagicMock, patch

from pipeline import check_confidence, format_docs, save_agent_report


# ---------------------------------------------------------------------------
# format_docs
# ---------------------------------------------------------------------------

class TestFormatDocs:
    def test_empty_list(self):
        assert format_docs([]) == "No documents of this type provided."

    def test_single_document(self):
        docs = [{"filename": "bank.pdf", "content": "balance 50000"}]
        result = format_docs(docs)
        assert "### File: bank.pdf" in result
        assert "balance 50000" in result

    def test_multiple_documents_separated_by_divider(self):
        docs = [
            {"filename": "a.pdf", "content": "content A"},
            {"filename": "b.pdf", "content": "content B"},
        ]
        result = format_docs(docs)
        assert "### File: a.pdf" in result
        assert "### File: b.pdf" in result
        assert "---" in result   # separator between docs

    def test_preserves_content_exactly(self):
        docs = [{"filename": "test.pdf", "content": "line1\nline2\n  indented"}]
        result = format_docs(docs)
        assert "line1\nline2\n  indented" in result

    def test_returns_string(self):
        assert isinstance(format_docs([]), str)
        assert isinstance(format_docs([{"filename": "x.pdf", "content": "y"}]), str)


# ---------------------------------------------------------------------------
# save_agent_report
# ---------------------------------------------------------------------------

class TestSaveAgentReport:
    def test_creates_file_in_specified_folder(self, tmp_path):
        folder = str(tmp_path / "agents")
        save_agent_report("bank_statement", "# Report\nContent", folder)
        expected = tmp_path / "agents" / "bank_statement_report.md"
        assert expected.exists()

    def test_file_content_matches(self, tmp_path):
        content = "# ITR Analysis\nGross income: 1800000"
        save_agent_report("itr", content, str(tmp_path))
        result = (tmp_path / "itr_report.md").read_text()
        assert result == content

    def test_creates_directory_if_missing(self, tmp_path):
        nested = str(tmp_path / "deep" / "nested" / "agents")
        save_agent_report("payslip", "content", nested)
        assert (tmp_path / "deep" / "nested" / "agents" / "payslip_report.md").exists()

    def test_overwrites_existing_report(self, tmp_path):
        folder = str(tmp_path)
        save_agent_report("cibil", "old content", folder)
        save_agent_report("cibil", "new content", folder)
        assert (tmp_path / "cibil_report.md").read_text() == "new content"


# ---------------------------------------------------------------------------
# check_confidence
# ---------------------------------------------------------------------------

class TestCheckConfidence:
    def test_above_threshold_does_not_call_ask_human(self, mock_crew_output):
        """confidence_score=80 is above bank_statement threshold (65) — no human input."""
        with patch("pipeline.ask_human") as mock_ask:
            result = check_confidence("bank_statement", mock_crew_output, {})
        mock_ask.run.assert_not_called()
        assert result == {}   # inputs unchanged

    def test_below_threshold_calls_ask_human(self, low_confidence_crew_output):
        """confidence_score=30 is below all thresholds — human input requested."""
        with patch("pipeline.ask_human") as mock_ask:
            mock_ask.run.return_value = "Clarification: income is 150000/month"
            result = check_confidence("bank_statement", low_confidence_crew_output, {})
        mock_ask.run.assert_called_once()
        assert "bank_statement_human_clarification" in result
        assert result["bank_statement_human_clarification"] == "Clarification: income is 150000/month"

    def test_clarification_stored_with_agent_name_key(self, low_confidence_crew_output):
        with patch("pipeline.ask_human") as mock_ask:
            mock_ask.run.return_value = "Some clarification"
            result = check_confidence("cibil", low_confidence_crew_output, {})
        assert "cibil_human_clarification" in result

    def test_existing_inputs_preserved(self, mock_crew_output):
        existing = {"bank_statement_docs": "### File: bank.pdf\ncontent"}
        with patch("pipeline.ask_human"):
            result = check_confidence("itr", mock_crew_output, existing)
        assert result["bank_statement_docs"] == existing["bank_statement_docs"]

    def test_no_pydantic_output_returns_inputs_unchanged(self):
        output = MagicMock()
        output.pydantic = None
        original = {"key": "value"}
        result = check_confidence("payslip", output, original)
        assert result == original

    def test_summary_agent_uses_higher_threshold(self, mock_crew_output):
        """Summary threshold is 75. score=80 should pass without asking human."""
        mock_crew_output.pydantic.confidence_score = 80
        with patch("pipeline.ask_human") as mock_ask:
            check_confidence("summary", mock_crew_output, {})
        mock_ask.run.assert_not_called()

    def test_summary_below_threshold(self, mock_crew_output):
        """Summary threshold is 75. score=70 should trigger human input."""
        mock_crew_output.pydantic.confidence_score = 70
        with patch("pipeline.ask_human") as mock_ask:
            mock_ask.run.return_value = "More info"
            check_confidence("summary", mock_crew_output, {})
        mock_ask.run.assert_called_once()
