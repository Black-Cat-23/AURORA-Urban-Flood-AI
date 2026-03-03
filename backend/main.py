from fastapi import FastAPI
from routers.gis import router as gis_router
from routers.grid import router as grid_router
from routers.features import router as features_router
from routers.ml import router as ml_router
from routers.readiness import router as readiness_router
from routers.resources import router as resources_router
from routers.simulation import router as simulation_router
from routers.auth import router as auth_router

app = FastAPI(title="AURORA Urban Flood Intelligence API")

app.include_router(auth_router)
app.include_router(gis_router)
app.include_router(grid_router)
app.include_router(features_router)
app.include_router(ml_router)
app.include_router(readiness_router)
app.include_router(resources_router)
app.include_router(simulation_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to AURORA API"}
