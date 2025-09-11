from typing import override

import gpxpy

from crunner.common import PLOTTED_PATH
from crunner.excel.header import Header
from crunner.excel.updaters import ExcelUpdater
from crunner.gpx import find_distance


class PlottedDistanceUpdater(ExcelUpdater):
    def __init__(self, area: str, should_overwrite: bool = False):
        headers = Header.DISTANCE
        super().__init__(
            "Plotted distance", area, headers, should_overwrite=should_overwrite
        )

    @override
    def _find_new_values(self) -> list[float | None]:
        with open(self.path, "r", encoding="utf-8") as file:
            gpx = gpxpy.parse(file)

        return [find_distance(gpx, "km")]

    @override
    def find_paths(self):
        return (PLOTTED_PATH / self.area).rglob("*.gpx")
