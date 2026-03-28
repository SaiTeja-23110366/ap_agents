from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import uuid

# This creates/connects to a local SQLite file called ap_agent.db
engine = create_engine("sqlite:///ap_agent.db", echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


def new_id():
    # Every record gets a unique ID automatically
    return str(uuid.uuid4())


class Vendor(Base):
    __tablename__ = "vendors"

    id           = Column(String, primary_key=True, default=new_id)
    name         = Column(String, nullable=False)
    bank_account = Column(String)          # We flag if this changes suddenly
    is_approved  = Column(Integer, default=1)  # 1 = approved, 0 = blocked
    created_at   = Column(DateTime, default=datetime.utcnow)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id          = Column(String, primary_key=True, default=new_id)
    po_number   = Column(String, nullable=False, unique=True)
    vendor_name = Column(String, nullable=False)
    quantity    = Column(Float)
    unit_price  = Column(Float)
    total       = Column(Float)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"

    id             = Column(String, primary_key=True, default=new_id)
    invoice_number = Column(String, nullable=False)
    vendor_name    = Column(String)
    po_number      = Column(String)        # Links to PurchaseOrder
    quantity       = Column(Float)
    unit_price     = Column(Float)
    subtotal       = Column(Float)
    vat_amount     = Column(Float)
    total          = Column(Float)
    due_date       = Column(String)
    status         = Column(String, default="pending")
    # Status can be: pending, validated, approved, rejected, escalated, paid
    received_at    = Column(DateTime, default=datetime.utcnow)


class ApprovalWorkflow(Base):
    __tablename__ = "approval_workflow"

    id          = Column(String, primary_key=True, default=new_id)
    invoice_id  = Column(String, nullable=False)
    approver    = Column(String)           # Who needs to approve
    decision    = Column(String)           # approved / rejected / pending
    reason      = Column(String)
    decided_at  = Column(DateTime)
    created_at  = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id         = Column(String, primary_key=True, default=new_id)
    invoice_id = Column(String)
    agent      = Column(String)    # Which agent did this — extractor/validator/router
    action     = Column(String)    # What it did
    result     = Column(String)    # What happened
    detail     = Column(Text)      # Full detail for debugging
    timestamp  = Column(DateTime, default=datetime.utcnow)


def init_db():
    # Creates all tables if they don't exist yet
    Base.metadata.create_all(engine)
    print("Database ready.")


def seed_sample_data():
    # Puts some realistic test data in so we can demo immediately
    session = Session()

    # Sample vendor
    if not session.query(Vendor).filter_by(name="Acme Supplies").first():
        session.add(Vendor(
            name="Acme Supplies",
            bank_account="GB29NWBK60161331926819",
            is_approved=1
        ))

    # Sample purchase order — our company ordered 100 units at £50 each
    if not session.query(PurchaseOrder).filter_by(po_number="PO-2024-001").first():
        session.add(PurchaseOrder(
            po_number="PO-2024-001",
            vendor_name="Acme Supplies",
            quantity=100,
            unit_price=50.0,
            total=5000.0
        ))

    session.commit()
    session.close()
    print("Sample data seeded.")