from io import BytesIO
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


def format_rupees(value: Any) -> str:
    return f"Rs. {Decimal(str(value)):,.0f}"


def generate_return_pdf(preparation: Dict[str, Any]) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, pageCompression=0)
    styles = getSampleStyleSheet()
    itr_form = preparation.get("itr_form", "ITR-1")
    assessment_year = preparation["assessment_year"]
    story = [Paragraph("TaxWise", styles["Title"]), Paragraph(f"{escape(itr_form)} Preparation Summary - AY {escape(assessment_year)}", styles["Heading2"]), Spacer(1, 6 * mm)]

    def section(title: str, rows: list[list[str]]) -> None:
        story.append(Paragraph(escape(title), styles["Heading3"]))
        safe_rows = [[Paragraph(escape(str(value)), styles["BodyText"]) for value in row] for row in rows]
        column_count = max(len(row) for row in safe_rows)
        table = Table(safe_rows, colWidths=[162 * mm / column_count] * column_count, repeatRows=1)
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey), ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica")]))
        story.extend([table, Spacer(1, 4 * mm)])

    taxpayer = preparation["taxpayer"]
    income = preparation["income"]
    calculation = preparation["calculation"]
    paid = preparation["taxes_paid"]
    section("PERSONAL INFORMATION", [["Name", str(taxpayer["name"])], ["PAN", str(taxpayer["pan"] or "Not provided")], ["Date of birth", str(taxpayer["date_of_birth"] or "Not provided")], ["Residential status", str(taxpayer["residential_status"])]] )
    capital_gains = income.get("capital_gains")
    short_term_gain = getattr(capital_gains, "short_term_capital_gain", 0)
    long_term_gain = getattr(capital_gains, "long_term_capital_gain", 0)
    section("INCOME SUMMARY", [["Salary", f"Rs. {income['salary']:,.0f}"], ["Pension", f"Rs. {income['pension']:,.0f}"], ["House property", f"Rs. {income['house_property']:,.0f}"], ["Other sources", f"Rs. {income['other_sources']:,.0f}"], ["Business or professional income", f"Rs. {income.get('business', 0):,.0f}"], ["Short-term capital gains", f"Rs. {short_term_gain:,.0f}"], ["Long-term capital gains", f"Rs. {long_term_gain:,.0f}"], ["Gross total income", f"Rs. {income['gross_total_income']:,.0f}"]])
    schedules = preparation.get("schedules", {})
    capital_gain_rows = schedules.get("capital_gains", [])
    if capital_gain_rows:
        section("CAPITAL GAINS TRANSACTIONS", [["Asset", "Holding", "Section", "Gain", "Taxable gain", "Tax"]] + [[row["asset_type"], row["holding_period"], row["applicable_section"], format_rupees(row["computed_gain"]), format_rupees(row["taxable_gain"]), format_rupees(row["tax"])] for row in capital_gain_rows])
    business_rows = schedules.get("business_income", [])
    if business_rows:
        section("BUSINESS INCOME SUMMARY (USER-ENTERED)", [["Business", "Nature", "Gross receipts", "Net profit / loss", "Presumptive section"]] + [[row["business_name"], row["nature_of_business"], format_rupees(row["gross_receipts"]), format_rupees(row["net_profit_or_loss"]), row.get("presumptive_section") or "Not specified"] for row in business_rows])
    section("TAX COMPUTATION", [["Taxable income", f"Rs. {calculation['taxable_income']:,.0f}"], ["Tax", f"Rs. {calculation['tax']:,.0f}"], ["Rebate", f"Rs. {calculation['rebate']:,.0f}"], ["Surcharge", f"Rs. {calculation['surcharge']:,.0f}"], ["Cess", f"Rs. {calculation['cess']:,.0f}"], ["Total tax", f"Rs. {calculation['total_tax']:,.0f}"]])
    section("TAXES PAID", [["TDS", f"Rs. {paid['tds']:,.0f}"], ["Advance tax", f"Rs. {paid['advance_tax']:,.0f}"], ["Self-assessment tax", f"Rs. {paid['self_assessment_tax']:,.0f}"], ["Total tax paid", f"Rs. {paid['total']:,.0f}"], ["Refund", f"Rs. {calculation['refund']:,.0f}"], ["Tax payable", f"Rs. {calculation['payable']:,.0f}"]])
    accounts = [["Bank", "Account"]] + [[str(account.get("bank_name", "")), str(account.get("account_number", ""))] for account in preparation["bank_accounts"]]
    if len(accounts) > 1:
        section("REFUND BANK DETAILS", accounts)
    limitations = [["Preparation limitation", str(value)] for value in preparation.get("support_status", {}).values() if value not in {"Supported", "Not applicable", "User-entered net profit included"}]
    if limitations:
        section("SUPPORT LIMITATIONS", limitations)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Prepared by TaxWise for review. This is a preparation summary, not an official Income Tax Department return, acknowledgement, ITR-V, or proof of filing. TaxWise does not submit this return to the Income Tax Department. Verify all entries and statutory schedules with a qualified tax professional before filing.", styles["BodyText"]))
    document.build(story)
    return output.getvalue()


def generate_itr1_pdf(preparation: Dict[str, Any]) -> bytes:
    return generate_return_pdf(preparation)