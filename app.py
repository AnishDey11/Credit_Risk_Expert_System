from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict

app = FastAPI(title="Credit Compass | DST Expert Risk System")
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
    expert_weights: Dict[str, float] = Field(default_factory=dict)


# Frame of discernment:
# A = loan approval, R = loan rejection, THETA = {A, R}.
A = frozenset({"A"})
R = frozenset({"R"})
THETA = frozenset({"A", "R"})


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def generate_bpa(score: float, reliability: float = 1.0):
    """
    Convert a 0-100 expert score to a simple-support BPA.

    score > 50: evidence supports approval.
    score < 50: evidence supports rejection.
    score = 50: all mass is assigned to uncertainty.

    Reliability discounting transfers part of the committed
    evidence to THETA (uncommitted/uncertain evidence).
    """
    score = max(0.0, min(100.0, float(score)))
    reliability = clamp(reliability)

    strength = abs(score - 50.0) / 50.0

    if score > 50:
        approval_mass, rejection_mass = strength, 0.0
    elif score < 50:
        approval_mass, rejection_mass = 0.0, strength
    else:
        approval_mass, rejection_mass = 0.0, 0.0

    # Shafer's reliability discounting:
    # m_alpha(X) = alpha*m(X), X != THETA
    # m_alpha(THETA) = 1-alpha + alpha*m(THETA)
    approval_mass *= reliability
    rejection_mass *= reliability
    uncertainty_mass = 1.0 - approval_mass - rejection_mass

    return {
        A: approval_mass,
        R: rejection_mass,
        THETA: uncertainty_mass
    }


def combine_bpa(m1, m2):
    """Return the unnormalized conjunctive combination and conflict."""
    combined = {A: 0.0, R: 0.0, THETA: 0.0}
    conflict = 0.0

    for focal1, mass1 in m1.items():
        for focal2, mass2 in m2.items():
            intersection = focal1.intersection(focal2)
            product_mass = mass1 * mass2

            if not intersection:
                conflict += product_mass
            else:
                combined[intersection] += product_mass

    return combined, conflict


def combine_all_experts(expert_bpas):
    """
    Combine all expert BPAs without intermediate normalization.
    Normalize once at the end using Dempster's rule.
    """
    combined = {A: 0.0, R: 0.0, THETA: 1.0}  # vacuous starting evidence

    for expert_bpa in expert_bpas:
        combined, _ = combine_bpa(combined, expert_bpa)

    non_conflicting_mass = sum(combined.values())
    conflict = clamp(1.0 - non_conflicting_mass)

    # Dempster normalization is undefined when K = 1 and unstable
    # when K is extremely close to 1.
    if conflict >= 0.999999:
        return {
            "approval": 0.0,
            "rejection": 0.0,
            "uncertainty": 1.0,
            "conflict": conflict,
            "normalization_failed": True
        }

    denominator = 1.0 - conflict
    approval = combined[A] / denominator
    rejection = combined[R] / denominator
    uncertainty = combined[THETA] / denominator

    # Guard against tiny floating-point drift.
    total = approval + rejection + uncertainty
    if total:
        approval, rejection, uncertainty = (
            approval / total, rejection / total, uncertainty / total
        )

    return {
        "approval": approval,
        "rejection": rejection,
        "uncertainty": uncertainty,
        "conflict": conflict,
        "normalization_failed": False
    }


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/api/assess")
def assess(a: Applicant):
    # Illustrative financial indicators retained from the original project.
    installment = a.loan_amount * 0.012
    dti = (a.monthly_debt + installment) / max(a.income, 1)
    savings_months = a.savings / max(a.monthly_debt + installment, 1)

    experts = {}

    def add(name, score, rationale, weight):
        experts[name] = {
            "score": round(max(0, min(100, score))),
            "rationale": rationale,
            "weight": float(weight)
        }

    # 1. Credit analyst
    add(
        "Credit analyst",
        100 - max(0, 700 - a.credit_score) * 0.22 - a.missed_payments * 8,
        f"Credit score {a.credit_score}; {a.missed_payments} missed payments.",
        a.expert_weights.get("credit", 1.2)
    )

    # 2. Financial analyst

    debt_score = max(
        0,
        min(100, 100 * (1 - dti / 0.50))
    )

    savings_score = max(
        0,
        min(100, (savings_months / 12) * 100)
    )

    financial_score = round(
        0.60 * debt_score + 0.40 * savings_score,
        2
    )

    add(
        "Financial analyst",
        financial_score,
        f"Debt affordability score {debt_score:.1f}/100; "
        f"savings coverage score {savings_score:.1f}/100; "
        f"estimated DTI {dti:.0%}; "
        f"savings buffer {savings_months:.1f} months.",
        a.expert_weights.get("financial", 1.25)
    )

    # 3. Banking risk officer
    add(
        "Banking risk officer",
        55 + a.stability * 8 + min(a.employment_years, 10) * 2
        - a.sector_risk * 5 - dti * 30,
        f"Stability {a.stability}/5; sector risk {a.sector_risk}/5; "
        f"employment {a.employment_years:g} years.",
        a.expert_weights.get("risk", 1.3)
    )

    # 4. Fraud detection specialist
    add(
        "Fraud specialist",
        100 - a.fraud_flags * 28,
        f"{a.fraud_flags} fraud / verification flag(s) detected.",
        a.expert_weights.get("fraud", 1.5)
    )

    # 5. Economic analyst
    add(
        "Economic analyst",
        60 + a.stability * 5 + min(savings_months, 12) * 2
        - a.sector_risk * 7 - max(0, dti - 0.35) * 70,
        "Macro resilience proxy from stability, savings and sector exposure.",
        a.expert_weights.get("economic", 1.0)
    )

    # Convert adjustable expert weights into relative reliability.
    # The largest positive weight maps to reliability 1.0.
    positive_weights = [max(0.0, e["weight"]) for e in experts.values()]
    max_weight = max(positive_weights, default=0.0)

    expert_bpas = []
    for expert in experts.values():
        weight = max(0.0, expert["weight"])
        reliability = weight / max_weight if max_weight > 0 else 1.0
        bpa = generate_bpa(expert["score"], reliability)

        expert["reliability"] = round(reliability, 4)
        expert["bpa"] = {
            "approval": round(bpa[A], 6),
            "rejection": round(bpa[R], 6),
            "uncertainty": round(bpa[THETA], 6)
        }
        expert_bpas.append(bpa)

    dst = combine_all_experts(expert_bpas)

    belief_approval = dst["approval"]
    belief_rejection = dst["rejection"]
    uncertainty = dst["uncertainty"]
    conflict = dst["conflict"]

    # For this binary frame, plausibility(X) = Bel(X) + m(THETA).
    plausibility_approval = belief_approval + uncertainty
    plausibility_rejection = belief_rejection + uncertainty

    scores = [e["score"] for e in experts.values()]
    disagreement = max(scores) - min(scores)

    conditions = []
    if dti > 0.40:
        conditions.append("Reduce existing liabilities or provide a co-applicant")
    if a.savings < installment * 3:
        conditions.append("Provide a stronger cash reserve / collateral")
    if a.employment_years < 2:
        conditions.append("Verify employment continuity")
    if a.fraud_flags > 0:
        conditions.append("Complete enhanced identity and document verification")
    if a.credit_score < 650:
        conditions.append("Price or structure the loan conservatively")
    if conflict >= 0.35:
        conditions.append("High conflict between expert evidence; escalate to human review")
    if uncertainty >= 0.40:
        conditions.append("Insufficient conclusive evidence; request additional information")

    # Decision thresholds are illustrative project rules, not lending policy.
    if a.fraud_flags >= 3:
        decision, color = "REJECT", "reject"
        reason = "Critical fraud indicators trigger the configured rejection safeguard."
    elif dst["normalization_failed"]:
        decision, color = "CONDITIONAL", "conditional"
        reason = "Expert evidence is completely or almost completely conflicting; manual review is required."
    elif belief_rejection >= 0.70:
        decision, color = "REJECT", "reject"
        reason = "Combined DST evidence shows strong belief in loan rejection."
    elif (
        belief_approval >= 0.70
        and conflict < 0.35
        and dti <= 0.42
        and a.fraud_flags == 0
    ):
        decision, color = "APPROVE", "approve"
        reason = "Combined DST evidence shows strong approval belief with manageable conflict and DTI."
    else:
        decision, color = "CONDITIONAL", "conditional"
        reason = "Evidence is not decisive enough for automatic approval or rejection; further review is required."

    return {
        "applicant": a.name,
        "decision": decision,
        "color": color,
        # Kept for compatibility with the existing UI; now means approval belief %.
        "overall": round(belief_approval * 100, 1),
        "dti": round(dti * 100, 1),
        "disagreement": round(disagreement, 1),
        "reason": reason,
        "experts": experts,
        "conditions": conditions,
        "installment_proxy": round(installment, 2),
        "savings_months": round(savings_months, 1),
        "dst": {
            "belief_approval": round(belief_approval, 6),
            "belief_rejection": round(belief_rejection, 6),
            "plausibility_approval": round(plausibility_approval, 6),
            "plausibility_rejection": round(plausibility_rejection, 6),
            "uncertainty": round(uncertainty, 6),
            "conflict": round(conflict, 6),
            "normalization_failed": dst["normalization_failed"]
        },
        "note": (
            "Educational prototype only. Expert rules, BPA mapping and thresholds are illustrative; "
            "this system is not validated for real lending decisions."
        )
    }
