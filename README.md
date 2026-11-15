# Credit Compass — Expert Risk Assessment

A responsive FastAPI + vanilla JS prototype for an explainable five-expert credit-risk system.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 (API docs at /docs).

## Logic used (illustrative)
- **Credit analyst:** credit score and missed-payment penalty.
- **Financial analyst:** estimated debt-to-income (DTI) and savings runway.
- **Banking risk officer:** stability, employment tenure, sector risk and DTI.
- **Fraud specialist:** verification flags reduce confidence sharply.
- **Economic analyst:** stability, savings runway, sector exposure and DTI.
- **Consensus:** weighted average of five 0–100 expert scores; weights are adjustable in UI.
- **Disagreement:** max expert score − min expert score. Spread ≥35 adds a human-review safeguard.
- **Decision gates:** reject if ≥3 fraud flags or consensus <48; approve only if consensus ≥76, spread <35, DTI ≤42%, and no fraud flags; otherwise conditional.
- **Conditions:** DTI >40%, savings below three installment proxies, employment <2 years, fraud flags, low score, or expert conflict add safeguards.

This is an educational demonstration—not a validated underwriting model, financial advice, or a real lending decision. The monthly installment is a simplified proxy, not an amortization calculation. Use fairness, explainability, privacy, model validation and human review before any production use.
