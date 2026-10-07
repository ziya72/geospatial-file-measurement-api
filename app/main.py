import tempfile

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import Feature, UploadedFile, get_db, init_db
from app.measure import crs_label, measure_features
from app.parser import read_geofile
from app.schemas import FileOut, MeasurementsOut, Summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  
    yield


app = FastAPI(title="Geospatial File Measurement API", lifespan=lifespan)


@app.post("/api/files/", response_model=FileOut, status_code=201)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()

    record = UploadedFile(id=uuid.uuid4().hex[:12], filename=filename, file_type=suffix[1:], status="PROCESSING")
    db.add(record)
    db.commit()

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{suffix}"
        path.write_bytes(file.file.read())
        gdf = read_geofile(path)
    results = measure_features(gdf)

    record.crs = crs_label(gdf.crs)
    record.feature_count = len(results)
    record.features = [Feature(**r) for r in results]
    record.status = "COMPLETED"
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/files/{file_id}/", response_model=FileOut)
def get_file(file_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, file_id)


@app.get("/api/files/{file_id}/measurements/", response_model=MeasurementsOut)
def get_measurements(file_id: str, db: Session = Depends(get_db)):
    record = _get_or_404(db, file_id)
    features = record.features
    measured = [f for f in features if f.area_m2 is not None or f.length_m is not None]
    summary = Summary(
        total_area_m2=round(sum(f.area_m2 or 0 for f in features), 2),
        total_length_m=round(sum(f.length_m or 0 for f in features), 2),
        measured_features=len(measured),
        not_measured_features=len(features) - len(measured),
    )
    return MeasurementsOut(file_id=record.id, crs=record.crs, summary=summary, features=features)


def _get_or_404(db: Session, file_id: str) -> UploadedFile:
    record = db.get(UploadedFile, file_id)
    if record is None:
        raise HTTPException(404, f"No file with id '{file_id}'.")
    return record