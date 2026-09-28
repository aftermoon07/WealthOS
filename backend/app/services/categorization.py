"""
TRANSACTION CATEGORIZATION ENGINE
===================================
Deterministic rule-based categorization.
User overrides always take precedence.

Rules are simple keyword/merchant matches.
No AI — fast, deterministic, testable.
"""
from __future__ import annotations

import re
from typing import Optional


# Merchant → category mapping (case-insensitive prefix/substring match)
# Order matters: first match wins.
MERCHANT_RULES: list[tuple[str, str]] = [
    # Food & Dining
    ("swiggy", "Dining"),
    ("zomato", "Dining"),
    ("dominos", "Dining"),
    ("pizza hut", "Dining"),
    ("mcdonald", "Dining"),
    ("kfc", "Dining"),
    ("starbucks", "Dining"),
    ("cafe coffee day", "Dining"),
    ("blinkit", "Groceries"),
    ("zepto", "Groceries"),
    ("bigbasket", "Groceries"),
    ("dmart", "Groceries"),
    ("reliance fresh", "Groceries"),
    ("more supermarket", "Groceries"),
    # Transport
    ("uber", "Transport"),
    ("ola", "Transport"),
    ("rapido", "Transport"),
    ("metro", "Transport"),
    ("irctc", "Transport"),
    ("makemytrip", "Travel"),
    ("goibibo", "Travel"),
    ("cleartrip", "Travel"),
    # Shopping
    ("amazon", "Shopping"),
    ("flipkart", "Shopping"),
    ("myntra", "Shopping"),
    ("ajio", "Shopping"),
    ("nykaa", "Shopping"),
    ("meesho", "Shopping"),
    # Subscriptions
    ("netflix", "Subscriptions"),
    ("spotify", "Subscriptions"),
    ("hotstar", "Subscriptions"),
    ("primevideo", "Subscriptions"),
    ("youtube premium", "Subscriptions"),
    ("zee5", "Subscriptions"),
    ("sonyliv", "Subscriptions"),
    ("apple", "Subscriptions"),
    ("google", "Subscriptions"),
    # Utilities
    ("bescom", "Utilities"),
    ("tata power", "Utilities"),
    ("bses", "Utilities"),
    ("mahanagar gas", "Utilities"),
    ("airtel", "Utilities"),
    ("jio", "Utilities"),
    ("vodafone", "Utilities"),
    ("vi ", "Utilities"),
    ("bsnl", "Utilities"),
    ("actfib", "Utilities"),
    # Insurance
    ("lic", "Insurance"),
    ("hdfc life", "Insurance"),
    ("icici prudential", "Insurance"),
    ("max life", "Insurance"),
    ("star health", "Insurance"),
    ("bajaj allianz", "Insurance"),
    # Healthcare
    ("apollo", "Healthcare"),
    ("fortis", "Healthcare"),
    ("medplus", "Healthcare"),
    ("1mg", "Healthcare"),
    ("pharmeasy", "Healthcare"),
    ("practo", "Healthcare"),
    # Investment
    ("sip", "Investment"),
    ("mutual fund", "Investment"),
    ("zerodha", "Investment"),
    ("groww", "Investment"),
    ("kuvera", "Investment"),
    ("smallcase", "Investment"),
    ("coin", "Investment"),
    ("paytm money", "Investment"),
    ("icicidirect", "Investment"),
    ("hdfc securities", "Investment"),
    ("angel one", "Investment"),
    # Salary
    ("salary", "Salary"),
    ("payroll", "Salary"),
    ("stipend", "Salary"),
    # Rent
    ("rent", "Rent"),
    # Education
    ("udemy", "Education"),
    ("coursera", "Education"),
    ("byju", "Education"),
    ("unacademy", "Education"),
    # Fuel
    ("petrol", "Fuel"),
    ("diesel", "Fuel"),
    ("hp petrol", "Fuel"),
    ("indian oil", "Fuel"),
    ("bharat petroleum", "Fuel"),
    # ATM / Cash
    ("atm", "Cash Withdrawal"),
    ("cash withdrawal", "Cash Withdrawal"),
    # EMI / Loan
    ("emi", "Loan EMI"),
    ("home loan", "Loan EMI"),
    ("car loan", "Loan EMI"),
    # Credit card
    ("credit card payment", "Credit Card Payment"),
    ("cc payment", "Credit Card Payment"),
]

# Description keyword rules (applied if merchant rules don't match)
DESCRIPTION_RULES: list[tuple[str, str]] = [
    ("salary", "Salary"),
    ("interest credit", "Interest Income"),
    ("dividend", "Dividend"),
    ("refund", "Refund"),
    ("reimbursement", "Reimbursement"),
    ("rent", "Rent"),
    ("emi", "Loan EMI"),
    ("insurance", "Insurance"),
    ("school", "Education"),
    ("college", "Education"),
    ("hospital", "Healthcare"),
    ("pharmacy", "Healthcare"),
    ("electricity", "Utilities"),
    ("water bill", "Utilities"),
    ("gas bill", "Utilities"),
    ("broadband", "Utilities"),
    ("mobile recharge", "Utilities"),
    ("fuel", "Fuel"),
    ("petrol", "Fuel"),
    ("grocery", "Groceries"),
    ("supermarket", "Groceries"),
    ("hotel", "Travel"),
    ("flight", "Travel"),
    ("train", "Travel"),
    ("subscription", "Subscriptions"),
    ("netflix", "Subscriptions"),
    ("transfer", None),  # Don't auto-categorize transfers
]


def categorize_transaction(
    description: str,
    merchant: Optional[str],
    amount: float,
    user_override: Optional[str] = None,
) -> str:
    """
    Categorize a transaction. User override always wins.

    Returns a category string.
    Returns 'Other' if no rule matches.
    """
    if user_override:
        return user_override

    # Try merchant match first
    if merchant:
        merchant_lower = merchant.lower().strip()
        for pattern, category in MERCHANT_RULES:
            if pattern in merchant_lower:
                return category

    # Try description match
    if description:
        desc_lower = description.lower().strip()
        for pattern, category in DESCRIPTION_RULES:
            if pattern in desc_lower:
                return category or "Other"

    return "Other"


def normalize_merchant(raw: Optional[str]) -> Optional[str]:
    """Normalize merchant name: strip UPI suffixes, extra spaces, etc."""
    if not raw:
        return None
    # Remove UPI reference suffixes like "SWIGGY/UPIREF123456"
    cleaned = re.split(r"[/@#]", raw)[0]
    # Remove trailing digits (transaction IDs)
    cleaned = re.sub(r"\d{6,}$", "", cleaned)
    return cleaned.strip().title() or None
