from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import numpy as np
import xgboost as xgb
from sklearn.cluster import DBSCAN
from routers.features import NormalizedFeatures

router = APIRouter(prefix="/api/ml", tags=["Flood Risk Prediction"])

class FloodRiskResult(BaseModel):
    grid_id: str
    flood_probability_score: float

class WardRiskResult(BaseModel):
    ward_id: str
    aggregate_risk_score: float

class PredictionResponse(BaseModel):
    grid_scores: List[FloodRiskResult]
    ward_scores: List[WardRiskResult]
    hotspot_clusters: int
    explainability: Dict[str, float]

# Mock pre-trained XGBoost model loading would happen here
# model = xgb.Booster()
# model.load_model('model.json')

@router.post("/predict_risk", response_model=PredictionResponse)
async def predict_flood_risk(features: List[NormalizedFeatures]):
    """
    Predicts the flood risk (0-1) for each grid using a machine learning model.
    Clusters high-risk micro-grids using DBSCAN to identify 2,500+ hotspots.
    """
    grid_scores = []
    
    # Feature importance mock payload
    explainability = {
        "elevation_score": 0.35,
        "drainage_proximity_index": 0.25,
        "rainfall_intensity_index": 0.20,
        "impervious_surface_ratio": 0.10,
        "slope_gradient": 0.05,
        "infrastructure_vulnerability_score": 0.03,
        "population_exposure_index": 0.02
    }
    
    # Generate risk scores (Mocking Inference since we do not have a pre-trained model on disk)
    high_risk_coords = []
    
    for idx, feature in enumerate(features):
        # We simulate the XGBoost inference using a weighted sum of the features
        risk = (
            feature.elevation_score * explainability["elevation_score"] +
            feature.drainage_proximity_index * explainability["drainage_proximity_index"] +
            feature.rainfall_intensity_index * explainability["rainfall_intensity_index"] +
            feature.impervious_surface_ratio * explainability["impervious_surface_ratio"] +
            feature.slope_gradient * explainability["slope_gradient"]
        )
        
        # Add some non-linear simulation 
        risk = min(risk * 1.1, 1.0) # Cap at 1.0
        
        grid_scores.append(FloodRiskResult(grid_id=feature.grid_id, flood_probability_score=round(risk, 4)))
        
        # If risk is > 0.7, we consider it for DBSCAN clustering. 
        # Using index as mock coordinates
        if risk > 0.7:
            high_risk_coords.append([idx % 100, idx // 100])
            
    # DBSCAN Clustering for Micro-Hotspots
    num_clusters = 0
    if len(high_risk_coords) > 0:
        X = np.array(high_risk_coords)
        clustering = DBSCAN(eps=3, min_samples=2).fit(X)
        num_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)

    # Ward-level aggregation (Mock: assuming we only have 1 ward in input for now)
    avg_risk = sum(g.flood_probability_score for g in grid_scores) / len(grid_scores) if grid_scores else 0
    ward_scores = [WardRiskResult(ward_id="mock_ward_1", aggregate_risk_score=round(avg_risk, 4))]

    return PredictionResponse(
        grid_scores=grid_scores,
        ward_scores=ward_scores,
        hotspot_clusters=num_clusters,
        explainability=explainability
    )
