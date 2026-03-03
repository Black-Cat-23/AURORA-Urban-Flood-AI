from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from dependencies import require_role, UserData

router = APIRouter(prefix="/api/simulation", tags=["Flood Simulation"])

class SimulationRequest(BaseModel):
    scenario: str # "100mm", "250mm", "extreme"
    # In a real app we'd pass an area ID or bbox to simulate
    area_id: str

class SimulationResult(BaseModel):
    submerged_area_sqm: float
    affected_population: int
    critical_infrastructure_impacted: int
    economic_damage_estimate_usd: float
    water_levels_geojson_url: str # Link to the output layer for the 3D map

@router.post("/run", response_model=SimulationResult)
async def run_simulation(
    req: SimulationRequest,
    current_user: UserData = Depends(require_role(["City Admin", "Ward Officer", "System Admin"]))
):
    """
    Simulates water rising using DEM flood-fill approximation based on rainfall scenario.
    """
    # Mocking the simulation results
    # In reality this involves taking the DEM, applying rainfall volume, 
    # subtracting drainage capacity, and filling local minimums.
    
    if req.scenario == "100mm":
        area = 45000.0
        pop = 1200
        infra = 3
        damage = 150000.0
    elif req.scenario == "250mm":
        area = 150000.0
        pop = 5400
        infra = 12
        damage = 850000.0
    elif req.scenario == "extreme":
        area = 500000.0
        pop = 25000
        infra = 45
        damage = 5000000.0
    else:
        area = 10000.0
        pop = 100
        infra = 0
        damage = 10000.0
        
    return SimulationResult(
        submerged_area_sqm=area,
        affected_population=pop,
        critical_infrastructure_impacted=infra,
        economic_damage_estimate_usd=damage,
        water_levels_geojson_url=f"/api/gis/layers/sim_{req.scenario}_{req.area_id}.geojson"
    )
