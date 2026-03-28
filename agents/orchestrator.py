import uuid
from utils.audit import log
from utils.llm import chat
from database.models import Invoice, AuditLog, Session, init_db, seed_sample_data
from agents.extractor import extract_invoice, save_invoice
from agents.validator import run_all_checks
from agents.router import run_routing


def process_invoice(raw_text: str) -> dict:
    """
    Master function — this is the single entry point for every invoice.
    Call this with raw invoice text and it handles everything end to end.
    
    This is the 'plan → act → observe → recover → complete' loop
    that Senitac specifically asked for.
    """

    invoice_id = str(uuid.uuid4())

    print("\n" + "="*60)
    print(f"NEW INVOICE — {invoice_id[:8]}...")
    print("="*60)

    log(invoice_id, "orchestrator", "invoice_received", "started",
        f"New invoice received — assigned id {invoice_id}")

    # ─── STEP 1: EXTRACT ────────────────────────────────────────
    print("\n[1/3] Extracting invoice data...\n")
    extraction = extract_invoice(raw_text, invoice_id)

    if not extraction["success"]:
        log(invoice_id, "orchestrator", "pipeline_complete", "failed",
            f"Extraction failed: {extraction['error']}")
        return {
            "invoice_id": invoice_id,
            "status": "failed",
            "stage": "extraction",
            "reason": extraction["error"]
        }

    invoice_data = extraction["data"]
    save_invoice(invoice_data, invoice_id)

    # ─── STEP 2: VALIDATE ───────────────────────────────────────
    print("\n[2/3] Validating invoice...\n")
    validation = run_all_checks(invoice_data, invoice_id)

    if not validation["passed"]:
        # Update invoice status in DB
        _update_status(invoice_id, "rejected")

        log(invoice_id, "orchestrator", "pipeline_complete", "rejected",
            f"Validation failed: {' | '.join(validation['issues'])}")

        return {
            "invoice_id": invoice_id,
            "status": "rejected",
            "stage": "validation",
            "issues": validation["issues"],
            "invoice_data": invoice_data
        }

    # ─── STEP 3: ROUTE ──────────────────────────────────────────
    print("\n[3/3] Routing for approval...\n")
    routing = run_routing(invoice_data, invoice_id)

    log(invoice_id, "orchestrator", "pipeline_complete", routing["decision"],
        f"Invoice {invoice_data.get('invoice_number')} → {routing['decision'].upper()}")

    return {
        "invoice_id": invoice_id,
        "status": routing["decision"],
        "approver": routing.get("approver"),
        "reason": routing.get("reason"),
        "sla_warning": routing.get("sla_warning", False),
        "invoice_data": invoice_data
    }


def _update_status(invoice_id: str, status: str):
    """Update invoice status in database."""
    session = Session()
    invoice = session.query(Invoice).filter_by(id=invoice_id).first()
    if invoice:
        invoice.status = status
    session.commit()
    session.close()


def get_audit_trail(invoice_id: str) -> list:
    """
    Pull full audit trail for any invoice.
    This is what makes the system trustworthy and explainable.
    """
    session = Session()
    logs = session.query(AuditLog).filter_by(
        invoice_id=invoice_id
    ).order_by(AuditLog.timestamp).all()
    session.close()

    return [
        {
            "time"  : l.timestamp.strftime("%H:%M:%S"),
            "agent" : l.agent,
            "action": l.action,
            "result": l.result,
            "detail": l.detail
        }
        for l in logs
    ]


def print_audit_trail(invoice_id: str):
    """Print full audit trail to console — useful for demo."""
    print(f"\n{'='*60}")
    print(f"AUDIT TRAIL — {invoice_id[:8]}...")
    print(f"{'='*60}")
    for entry in get_audit_trail(invoice_id):
        print(f"[{entry['time']}] [{entry['agent'].upper()}] {entry['action']} → {entry['result']}")
        if entry["detail"]:
            print(f"    {entry['detail']}")