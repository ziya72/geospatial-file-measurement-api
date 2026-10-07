from pathlib import Path

from tests.helpers import PLACES, square_and_line, write_kml, write_shapefile_zip

lon, lat = PLACES["aligarh"]

shapes = square_and_line(lon, lat)

out = Path("samples")
out.mkdir(exist_ok=True)
write_kml(shapes, out / "survey.kml")
write_shapefile_zip(shapes.iloc[[0]], out, name="plots")
print("Created samples/survey.kml and samples/plots.zip")