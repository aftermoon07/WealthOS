"""
CSV INGESTION PIPELINE
=======================
Parses various CSV formats, normalizes to internal schema,
validates, deduplicates, and categorizes.

Pipeline:
  CSV → Parse → Validate → Normalize → Deduplicate → Categorize → Return
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional


# ─── Normalized Row ────────────────────────────────────────────────────────────

@dataclass
class NormalizedRow:
    date: date
    description: str
    amount: Decimal          # Always positive
    is_debit: bool           # True = money out (expense/transfer), False = money in (income)
    merchant: Optional[str] = None
    reference: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    valid: list[NormalizedRow] = field(default_factory=list)
    invalid: list[dict] = field(default_factory=list)  # {row, error}
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duplicate_candidates: list[dict] = field(default_factory=list)


# ─── Format Detectors ─────────────────────────────────────────────────────────


def _detect_format(headers: list[str]) -> str:
    """Detect CSV format from column headers."""
    h = {c.lower().strip() for c in headers}

    if "debit amount" in h and "credit amount" in h:
        return "HDFC"
    if "withdrawal amt." in h and "deposit amt." in h:
        return "HDFC_ALT"
    if "dr/cr" in h and "amount" in h:
        return "ICICI"
    if "transaction amount" in h and "cr/dr" in h:
        return "AXIS"
    if {"date", "description", "debit", "credit"}.issubset(h):
        return "GENERIC_DEBIT_CREDIT"
    if {"date", "amount", "description"}.issubset(h):
        return "GENERIC_AMOUNT"
    if {"date", "narration", "debit", "credit"}.issubset(h):
        return "KOTAK"
    return "UNKNOWN"


# ─── Date Parsers ─────────────────────────────────────────────────────────────

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
    "%d %b %Y", "%d %B %Y", "%d/%m/%y",
]


def _parse_date(val: str) -> Optional[date]:
    from datetime import datetime
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(val: str) -> Optional[Decimal]:
    if not val or not val.strip():
        return None
    cleaned = val.strip().replace(",", "").replace("₹", "").replace("Rs", "").replace("INR", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


# ─── Row Normalizers per Format ────────────────────────────────────────────────


def _normalize_generic_debit_credit(row: dict) -> Optional[tuple[NormalizedRow, Optional[str]]]:
    """date, description, debit, credit"""
    d = _parse_date(row.get("date", ""))
    if not d:
        return None, "Invalid date"

    desc = (row.get("description") or row.get("narration") or "").strip()
    debit = _parse_amount(row.get("debit", ""))
    credit = _parse_amount(row.get("credit", ""))

    if debit and debit > 0:
        return NormalizedRow(date=d, description=desc, amount=debit, is_debit=True, raw=row), None
    elif credit and credit > 0:
        return NormalizedRow(date=d, description=desc, amount=credit, is_debit=False, raw=row), None
    return None, "No debit or credit amount"


def _normalize_generic_amount(row: dict) -> Optional[tuple[NormalizedRow, Optional[str]]]:
    """date, amount (positive=credit, negative=debit), description"""
    d = _parse_date(row.get("date", ""))
    if not d:
        return None, "Invalid date"

    desc = (row.get("description") or row.get("narration") or "").strip()
    amt = _parse_amount(row.get("amount", ""))
    if amt is None:
        return None, "Invalid amount"

    is_debit = amt < 0
    return NormalizedRow(date=d, description=desc, amount=abs(amt), is_debit=is_debit, raw=row), None


def _normalize_hdfc(row: dict) -> Optional[tuple[NormalizedRow, Optional[str]]]:
    """HDFC format: Date, Narration, Value Dat, Ref No, Debit Amount, Credit Amount"""
    keys = {k.lower().strip(): v for k, v in row.items()}
    d = _parse_date(keys.get("date", ""))
    if not d:
        return None, "Invalid date"

    desc = (keys.get("narration") or keys.get("description") or "").strip()
    debit = _parse_amount(keys.get("debit amount", "") or keys.get("withdrawal amt.", ""))
    credit = _parse_amount(keys.get("credit amount", "") or keys.get("deposit amt.", ""))
    ref = keys.get("ref no.", "") or keys.get("chq./ref.no.", "")

    if debit and debit > 0:
        return NormalizedRow(date=d, description=desc, amount=debit, is_debit=True, reference=ref, raw=row), None
    elif credit and credit > 0:
        return NormalizedRow(date=d, description=desc, amount=credit, is_debit=False, reference=ref, raw=row), None
    return None, "No debit or credit amount"


FORMAT_NORMALIZERS = {
    "HDFC": _normalize_hdfc,
    "HDFC_ALT": _normalize_hdfc,
    "GENERIC_DEBIT_CREDIT": _normalize_generic_debit_credit,
    "KOTAK": _normalize_generic_debit_credit,
    "GENERIC_AMOUNT": _normalize_generic_amount,
    "UNKNOWN": _normalize_generic_debit_credit,  # best effort
}


# ─── Main Ingestion Function ───────────────────────────────────────────────────


def parse_bank_csv(
    content: str,
    existing_fingerprints: Optional[set[str]] = None,
) -> ParseResult:
    """
    Parse a bank/credit card CSV.
    Returns ParseResult with valid rows, invalid rows, warnings, and duplicate candidates.
    Does NOT write to the database — caller handles persistence.
    """
    result = ParseResult()
    existing_fingerprints = existing_fingerprints or set()

    try:
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            result.errors.append("CSV has no headers")
            return result

        headers = list(reader.fieldnames)
        fmt = _detect_format(headers)
        if fmt == "UNKNOWN":
            result.warnings.append(
                f"Unrecognized CSV format. Headers found: {headers}. Attempting best-effort parse."
            )

        normalizer = FORMAT_NORMALIZERS.get(fmt, _normalize_generic_debit_credit)
        rows = list(reader)

        for i, row in enumerate(rows, start=2):  # start=2 because row 1 is header
            # Skip obviously blank rows
            if not any(v.strip() for v in row.values() if v):
                continue

            normalized, error = normalizer(row)

            if error or normalized is None:
                result.invalid.append({
                    "row_number": i,
                    "raw": dict(row),
                    "error": error or "Failed to normalize",
                })
                continue

            # Fingerprint for deduplication
            fp = f"{normalized.date}|{normalized.amount}|{normalized.description[:40]}"
            if fp in existing_fingerprints:
                result.duplicate_candidates.append({
                    "row_number": i,
                    "date": str(normalized.date),
                    "amount": str(normalized.amount),
                    "description": normalized.description,
                    "reason": "Matches existing transaction (date + amount + description)",
                })
                continue

            result.valid.append(normalized)

    except Exception as exc:
        result.errors.append(f"Parse error: {exc}")

    return result
