from datetime import datetime
from utils.audit import log
from utils.llm import chat
from database.models import Invoice, ApprovalWorkflow, Vendor, Session


def check_fraud_risk(invoice_data: dict, invoice_id: str) -> dict:
    """
    Flag if vendor bank account has changed.
    This is one of the biggest fraud vectors in AP —
    someone pretends to be a vendor and changes bank details.
    Always escalate to human, never auto-approve.
    """
    session = Session()
    vendor = session.query(Vendor).filter_by(
        name=invoice_data.get("vendor_name")
    ).first()
    session.close()

    if not vendor:
        log(invoice_id, "router", "fraud_check", "escalate",
            f"Unknown vendor: {invoice_data.get('vendor_name')} — not in approved vendor list")
        return {"escalate": True, "reason": "Unknown vendor — not in approved list"}

    if not vendor.is_approved:
        log(invoice_id, "router", "fraud_check", "escalate",
            f"Vendor {vendor.name} is blocked")
        return {"escalate": True, "reason": f"Vendor {vendor.name} is blocked"}

    log(invoice_id, "router", "fraud_check", "passed",
        f"Vendor {vendor.name} is approved and known")
    return {"escalate": False}


def determine_approver(total: float, invoice_id: str) -> str:
    """
    Approval routing based on invoice amount.
    Every company has different thresholds — this is configurable.
    
    < £1,000      → auto approved
    £1,000-10,000 → manager
    > £10,000     → CFO
    """
    if total < 1000:
        approver = "auto"
        log(invoice_id, "router", "approver_assigned", "auto",
            f"Total £{total} is under £1,000 — auto approved")
    elif total <= 10000:
        approver = "manager"
        log(invoice_id, "router", "approver_assigned", "manager",
            f"Total £{total} requires manager approval")
    else:
        approver = "cfo"
        log(invoice_id, "router", "approver_assigned", "cfo",
            f"Total £{total} requires CFO approval")

    return approver


def check_sla_risk(due_date_str: str, invoice_id: str) -> dict:
    """
    Check if payment due date is approaching.
    If due within 3 days — escalate immediately so it doesn't get missed.
    """
    if not due_date_str:
        log(invoice_id, "router", "sla_check", "skipped",
            "No due date found — skipping SLA check")
        return {"at_risk": False}

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        days_remaining = (due_date - datetime.utcnow()).days

        if days_remaining < 0:
            log(invoice_id, "router", "sla_check", "overdue",
                f"Invoice is {abs(days_remaining)} days overdue!")
            return {"at_risk": True, "reason": f"Invoice is {abs(days_remaining)} days OVERDUE"}

        elif days_remaining <= 3:
            log(invoice_id, "router", "sla_check", "at_risk",
                f"Due in {days_remaining} days — urgent escalation needed")
            return {"at_risk": True, "reason": f"Due in {days_remaining} days — urgent"}

        else:
            log(invoice_id, "router", "sla_check", "passed",
                f"Due in {days_remaining} days — within SLA")
            return {"at_risk": False}

    except ValueError:
        log(invoice_id, "router", "sla_check", "skipped",
            f"Could not parse due date: {due_date_str}")
        return {"at_risk": False}


def create_approval_record(invoice_id: str, approver: str, decision: str, reason: str):
    """
    Save approval decision to database.
    """
    session = Session()
    record = ApprovalWorkflow(
        invoice_id=invoice_id,
        approver=approver,
        decision=decision,
        reason=reason,
        decided_at=datetime.utcnow() if decision != "pending" else None
    )
    session.add(record)

    # Also update invoice status
    invoice = session.query(Invoice).filter_by(id=invoice_id).first()
    if invoice:
        invoice.status = decision

    session.commit()
    session.close()


def run_routing(invoice_data: dict, invoice_id: str) -> dict:
    """
    Master routing function — runs fraud check, SLA check,
    determines approver, and records the decision.
    This is what the orchestrator calls after validation passes.
    """
    log(invoice_id, "router", "routing_started", "running",
        f"Routing invoice {invoice_data.get('invoice_number')}")

    # Step 1 — Fraud check
    fraud = check_fraud_risk(invoice_data, invoice_id)
    if fraud["escalate"]:
        create_approval_record(invoice_id, "compliance_team", "escalated", fraud["reason"])
        log(invoice_id, "router", "routing_complete", "escalated", fraud["reason"])
        return {"decision": "escalated", "reason": fraud["reason"]}

    # Step 2 — SLA check
    sla = check_sla_risk(invoice_data.get("due_date"), invoice_id)
    if sla["at_risk"]:
        # Don't block — just flag urgency alongside normal routing
        log(invoice_id, "router", "sla_warning", "flagged", sla["reason"])

    # Step 3 — Determine approver based on amount
    total    = invoice_data.get("total", 0)
    approver = determine_approver(total, invoice_id)

    # Step 4 — Record decision
    if approver == "auto":
        create_approval_record(invoice_id, "system", "approved",
                               "Auto approved — under £1,000 threshold")
        log(invoice_id, "router", "routing_complete", "approved",
            "Auto approved")
        return {
            "decision": "approved",
            "approver": "system",
            "sla_warning": sla["at_risk"],
            "reason": "Auto approved — under threshold"
        }
    else:
        create_approval_record(invoice_id, approver, "pending",
                               f"Awaiting {approver} approval")
        log(invoice_id, "router", "routing_complete", "pending",
            f"Sent to {approver} for approval")
        return {
            "decision": "pending",
            "approver": approver,
            "sla_warning": sla["at_risk"],
            "reason": f"Awaiting {approver} approval"
        }