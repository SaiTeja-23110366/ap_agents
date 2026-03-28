from database.models import init_db, seed_sample_data, Base, engine
from agents.orchestrator import process_invoice, print_audit_trail


def reset_db():
    """Drop all tables and recreate — useful for clean demo runs."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_sample_data()
    print("Database reset and sample data seeded.\n")


def run_scenario(name: str, invoice_text: str):
    """Run a single invoice scenario and print full results."""
    print(f"\n{'#'*60}")
    print(f"SCENARIO: {name}")
    print(f"{'#'*60}")

    result = process_invoice(invoice_text)

    print(f"\n{'─'*60}")
    print(f"RESULT: {result['status'].upper()}")
    if result.get("issues"):
        print("Issues found:")
        for issue in result["issues"]:
            print(f"  - {issue}")
    if result.get("approver"):
        print(f"Approver : {result['approver']}")
    if result.get("reason"):
        print(f"Reason   : {result['reason']}")
    if result.get("sla_warning"):
        print("⚠ SLA WARNING: Payment deadline is approaching!")

    print_audit_trail(result["invoice_id"])


if __name__ == "__main__":

    reset_db()

    # ── SCENARIO 1: Clean invoice — happy path ──────────────────
    run_scenario("Clean invoice — happy path", """
INVOICE
From: Acme Supplies
Invoice Number: INV-2025-001
Invoice Date: 2025-03-28
Due Date: 2025-06-30
Purchase Order Reference: PO-2024-001
Line Items:
- Widget A x 100 units @ £50.00 each = £5,000.00
Subtotal: £5,000.00
VAT (20%): £1,000.00
Total Due: £6,000.00
Bank Details: GB29NWBK60161331926819
""")

    # ── SCENARIO 2: Duplicate invoice ───────────────────────────
    run_scenario("Duplicate invoice detection", """
INVOICE
From: Acme Supplies
Invoice Number: INV-2025-001
Invoice Date: 2025-03-28
Due Date: 2025-06-30
Purchase Order Reference: PO-2024-001
Line Items:
- Widget A x 100 units @ £50.00 each = £5,000.00
Subtotal: £5,000.00
VAT (20%): £1,000.00
Total Due: £6,000.00
Bank Details: GB29NWBK60161331926819
""")

    # ── SCENARIO 3: Missing PO ───────────────────────────────────
    run_scenario("Missing PO number", """
INVOICE
From: Acme Supplies
Invoice Number: INV-2025-002
Invoice Date: 2025-03-28
Due Date: 2025-06-30
Line Items:
- Widget A x 100 units @ £50.00 each = £5,000.00
Subtotal: £5,000.00
VAT (20%): £1,000.00
Total Due: £6,000.00
""")

    # ── SCENARIO 4: Price mismatch ───────────────────────────────
    run_scenario("3-way match — price mismatch", """
INVOICE
From: Acme Supplies
Invoice Number: INV-2025-003
Invoice Date: 2025-03-28
Due Date: 2025-06-30
Purchase Order Reference: PO-2024-001
Line Items:
- Widget A x 100 units @ £75.00 each = £7,500.00
Subtotal: £7,500.00
VAT (20%): £1,500.00
Total Due: £9,000.00
""")

    # ── SCENARIO 5: Unknown vendor ───────────────────────────────
    run_scenario("Unknown vendor — fraud risk", """
INVOICE
From: Suspicious Vendor Ltd
Invoice Number: INV-2025-004
Invoice Date: 2025-03-28
Due Date: 2025-06-30
Purchase Order Reference: PO-2024-001
Line Items:
- Consulting Services x 1 @ £5,000.00
Subtotal: £5,000.00
VAT (20%): £1,000.00
Total Due: £6,000.00
""")

    print("\n" + "="*60)
    print("ALL SCENARIOS COMPLETE")
    print("="*60)