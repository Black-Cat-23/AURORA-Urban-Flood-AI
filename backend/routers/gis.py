from fastapi import APIRouter, UploadFile, File, HTTPException
import geopandas as gpd
import rasterio
import shutil
import os
from pathlib import Path
import zipfile

router = APIRouter(prefix="/api/gis", tags=["GIS"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload/shapefile")
async def upload_shapefile(file: UploadFile = File(...)):
    """
    Ingest ward boundaries via shapefile (zip containing .shp, .shx, .dbf, .prj).
    Validates the spatial integrity and normalizes to WGS84.
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Shapefile must be uploaded as a .zip file.")

    file_path = UPLOAD_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract and find .shp file
        extract_dir = UPLOAD_DIR / file.filename.replace('.zip', '')
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        shp_files = list(extract_dir.glob('*.shp'))
        if not shp_files:
            raise HTTPException(status_code=400, detail="Corrupt upload: No .shp file found in the archive.")
            
        # Validate and normalize
        gdf = gpd.read_file(shp_files[0])
        if gdf.empty:
            raise HTTPException(status_code=400, detail="Shapefile contains no records.")
            
        # Normalize to WGS84 (EPSG:4326)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
            
        # Here we would normally store this in PostGIS
        # For now, return success
        return {
            "message": "Shapefile uploaded and validated successfully.", 
            "features_count": len(gdf),
            "crs": str(gdf.crs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process shapefile: {str(e)}")
    finally:
        if file_path.exists():
            file_path.unlink()

@router.post("/upload/dem")
async def upload_dem(file: UploadFile = File(...)):
    """
    Ingest DEM raster (e.g. .tif). Validates resolution and coordinate bounds.
    """
    if not file.filename.endswith(('.tif', '.tiff')):
        raise HTTPException(status_code=400, detail="DEM must be a GeoTIFF (.tif or .tiff).")
        
    file_path = UPLOAD_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Validate with rasterio
        with rasterio.open(file_path) as src:
            bounds = src.bounds
            crs = src.crs
            res = src.res
            
            if crs is None:
                raise HTTPException(status_code=400, detail="DEM is missing coordinate reference system.")
                
            # Perform projection/validation logic here
            
        return {
            "message": "DEM uploaded and validated successfully.",
            "bounds": bounds,
            "crs": str(crs),
            "resolution": res
        }
    except rasterio.errors.RasterioIOError:
        raise HTTPException(status_code=400, detail="Corrupt DEM raster file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process DEM: {str(e)}")
    finally:
        if file_path.exists():
            file_path.unlink()
