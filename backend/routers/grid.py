from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import geopandas as gpd
from shapely.geometry import box
import numpy as np

router = APIRouter(prefix="/api/grid", tags=["Grid Processing"])

class GridRequest(BaseModel):
    # Depending on implementation, you might pass a layer name or an uploaded file path.
    # For now, we will assume we read a pre-processed wards geojson.
    file_path: str
    cell_size_m: int = 100

@router.post("/segment")
async def generate_micro_grids(req: GridRequest):
    """
    Generates a 100m x 100m micro-grid overlaying the given city bounds/shapefile.
    Input CRS should be a projected coordinate system to use meters (e.g. EPSG:3857) or we re-project within.
    """
    try:
        gdf = gpd.read_file(req.file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found or not processed yet.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load file: {str(e)}")
        
    original_crs = gdf.crs
    
    # Reproject to EPSG:3857 (Pseudo-Mercator) to work in meters for the 100m x 100m grid Generation
    # If the user data is in India, EPSG:32643 or EPSG:32644 (UTM zones) is better, but 3857 works globally for rough meters.
    gdf_proj = gdf.to_crs(epsg=3857)
    
    # Get total bounds
    minx, miny, maxx, maxy = gdf_proj.total_bounds
    
    # Generate grid cells
    cell_size = req.cell_size_m
    x_coords = np.arange(minx, maxx, cell_size)
    y_coords = np.arange(miny, maxy, cell_size)
    
    cells = []
    for x in x_coords:
        for y in y_coords:
            grid_cell = box(x, y, x + cell_size, y + cell_size)
            cells.append(grid_cell)
            
    grid_gdf = gpd.GeoDataFrame({'geometry': cells}, crs="EPSG:3857")
    
    # Keep only cells that intersect with the ward boundaries
    # A spatial join or intersection is needed
    intersecting_grid = gpd.sjoin(grid_gdf, gdf_proj, how="inner", predicate="intersects")
    
    # optionally remove duplicates if multiple wards intersect the same cell
    intersecting_grid = intersecting_grid.drop_duplicates(subset='geometry')
    
    # Reproject back to WGS84
    intersecting_grid = intersecting_grid.to_crs(epsg=4326)
    
    return {
        "message": f"Successfully generated {len(intersecting_grid)} micro-grid cells of {cell_size}m.",
        "cell_count": len(intersecting_grid),
        "crs": "EPSG:4326"
    }
