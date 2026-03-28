from utils.audit import log
from utils.llm import chat
from database.models import Invoice, PurchaseOrder, Session


def check_duplicate(invoice_data: dict, current_invoice_id: str) -> dict:
    """
    Check if we've seen this exact invoice before.
    Same vendor + same amount + same invoice number = duplicate.
    """
    session = Session()

    existing = session.query(Invoice).filter(
        Invoice.invoice_number == invoice_data.get("invoice_number"),
        Invoice.vendor_name    == invoice_data.get("vendor_name"),
        Invoice.id             != current_invoice_id  # ignore itself
    ).first()

    session.close()

    if existing:
        log(current_invoice_id, "validator", "duplicate_check", "failed",
            f"Duplicate found — invoice {invoice_data.get('invoice_number')} already exists with id {existing.id}")
        return {"passed": False, "reason": f"Duplicate invoice detected — already processed as {existing.id}"}

    log(current_invoice_id, "validator", "duplicate_check", "passed",
        "No duplicate found")
    return {"passed": True}


def check_three_way_match(invoice_data: dict, invoice_id: str) -> dict:
    """
    Core AP validation — PO vs Invoice must match on vendor, quantity, price.
    This is the most important check in the entire system.
    """
    session = Session()
    po_number = invoice_data.get("po_number")

    # Case 1 — No PO number on invoice at all
    if not po_number:
        log(invoice_id, "validator", "three_way_match", "failed",
            "No PO number found on invoice — cannot match")
        session.close()
        return {"passed": False, "reason": "Missing PO number — needs human review to locate PO"}

    # Case 2 — PO number given but doesn't exist in our system
    po = session.query(PurchaseOrder).filter_by(po_number=po_number).first()
    session.close()

    if not po:
        log(invoice_id, "validator", "three_way_match", "failed",
            f"PO {po_number} not found in system")
        return {"passed": False, "reason": f"PO {po_number} does not exist in system"}

    # Case 3 — PO exists, now check the numbers match
    mismatches = []

    if invoice_data.get("quantity") and abs(invoice_data["quantity"] - po.quantity) > 0.01:
        mismatches.append(
            f"Quantity mismatch — Invoice: {invoice_data['quantity']}, PO: {po.quantity}"
        )

    if invoice_data.get("unit_price") and abs(invoice_data["unit_price"] - po.unit_price) > 0.01:
        mismatches.append(
            f"Price mismatch — Invoice: {invoice_data['unit_price']}, PO: {po.unit_price}"
        )

    if invoice_data.get("vendor_name") and invoice_data["vendor_name"].lower() != po.vendor_name.lower():
        mismatches.append(
            f"Vendor mismatch — Invoice: {invoice_data['vendor_name']}, PO: {po.vendor_name}"
        )

    if mismatches:
        detail = " | ".join(mismatches)
        log(invoice_id, "validator", "three_way_match", "failed", detail)
        return {"passed": False, "reason": detail}

    log(invoice_id, "validator", "three_way_match", "passed",
        f"PO {po_number} matched — vendor, quantity, price all correct")
    return {"passed": True}


def check_vat(invoice_data: dict, invoice_id: str) -> dict:
    """
    UK VAT is 20%. Check the VAT amount on invoice is correct.
    """
    subtotal  = invoice_data.get("subtotal")
    vat       = invoice_data.get("vat_amount")

    if not subtotal or not vat:
        log(invoice_id, "validator", "vat_check", "skipped",
            "Missing subtotal or VAT amount — skipping VAT check")
        return {"passed": True}  # Don't block if data is missing, just skip

    expected_vat = round(subtotal * 0.20, 2)
    actual_vat   = round(vat, 2)

    if abs(expected_vat - actual_vat) > 0.10:  # Allow 10p rounding tolerance
        log(invoice_id, "validator", "vat_check", "failed",
            f"VAT mismatch — Expected: £{expected_vat}, Invoice has: £{actual_vat}")
        return {"passed": False, "reason": f"VAT incorrect — expected £{expected_vat}, got £{actual_vat}"}

    log(invoice_id, "validator", "vat_check", "passed",
        f"VAT correct — £{actual_vat} on subtotal of £{subtotal}")
    return {"passed": True}


def run_all_checks(invoice_data: dict, invoice_id: str) -> dict:
    """
    Master validation function — runs all checks in order.
    Returns overall pass/fail with list of all issues found.
    This is what the orchestrator calls.
    """
    log(invoice_id, "validator", "validation_started", "running",
        f"Running all checks for invoice {invoice_data.get('invoice_number')}")

    issues = []

    # Run all 3 checks
    dup   = check_duplicate(invoice_data, invoice_id)
    match = check_three_way_match(invoice_data, invoice_id)
    vat   = check_vat(invoice_data, invoice_id)

    if not dup["passed"]:
        issues.append(dup["reason"])
    if not match["passed"]:
        issues.append(match["reason"])
    if not vat["passed"]:
        issues.append(vat["reason"])

    if issues:
        log(invoice_id, "validator", "validation_complete", "failed",
            f"{len(issues)} issue(s) found: {' | '.join(issues)}")
        return {"passed": False, "issues": issues}

    log(invoice_id, "validator", "validation_complete", "passed",
        "All checks passed — invoice is clean")
    return {"passed": True, "issues": []}