import json

import geopandas as gpd
from shapely import force_2d, make_valid
from shapely.geometry import mapping

AREA_TYPES = {"Polygon", "MultiPolygon"}
LENGTH_TYPES = {"LineString", "MultiLineString"}


def crs_label(crs) -> str | None:
    """A short human-readable name for a CRS, e.g. 'EPSG:4326'."""
    if crs is None:
        return None
    epsg = crs.to_epsg()
    return f"EPSG:{epsg}" if epsg else crs.name

def measure_features(gdf: gpd.GeoDataFrame) -> list[dict]:
    properties = _properties_as_json(gdf)
    results = []
    for position, geom in enumerate(gdf.geometry):
            record = {
                "feature_index": position,
                "geometry_type": geom.geom_type if geom is not None else None,
                "geometry": mapping(geom) if geom is not None and not geom.is_empty else None,
                "properties": properties[position],
                "area_m2": None,
                "length_m": None,
                "measured_in": None,
                "note": None,
            }
            _add_measurement(record, geom, gdf.crs)
            results.append(record)
    return results

def _add_measurement(record: dict, geom, crs) -> None:
    geom_type = record["geometry_type"]

    if geom is None or geom.is_empty:
        record["note"] = "Empty geometry: nothing to measure."
        return
    if geom_type not in AREA_TYPES | LENGTH_TYPES:
        record["note"] = f"No measurement for {geom_type}."
        return
    if crs is None:
        record["note"] = "Unknown CRS (no .prj file): cannot measure safely."
        return

    flat = force_2d(geom)  # drop height (Z) values; we want flat area and length
    if not flat.is_valid:
        flat = make_valid(flat)  # e.g. a polygon whose edges cross itself
        record["note"] = "Geometry was invalid and was repaired before measuring."

    shape = gpd.GeoSeries([flat], crs=crs)
    if crs.is_geographic:
        # Degrees are not metres: move the shape to its local UTM zone, where units are metres.
        target = shape.estimate_utm_crs()
        shape.to_crs(target)
        to_metres = 1.0
    else:
        # Already projected: measure in the file's own units, converted to metres (e.g. feet).
        target = crs
        to_metres = crs.axis_info[0].unit_conversion_factor

    projected = shape.iloc[0]
    record["measured_in"] = crs_label(target)
    if geom_type in AREA_TYPES:
        record["area_m2"] = round(projected.area * to_metres**2, 2)
    else:
        record["length_m"] = round(projected.length * to_metres, 2)

def _properties_as_json(gdf: gpd.GeoDataFrame) -> list[dict]:
    table = gdf.drop(columns=gdf.geometry.name)
    if table.columns.empty:
        return [{} for _ in range(len(gdf))]
    return json.loads(table.to_json(orient="records", date_format="iso", default_handler=str))