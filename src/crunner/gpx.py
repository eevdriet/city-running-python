import math
import xml.etree.ElementTree as XMLTree
from collections import defaultdict
from itertools import chain, pairwise
from pathlib import Path
from typing import Any, Optional

import gpxpy.gpx
import networkx as nx
import send2trash
from geopy.distance import geodesic, great_circle

from crunner.common import GPX_PATH, OFFSET_PATH, PLOTTED_PATH, Circuit
from crunner.graph import Coord, Edge, find_edge_coords
from crunner.path import Paths


def strip_gpx(gpx: gpxpy.gpx.GPX) -> gpxpy.gpx.GPX:
    # Remove metadata and non-actrivity information
    gpx.metadata_extensions = []
    gpx.waypoints = []
    gpx.routes = []

    # Strip unnecessary data from tracks
    for track in gpx.tracks:
        for segment in track.segments:
            for idx, point in enumerate(segment.points):
                point.elevation = None
                point.extensions = []

                if 0 < idx < len(segment.points) - 1:
                    point.time = None

    return gpx


def add_total_distance(gpx: gpxpy.gpx.GPX, typ: str, dist: float | None = None) -> bool:
    dist = dist if dist is not None else find_distance(gpx, typ)
    if not dist:
        return False

    if typ == "m":
        dist = round(dist / 1000, 3)

    if not gpx.extensions:
        gpx.extensions = []

    if any(elem.tag == "distance" for elem in gpx.extensions):
        return False

    distance_elem = XMLTree.Element("distance")
    distance_elem.text = str(dist)
    gpx.extensions.append(distance_elem)

    return True


OFFSET = 0.00001


def offset_point(lat, lon, dx, dy):
    """
    Apply an offset (dx, dy) to a latitude and longitude coordinate.
    The offsets are in degrees of latitude and longitude.
    """
    # Approximate conversion factors (valid for small offsets)
    lat_factor = 1 / 111320  # ~1 meter per degree of latitude
    lon_factor = 1 / (
        40075000 * math.cos(math.radians(lat)) / 360
    )  # Longitude factor varies with latitude

    return lat + (dy * lat_factor), lon + (dx * lon_factor)


def get_perpendicular_vector(lat1, lon1, lat2, lon2, offset_dist=0.0001):
    """
    Computes a small perpendicular vector for an edge (lat1, lon1) → (lat2, lon2)
    and returns the offset points.
    """
    # Compute direction vector
    dx = lon2 - lon1
    dy = lat2 - lat1

    # Compute perpendicular vector (-dy, dx)
    length = math.sqrt(dx**2 + dy**2)
    if length == 0:
        return (lat1, lon1), (lat2, lon2)  # Avoid division by zero

    # Normalize and scale by offset distance
    perp_dx = (-dy / length) * offset_dist
    perp_dy = (dx / length) * offset_dist

    # Apply offset
    new_lat1, new_lon1 = offset_point(lat1, lon1, perp_dx, perp_dy)
    new_lat2, new_lon2 = offset_point(lat2, lon2, perp_dx, perp_dy)

    return (new_lat1, new_lon1), (new_lat2, new_lon2)


def to_gpx(
    circuit: Circuit,
    graph: nx.MultiDiGraph,
    path: Path,
    stats: Optional[dict[str, Any]] = None,
    edges: list = [],
):
    # Set up track
    stats = stats if stats else {}
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name=path.stem)
    gpx.tracks.append(track)

    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for idx, (src, dst, *_) in enumerate(circuit):
        coords = find_edge_coords(graph, src, dst)
        coords = coords if idx == 0 else coords[1:]

        for coord in coords:
            lat, lng = coord

            point = gpxpy.gpx.GPXTrackPoint(lat, lng)
            segment.points.append(point)

    # Add total distance information
    add_total_distance(gpx, "km")

    xml = gpx.to_xml()
    gpx_path = Paths.gpx(path)

    with open(gpx_path, "w") as file:
        file.write(xml)


def find_distance(
    gpx: gpxpy.gpx.GPX, typ: str = "km", ndecimals: int = 3
) -> float | None:
    dist = 0

    if gpx.extensions:
        for dist_elem in gpx.extensions:
            if dist_elem.text and dist_elem.tag.startswith("distance"):
                dist = float(dist_elem.text)
                if dist_elem.tag.endswith("_m") and typ == "km":
                    dist /= 1000
                elif dist_elem.tag.endswith("_km") and typ == "m":
                    dist *= 1000
    else:
        for track in gpx.tracks:
            for segment in track.segments:
                for curr, next in pairwise(segment.points):
                    coord1: Coord = curr.latitude, curr.longitude
                    coord2: Coord = next.latitude, next.longitude

                    dist += great_circle(coord1, coord2).kilometers

    return round(dist, ndecimals) if dist > 0 else None


def update_gpx():
    # Search through all plotted GPX files
    for dir in [Paths.gpx(), Paths.plotted(), Paths.runs()]:
        for path in dir.rglob("**/*.gpx"):
            with open(path, "r") as file:
                gpx = gpxpy.parse(file)

            add_total_distance(gpx, "km")

            # Verify that the name has not been set based on the file name
            if not gpx.name or gpx.name.lower().startswith("new"):
                # If so, set the name and write the GPX file
                print(f"{gpx.name} -> {path.stem}")
                gpx.name = path.stem

                xml = gpx.to_xml()
                with open(path, "w") as file:
                    file.write(xml)


def find_corrupted_gpx():
    print("Finding corrupted GPX files...")
    for path in GPX_PATH.rglob("**/*.gpx"):
        try:
            with open(path, "r") as file:
                gpxpy.parse(file)
        except:
            send2trash.send2trash(path)
            print(f"\t- {path}")


if __name__ == "__main__":
    update_gpx()
