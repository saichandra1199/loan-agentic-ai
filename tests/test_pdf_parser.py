"""Tests for tools/pdf_parser.py — document classification and loading."""
import pytest
from unittest.mock import MagicMock, patch

from tools.pdf_parser import classify_document, load_documents


# ---------------------------------------------------------------------------
# classify_document — pure function, no I/O
# ---------------------------------------------------------------------------

class TestClassifyByFilename:
    def test_bank_statement(self):
        assert classify_document("bank_statement.pdf", "") == "bank_statement"

    def test_bank_account(self):
        assert classify_document("account_2023.pdf", "") == "bank_statement"

    def test_itr(self):
        assert classify_document("itr_2023.pdf", "") == "itr"

    def test_income_tax_return(self):
        assert classify_document("income_tax_return.pdf", "") == "itr"

    def test_payslip(self):
        assert classify_document("payslip_oct.pdf", "") == "payslip"

    def test_salary_slip(self):
        assert classify_document("salary_slip.pdf", "") == "payslip"

    def test_cibil(self):
        assert classify_document("cibil_report.pdf", "") == "cibil"

    def test_credit_score(self):
        assert classify_document("credit_score.pdf", "") == "cibil"

    def test_property(self):
        assert classify_document("property_doc.pdf", "") == "property"

    def test_sale_deed(self):
        assert classify_document("sale_deed.pdf", "") == "property"

    def test_flat(self):
        assert classify_document("flat_agreement.pdf", "") == "property"

    def test_unknown_filename(self):
        assert classify_document("random_document.pdf", "") == "unknown"


class TestClassifyByContent:
    def test_cibil_by_credit_score_keyword(self):
        assert classify_document("doc.pdf", "credit score 785 repayment history") == "cibil"

    def test_payslip_by_salary_employer(self):
        assert classify_document("doc.pdf", "salary employer monthly deduction") == "payslip"

    def test_itr_by_assessment_year(self):
        assert classify_document("doc.pdf", "assessment year gross total income") == "itr"

    def test_bank_by_closing_balance(self):
        assert classify_document("doc.pdf", "closing balance account number") == "bank_statement"

    def test_property_by_registration_sqft(self):
        assert classify_document("doc.pdf", "registration sq ft plot area") == "property"

    def test_filename_takes_priority_over_content(self):
        # Filename says itr, content looks like bank — filename wins
        assert classify_document("itr.pdf", "closing balance account number") == "itr"


# ---------------------------------------------------------------------------
# load_documents — mocks pdfplumber to avoid needing real PDFs
# ---------------------------------------------------------------------------

def _make_mock_pdf(text: str):
    """Return a mock pdfplumber PDF context manager returning one page with text."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = text
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


def test_load_documents_classifies_by_filename(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "bank_statement.pdf").write_bytes(b"%PDF-1.4 fake")
    (docs_dir / "itr.pdf").write_bytes(b"%PDF-1.4 fake")

    with patch("pdfplumber.open", return_value=_make_mock_pdf("some content")):
        result = load_documents(str(docs_dir))

    assert len(result["bank_statement"]) == 1
    assert result["bank_statement"][0]["filename"] == "bank_statement.pdf"
    assert len(result["itr"]) == 1
    assert result["itr"][0]["filename"] == "itr.pdf"


def test_load_documents_empty_folder_returns_empty_lists(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    result = load_documents(str(docs_dir))
    for key in ("bank_statement", "itr", "payslip", "cibil", "property"):
        assert result[key] == []


def test_load_documents_unknown_files_go_to_unknown_bucket(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "miscellaneous.pdf").write_bytes(b"%PDF-1.4 fake")

    with patch("pdfplumber.open", return_value=_make_mock_pdf("nothing recognisable here")):
        result = load_documents(str(docs_dir))

    assert len(result["unknown"]) == 1
    assert result["unknown"][0]["filename"] == "miscellaneous.pdf"


def test_load_documents_content_is_extracted(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "bank_statement.pdf").write_bytes(b"%PDF-1.4 fake")

    with patch("pdfplumber.open", return_value=_make_mock_pdf("account number 112233")):
        result = load_documents(str(docs_dir))

    assert "account number 112233" in result["bank_statement"][0]["content"]


def test_load_documents_ignores_non_pdf_files(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "notes.txt").write_text("some notes")
    (docs_dir / "bank_statement.pdf").write_bytes(b"%PDF-1.4 fake")

    with patch("pdfplumber.open", return_value=_make_mock_pdf("account number")):
        result = load_documents(str(docs_dir))

    total_docs = sum(len(v) for v in result.values())
    assert total_docs == 1   # only the PDF
