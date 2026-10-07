import json

import geopandas as gpd
from shapely.geometry import mapping


def measure_features(gdf: gpd.GeoDataFrame) -> list[dict]:
    properties = _properties_as_json(gdf)
    results = []
    for position, geom in enumerate(gdf.geometry):
        results.append({
            "feature_index": position,
            "geometry_type": geom.geom_type if geom is not None else None,
            "geometry": mapping(geom) if geom is not None and not geom.is_empty else None,
            "properties": properties[position],
        })
    return results


def _properties_as_json(gdf: gpd.GeoDataFrame) -> list[dict]:
    table = gdf.drop(columns=gdf.geometry.name)
    if table.columns.empty:
        return [{} for _ in range(len(gdf))]
    return json.loads(table.to_json(orient="records", date_format="iso", default_handler=str))