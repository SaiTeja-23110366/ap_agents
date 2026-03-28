import json
from utils.llm import chat
from utils.audit import log
from database.models import Invoice, Session


def extract_invoice(raw_text: str, invoice_id: str) -> dict:
    """
    Takes raw invoice text and uses LLM to extract structured fields.
    Same idea as your professor's pipeline — unstructured input → structured output.
    """

    system_prompt = """You are an invoice extraction specialist.
Extract invoice data from the text provided and return ONLY a valid JSON object.
No explanation, no markdown, no code blocks. Just raw JSON.

Return exactly this structure:
{
    "invoice_number": "string or null",
    "vendor_name": "string or null",
    "po_number": "string or null",
    "quantity": number or null,
    "unit_price": number or null,
    "subtotal": number or null,
    "vat_amount": number or null,
    "total": number or null,
    "due_date": "string or null"
}"""

    user_prompt = f"Extract the invoice data from this text:\n\n{raw_text}"

    log(invoice_id, "extractor", "extraction_started", "running",
        f"Input length: {len(raw_text)} chars")

    try:
        raw_response = chat(system_prompt, user_prompt)

        # Clean response in case model adds backticks anyway
        cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)

        log(invoice_id, "extractor", "extraction_complete", "success",
            f"Extracted: vendor={data.get('vendor_name')}, total={data.get('total')}, po={data.get('po_number')}")

        return {"success": True, "data": data}

    except json.JSONDecodeError as e:
        log(invoice_id, "extractor", "extraction_complete", "failed",
            f"JSON parse error: {e} | Raw response: {raw_response}")
        return {"success": False, "error": f"Could not parse JSON: {e}"}

    except Exception as e:
        log(invoice_id, "extractor", "extraction_complete", "failed", str(e))
        return {"success": False, "error": str(e)}


def save_invoice(data: dict, invoice_id: str) -> Invoice:
    """
    Saves extracted invoice data to the database.
    """
    session = Session()

    invoice = Invoice(
        id=invoice_id,
        invoice_number=data.get("invoice_number"),
        vendor_name=data.get("vendor_name"),
        po_number=data.get("po_number"),
        quantity=data.get("quantity"),
        unit_price=data.get("unit_price"),
        subtotal=data.get("subtotal"),
        vat_amount=data.get("vat_amount"),
        total=data.get("total"),
        due_date=data.get("due_date"),
        status="extracted"
    )

    session.add(invoice)
    session.commit()
    session.close()

    log(invoice_id, "extractor", "invoice_saved", "success",
        f"Invoice {data.get('invoice_number')} saved to database")

    return invoice