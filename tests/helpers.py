import zipfile
from pathlib import Path

import geopandas as gpd
from pyproj import CRS, Transformer
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info
from shapely.geometry import LineString, Point, box

PLACES = {
    "aligarh": (78.08, 27.89),
    "mumbai": (72.88, 19.08),
    "london": (-0.13, 51.51),
    "sydney": (151.21, -33.87),
    "quito": (-78.47, -0.18),     
}
def utm_crs_for(lon: float, lat: float) -> CRS:

    matches = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(west_lon_degree=lon, south_lat_degree=lat,
                                        east_lon_degree=lon, north_lat_degree=lat),
    )
    return CRS.from_epsg(matches[0].code)

def square_and_line(lon: float, lat: float) -> gpd.GeoDataFrame:
    
    utm = utm_crs_for(lon, lat)
    x, y = Transformer.from_crs("EPSG:4326", utm, always_xy=True).transform(lon, lat)
    return gpd.GeoDataFrame(
        {"name": ["square", "road", "well"]},
        geometry=[
            box(x, y, x + 1000, y + 1000),                    # area = 1,000,000 m2 exactly
            LineString([(x, y - 500), (x + 2000, y - 500)]),  # length = 2,000 m exactly
            Point(x + 500, y + 500),
        ],
        crs=utm,
    )

def write_kml(gdf: gpd.GeoDataFrame, path: Path) -> Path:
    gdf.to_crs("EPSG:4326").to_file(path, driver="KML")
    return path

def write_shapefile_zip(gdf: gpd.GeoDataFrame, folder: Path, name: str = "plots", drop: str | None = None) -> Path:
    
    shp_dir = folder / "shp"
    shp_dir.mkdir(exist_ok=True)
    gdf.to_file(shp_dir / f"{name}.shp")
    zip_path = folder / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for part in shp_dir.iterdir():
            if drop and part.suffix.lower() == drop:
                continue
            z.write(part, arcname=part.name)
    return zip_path