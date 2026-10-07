from pathlib import Path

import geopandas as gpd


def read_geofile(path: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(path)