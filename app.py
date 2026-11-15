from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict

app = FastAPI(title="Credit Compass | Expert Risk System")
app.mount("/static", StaticFiles(directory="static"), name="static")

class Applicant(BaseModel):
    name: str = "New Applicant"
    income: float = Field(ge=0)
    monthly_debt: float = Field(ge=0)
    loan_amount: float = Field(ge=0)
    tenure_months: int = Field(ge=1, le=600)
    credit_score: int = Field(ge=300, le=900)
    missed_payments: int = Field(ge=0, le=100)
    employment_years: float = Field(ge=0)
    savings: float = Field(ge=0)
    fraud_flags: int = Field(ge=0, le=20)
    sector_risk: int = Field(ge=1, le=5)
    stability: int = Field(ge=1, le=5)
    expert_weights: Dict[str, float] = {}

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.post("/api/assess")
def assess(a: Applicant):
    # Transparent rule-based expert system (illustrative, not a lending model).
    installment = a.loan_amount * 0.012  # simplified monthly payment proxy
    dti = (a.monthly_debt + installment) / max(a.income, 1)
    savings_months = a.savings / max(a.monthly_debt + installment, 1)
    experts = {}
    def add(name, score, rationale, weight):
        experts[name] = {"score": round(max(0,min(100,score))), "rationale": rationale, "weight": weight}

    # Credit analyst: score + payment record
    add("Credit analyst", 100 - max(0,700-a.credit_score)*0.22 - a.missed_payments*8,
        f"Credit score {a.credit_score}; {a.missed_payments} missed payments.", a.expert_weights.get("credit",1.2))
    # Financial analyst: debt burden and cushion
    add("Financial analyst", 100 - max(0,dti-0.25)*150 + min(savings_months,12)*1.5,
        f"Estimated debt-to-income {dti:.0%}; savings buffer {savings_months:.1f} months.", a.expert_weights.get("financial",1.25))
    # Risk officer: stability, leverage, sector
    add("Banking risk officer", 55 + a.stability*8 + min(a.employment_years,10)*2 - a.sector_risk*5 - dti*30,
        f"Stability {a.stability}/5; sector risk {a.sector_risk}/5; tenure {a.employment_years:g} years.", a.expert_weights.get("risk",1.3))
    # Fraud specialist: flags are a hard caution signal
    add("Fraud specialist", 100 - a.fraud_flags*28,
        f"{a.fraud_flags} fraud / verification flag(s) detected.", a.expert_weights.get("fraud",1.5))
    # Economic analyst: scenario-sensitive buffer and resilience
    add("Economic analyst", 60 + a.stability*5 + min(savings_months,12)*2 - a.sector_risk*7 - max(0,dti-.35)*70,
        f"Macro resilience proxy from stability, savings and sector exposure.", a.expert_weights.get("economic",1.0))
    # Correct typo-safe weight key fallback
    experts["Economic analyst"]["weight"] = a.expert_weights.get("economic",1.0)

    total_w=sum(e["weight"] for e in experts.values())
    overall=sum(e["score"]*e["weight"] for e in experts.values())/total_w
    scores=[e["score"] for e in experts.values()]
    disagreement=max(scores)-min(scores)
    conditions=[]
    if dti > .40: conditions.append("Reduce existing liabilities or provide a co-applicant")
    if a.savings < installment*3: conditions.append("Provide a stronger cash reserve / collateral")
    if a.employment_years < 2: conditions.append("Verify employment continuity")
    if a.fraud_flags > 0: conditions.append("Complete enhanced identity and document verification")
    if a.credit_score < 650: conditions.append("Price or structure the loan conservatively")
    if disagreement >= 35: conditions.append("Escalate conflicting expert opinions to a human review panel")

    if a.fraud_flags >= 3 or overall < 48:
        decision="REJECT"; color="reject"; reason="Critical fraud signals or a weak aggregate risk profile."
    elif overall >= 76 and disagreement < 35 and dti <= .42 and a.fraud_flags == 0:
        decision="APPROVE"; color="approve"; reason="Strong aggregate score with manageable disagreement and leverage."
    else:
        decision="CONDITIONAL"; color="conditional"; reason="Risk is manageable only with safeguards or additional review."

    return {"applicant":a.name,"decision":decision,"color":color,"overall":round(overall,1),
            "dti":round(dti*100,1),"disagreement":round(disagreement,1),"reason":reason,
            "experts":experts,"conditions":conditions,"installment_proxy":round(installment,2),
            "savings_months":round(savings_months,1),
            "note":"Educational prototype only. Scores and rules are illustrative; not for real lending decisions."}
