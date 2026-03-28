import uuid
from database.models import init_db, seed_sample_data
from agents.extractor import extract_invoice, save_invoice

# Initialize DB
init_db()
seed_sample_data()

# Read our sample invoice
with open("data/sample_invoice.txt", "r") as f:
    raw_text = f.read()

# Give this invoice a unique ID
invoice_id = str(uuid.uuid4())
print(f"\nProcessing invoice ID: {invoice_id}\n")

# Extract
result = extract_invoice(raw_text, invoice_id)

if result["success"]:
    print("\nExtracted data:")
    for key, value in result["data"].items():
        print(f"  {key}: {value}")

    # Save to DB
    save_invoice(result["data"], invoice_id)
    print("\nInvoice saved to database successfully.")
else:
    print(f"\nExtraction failed: {result['error']}")