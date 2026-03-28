from database.models import AuditLog, Session
from datetime import datetime


def log(invoice_id: str, agent: str, action: str, result: str, detail: str = ""):
    """
    Call this after EVERY action any agent takes.
    This is what makes the system auditable and trustworthy.
    
    Example:
        log("inv-123", "validator", "duplicate_check", "passed", "No duplicate found")
    """
    session = Session()
    entry = AuditLog(
        invoice_id=invoice_id,
        agent=agent,
        action=action,
        result=result,
        detail=detail,
        timestamp=datetime.utcnow()
    )
    session.add(entry)
    session.commit()
    session.close()

    # Also print to console so we can watch it live during demo
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] [{agent.upper()}] {action} → {result}")
    if detail:
        print(f"    {detail}")