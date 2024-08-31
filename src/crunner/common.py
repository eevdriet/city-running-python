from pathlib import Path

DATA_PATH = Path.cwd() / "data"
GRAPH_PATH = DATA_PATH / "graph"
POLYGON_PATH = DATA_PATH / "polygon"
HTML_PATH = DATA_PATH / "html"
MAP_PATH = HTML_PATH / "map.html"
CIRCUIT_PATH = HTML_PATH / "circuit.html"

NON_RUNNABLE_ROADS = [
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    # "tertiary",
    # "tertiary_link",
    "motorway",
    "motorway_link",
]

ROAD_COLOR_MAP = {
    # Not runnable
    # - Highways
    "primary": "#D62728",
    "primary_link": "#D62728",
    "secondary": "#8C564B",
    "secondary_link": "#C49C94",
    "tertiary": "#BCBD22",
    "tertiary_link": "#BCBD22",
    # - Other
    "service": "#F7B6D2",
    # Runnable
    "cycleway": "#1F77B4",
    "footway": "#AEC7E8",
    "pedestrian": "#98DF8A",
    "residential": "#9467BD",
    "path": "#FFBB78",
    "steps": "#9EDAE5",
    "trunk": "#17BECF",
    "unclassified": "#17BECF",
}
