import uuid
from database.models import init_db, seed_sample_data
from agents.extractor import extract_invoice, save_invoice
from agents.validator import run_all_checks
from agents.router import run_routing

init_db()
seed_sample_data()

with open("data/sample_invoice.txt", "r") as f:
    raw_text = f.read()

invoice_id = str(uuid.uuid4())
print(f"\nProcessing invoice: {invoice_id}\n")

# Extract
result = extract_invoice(raw_text, invoice_id)
if not result["success"]:
    print("Extraction failed:", result["error"])
    exit()
save_invoice(result["data"], invoice_id)

# Validate
print("\n--- Validation ---\n")
validation = run_all_checks(result["data"], invoice_id)
if not validation["passed"]:
    print("Validation failed:", validation["issues"])
    exit()

# Route
print("\n--- Routing ---\n")
routing = run_routing(result["data"], invoice_id)

print(f"\nDecision  : {routing['decision'].upper()}")
print(f"Approver  : {routing.get('approver', 'N/A')}")
print(f"Reason    : {routing.get('reason')}")
if routing.get("sla_warning"):
    print(f"SLA WARNING: Payment deadline is approaching!")