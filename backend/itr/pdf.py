from io import BytesIO
from datetime import datetime, timezone
from typing import Any, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


def generate_itr1_pdf(preparation: Dict[str, Any]) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, pageCompression=0)
    styles = getSampleStyleSheet()
    story = [Paragraph("<b>TaxWise</b>", styles["Title"]), Paragraph("ITR-1 Preparation - AY 2026-27", styles["Heading2"]), Spacer(1, 6 * mm)]

    def section(title: str, rows: list[list[str]]) -> None:
        story.append(Paragraph(title, styles["Heading3"]))
        table = Table(rows, colWidths=[62 * mm, 100 * mm])
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey), ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica")]))
        story.extend([table, Spacer(1, 4 * mm)])

    taxpayer = preparation["taxpayer"]
    income = preparation["income"]
    calculation = preparation["calculation"]
    paid = preparation["taxes_paid"]
    section("PERSONAL INFORMATION", [["Name", str(taxpayer["name"])], ["PAN", str(taxpayer["pan"] or "Not provided")], ["Date of birth", str(taxpayer["date_of_birth"] or "Not provided")], ["Residential status", str(taxpayer["residential_status"])]] )
    section("INCOME", [["Salary", f"Rs. {income['salary']:,.0f}"], ["Pension", f"Rs. {income['pension']:,.0f}"], ["House property", f"Rs. {income['house_property']:,.0f}"], ["Other sources", f"Rs. {income['other_sources']:,.0f}"], ["Gross total income", f"Rs. {income['gross_total_income']:,.0f}"]])
    section("TAX COMPUTATION", [["Taxable income", f"Rs. {calculation['taxable_income']:,.0f}"], ["Tax", f"Rs. {calculation['tax']:,.0f}"], ["Rebate", f"Rs. {calculation['rebate']:,.0f}"], ["Surcharge", f"Rs. {calculation['surcharge']:,.0f}"], ["Cess", f"Rs. {calculation['cess']:,.0f}"], ["Total tax", f"Rs. {calculation['total_tax']:,.0f}"]])
    section("TAXES PAID", [["TDS", f"Rs. {paid['tds']:,.0f}"], ["Advance tax", f"Rs. {paid['advance_tax']:,.0f}"], ["Self-assessment tax", f"Rs. {paid['self_assessment_tax']:,.0f}"], ["Total tax paid", f"Rs. {paid['total']:,.0f}"], ["Refund", f"Rs. {calculation['refund']:,.0f}"], ["Tax payable", f"Rs. {calculation['payable']:,.0f}"]])
    accounts = [["Bank", "Account"]] + [[str(account.get("bank_name", "")), str(account.get("account_number", ""))] for account in preparation["bank_accounts"]]
    if len(accounts) > 1:
        section("REFUND BANK DETAILS", accounts)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Prepared by TaxWise for review. This document is not an Income Tax Department acknowledgement, ITR-V, or proof of filing. TaxWise does not submit this return to the Income Tax Department.", styles["BodyText"]))
    document.build(story)
    return output.getvalue()