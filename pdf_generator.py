from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import random
from datetime import datetime, timedelta

# ==========================================
# 1. DEFINE THE CONSISTENT PERSONA (DATA)
# ==========================================
user_profile = {
    "name": "ARJUN K. VERMA",
    "address": "45/B, Green Avenue, Sector 12, Tech City, 560001",
    "mobile": "+91-98765-43210",
    "email": "arjun.verma@example.com",
    "pan_tax_id": "ABCDE1234F",  # Tax ID / PAN
    "dob": "15-Aug-1990",
    "employer": "TechGlobal Solutions Pvt Ltd",
    "designation": "Senior Software Engineer",
    "bank_name": "CITIZEN TRUST BANK",
    "account_number": "112233445566",
    "monthly_gross": 150000.00,
    "net_salary": 132000.00
}

# Helper to add a "SAMPLE" watermark
def add_watermark(c):
    c.saveState()
    c.translate(300, 400)
    c.rotate(45)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.setFont("Helvetica-Bold", 100)
    c.drawCentredString(0, 0, "SAMPLE POC")
    c.restoreState()

# ==========================================
# 2. GENERATE PAYSLIP
# ==========================================
def generate_payslip(data, filename="payslip.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    add_watermark(c)
    
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, f"PAYSLIP: {data['employer']}")
    c.setFont("Helvetica", 10)
    c.drawString(50, 735, "Month: October 2023")
    
    # Employee Details
    c.line(50, 720, 550, 720)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 700, "Employee Details")
    c.setFont("Helvetica", 10)
    y = 680
    c.drawString(50, y, f"Name: {data['name']}")
    c.drawString(300, y, f"Designation: {data['designation']}")
    y -= 20
    c.drawString(50, y, f"ID No: EMP-9090")
    c.drawString(300, y, f"Tax ID (PAN): {data['pan_tax_id']}")
    y -= 20
    c.drawString(50, y, f"Bank Acc: {data['account_number']}")
    
    # Earnings Table
    y -= 40
    c.line(50, y, 550, y)
    c.drawString(50, y-15, "Earnings")
    c.drawString(200, y-15, "Amount")
    c.drawString(300, y-15, "Deductions")
    c.drawString(450, y-15, "Amount")
    y -= 20
    c.line(50, y, 550, y)
    
    # Data
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
    
    # Total
    y -= 40
    c.line(50, y, 550, y)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y-20, "Total Earnings")
    c.drawString(200, y-20, f"{data['monthly_gross']:.2f}")
    c.drawString(300, y-20, "Net Pay:")
    c.drawString(450, y-20, f"{data['net_salary']:.2f}")
    
    c.save()
    print(f"Generated: {filename}")

# ==========================================
# 3. GENERATE BANK STATEMENT
# ==========================================
def generate_bank_statement(data, filename="bank_statement.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    add_watermark(c)
    
    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 750, data['bank_name'])
    c.setFont("Helvetica", 10)
    c.drawString(50, 735, "Statement Period: 01-Oct-2023 to 31-Oct-2023")
    
    # Customer Info
    c.line(50, 720, 550, 720)
    c.drawString(50, 700, data['name'])
    c.drawString(50, 685, data['address'])
    c.drawString(400, 700, f"Account: {data['account_number']}")
    c.drawString(400, 685, "Type: Savings")
    
    # Transactions
    y = 650
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Date")
    c.drawString(130, y, "Description")
    c.drawString(350, y, "Debit")
    c.drawString(420, y, "Credit")
    c.drawString(490, y, "Balance")
    c.line(50, y-5, 550, y-5)
    
    balance = 52000.00
    transactions = [
        ("01-Oct", "Opening Balance", 0, 0),
        ("05-Oct", "SALARY CREDIT", 0, data['net_salary']),
        ("10-Oct", "ATM WITHDRAWAL", 5000, 0),
        ("15-Oct", "NETFLIX SUB", 600, 0),
        ("20-Oct", "GROCERY STORE", 3500, 0),
    ]
    
    c.setFont("Helvetica", 10)
    y -= 25
    
    # Simulate processing transactions
    for date, desc, debit, credit in transactions:
        balance = balance - debit + credit
        c.drawString(50, y, date)
        c.drawString(130, y, desc)
        c.drawString(350, y, f"{debit:.2f}" if debit > 0 else "")
        c.drawString(420, y, f"{credit:.2f}" if credit > 0 else "")
        c.drawString(490, y, f"{balance:.2f}")
        y -= 20

    c.line(50, y, 550, y)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y-20, "Closing Balance:")
    c.drawString(490, y-20, f"{balance:.2f}")
    
    c.save()
    print(f"Generated: {filename}")

# ==========================================
# 4. GENERATE ITR (Income Tax Return)
# ==========================================
def generate_itr(data, filename="itr.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    add_watermark(c)
    
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 750, "INDIAN INCOME TAX RETURN VERIFICATION FORM")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(300, 730, "Assessment Year: 2023-24")
    
    y = 680
    c.line(50, y+10, 550, y+10)
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "PERSONAL INFORMATION")
    y -= 20
    c.drawString(50, y, f"Name: {data['name']}")
    c.drawString(350, y, f"PAN: {data['pan_tax_id']}")
    y -= 20
    c.drawString(50, y, f"Address: {data['address']}")
    y -= 20
    c.drawString(50, y, f"Status: INDIVIDUAL")
    
    y -= 40
    c.line(50, y+10, 550, y+10)
    c.drawString(50, y, "INCOME COMPUTATION")
    y -= 20
    c.drawString(50, y, "1. Gross Total Income")
    c.drawString(450, y, f"{data['monthly_gross'] * 12:.2f}")
    y -= 20
    c.drawString(50, y, "2. Deductions (80C, etc.)")
    c.drawString(450, y, "150000.00")
    y -= 20
    c.drawString(50, y, "3. Total Taxable Income")
    taxable = (data['monthly_gross'] * 12) - 150000
    c.drawString(450, y, f"{taxable:.2f}")
    y -= 20
    c.drawString(50, y, "4. Total Tax Paid")
    c.drawString(450, y, "125000.00")
    
    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "E-Filing Acknowledgement Number: 778899001122")
    c.drawString(50, y-20, f"Date of Filing: 31-Jul-2023")
    
    c.save()
    print(f"Generated: {filename}")

# ==========================================
# 5. GENERATE CREDIT REPORT
# ==========================================
def generate_credit_report(data, filename="credit_report.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    add_watermark(c)
    
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 750, "CIBIL / CREDIT INFORMATION REPORT")
    
    # Score Section
    c.rect(50, 650, 500, 80)
    c.setFont("Helvetica-Bold", 40)
    c.drawString(70, 675, "785") # The Score
    c.setFont("Helvetica", 12)
    c.drawString(160, 690, "CIBIL TRANSUNION SCORE")
    c.drawString(160, 670, "Risk Grade: Low Risk")
    
    # Personal Info
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
    
    # Account Summary
    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Account Summary")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Total Accounts: 3")
    c.drawString(200, y, "Overdue Accounts: 0")
    c.drawString(400, y, "Current Balance: 45,000")
    
    # List
    y -= 30
    c.line(50, y, 550, y)
    y -= 15
    c.drawString(50, y, "Credit Card - HDFC Bank")
    c.drawString(300, y, "Active")
    c.drawString(450, y, "No Overdue")
    y -= 20
    c.drawString(50, y, "Personal Loan - SBI")
    c.drawString(300, y, "Closed")
    c.drawString(450, y, "Paid in Full")
    
    c.save()
    print(f"Generated: {filename}")

# ==========================================
# EXECUTE
# ==========================================
if __name__ == "__main__":
    generate_payslip(user_profile)
    generate_bank_statement(user_profile)
    generate_itr(user_profile)
    generate_credit_report(user_profile)
    print("\nAll documents generated successfully.")