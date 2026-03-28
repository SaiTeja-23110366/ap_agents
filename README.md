# AP Agent — AI Accounts Payable Employee

An autonomous multi-agent system that processes invoices end-to-end 
with zero human intervention for standard cases.

Built as a submission for Senitac's AI AP Employee hiring challenge.

## What it does

- Ingests raw invoice text (PDF, email, manual input)
- Extracts structured data using LLM
- Validates against purchase orders (3-way match)
- Detects duplicate invoices
- Validates VAT calculations
- Routes to correct approver based on amount
- Flags SLA breaches and fraud risk
- Logs every action to a full audit trail

## Scenarios handled

| Scenario | Outcome |
|---|---|
| Clean invoice | Auto-routed to approver |
| Duplicate invoice | Rejected instantly |
| Missing PO number | Flagged for human review |
| Price mismatch | Rejected with specific detail |
| Unknown vendor | Escalated as fraud risk |

## Tech stack

- Python 3.10
- Gemini 1.5 Flash (via OpenAI-compatible SDK)
- SQLite + SQLAlchemy
- pytest

## Setup

1. Clone the repo
2. Install dependencies: `pip install openai sqlalchemy python-dotenv pdfplumber pytest`
3. Copy `.env.example` to `.env` and add your Gemini API key
4. Run: `python main.py`

## Architecture

Orchestrator → Extractor Agent → Validator Agent → Router Agent
                                       ↓
                                  Audit Logger (every step)