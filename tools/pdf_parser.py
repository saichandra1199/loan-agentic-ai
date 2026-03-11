import pdfplumber
import os

def parse_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    return text


def classify_document(filename: str, content: str) -> str:
    """
    Classify document type based on filename keywords and content hints.
    Returns one of: bank_statement, itr, payslip, cibil, property, unknown
    """
    name = filename.lower()
    content_lower = content.lower()

    if any(k in name for k in ["bank", "statement", "account"]):
        return "bank_statement"
    elif any(k in name for k in ["itr", "income_tax", "tax_return"]):
        return "itr"
    elif any(k in name for k in ["payslip", "salary_slip", "pay_stub", "payroll"]):
        return "payslip"
    elif any(k in name for k in ["cibil", "credit_report", "credit_score", "equifax", "experian"]):
        return "cibil"
    elif any(k in name for k in ["property", "sale_deed", "agreement", "land", "flat", "house"]):
        return "property"
    # Fallback: content-based detection
    elif "credit score" in content_lower or "repayment history" in content_lower:
        return "cibil"
    elif "salary" in content_lower and "employer" in content_lower:
        return "payslip"
    elif "assessment year" in content_lower or "gross total income" in content_lower:
        return "itr"
    elif "closing balance" in content_lower or "account number" in content_lower:
        return "bank_statement"
    elif "registration" in content_lower and ("sq ft" in content_lower or "plot" in content_lower):
        return "property"
    else:
        return "unknown"


def load_documents(folder: str) -> dict:
    """
    Load all PDFs from folder and classify them.
    Returns a dict: { doc_type: [{"filename": ..., "content": ...}, ...] }
    """
    classified = {
        "bank_statement": [],
        "itr": [],
        "payslip": [],
        "cibil": [],
        "property": [],
        "unknown": []
    }

    for filename in os.listdir(folder):
        if filename.endswith(".pdf"):
            filepath = os.path.join(folder, filename)
            content = parse_pdf(filepath)
            doc_type = classify_document(filename, content)
            classified[doc_type].append({
                "filename": filename,
                "content": content
            })
            print(f"  📄 {filename} → classified as: {doc_type}")

    return classified