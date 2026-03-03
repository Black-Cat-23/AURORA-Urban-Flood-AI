from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict
import pulp
from dependencies import require_role, UserData

router = APIRouter(prefix="/api/resources", tags=["Resource Allocation"])

class WardAllocationRequest(BaseModel):
    ward_id: str
    risk_score: float
    infrastructure_needs: int
    drainage_cleaning_cost: float
    base_reduction_per_pump: float = 0.05
    base_reduction_per_cleaning: float = 0.1

class ResourceConstraints(BaseModel):
    total_budget: float
    available_pumps: int
    personnel_capacity: int
    vehicle_availability: int
    
class WardAllocationResult(BaseModel):
    ward_id: str
    allocated_pumps: int
    cleaning_budget_allocated: float
    projected_risk_reduction_pct: float

class OptimizationResponse(BaseModel):
    allocations: List[WardAllocationResult]
    total_projected_reduction_pct: float
    unspent_budget: float
    unused_pumps: int

@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_resources(
    wards: List[WardAllocationRequest], 
    constraints: ResourceConstraints,
    current_user: UserData = Depends(require_role(["City Admin", "System Admin"]))
):
    """
    Uses Linear Programming to maximize risk reduction given budget and resource constraints.
    """
    # Create problem
    prob = pulp.LpProblem("Proactive_Resource_Deployment", pulp.LpMaximize)
    
    # Variables: how many pumps to allocate per ward, and budget to allocate for drainage
    pump_vars = pulp.LpVariable.dicts("Pumps", [w.ward_id for w in wards], lowBound=0, upBound=5, cat='Integer')
    cleaning_vars = pulp.LpVariable.dicts("Cleaning_Budget", [w.ward_id for w in wards], lowBound=0, cat='Continuous')
    
    # Objective Function: Maximize total risk reduction (weighted by risk score to prioritize critical areas)
    prob += pulp.lpSum([
        w.risk_score * (
            pump_vars[w.ward_id] * w.base_reduction_per_pump +
            (cleaning_vars[w.ward_id] / max(w.drainage_cleaning_cost, 1)) * w.base_reduction_per_cleaning
        ) for w in wards
    ]), "Total_Risk_Reduction"
    
    # Constraints
    # 1. Total pumps constraint
    prob += pulp.lpSum([pump_vars[w.ward_id] for w in wards]) <= constraints.available_pumps, "Pump_Capacity"
    # 2. Total budget constraint
    prob += pulp.lpSum([cleaning_vars[w.ward_id] for w in wards]) <= constraints.total_budget, "Budget_Capacity"
    
    # 3. Maximum cleaning budget per ward limit (to spread resources)
    for w in wards:
        prob += cleaning_vars[w.ward_id] <= (constraints.total_budget * 0.4), f"Max_Budget_{w.ward_id}"
        
    # Solve
    prob.solve()
    
    if pulp.LpStatus[prob.status] != "Optimal":
        # Handle fallback strategies
        pass
        
    allocations = []
    total_reduction = 0.0
    spent_budget = 0.0
    used_pumps = 0
    
    for w in wards:
        pumps = int(pump_vars[w.ward_id].varValue)
        budget = round(cleaning_vars[w.ward_id].varValue, 2)
        
        used_pumps += pumps
        spent_budget += budget
        
        reduction = (pumps * w.base_reduction_per_pump) + ((budget / max(w.drainage_cleaning_cost, 1)) * w.base_reduction_per_cleaning)
        # Cap reduction
        reduction = min(reduction, 0.9)
        total_reduction += reduction
        
        allocations.append(WardAllocationResult(
            ward_id=w.ward_id,
            allocated_pumps=pumps,
            cleaning_budget_allocated=budget,
            projected_risk_reduction_pct=round(reduction * 100, 2)
        ))
        
    return OptimizationResponse(
        allocations=allocations,
        total_projected_reduction_pct=round(total_reduction / max(len(wards), 1) * 100, 2),
        unspent_budget=round(constraints.total_budget - spent_budget, 2),
        unused_pumps=constraints.available_pumps - used_pumps
    )
