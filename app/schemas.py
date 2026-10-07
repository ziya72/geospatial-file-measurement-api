from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets Pydantic read SQLAlchemy objects

    id: str
    filename: str
    file_type: str
    feature_count: int
    crs: str | None
    status: str
    error: str | None
    created_at: datetime


class FeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_index: int
    geometry_type: str | None
    geometry: dict | None
    properties: dict
    area_m2: float | None
    length_m: float | None
    measured_in: str | None
    note: str | None


class Summary(BaseModel):
    total_area_m2: float
    total_length_m: float
    measured_features: int
    not_measured_features: int


class MeasurementsOut(BaseModel):
    file_id: str
    crs: str | None
    units: dict[str, str] = {"area": "square metres", "length": "metres"}
    summary: Summary
    features: list[FeatureOut]