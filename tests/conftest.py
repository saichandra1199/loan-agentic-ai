"""Shared pytest fixtures."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_crew_output():
    """A CrewOutput-like mock with a populated pydantic attribute."""
    output = MagicMock()
    output.pydantic = MagicMock()
    output.pydantic.confidence_score = 80
    output.pydantic.confidence_reason = "All expected fields found; document was complete."
    output.__str__ = lambda self: "Mock analysis result text"
    return output


@pytest.fixture
def low_confidence_crew_output():
    """A CrewOutput mock whose confidence score is below every threshold."""
    output = MagicMock()
    output.pydantic = MagicMock()
    output.pydantic.confidence_score = 30
    output.pydantic.confidence_reason = "Critical data missing — only partial document provided."
    output.__str__ = lambda self: "Partial analysis result"
    return output


@pytest.fixture
def sample_docs():
    return [
        {"filename": "bank_statement.pdf", "content": "Account 12345\nClosing balance 50000"},
        {"filename": "payslip.pdf",        "content": "Employer TechCorp\nNet salary 80000"},
    ]
