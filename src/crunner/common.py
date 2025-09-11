from pathlib import Path

Circuit = list[tuple[int, int, any]]

__ROOT = Path(__file__).parent.parent.parent
DATA_PATH = __ROOT / ".." / "data"

CIRCUIT_PATH = DATA_PATH / "circuit"
EXCEL_PATH = DATA_PATH / "excel"
GPX_PATH = DATA_PATH / "gpx"
GRAPH_PATH = DATA_PATH / "graph"
HTML_PATH = DATA_PATH / "html"
MAP_PATH = DATA_PATH / "map"
OFFSET_PATH = DATA_PATH / "offset"
OSM_PATH = DATA_PATH / "osm"
PLOTTED_PATH = DATA_PATH / "plotted"
AREA_PATH = DATA_PATH / "area"
POLYGON_PATH = DATA_PATH / "polygon"
RUNS_PATH = DATA_PATH / "runs"
STREET_PATH = DATA_PATH / "streets"


AREA_IDS = {
    "CP": "Capelle",
    "GR": "Groningen",
    "RR": "Rotterdam",
    "RRG": "Rotterdam (gemeente)",
}


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
    "track": "#17BECF",
    "unclassified": "#17BECF",
}
