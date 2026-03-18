"""
Generate sample loan application PDFs for testing.
All files are written directly to data/documents/.
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUTPUT_DIR = "data/documents"

user_profile = {
    "name":           "ARJUN K. VERMA",
    "address":        "45/B, Green Avenue, Sector 12, Tech City, 560001",
    "mobile":         "+91-98765-43210",
    "email":          "arjun.verma@example.com",
    "pan_tax_id":     "ABCDE1234F",
    "dob":            "15-Aug-1990",
    "employer":       "TechGlobal Solutions Pvt Ltd",
    "designation":    "Senior Software Engineer",
    "bank_name":      "CITIZEN TRUST BANK",
    "account_number": "112233445566",
    "monthly_gross":  150000.00,
    "net_salary":     132000.00,
}


def _path(filename: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, filename)


def _add_watermark(c: canvas.Canvas) -> None:
    c.saveState()
    c.translate(300, 400)
    c.rotate(45)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.setFont("Helvetica-Bold", 100)
    c.drawCentredString(0, 0, "SAMPLE POC")
    c.restoreState()


# ---------------------------------------------------------------------------
# Payslip (October 2023)
# ---------------------------------------------------------------------------
def generate_payslip(data: dict, filename: str = "payslip.pdf") -> None:
    c = canvas.Canvas(_path(filename), pagesize=letter)
    _add_watermark(c)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, f"PAYSLIP: {data['employer']}")
    c.setFont("Helvetica", 10)
    c.drawString(50, 735, "Month: October 2023")

    c.line(50, 720, 550, 720)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 700, "Employee Details")
    c.setFont("Helvetica", 10)

    y = 680
    c.drawString(50, y, f"Name: {data['name']}")
    c.drawString(300, y, f"Designation: {data['designation']}")
    y -= 20
    c.drawString(50, y, "ID No: EMP-9090")
    c.drawString(300, y, f"Tax ID (PAN): {data['pan_tax_id']}")
    y -= 20
    c.drawString(50, y, f"Bank Acc: {data['account_number']}")

    y -= 40
    c.line(50, y, 550, y)
    c.drawString(50, y - 15, "Earnings")
    c.drawString(200, y - 15, "Amount")
    c.drawString(300, y - 15, "Deductions")
    c.drawString(450, y - 15, "Amount")
    y -= 20
    c.line(50, y, 550, y)

    y -= 20
    c.drawString(50, y, "Basic Salary")
    c.drawString(200, y, f"{data['monthly_gross'] * 0.5:.2f}")
    c.drawString(300, y, "Tax (TDS)")
    c.drawString(450, y, "15000.00")

    y -= 20
    c.drawString(50, y, "HRA")
    c.drawString(200, y, f"{data['monthly_gross'] * 0.3:.2f}")
    c.drawString(300, y, "Provident Fund")
    c.drawString(450, y, "3000.00")

    y -= 20
    c.drawString(50, y, "Special Allowance")
    c.drawString(200, y, f"{data['monthly_gross'] * 0.2:.2f}")

    y -= 40
    c.line(50, y, 550, y)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y - 20, "Total Earnings")
    c.drawString(200, y - 20, f"{data['monthly_gross']:.2f}")
    c.drawString(300, y - 20, "Net Pay:")
    c.drawString(450, y - 20, f"{data['net_salary']:.2f}")

    c.save()
    print(f"Generated: {_path(filename)}")


# ---------------------------------------------------------------------------
# Bank Statement — 6 months (May – October 2023)
# ---------------------------------------------------------------------------
def generate_bank_statement(data: dict, filename: str = "bank_statement.pdf") -> None:
    months = [
        ("May 2023",  "01-May", "31-May", "05-May"),
        ("Jun 2023",  "01-Jun", "30-Jun", "05-Jun"),
        ("Jul 2023",  "01-Jul", "31-Jul", "05-Jul"),
        ("Aug 2023",  "01-Aug", "31-Aug", "05-Aug"),
        ("Sep 2023",  "01-Sep", "30-Sep", "05-Sep"),
        ("Oct 2023",  "01-Oct", "31-Oct", "05-Oct"),
    ]

    # Recurring monthly transactions beyond the salary credit
    recurring = [
        ("EMI - HOME LOAN SBI",   25000.0, 0.0),
        ("EMI - CAR LOAN HDFC",    8500.0, 0.0),
        ("ELECTRICITY BILL",        2200.0, 0.0),
        ("BROADBAND + OTT",          1800.0, 0.0),
        ("GROCERY / RETAIL",         5000.0, 0.0),
        ("ATM WITHDRAWAL",           5000.0, 0.0),
    ]

    c = canvas.Canvas(_path(filename), pagesize=letter)
    _add_watermark(c)

    # Header (first page)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 750, data["bank_name"])
    c.setFont("Helvetica", 10)
    c.drawString(50, 735, "Statement Period: 01-May-2023 to 31-Oct-2023  (6 months)")

    c.line(50, 720, 550, 720)
    c.drawString(50, 700, data["name"])
    c.drawString(50, 685, data["address"])
    c.drawString(400, 700, f"Account: {data['account_number']}")
    c.drawString(400, 685, "Type: Savings")

    # Column headers
    y = 655
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50,  y, "Date")
    c.drawString(120, y, "Description")
    c.drawString(330, y, "Debit")
    c.drawString(395, y, "Credit")
    c.drawString(465, y, "Balance")
    c.line(50, y - 5, 550, y - 5)

    c.setFont("Helvetica", 9)
    y -= 20
    balance = 52000.0

    for month_label, open_date, _, salary_date in months:
        # Opening balance row
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y, open_date)
        c.drawString(120, y, f"Opening Balance — {month_label}")
        c.drawString(465, y, f"{balance:,.2f}")
        c.setFont("Helvetica", 9)
        y -= 14

        # Salary credit
        balance += data["net_salary"]
        c.drawString(50, y, salary_date)
        c.drawString(120, y, "SALARY CREDIT - TECHGLOBAL")
        c.drawString(395, y, f"{data['net_salary']:,.2f}")
        c.drawString(465, y, f"{balance:,.2f}")
        y -= 14

        # Recurring debits
        for desc, debit, credit in recurring:
            balance = balance - debit + credit
            c.drawString(50, y, "—")
            c.drawString(120, y, desc)
            if debit:
                c.drawString(330, y, f"{debit:,.2f}")
            if credit:
                c.drawString(395, y, f"{credit:,.2f}")
            c.drawString(465, y, f"{balance:,.2f}")
            y -= 14

            # Page break
            if y < 80:
                c.showPage()
                _add_watermark(c)
                y = 750
                c.setFont("Helvetica", 9)

        y -= 6  # spacing between months

    c.line(50, y, 550, y)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(330, y - 18, "Closing Balance (31-Oct-2023):")
    c.drawString(465, y - 18, f"{balance:,.2f}")

    c.save()
    print(f"Generated: {_path(filename)}")


# ---------------------------------------------------------------------------
# ITR — two assessment years
# ---------------------------------------------------------------------------
def generate_itr(data: dict, filename: str = "itr.pdf") -> None:
    c = canvas.Canvas(_path(filename), pagesize=letter)
    _add_watermark(c)

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 750, "INDIAN INCOME TAX RETURN VERIFICATION FORM")

    for ay, gross, tds in [("2023-24", data["monthly_gross"] * 12, 180000),
                            ("2022-23", data["monthly_gross"] * 12 * 0.9, 162000)]:
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(300, 730 if ay == "2023-24" else 420, f"Assessment Year: {ay}")

        y = 680 if ay == "2023-24" else 370
        c.line(50, y + 10, 550, y + 10)
        c.setFont("Helvetica", 10)
        c.drawString(50, y, "PERSONAL INFORMATION")
        y -= 20
        c.drawString(50, y, f"Name: {data['name']}")
        c.drawString(350, y, f"PAN: {data['pan_tax_id']}")
        y -= 20
        c.drawString(50, y, f"Address: {data['address']}")
        y -= 20
        c.drawString(50, y, "Status: INDIVIDUAL")

        y -= 40
        c.line(50, y + 10, 550, y + 10)
        c.drawString(50, y, "INCOME COMPUTATION")
        y -= 20
        taxable = gross - 150000
        for label, val in [
            ("1. Gross Total Income", gross),
            ("2. Deductions (80C, 80D, NPS)", 150000),
            ("3. Total Taxable Income", taxable),
            (f"4. TDS Deducted by Employer", tds),
        ]:
            c.drawString(50, y, label)
            c.drawString(450, y, f"{val:,.2f}")
            y -= 20

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y - 10, f"E-Filing Acknowledgement: {'778899001122' if ay == '2023-24' else '667788990011'}")
        c.drawString(50, y - 25, f"Date of Filing: {'31-Jul-2023' if ay == '2023-24' else '29-Jul-2022'}")

    c.save()
    print(f"Generated: {_path(filename)}")


# ---------------------------------------------------------------------------
# CIBIL / Credit Report
# ---------------------------------------------------------------------------
def generate_credit_report(data: dict, filename: str = "credit_report.pdf") -> None:
    c = canvas.Canvas(_path(filename), pagesize=letter)
    _add_watermark(c)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 750, "CIBIL / CREDIT INFORMATION REPORT")

    c.rect(50, 650, 500, 80)
    c.setFont("Helvetica-Bold", 40)
    c.drawString(70, 675, "785")
    c.setFont("Helvetica", 12)
    c.drawString(160, 690, "CIBIL TRANSUNION SCORE")
    c.drawString(160, 670, "Risk Grade: Low Risk")

    y = 600
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Consumer Information")
    c.setFont("Helvetica", 10)
    y -= 20
    c.drawString(50, y, f"Name: {data['name']}")
    c.drawString(300, y, f"Date of Birth: {data['dob']}")
    y -= 20
    c.drawString(50, y, f"PAN: {data['pan_tax_id']}")
    c.drawString(300, y, f"Mobile: {data['mobile']}")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Account Summary")
    c.setFont("Helvetica", 10)
    y -= 20
    c.drawString(50, y, "Total Accounts: 3")
    c.drawString(200, y, "Overdue Accounts: 0")
    c.drawString(400, y, "Current Balance: 33,50,000")

    accounts = [
        ("Home Loan — SBI",          "Active",  "₹33,50,000", "No Overdue"),
        ("Car Loan — HDFC Bank",     "Active",  "₹1,02,000",  "No Overdue"),
        ("Credit Card — HDFC Bank",  "Active",  "₹45,000",    "No Overdue"),
        ("Personal Loan — SBI",      "Closed",  "Nil",         "Paid in Full"),
    ]

    y -= 30
    c.line(50, y, 550, y)
    c.setFont("Helvetica-Bold", 10)
    y -= 15
    c.drawString(50, y, "Lender / Type")
    c.drawString(230, y, "Status")
    c.drawString(310, y, "Outstanding")
    c.drawString(430, y, "DPD")
    c.line(50, y - 5, 550, y - 5)
    c.setFont("Helvetica", 10)

    for lender, status, outstanding, dpd in accounts:
        y -= 20
        c.drawString(50, y, lender)
        c.drawString(230, y, status)
        c.drawString(310, y, outstanding)
        c.drawString(430, y, dpd)

    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Hard Inquiries (last 6 months): 1")
    y -= 20
    c.drawString(50, y, "Days Past Due (DPD) in last 12 months: 0")

    c.save()
    print(f"Generated: {_path(filename)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    generate_payslip(user_profile)
    generate_bank_statement(user_profile)
    generate_itr(user_profile)
    generate_credit_report(user_profile)
    print("\nAll documents generated successfully.")
