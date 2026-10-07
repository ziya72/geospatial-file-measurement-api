"""Tests for the measurement logic, without the API."""
import geopandas as gpd
import pytest
from pyproj import Geod
from shapely.geometry import GeometryCollection, Point, Polygon

from app.measure import crs_label, measure_features
from tests.helpers import PLACES, square_and_line, utm_crs_for

ANY_PLACE = PLACES["aligarh"]
every_place = pytest.mark.parametrize("lon, lat", PLACES.values(), ids=PLACES.keys())


def by_name(results):
    return {r["properties"]["name"]: r for r in results}


@every_place
def test_square_in_degrees_measures_one_square_km(lon, lat):
    gdf = square_and_line(lon, lat).to_crs("EPSG:4326")  # the file gives degrees, like a KML would
    square = by_name(measure_features(gdf))["square"]

    assert square["area_m2"] == pytest.approx(1_000_000, rel=0.001)  # within 0.1%
    assert square["measured_in"] == crs_label(utm_crs_for(lon, lat))


@every_place
def test_line_in_degrees_measures_two_km(lon, lat):
    gdf = square_and_line(lon, lat).to_crs("EPSG:4326")
    road = by_name(measure_features(gdf))["road"]

    assert road["length_m"] == pytest.approx(2_000, rel=0.001)
    assert road["area_m2"] is None


@every_place
def test_utm_result_agrees_with_geodesic_measurement(lon, lat):
    """Second opinion: measure directly on the curved Earth (no projection) and compare."""
    gdf = square_and_line(lon, lat).to_crs("EPSG:4326")
    ours = by_name(measure_features(gdf))["square"]["area_m2"]

    geodesic_area, _ = Geod(ellps="WGS84").geometry_area_perimeter(gdf.geometry.iloc[0])
    assert ours == pytest.approx(abs(geodesic_area), rel=0.005)  # within 0.5%


def test_point_is_not_measured():
    gdf = square_and_line(*ANY_PLACE).to_crs("EPSG:4326")
    well = by_name(measure_features(gdf))["well"]

    assert well["geometry_type"] == "Point"
    assert well["area_m2"] is None and well["length_m"] is None
    assert "No measurement" in well["note"]


def test_projected_file_is_measured_without_reprojecting():
    gdf = square_and_line(*ANY_PLACE)  # already in UTM metres
    square = by_name(measure_features(gdf))["square"]

    assert square["area_m2"] == pytest.approx(1_000_000)
    assert square["measured_in"] == crs_label(gdf.crs)


def test_unknown_crs_is_reported_not_guessed():
    gdf = square_and_line(*ANY_PLACE).set_crs(None, allow_override=True)
    square = by_name(measure_features(gdf))["square"]

    assert square["area_m2"] is None
    assert "Unknown CRS" in square["note"]


def test_unsupported_and_empty_geometries_do_not_crash():
    lon, lat = ANY_PLACE
    gdf = gpd.GeoDataFrame(
        {"name": ["collection", "empty"]},
        geometry=[GeometryCollection([Point(lon, lat)]), Polygon()],
        crs="EPSG:4326",
    )
    results = by_name(measure_features(gdf))

    assert "No measurement" in results["collection"]["note"]
    assert "Empty" in results["empty"]["note"]


def test_self_intersecting_polygon_is_repaired():
    lon, lat = ANY_PLACE
    d = 0.01  # a small shape, about 1 km across
    bow_tie = Polygon([(lon, lat), (lon + d, lat + d), (lon + d, lat), (lon, lat + d)])  # edges cross
    gdf = gpd.GeoDataFrame({"name": ["bow tie"]}, geometry=[bow_tie], crs="EPSG:4326")
    result = measure_features(gdf)[0]

    assert result["area_m2"] > 0
    assert "repaired" in result["note"]


def test_features_without_any_attributes():
    lon, lat = ANY_PLACE
    gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")  # no attribute columns
    result = measure_features(gdf)[0]

    assert result["properties"] == {}
    assert result["geometry_type"] == "Point"