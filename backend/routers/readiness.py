from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/readiness", tags=["Readiness Scoring"])

class WardReadinessInput(BaseModel):
    ward_id: str
    avg_flood_risk: float # 0 to 1
    drainage_efficiency: float # 0 to 1
    emergency_access: float # 0 to 1
    infrastructure_stability: float # 0 to 1

class WardReadinessResult(BaseModel):
    ward_id: str
    readiness_score_pct: float
    risk_classification: str
    weakest_factor: str

@router.post("/score", response_model=List[WardReadinessResult])
async def calculate_readiness_score(wards: List[WardReadinessInput]):
    """
    Computes Pre-Monsoon Readiness Score and classifies risk level per ward.
    """
    results = []
    
    for ward in wards:
        # Score Formula: (1 - Avg Flood Risk) * Drainage * Access * Stability
        safety_factor = max(0.0, 1.0 - ward.avg_flood_risk)
        raw_score = (safety_factor * 
                     ward.drainage_efficiency * 
                     ward.emergency_access * 
                     ward.infrastructure_stability)
        
        score_pct = raw_score * 100
        
        # Classification
        if score_pct >= 80:
            classification = "Low"
        elif score_pct >= 60:
            classification = "Moderate"
        elif score_pct >= 40:
            classification = "High"
        else:
            classification = "Critical"
            
        # Weakest Factor Identification
        factors = {
            "Flood Safety": safety_factor,
            "Drainage Efficiency": ward.drainage_efficiency,
            "Emergency Access": ward.emergency_access,
            "Infrastructure Stability": ward.infrastructure_stability
        }
        weakest = min(factors, key=factors.get)
        
        results.append(WardReadinessResult(
            ward_id=ward.ward_id,
            readiness_score_pct=round(score_pct, 2),
            risk_classification=classification,
            weakest_factor=weakest
        ))
        
    return results
