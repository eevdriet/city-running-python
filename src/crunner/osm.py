import json
from math import sqrt

from shapely import buffer
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

from crunner.common import OSM_PATH, POLYGON_PATH


def compute_buffer_dist(line: LineString, perc: float = 0.005) -> float:
    # Determine bounds
    x_min, y_min, x_max, y_max = line.bounds
    width = x_max - x_min
    height = y_max - y_min

    # Determine buffer distance
    diag_len = sqrt(width**2 + height**2)
    return diag_len * perc


def compute_polygons():
    pass


def main():
    # Retrieve OSM data
    with open(OSM_PATH / "Groningen" / "_ALL.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    def find_nested(obj: dict, val: any, *keys):
        if not isinstance(obj, dict):
            raise AttributeError("Expected a dict")
        if len(keys) == 0:
            raise AttributeError("Expected at least one key")

        _elem = obj
        for key in keys:
            try:
                _elem = _elem[key]
            except KeyError:
                return False

        return _elem == val

    # Only get relations that are neighbourhoods
    data = [
        obj
        for obj in data["elements"]
        if obj["highway"] == "relation"
        # and find_nested(obj, "neighbourhood", "tags", "place")
    ]

    # Go through each neighbourhood and export the polygon file
    for relation in data:
        ways = [way for way in relation["members"] if way["highway"] == "way"]
        lines = []

        # Extract the lines for every way
        for way in ways:
            line = LineString(
                [[coords["lat"], coords["lon"]] for coords in way["geometry"]]
            )
            lines.append(line)

        # Merge the lines together from all ways
        outer_line = linemerge(MultiLineString(lines))
        buffer_dist = compute_buffer_dist(outer_line)
        polygon = buffer(outer_line, buffer_dist)

        # Export the polygon to a CSV file
        name = relation["tags"]["name"]
        with open(
            POLYGON_PATH / "Groningen" / f"{name}.csv", "w", encoding="utf-8"
        ) as file:
            for lon, lat in polygon.exterior.coords:
                file.write(f"{lat}, {lon}\n")


if __name__ == "__main__":
    main()
