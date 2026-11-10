from documents.itr2_extractor import extract_itr2_candidates


def test_itr2_extractor_preserves_multiple_capital_gain_transactions():
    pages = [
        """PERSONAL INFORMATION
Residential Status: Resident
Citizenship: Indian
Bank: HDFC Bank
Account Number: 501234567890
IFSC: HDFC0001234

Transaction 1
Asset: Listed equity shares
Purchase Date: 10-06-2025
Sale Date: 20-12-2025
Sale Consideration: ₹3,00,000
Acquisition Cost: ₹2,20,000
Transfer Expenses: ₹2,000
STT Paid: Yes

Transaction 2
Asset: Listed equity shares
Purchase Date: 10-05-2023
Sale Date: 15-01-2026
Sale Consideration: ₹5,00,000
Acquisition Cost: ₹3,00,000
Transfer Expenses: ₹2,000
STT Paid: Yes

Transaction 3
Asset: Residential property
Purchase Date: 10-05-2018
Sale Date: 20-02-2026
Sale Consideration: ₹70,00,000
Acquisition Cost: ₹35,00,000
Improvement Cost: ₹5,00,000
Transfer Expenses: ₹1,00,000
"""
    ]
    candidates = extract_itr2_candidates(pages)
    transactions = [item for item in candidates if item.field.startswith("capital_gain_transaction_")]

    assert len(transactions) == 3
    assert transactions[0].value["asset_type"] == "listed_equity_share"
    assert transactions[1].value["sale_consideration"] == "500000"
    assert transactions[2].value["asset_type"] == "immovable_property"
    assert transactions[2].page == 1


def test_itr2_extractor_keeps_page_provenance():
    pages = ["PAGE 1\nName: ignored", "PAGE 2\nMaximum Balance: ₹4,50,000"]
    candidates = extract_itr2_candidates(pages)
    maximum = next(item for item in candidates if item.field == "foreign_maximum_balance")
    assert maximum.page == 2
