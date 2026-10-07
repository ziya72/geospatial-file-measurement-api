import tempfile
from pathlib import Path
from fastapi import FastAPI, File, UploadFile
from app.measure import measure_features

from app.parser import read_geofile

app = FastAPI(title="Geospatial File Measurement API")

@app.post("/api/files/")
def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{suffix}"
        path.write_bytes(file.file.read())
        gdf = read_geofile(path)
    return {
        "filename": file.filename,
        "feature_count": len(gdf),
        "crs": str(gdf.crs),
        "features": measure_features(gdf),
    }