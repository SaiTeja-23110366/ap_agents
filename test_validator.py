import uuid
from database.models import init_db, seed_sample_data
from agents.extractor import extract_invoice, save_invoice
from agents.validator import run_all_checks

init_db()
seed_sample_data()

with open("data/sample_invoice.txt", "r") as f:
    raw_text = f.read()

invoice_id = str(uuid.uuid4())
print(f"\nProcessing invoice: {invoice_id}\n")

# Extract first
result = extract_invoice(raw_text, invoice_id)
if not result["success"]:
    print("Extraction failed:", result["error"])
    exit()

save_invoice(result["data"], invoice_id)

# Now validate
print("\n--- Running Validation ---\n")
validation = run_all_checks(result["data"], invoice_id)

if validation["passed"]:
    print("\nAll checks passed — invoice is clean and ready for approval.")
else:
    print(f"\nValidation failed — {len(validation['issues'])} issue(s):")
    for issue in validation["issues"]:
        print(f"  - {issue}")